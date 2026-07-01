import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, BOT_PROXY
from db.database import engine, async_session, DBSessionMiddleware
from db.models import Base
from bot.handlers import (
    menu,
    onboarding,
    situation,
    problems,
    work_on_problem,
    checkin,
    free_talk,
    progress,
)

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

dp = Dispatcher(storage=MemoryStorage())
dp.update.middleware(DBSessionMiddleware())

dp.include_router(menu.router)
dp.include_router(onboarding.router)
dp.include_router(situation.router)
dp.include_router(problems.router)
dp.include_router(work_on_problem.router)
dp.include_router(checkin.router)
dp.include_router(free_talk.router)
dp.include_router(progress.router)


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Database tables created")


async def main():
    session = AiohttpSession(proxy=BOT_PROXY) if BOT_PROXY else None
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp.startup.register(on_startup)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
