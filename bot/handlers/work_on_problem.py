import json

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import get_problems, get_problem, update_problem, create_plan, update_plan
from bot.states.states import WorkOnProblem
from bot.keyboards.keyboards import (
    main_menu, problems_inline, confirm_plan_keyboard, cancel_keyboard,
)
from ai.llm_client import llm_chat, llm_chat_json
from ai.prompts import build_system_prompt

router = Router()


async def start_work_on_problem(message: Message, state: FSMContext, session: AsyncSession):
    problems = await get_problems(session, message.from_user.id)
    active = [p for p in problems if p.status == "выявлена" and (p.probability or 0) >= 60]
    if not active:
        await message.answer(
            "Нет проблем, готовых к проработке (статус «выявлена», вероятность ≥ 60%).\n"
            "Сначала выяви проблемы через «Разбор ситуации».",
            reply_markup=main_menu(),
        )
        return

    await state.set_state(WorkOnProblem.choosing)
    await message.answer(
        "Выбери проблему для работы:",
        reply_markup=problems_inline(active, prefix="work"),
    )


@router.callback_query(lambda c: c.data.startswith("work:"))
async def on_choose_problem(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    problem_id = int(callback.data.split(":")[1])
    problem = await get_problem(session, problem_id)
    if not problem:
        await callback.message.edit_text("Проблема не найдена.")
        return

    await state.update_data(problem_id=problem_id)
    await state.set_state(WorkOnProblem.discussing)

    profile = await get_profiles(session, callback.from_user.id)
    problems = await get_problems(session, callback.from_user.id)

    system = build_system_prompt(
        "work_on_problem", profile, problems, None, None,
        f"Обсуждаем проблему: {problem.name}. "
        "Спроси пользователя об истории проблемы, как она проявляется. "
        "После обсуждения предложи план проработки и верни JSON с планом."
    )

    user_msg = f"Давай обсудим проблему «{problem.name}»."
    history = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]
    await state.update_data(history=history)

    resp = await llm_chat(history)
    history.append({"role": "assistant", "content": resp})
    await state.update_data(history=history)

    await callback.message.edit_text(resp)
    await callback.message.answer(
        "Если хочешь предложить свой план — напиши. Или нажми «Согласен», когда будешь готов.",
        reply_markup=confirm_plan_keyboard(),
    )
    await callback.answer()


@router.message(WorkOnProblem.discussing)
async def on_discuss(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    history: list = data.get("history", [])
    history.append({"role": "user", "content": message.text})

    resp = await llm_chat(history)
    history.append({"role": "assistant", "content": resp})
    await state.update_data(history=history)

    await message.answer(resp, reply_markup=confirm_plan_keyboard())


@router.message(WorkOnProblem.discussing, F.text == "Согласен")
async def on_plan_agree(message: Message, state: FSMContext, session: AsyncSession):
    await _save_plan(message, state, session)


@router.message(WorkOnProblem.discussing, F.text == "Скорректировать")
async def on_plan_adjust(message: Message, state: FSMContext, session: AsyncSession):
    await message.answer("Напиши, что нужно изменить в плане:")
    await state.set_state(WorkOnProblem.plan_review)


@router.message(WorkOnProblem.plan_review)
async def on_plan_review(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    history: list = data.get("history", [])
    history.append({"role": "user", "content": f"Скорректируй план: {message.text}"})

    resp = await llm_chat(history)
    history.append({"role": "assistant", "content": resp})
    await state.update_data(history=history)

    await message.answer(resp, reply_markup=confirm_plan_keyboard())
    await state.set_state(WorkOnProblem.discussing)


@router.message(WorkOnProblem.discussing, F.text == "Отменить")
async def on_plan_cancel(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    await message.answer("Работа над проблемой отменена.", reply_markup=main_menu())


async def _save_plan(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    problem_id = data.get("problem_id")
    history: list = data.get("history", [])

    system = build_system_prompt(
        "work_on_problem",
        await get_profiles(session, message.from_user.id),
        await get_problems(session, message.from_user.id),
        None, None,
        "Извлеки из обсуждения план проработки. Верни JSON с ключами: "
        "approach (строка), tasks (массив {description, deadline, status}), "
        "habits (массив {description, frequency, status}).",
    )

    plan_messages = [{"role": "system", "content": system}] + history
    plan_data = await llm_chat_json(plan_messages)

    plan = await create_plan(
        session, message.from_user.id,
        linked_problem_id=problem_id,
        tasks=plan_data.get("tasks", []),
        habits=plan_data.get("habits", []),
        approach=plan_data.get("approach", ""),
    )

    await update_problem(session, problem_id, status="в_работе")

    await state.clear()
    await message.answer(
        f"✅ План сохранён! Подход: {plan.approach}\n"
        f"Задач: {len(plan.tasks or [])}, привычек: {len(plan.habits or [])}\n"
        f"Статус проблемы изменён на «в работе».",
        reply_markup=main_menu(),
    )


async def get_profiles(session, user_id):
    from db.crud import get_profile
    return await get_profile(session, user_id)
