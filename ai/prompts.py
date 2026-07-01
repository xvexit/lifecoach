import json
from typing import Optional

from db.models import Profile, Case, Problem, Plan


def build_system_prompt(
    mode: str,
    profile: Optional[Profile] = None,
    problems: Optional[list[Problem]] = None,
    plan: Optional[Plan] = None,
    recent_cases: Optional[list[Case]] = None,
    extra: Optional[str] = None,
) -> str:
    parts = ["Ты — AI-психолог PsyBot. Отвечай на русском языке. Будь эмпатичным, поддерживающим, профессиональным."]

    profile_data = {}
    if profile:
        profile_data = {
            "basic_info": profile.basic_info or {},
            "onboarding_level": profile.onboarding_level,
            "emotional_profile": profile.emotional_profile or {},
            "relationships_profile": profile.relationships_profile or {},
            "primary_pain": profile.primary_pain or "",
            "desired_change": profile.desired_change or "",
            "goal": profile.goal or "",
        }
        if profile.childhood:
            profile_data["childhood"] = profile.childhood
        if profile.core_beliefs:
            profile_data["core_beliefs"] = profile.core_beliefs
        if profile.deep_profile:
            profile_data["deep_profile"] = profile.deep_profile

    if profile_data:
        parts.append(f"Данные профиля пользователя: {json.dumps(profile_data, ensure_ascii=False)}")

    if problems:
        problems_data = [
            {"id": p.id, "name": p.name, "probability": p.probability, "status": p.status, "severity": p.severity}
            for p in problems
        ]
        parts.append(f"Текущие проблемы: {json.dumps(problems_data, ensure_ascii=False)}")

    if plan:
        plan_data = {
            "id": plan.id,
            "tasks": plan.tasks,
            "habits": plan.habits,
            "approach": plan.approach or "",
            "progress": plan.progress,
        }
        parts.append(f"Текущий план: {json.dumps(plan_data, ensure_ascii=False)}")

    if recent_cases:
        cases_data = [
            {"id": c.id, "situation": c.situation, "emotions": c.emotions,
             "thoughts": c.thoughts, "trigger": c.trigger}
            for c in recent_cases[-5:]
        ]
        parts.append(f"Последние случаи: {json.dumps(cases_data, ensure_ascii=False)}")

    mode_instructions = {
        "onboarding": (
            "Режим: онбординг. Задавай вопросы по очереди. "
            "После каждого ответа подтверждай и задавай следующий. "
            "Будь дружелюбным и располагающим."
        ),
        "situation_collect": (
            "Режим: сбор информации о ситуации. "
            "Задавай уточняющие вопросы: что произошло, что чувствовал, какие мысли были, "
            "как поступил, что триггернуло. "
            "После каждого ответа задавай следующий вопрос. "
            "Когда информации достаточно, скажи 'готово'."
        ),
        "situation_analyze": (
            "Режим: анализ ситуации. Проанализируй ситуацию с точки зрения психологии. "
            "Верни JSON с ключами: analysis (текст для пользователя), "
            "identified_problems (массив объектов с name, probability, reasoning), "
            "case_data (объект с situation, emotions, thoughts, behavior, trigger)."
        ),
        "problems_list": "Режим: список проблем. Ответь на вопросы пользователя о его проблемах.",
        "work_on_problem": (
            "Режим: работа над проблемой. Обсуждай выбранную проблему: "
            "откуда она, как проявляется. Предложи план проработки: "
            "поведенческие задачи, привычки, ментальные упражнения, дневниковые практики. "
            "После обсуждения верни JSON с планом."
        ),
        "checkin": (
            "Режим: чек-ин. Спроси о настроении (1-10), были ли ситуации, "
            "связанные с проблемами, проверь выполнение задач. "
            "Хвали за выполнение, без осуждения за невыполнение."
        ),
        "free_talk": (
            "Режим: свободный диалог. Слушай и поддерживай. "
            "Не обновляй базу автоматически. "
            "Если пользователь просит 'сделать вывод', проанализируй сессию."
        ),
        "progress": "Режим: прогресс. Ответь на вопросы о динамике и прогрессе.",
    }

    parts.append(mode_instructions.get(mode, ""))
    if extra:
        parts.append(extra)

    return "\n\n".join(parts)
