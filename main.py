import asyncio
import os

import aiohttp
from aiohttp import web

from config import settings
from db.session import init_db
from utils.logger import setup_logging, get_logger
from bot.dispatcher import build_dispatcher
from core.scanner import scanner_loop, self_ping_loop

logger = get_logger("main")

WEBHOOK_PATH = "/webhook"


async def ensure_webhook_set(bot) -> None:
    if not settings.WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.warning(
            "WEBHOOK_URL not set — running in polling mode (local dev only). "
            "On Render you MUST set WEBHOOK_URL."
        )
        return

    webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
    while True:
        try:
            async with asyncio.timeout(15):
                await bot.set_webhook(webhook_url)
            logger.info("Webhook set: %s", webhook_url)
            return
        except asyncio.TimeoutError:
            logger.error(
                "set_webhook timed out (Telegram unreachable) — retrying in 60s"
            )
        except Exception as exc:
            logger.error("set_webhook failed: %s — retrying in 60s", exc)
        await asyncio.sleep(60)


async def on_startup(app: web.Application) -> None:
    await init_db()

    bot = app["bot"]
    http_session = aiohttp.ClientSession()
    app["http_session"] = http_session

    asyncio.create_task(ensure_webhook_set(bot))
    asyncio.create_task(scanner_loop(bot, http_session))
    asyncio.create_task(
        self_ping_loop(http_session, settings.WEBHOOK_URL)
    )


async def on_shutdown(app: web.Application) -> None:
    bot = app["bot"]
    await bot.session.close()

    http_session = app["http_session"]
    await http_session.close()


async def healthz(_: web.Request) -> web.Response:
    return web.Response(text="OK")


async def ping(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def index(_: web.Request) -> web.Response:
    return web.Response(
        text="SnipGift is running", content_type="text/plain"
    )


def create_app() -> web.Application:
    setup_logging(settings.LOG_LEVEL)

    bot, dp = build_dispatcher(settings.BOT_TOKEN)

    app = web.Application()
    app["bot"] = bot
    app["dispatcher"] = dp
    app["http_session"] = None

    app.router.add_get("/", index)
    app.router.add_get("/healthz", healthz)
    app.router.add_get("/ping", ping)

    from aiogram.webhook.aiohttp_server import (
        SimpleRequestHandler,
        setup_application,
    )

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


def main() -> None:
    app = create_app()
    host = settings.HOST
    port = settings.PORT
    if os.getenv("PORT"):
        port = int(os.getenv("PORT"))
    logger.info("Starting SnipGift on %s:%s", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
