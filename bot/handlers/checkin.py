from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_profile, get_problems, get_plans, get_cases,
    create_mood_log, create_conversation, add_message_to_conversation, end_conversation,
)
from bot.states.states import CheckIn
from bot.keyboards.keyboards import main_menu, scale_1_10, yes_no, done_keyboard
from ai.llm_client import llm_chat
from ai.prompts import build_system_prompt

router = Router()


async def start_checkin(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    conv = await create_conversation(session, uid, "checkin")
    await state.update_data(conv_id=conv.id)

    profile = await get_profile(session, uid)
    problems = await get_problems(session, uid)
    plans = await get_plans(session, uid)

    await state.set_state(CheckIn.mood)
    await message.answer(
        "🧘‍♂️ *Чек-ин*\n\nОцени своё настроение прямо сейчас (1-10):",
        parse_mode="Markdown",
        reply_markup=scale_1_10(),
    )
    await add_message_to_conversation(session, conv.id, "assistant", "Оцени настроение 1-10")


@router.message(CheckIn.mood)
async def on_mood(message: Message, state: FSMContext, session: AsyncSession):
    try:
        mood = int(message.text.strip())
        if mood < 1 or mood > 10:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, выбери число от 1 до 10:", reply_markup=scale_1_10())
        return

    await state.update_data(mood=mood)

    data = await state.get_data()
    conv_id = data.get("conv_id")
    await add_message_to_conversation(session, conv_id, "user", f"Настроение: {mood}")

    uid = message.from_user.id
    problems = await get_problems(session, uid)
    active = [p for p in problems if p.status in ("выявлена", "в_работе")]

    if active:
        await state.set_state(CheckIn.situations)
        names = "\n".join(f"• {p.name}" for p in active[:5])
        await message.answer(
            f"Были ли сегодня ситуации, связанные с этими темами?\n{names}",
            reply_markup=yes_no(),
        )
    else:
        await state.update_data(situations="нет")
        await ask_tasks(message, state, session)


@router.message(CheckIn.situations)
async def on_situations(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(situations=message.text)
    data = await state.get_data()
    conv_id = data.get("conv_id")
    await add_message_to_conversation(session, conv_id, "user", f"Ситуации: {message.text}")
    await ask_tasks(message, state, session)


async def ask_tasks(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    plans = await get_plans(session, uid)
    active_tasks = []
    for p in plans:
        tasks = p.tasks or []
        for t in tasks:
            if t.get("status") != "done":
                active_tasks.append(t)

    if active_tasks:
        await state.update_data(active_tasks=active_tasks, plan=plans[0] if plans else None)
        await state.set_state(CheckIn.tasks)
        lines = []
        for i, t in enumerate(active_tasks[:5], 1):
            lines.append(f"{i}. {t.get('description', '—')}")
        await message.answer(
            "Активные задачи:\n" + "\n".join(lines) + "\n\n"
            "Какие выполнил? Напиши номера через запятую или «ничего»:"
        )
    else:
        await finish_checkin(message, state, session)


@router.message(CheckIn.tasks)
async def on_tasks(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    await add_message_to_conversation(session, conv_id, "user", f"Задачи: {message.text}")

    # parse completed tasks
    completed = []
    for part in message.text.replace(",", " ").split():
        try:
            idx = int(part) - 1
            active = data.get("active_tasks", [])
            if 0 <= idx < len(active):
                completed.append(active[idx].get("description", ""))
        except ValueError:
            pass

    await state.update_data(tasks_completed=completed)

    if completed:
        await message.answer(
            f"Отлично! Молодец! ✅ Выполнено: {', '.join(completed[:3])}",
        )
    else:
        await message.answer(
            "Ничего страшного. Расскажи, что помешало? "
            "Может, стоит скорректировать задачи?",
        )

    await finish_checkin(message, state, session)


async def finish_checkin(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")

    mood = data.get("mood", 5)
    completed = data.get("tasks_completed", [])

    await create_mood_log(
        session, message.from_user.id,
        mood=mood,
        note=data.get("situations", ""),
        tasks_completed=completed,
    )

    if conv_id:
        await end_conversation(session, conv_id)

    # update plan progress
    plan = data.get("plan")
    if plan and completed:
        tasks = plan.tasks or []
        for t in tasks:
            if t.get("description") in completed:
                t["status"] = "done"
        done_count = sum(1 for t in tasks if t.get("status") == "done")
        plan.progress = min(100, int(done_count / max(len(tasks), 1) * 100))
        from db.crud import update_plan
        await update_plan(session, plan.id, tasks=tasks, progress=plan.progress)

    await state.clear()
    await message.answer(
        "✅ Чек-ин завершён! Хорошего дня 🌟",
        reply_markup=main_menu(),
    )
