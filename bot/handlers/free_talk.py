import json

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_profile, get_cases, get_problems,
    create_conversation, add_message_to_conversation, end_conversation,
    create_case, create_problem, update_problem,
)
from bot.states.states import FreeTalk
from bot.keyboards.keyboards import main_menu, make_conclusion_keyboard, yes_no_unsure
from ai.llm_client import llm_chat, llm_chat_json
from ai.prompts import build_system_prompt

router = Router()


async def start_free_talk(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    conv = await create_conversation(session, uid, "free_talk")
    await state.update_data(conv_id=conv.id)
    await state.set_state(FreeTalk.talking)

    profile = await get_profile(session, uid)
    problems = await get_problems(session, uid)
    recent_cases = await get_cases(session, uid)

    system = build_system_prompt("free_talk", profile, problems, None, recent_cases)
    history = [{"role": "system", "content": system}]
    await state.update_data(history=history)

    resp = await llm_chat(history + [
        {"role": "user", "content": "Начни диалог. Спроси, что пользователь хочет обсудить."}
    ])
    history.append({"role": "assistant", "content": resp})
    await state.update_data(history=history)
    await add_message_to_conversation(session, conv.id, "assistant", resp)
    await message.answer(resp, reply_markup=make_conclusion_keyboard())


@router.message(FreeTalk.talking)
async def on_free_message(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    history: list = data.get("history", [])
    conv_id = data.get("conv_id")

    if message.text == "Сделать вывод":
        await make_conclusion(message, state, session)
        return

    await add_message_to_conversation(session, conv_id, "user", message.text)
    history.append({"role": "user", "content": message.text})

    profile = await get_profile(session, message.from_user.id)
    problems = await get_problems(session, message.from_user.id)
    recent_cases = await get_cases(session, message.from_user.id)
    system = build_system_prompt("free_talk", profile, problems, None, recent_cases)
    history[0] = {"role": "system", "content": system}

    resp = await llm_chat(history)
    history.append({"role": "assistant", "content": resp})
    await add_message_to_conversation(session, conv_id, "assistant", resp)
    await state.update_data(history=history)
    await message.answer(resp, reply_markup=make_conclusion_keyboard())


async def make_conclusion(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    history: list = data.get("history", [])
    conv_id = data.get("conv_id")

    if conv_id:
        await end_conversation(session, conv_id)

    uid = message.from_user.id
    profile = await get_profile(session, uid)
    problems = await get_problems(session, uid)
    recent_cases = await get_cases(session, uid)

    system = build_system_prompt("situation_analyze", profile, problems, None, recent_cases)

    messages = [{"role": "system", "content": system}]
    for m in history:
        messages.append(m)

    result = await llm_chat_json(messages)

    analysis = result.get("analysis", "")
    identified = result.get("identified_problems", [])
    case_data = result.get("case_data", {})

    await message.answer(
        f"📊 *Анализ сессии*\n\n{analysis}",
        parse_mode="Markdown",
    )

    if identified:
        lines = [f"• {p.get('name', '?')} — {p.get('probability', 0)}%" for p in identified]
        await message.answer(
            "Возможные проблемы:\n" + "\n".join(lines) + "\n\nДобавить в карту проблем?",
            reply_markup=yes_no_unsure(),
        )
        await state.update_data(
            case_data=case_data,
            identified_problems=identified,
        )
    else:
        await state.clear()
        await message.answer("Вывод сделан. Возвращайся в любое время!", reply_markup=main_menu())


@router.message(F.text.in_({"Да", "Нет", "Не уверен"}))
async def on_confirm_from_free(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    identified = data.get("identified_problems")
    if not identified:
        return

    uid = message.from_user.id
    if message.text == "Да":
        case_data = data.get("case_data", {})

        case = await create_case(
            session, uid,
            situation=case_data.get("situation", ""),
            emotions=case_data.get("emotions", ""),
            thoughts=case_data.get("thoughts", ""),
            behavior=case_data.get("behavior", ""),
            trigger=case_data.get("trigger", ""),
            source="режим 5",
        )

        for ip in identified:
            name = ip.get("name", "")
            prob = ip.get("probability", 0)
            existing_problems = await get_problems(session, uid)
            existing = [p for p in existing_problems if p.name.lower() == name.lower()]
            if existing:
                problem = existing[0]
                linked_cases = list(problem.linked_cases or [])
                if case.id not in linked_cases:
                    linked_cases.append(case.id)
                await update_problem(
                    session, problem.id,
                    probability=max(problem.probability, prob),
                    frequency=(problem.frequency or 0) + 1,
                    linked_cases=linked_cases,
                )
            else:
                await create_problem(
                    session, uid,
                    name=name,
                    probability=prob,
                    frequency=1,
                    linked_cases=[case.id],
                    severity=min(5, max(1, prob // 20)),
                )

        await message.answer("✅ Сохранено.", reply_markup=main_menu())
    else:
        await message.answer("Понял.", reply_markup=main_menu())

    await state.clear()
