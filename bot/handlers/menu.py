import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from db.crud import get_profile
from bot.keyboards.keyboards import main_menu
from bot.handlers.onboarding import start_onboarding, start_onboarding_level2, start_onboarding_level3
from bot.handlers.situation import start_situation_collect
from bot.handlers.problems import show_problems
from bot.handlers.work_on_problem import start_work_on_problem
from bot.handlers.checkin import start_checkin
from bot.handlers.free_talk import start_free_talk
from bot.handlers.progress import show_progress

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    logger.info("Received /start from user %d", message.from_user.id)
    profile = await get_profile(session, message.from_user.id)
    logger.info("Profile: %s", profile)
    if not profile or profile.onboarding_level == 0:
        await start_onboarding(message, state, session)
    else:
        await message.answer(
            f"С возвращением! 👋\nВыбери режим работы в меню.",
            reply_markup=main_menu(),
        )


@router.message(F.text == "Главное меню")
@router.message(F.text == "Меню")
async def go_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(F.text == "Разбор ситуации")
async def menu_situation(message: Message, state: FSMContext, session: AsyncSession):
    await start_situation_collect(message, state, session)


@router.message(F.text == "Мои проблемы")
async def menu_problems(message: Message, state: FSMContext, session: AsyncSession):
    await show_problems(message, session)


@router.message(F.text == "Работа над проблемой")
async def menu_work(message: Message, state: FSMContext, session: AsyncSession):
    await start_work_on_problem(message, state, session)


@router.message(F.text == "Чек-ин")
async def menu_checkin(message: Message, state: FSMContext, session: AsyncSession):
    await start_checkin(message, state, session)


@router.message(F.text == "Просто поговорить")
async def menu_free(message: Message, state: FSMContext, session: AsyncSession):
    await start_free_talk(message, state, session)


@router.message(F.text == "Мой прогресс")
async def menu_progress(message: Message, session: AsyncSession):
    await show_progress(message, session)
