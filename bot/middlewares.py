import time

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5) -> None:
        super().__init__()
        self.rate_limit = rate_limit
        self._last = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        if user_id:
            now = time.monotonic()
            last = self._last.get(user_id, 0.0)
            elapsed = now - last
            if elapsed < self.rate_limit:
                await event.answer("Слишком быстро, подожди немного...")
                return
            self._last[user_id] = now
        return await handler(event, data)
