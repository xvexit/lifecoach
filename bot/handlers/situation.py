import json

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_profile, get_problems, get_cases, get_plans,
    create_conversation, add_message_to_conversation, end_conversation,
    create_case, create_problem, update_problem,
)
from bot.states.states import SituationCollect, SituationConfirm
from bot.keyboards.keyboards import main_menu, yes_no_unsure
from ai.llm_client import llm_chat, llm_chat_json
from ai.prompts import build_system_prompt

router = Router()


async def start_situation_collect(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    conv = await create_conversation(session, uid, "situation_collect")
    await state.update_data(conv_id=conv.id)
    await state.set_state(SituationCollect.collecting)

    profile = await get_profile(session, uid)
    problems = await get_problems(session, uid)
    recent_cases = await get_cases(session, uid)
    plans = await get_plans(session, uid)
    plan = plans[0] if plans else None

    system = build_system_prompt(
        "situation_collect", profile, problems, plan, recent_cases,
        "Спроси пользователя, что произошло. Задавай уточняющие вопросы."
    )
    history = [{"role": "system", "content": system}]
    await state.update_data(history=history)

    prompt = "Расскажи, что случилось? Опиши ситуацию подробно."
    history.append({"role": "user", "content": prompt})
    resp = await llm_chat(history)
    history.append({"role": "assistant", "content": resp})
    await state.update_data(history=history)
    await add_message_to_conversation(session, conv.id, "assistant", resp)
    await message.answer(resp)


@router.message(SituationCollect.collecting)
async def on_situation_message(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    history: list = data.get("history", [])
    conv_id = data.get("conv_id")

    await add_message_to_conversation(session, conv_id, "user", message.text)
    history.append({"role": "user", "content": message.text})

    system = build_system_prompt(
        "situation_collect",
        await get_profile(session, message.from_user.id),
        await get_problems(session, message.from_user.id),
        None,
        await get_cases(session, message.from_user.id),
        "Если информации достаточно для анализа, ответь: 'готово'. "
        "Иначе задай следующий уточняющий вопрос."
    )
    history[0] = {"role": "system", "content": system}

    resp = await llm_chat(history, temperature=0.5)
    history.append({"role": "assistant", "content": resp})
    await add_message_to_conversation(session, conv_id, "assistant", resp)
    await state.update_data(history=history)

    if "готово" in resp.lower():
        await end_conversation(session, conv_id)
        await analyze_situation(message, state, session)
    else:
        await message.answer(resp)


async def analyze_situation(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    data = await state.get_data()
    history: list = data.get("history", [])

    profile = await get_profile(session, uid)
    problems = await get_problems(session, uid)
    recent_cases = await get_cases(session, uid)

    system = build_system_prompt(
        "situation_analyze", profile, problems, None, recent_cases,
        "Проанализируй ситуацию. Верни JSON с ключами: analysis, identified_problems, case_data.",
    )

    messages = [{"role": "system", "content": system}]
    for m in history:
        messages.append(m)

    result = await llm_chat_json(messages)

    analysis = result.get("analysis", "")
    identified = result.get("identified_problems", [])
    case_data = result.get("case_data", {})

    await state.update_data(
        analysis=analysis,
        identified_problems=identified,
        case_data=case_data,
    )
    await state.set_state(SituationConfirm.waiting_confirm)

    await message.answer(
        f"📊 **Анализ ситуации**\n\n{analysis}\n\n"
        + ("_" if identified else "Проблем не выявлено.")
    )

    if identified:
        lines = []
        for p in identified:
            lines.append(f"• {p.get('name', '?')} — {p.get('probability', 0)}%")
        await message.answer(
            "Возможные проблемы:\n" + "\n".join(lines) + "\n\nДобавить в карту проблем?",
            reply_markup=yes_no_unsure(),
        )


@router.message(SituationConfirm.waiting_confirm)
async def on_confirm(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    uid = message.from_user.id

    if message.text == "Да":
        case_data = data.get("case_data", {})
        identified = data.get("identified_problems", [])

        case = await create_case(
            session, uid,
            situation=case_data.get("situation", ""),
            emotions=case_data.get("emotions", ""),
            thoughts=case_data.get("thoughts", ""),
            behavior=case_data.get("behavior", ""),
            trigger=case_data.get("trigger", ""),
            source="режим 1",
        )

        linked_ids = []
        for ip in identified:
            name = ip.get("name", "")
            prob = ip.get("probability", 0)
            existing_problems = await get_problems(session, uid)
            existing = [p for p in existing_problems if p.name.lower() == name.lower()]
            if existing:
                problem = existing[0]
                new_prob = max(problem.probability, prob)
                new_freq = (problem.frequency or 0) + 1
                linked_cases = list(problem.linked_cases or [])
                if case.id not in linked_cases:
                    linked_cases.append(case.id)
                await update_problem(
                    session, problem.id,
                    probability=new_prob,
                    frequency=new_freq,
                    linked_cases=linked_cases,
                    linked_problems=linked_ids if linked_ids else problem.linked_problems,
                )
                linked_ids.append(problem.id)
            else:
                problem = await create_problem(
                    session, uid,
                    name=name,
                    probability=prob,
                    frequency=1,
                    linked_cases=[case.id],
                    severity=min(5, max(1, prob // 20)),
                )
                linked_ids.append(problem.id)

        if linked_ids:
            await update_problem(session, linked_ids[0], linked_problems=linked_ids[1:])

        await message.answer(
            "✅ Ситуация сохранена. Проблемы обновлены.",
            reply_markup=main_menu(),
        )
    elif message.text == "Не уверен":
        await message.answer(
            "Хорошо, я сохранил анализ. Если захочешь — сможешь вернуться позже.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "Понял, не сохраняю. Если захочешь — возвращайся.",
            reply_markup=main_menu(),
        )

    await state.clear()
