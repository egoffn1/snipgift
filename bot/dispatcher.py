from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import start, settings, alerts
from bot.middlewares import ThrottlingMiddleware
from utils.logger import get_logger

logger = get_logger("bot.dispatcher")


def build_dispatcher(token: str) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(alerts.router)

    for router in (start.router, settings.router, alerts.router):
        router.message.middleware(ThrottlingMiddleware())
        router.callback_query.middleware(ThrottlingMiddleware())

    return bot, dp
