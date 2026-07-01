from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import get_profile, update_profile, create_conversation, add_message_to_conversation, end_conversation
from bot.states.states import Onboarding, OnboardingLevel2, OnboardingLevel3
from bot.keyboards.keyboards import (
    main_menu, scale_1_5, scale_1_10, yes_no,
    multi_choice_emotions, multi_choice_triggers, multi_choice_stress,
    skip_keyboard, done_keyboard, cancel_keyboard,
)
from ai.llm_client import llm_chat
from ai.prompts import build_system_prompt

router = Router()

ONBOARDING_QUESTIONS = {
    "q_age": "Сколько тебе лет?",
    "q_occupation": "Чем занимаешься? (работа/учёба)",
    "q_living": "Живёшь один, с партнёром или с родителями?",
    "q_pain": "Что тебя больше всего напрягает в жизни прямо сейчас?",
    "q_change": "Если бы мог изменить одну вещь в себе — что бы это было?",
    "q_emotions": "Какие эмоции испытываешь чаще всего? (выбирай, в конце нажми ✅ Готово)",
    "q_triggers": "В каких ситуациях чувствуешь себя хуже всего? (выбирай, в конце нажми ✅ Готово)",
    "q_stress": "Как обычно реагируешь на стресс? (выбирай, в конце нажми ✅ Готово)",
    "q_assertiveness": "Легко ли тебе говорить нет? (оцени по шкале 1-5)",
    "q_help": "Легко ли тебе просить о помощи? (1-5)",
    "q_people_pleasing": "Часто ли подстраиваешься под других в ущерб себе? (1-5)",
    "q_trust": "Есть ли человек, которому доверяешь полностью?",
    "q_goal": "Зачем начал пользоваться этим ботом?",
}

ONBOARDING_2_QUESTIONS = {
    "q_childhood_family": "Расскажи о своей семье в детстве. Какие были отношения с родителями?",
    "q_childhood_relationship": "Как складывались отношения с близкими в детстве? Чувствовал ли ты поддержку?",
    "q_core_belief_self": "Какое у тебя базовое убеждение о себе? Например: «я недостаточно хорош», «я справлюсь»...",
    "q_core_belief_others": "Какое у тебя базовое убеждение о других людях?",
    "q_core_belief_world": "Какое у тебя базовое убеждение о мире в целом?",
    "q_repeating_pattern": "Замечаешь ли повторяющиеся сценарии в своей жизни? Какие?",
}

ONBOARDING_3_QUESTIONS = {
    "q_romantic_pattern": "Расскажи о своих паттернах в романтических отношениях. Что повторяется?",
    "q_self_esteem": "Как у тебя с самооценкой? Как ты оцениваешь себя?",
    "q_psychosomatic": "Замечаешь ли телесные симптомы при стрессе? (головные боли, напряжение, проблемы со сном...)",
    "q_values": "Какие ценности для тебя важны? Что для тебя действительно значимо в жизни?",
    "q_boundaries": "Как у тебя с личными границами? Умеешь ли их отстаивать?",
}


def get_question_keyboard(field: str):
    if field in ("q_assertiveness", "q_help", "q_people_pleasing"):
        return scale_1_5()
    if field == "q_trust":
        return yes_no()
    if field == "q_emotions":
        return multi_choice_emotions()
    if field == "q_triggers":
        return multi_choice_triggers()
    if field == "q_stress":
        return multi_choice_stress()
    return None


SAVED_EMOTIONS: dict[int, list[str]] = {}
SAVED_TRIGGERS: dict[int, list[str]] = {}
SAVED_STRESS: dict[int, list[str]] = {}

ONBOARDING_FIELDS = list(ONBOARDING_QUESTIONS.keys())


async def start_onboarding(message: Message, state: FSMContext, session: AsyncSession):
    await update_profile(session, message.from_user.id, onboarding_level=1)
    conv = await create_conversation(session, message.from_user.id, "onboarding")
    await state.update_data(conv_id=conv.id)
    await state.set_state(Onboarding.q_age)
    await message.answer(
        "👋 Привет! Я — PsyBot, твой AI-психолог.\n"
        "Давай познакомимся. Я задам несколько вопросов, это займёт 10-15 минут.\n"
        "Отвечай честно — это поможет мне лучше тебя понять.\n\n"
        "Начнём!",
        reply_markup=cancel_keyboard(),
    )
    await ask_question(message, state, "q_age", session)


async def ask_question(message: Message, state: FSMContext, field: str, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id:
        await add_message_to_conversation(session, conv_id, "assistant", ONBOARDING_QUESTIONS.get(field, ""))
    kb = get_question_keyboard(field)
    await message.answer(ONBOARDING_QUESTIONS[field], reply_markup=kb)


@router.message(Onboarding.q_age)
async def on_age(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_age", "basic_info", {"age": message.text})


@router.message(Onboarding.q_occupation)
async def on_occupation(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_occupation", "basic_info", {"occupation": message.text})


@router.message(Onboarding.q_living)
async def on_living(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_living", "basic_info", {"living_situation": message.text})


@router.message(Onboarding.q_pain)
async def on_pain(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_pain", "primary_pain", message.text)


@router.message(Onboarding.q_change)
async def on_change(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_change", "desired_change", message.text)


@router.message(Onboarding.q_emotions)
async def on_emotions(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    if uid not in SAVED_EMOTIONS:
        SAVED_EMOTIONS[uid] = []
    text = message.text.strip()
    if text == "✅ Готово":
        val = SAVED_EMOTIONS.pop(uid, [])
        await save_and_next(message, state, session, "q_emotions", "emotional_profile", {"frequent_emotions": val})
    else:
        if text not in SAVED_EMOTIONS[uid]:
            SAVED_EMOTIONS[uid].append(text)
        await message.answer(f"➕ Добавлено. Выбрано: {', '.join(SAVED_EMOTIONS[uid])}\nНажми ✅ Готово, чтобы продолжить.")


@router.message(Onboarding.q_triggers)
async def on_triggers(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    if uid not in SAVED_TRIGGERS:
        SAVED_TRIGGERS[uid] = []
    text = message.text.strip()
    if text == "✅ Готово":
        val = SAVED_TRIGGERS.pop(uid, [])
        await save_and_next(message, state, session, "q_triggers", "emotional_profile", {"trigger_situations": val})
    else:
        if text not in SAVED_TRIGGERS[uid]:
            SAVED_TRIGGERS[uid].append(text)
        await message.answer(f"➕ Добавлено. Выбрано: {', '.join(SAVED_TRIGGERS[uid])}\nНажми ✅ Готово, чтобы продолжить.")


@router.message(Onboarding.q_stress)
async def on_stress(message: Message, state: FSMContext, session: AsyncSession):
    uid = message.from_user.id
    if uid not in SAVED_STRESS:
        SAVED_STRESS[uid] = []
    text = message.text.strip()
    if text == "✅ Готово":
        val = SAVED_STRESS.pop(uid, [])
        await save_and_next(message, state, session, "q_stress", "emotional_profile", {"stress_response": val})
    else:
        if text not in SAVED_STRESS[uid]:
            SAVED_STRESS[uid].append(text)
        await message.answer(f"➕ Добавлено. Выбрано: {', '.join(SAVED_STRESS[uid])}\nНажми ✅ Готово, чтобы продолжить.")


@router.message(Onboarding.q_assertiveness)
async def on_assertiveness(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(
        message, state, session, "q_assertiveness", "relationships_profile",
        {"assertiveness": int(message.text)}
    )


@router.message(Onboarding.q_help)
async def on_help(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(
        message, state, session, "q_help", "relationships_profile",
        {"asking_help": int(message.text)}
    )


@router.message(Onboarding.q_people_pleasing)
async def on_people_pleasing(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(
        message, state, session, "q_people_pleasing", "relationships_profile",
        {"people_pleasing": int(message.text)}
    )


@router.message(Onboarding.q_trust)
async def on_trust(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_trust", "relationships_profile", {"has_trusted_person": message.text == "Да"})


@router.message(Onboarding.q_goal)
async def on_goal(message: Message, state: FSMContext, session: AsyncSession):
    await save_and_next(message, state, session, "q_goal", "goal", message.text, is_last=True)


async def save_and_next(
    message: Message, state: FSMContext, session: AsyncSession,
    field: str, profile_key: str, profile_value, is_last: bool = False,
):
    uid = message.from_user.id
    data = await state.get_data()
    conv_id = data.get("conv_id")

    if conv_id:
        await add_message_to_conversation(session, conv_id, "user", message.text)

    if profile_key in ("basic_info", "emotional_profile", "relationships_profile"):
        existing = {}
        profile = await get_profile(session, uid)
        if profile:
            existing = getattr(profile, profile_key, {}) or {}
        if isinstance(existing, dict) and isinstance(profile_value, dict):
            existing.update(profile_value)
        await update_profile(session, uid, **{profile_key: existing})
    else:
        await update_profile(session, uid, **{profile_key: profile_value})

    if is_last:
        await finish_onboarding(message, state, session)
        return

    current_idx = ONBOARDING_FIELDS.index(field)
    if current_idx + 1 < len(ONBOARDING_FIELDS):
        next_field = ONBOARDING_FIELDS[current_idx + 1]
        next_state = getattr(Onboarding, next_field)
        await state.set_state(next_state)
        await ask_question(message, state, next_field, session)


async def finish_onboarding(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id:
        await end_conversation(session, conv_id)
    await state.clear()
    await update_profile(session, message.from_user.id, onboarding_level=1)
    await message.answer(
        "🎉 Спасибо за ответы! Онбординг пройден.\n"
        "Через 2-3 дня я предложу продолжить знакомство.\n\n"
        "А пока — давай работать! Выбирай режим в меню.",
        reply_markup=main_menu(),
    )


@router.message(lambda m: m.text == "Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu())


# --- Level 2 ---
async def start_onboarding_level2(message: Message, state: FSMContext, session: AsyncSession):
    await update_profile(session, message.from_user.id, onboarding_level=2)
    conv = await create_conversation(session, message.from_user.id, "onboarding_l2")
    await state.update_data(conv_id=conv.id)
    await state.set_state(OnboardingLevel2.q_childhood_family)
    await message.answer(
        "📋 Онбординг, уровень 2. Поговорим о детстве и убеждениях.\n"
        "Это может быть непросто — ты можешь отвечать в комфортном темпе.",
        reply_markup=skip_keyboard(),
    )
    await _ask_l2(message, state, "q_childhood_family")


L2_FIELDS = list(ONBOARDING_2_QUESTIONS.keys())
L2_STORAGE_KEY = "childhood"


async def _ask_l2(message: Message, state: FSMContext, field: str):
    await message.answer(ONBOARDING_2_QUESTIONS[field], reply_markup=skip_keyboard())


@router.message(OnboardingLevel2.q_childhood_family)
async def on_l2_q1(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_childhood_family")


@router.message(OnboardingLevel2.q_childhood_relationship)
async def on_l2_q2(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_childhood_relationship")


@router.message(OnboardingLevel2.q_core_belief_self)
async def on_l2_q3(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_core_belief_self", key="core_beliefs")


@router.message(OnboardingLevel2.q_core_belief_others)
async def on_l2_q4(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_core_belief_others", key="core_beliefs")


@router.message(OnboardingLevel2.q_core_belief_world)
async def on_l2_q5(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_core_belief_world", key="core_beliefs")


@router.message(OnboardingLevel2.q_repeating_pattern)
async def on_l2_q6(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l2_and_next(message, state, session, "q_repeating_pattern", is_last=True)


async def _save_l2_and_next(
    message: Message, state: FSMContext, session: AsyncSession,
    field: str, key: str = "childhood", is_last: bool = False,
):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id and message.text != "Пропустить":
        await add_message_to_conversation(session, conv_id, "user", message.text)

    existing = {}
    profile = await get_profile(session, message.from_user.id)
    if profile:
        existing_val = getattr(profile, key, {}) or {}
        if isinstance(existing_val, dict):
            existing = existing_val

    if message.text != "Пропустить":
        existing[field] = message.text

    await update_profile(session, message.from_user.id, **{key: existing})

    if is_last:
        await finish_onboarding_l2(message, state, session)
        return

    current_idx = L2_FIELDS.index(field)
    if current_idx + 1 < len(L2_FIELDS):
        next_field = L2_FIELDS[current_idx + 1]
        next_state = getattr(OnboardingLevel2, next_field)
        await state.set_state(next_state)
        await _ask_l2(message, state, next_field)


async def finish_onboarding_l2(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id:
        await end_conversation(session, conv_id)
    await state.clear()
    await update_profile(session, message.from_user.id, onboarding_level=2)
    await message.answer(
        "✅ Уровень 2 пройден. Через неделю предложу ещё один этап.",
        reply_markup=main_menu(),
    )


# --- Level 3 ---
async def start_onboarding_level3(message: Message, state: FSMContext, session: AsyncSession):
    await update_profile(session, message.from_user.id, onboarding_level=3)
    conv = await create_conversation(session, message.from_user.id, "onboarding_l3")
    await state.update_data(conv_id=conv.id)
    await state.set_state(OnboardingLevel3.q_romantic_pattern)
    await message.answer(
        "📋 Онбординг, уровень 3. Поговорим глубже.",
        reply_markup=skip_keyboard(),
    )
    await _ask_l3(message, state, "q_romantic_pattern")


L3_FIELDS = list(ONBOARDING_3_QUESTIONS.keys())


async def _ask_l3(message: Message, state: FSMContext, field: str):
    await message.answer(ONBOARDING_3_QUESTIONS[field], reply_markup=skip_keyboard())


@router.message(OnboardingLevel3.q_romantic_pattern)
async def on_l3_q1(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l3_and_next(message, state, session, "q_romantic_pattern")


@router.message(OnboardingLevel3.q_self_esteem)
async def on_l3_q2(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l3_and_next(message, state, session, "q_self_esteem")


@router.message(OnboardingLevel3.q_psychosomatic)
async def on_l3_q3(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l3_and_next(message, state, session, "q_psychosomatic")


@router.message(OnboardingLevel3.q_values)
async def on_l3_q4(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l3_and_next(message, state, session, "q_values")


@router.message(OnboardingLevel3.q_boundaries)
async def on_l3_q5(message: Message, state: FSMContext, session: AsyncSession):
    await _save_l3_and_next(message, state, session, "q_boundaries", is_last=True)


async def _save_l3_and_next(
    message: Message, state: FSMContext, session: AsyncSession,
    field: str, is_last: bool = False,
):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id and message.text != "Пропустить":
        await add_message_to_conversation(session, conv_id, "user", message.text)

    existing = {}
    profile = await get_profile(session, message.from_user.id)
    if profile:
        existing_val = getattr(profile, "deep_profile", {}) or {}
        if isinstance(existing_val, dict):
            existing = existing_val

    if message.text != "Пропустить":
        existing[field] = message.text

    await update_profile(session, message.from_user.id, deep_profile=existing)

    if is_last:
        await finish_onboarding_l3(message, state, session)
        return

    current_idx = L3_FIELDS.index(field)
    if current_idx + 1 < len(L3_FIELDS):
        next_field = L3_FIELDS[current_idx + 1]
        next_state = getattr(OnboardingLevel3, next_field)
        await state.set_state(next_state)
        await _ask_l3(message, state, next_field)


async def finish_onboarding_l3(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    conv_id = data.get("conv_id")
    if conv_id:
        await end_conversation(session, conv_id)
    await state.clear()
    await update_profile(session, message.from_user.id, onboarding_level=3)
    await message.answer(
        "✅ Онбординг полностью пройден! Теперь у меня полная картина.",
        reply_markup=main_menu(),
    )
