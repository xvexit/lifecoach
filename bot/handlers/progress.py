from datetime import datetime, timedelta

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import get_problems, get_mood_logs, get_plans

router = Router()


async def show_progress(message: Message, session: AsyncSession):
    uid = message.from_user.id
    problems = await get_problems(session, uid)
    mood_logs = await get_mood_logs(session, uid, limit=30)
    plans = await get_plans(session, uid)

    # Problem stats
    total = len(problems)
    identified = sum(1 for p in problems if p.status == "выявлена")
    in_work = sum(1 for p in problems if p.status == "в_работе")
    done = sum(1 for p in problems if p.status == "проработана")

    # Mood chart
    if mood_logs:
        logs = list(reversed(mood_logs))
        dates_part = [l.date.strftime("%d.%m") if hasattr(l.date, "strftime") else str(l.date)[:10] for l in logs[-14:]]
        moods = [l.mood for l in logs[-14:]]

        emoji_chart = []
        for m in moods:
            if m <= 3:
                emoji_chart.append("🟥")
            elif m <= 5:
                emoji_chart.append("🟧")
            elif m <= 7:
                emoji_chart.append("🟨")
            else:
                emoji_chart.append("🟩")

        chart_line = "".join(emoji_chart)
        date_line = " ".join(dates_part)

        # Trend (last 7 days vs previous 7)
        if len(moods) >= 7:
            last_week = moods[-7:]
            prev_week = moods[-14:-7] if len(moods) >= 14 else moods[:7]
            avg_last = sum(last_week) / len(last_week)
            avg_prev = sum(prev_week) / len(prev_week) if prev_week else avg_last
            if avg_last > avg_prev + 0.5:
                trend = "📈 Растёт"
            elif avg_last < avg_prev - 0.5:
                trend = "📉 Падает"
            else:
                trend = "➡️ Стабильно"
        else:
            trend = "➡️ Недостаточно данных"

        current_streak = 0
        for log in reversed(logs):
            log_date = log.date.date() if hasattr(log.date, "date") else log.date
            if isinstance(log_date, str):
                log_date = datetime.fromisoformat(log_date).date()
            expected = datetime.utcnow().date() - timedelta(days=current_streak)
            if log_date == expected:
                current_streak += 1
            else:
                break

        streak_text = f"🔥 {current_streak} дней подряд" if current_streak > 0 else "Начни серию сегодня!"
    else:
        chart_line = "Нет данных"
        date_line = ""
        trend = "Нет данных"
        streak_text = "Нет данных"

    # Tasks done
    total_tasks = 0
    done_tasks = 0
    for p in plans:
        tasks = p.tasks or []
        total_tasks += len(tasks)
        done_tasks += sum(1 for t in tasks if t.get("status") == "done")

    text = (
        "📊 *Мой прогресс*\n\n"
        "*📈 Настроение (последние 14 дней):*\n"
        f"{chart_line}\n"
        f"{date_line}\n"
        f"Тренд: {trend}\n"
        f"{streak_text}\n\n"
        "*🧠 Проблемы:*\n"
        f"Всего: {total}\n"
        f"🔍 Выявлено: {identified}\n"
        f"🛠 В работе: {in_work}\n"
        f"✅ Проработано: {done}\n\n"
        "*📋 Задачи:*\n"
        f"Выполнено: {done_tasks} / {total_tasks}\n"
    )

    await message.answer(text, parse_mode="Markdown")
