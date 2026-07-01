import json

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import get_problems, get_problem, get_cases
from bot.keyboards.keyboards import main_menu, problems_inline, problem_detail_inline

router = Router()


async def show_problems(message: Message, session: AsyncSession):
    problems = await get_problems(session, message.from_user.id)
    if not problems:
        await message.answer(
            "⚠️ У тебя пока нет выявленных проблем.\n"
            "Попробуй режим «Разбор ситуации», чтобы выявить паттерны.",
            reply_markup=main_menu(),
        )
        return

    lines = []
    for p in sorted(problems, key=lambda x: (x.severity or 1) * (x.probability or 0), reverse=True):
        score = (p.severity or 1) * (p.probability or 0)
        status_emojis = {"выявлена": "🔍", "в_работе": "🛠", "проработана": "✅"}
        emoji = status_emojis.get(p.status, "❓")
        lines.append(
            f"{emoji} *{p.name}*\n"
            f"  Вероятность: {p.probability}% | Severity: {p.severity}/5\n"
            f"  Проявлений: {p.frequency} | Статус: {p.status}\n"
            f"  Приоритет: {score}"
        )

    await message.answer(
        "📋 *Мои проблемы*\n\n" + "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=problems_inline(problems),
    )


@router.callback_query(lambda c: c.data.startswith("problem:"))
async def on_problem_detail(callback: CallbackQuery, session: AsyncSession):
    problem_id = int(callback.data.split(":")[1])
    problem = await get_problem(session, problem_id)
    if not problem:
        await callback.message.edit_text("Проблема не найдена.")
        return

    cases = await get_cases(session, callback.from_user.id)
    linked_cases = [c for c in cases if c.id in (problem.linked_cases or [])]

    linked_problem_names = []
    for lp_id in (problem.linked_problems or []):
        lp = await get_problem(session, lp_id)
        if lp:
            linked_problem_names.append(lp.name)

    text = (
        f"🧠 *{problem.name}*\n\n"
        f"*Вероятность:* {problem.probability}%\n"
        f"*Severity:* {problem.severity}/5\n"
        f"*Проявлений:* {problem.frequency}\n"
        f"*Статус:* {problem.status}\n\n"
        f"*Описание:*\n{problem.description or 'Не добавлено'}\n"
    )

    if problem.root_cause:
        text += f"\n*Гипотеза о причине:*\n{problem.root_cause}\n"

    if linked_cases:
        text += "\n*Связанные случаи:*\n"
        for c in linked_cases[-3:]:
            text += f"• {c.situation[:100]}...\n"

    if linked_problem_names:
        text += f"\n*Связи с другими проблемами:*\n{', '.join(linked_problem_names)}\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=problem_detail_inline(problem_id))
    await callback.answer()
