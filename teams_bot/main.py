"""HTTP entry point for the Microsoft Teams EID schedule bot."""

from __future__ import annotations

import logging
import sys
import traceback
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bot import EidScheduleBot
from config import MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, PORT

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SETTINGS = BotFrameworkAdapterSettings(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)
BOT = EidScheduleBot()


async def on_error(context: TurnContext, error: Exception) -> None:
    logger.error("Bot error: %s\n%s", error, traceback.format_exc())
    await context.send_activity("Sorry — something went wrong handling that message.")
    if context.activity.channel_id == "emulator":
        await context.send_activity(
            Activity(
                type=ActivityTypes.trace,
                value=f"{error}",
                name="BotError",
            )
        )


ADAPTER.on_turn_error = on_error


async def messages(req: Request) -> Response:
    if "application/json" not in req.headers.get("Content-Type", ""):
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)


async def health(_: Request) -> Response:
    return json_response({"status": "ok", "bot": "eid-schedule"})


def create_app() -> web.Application:
    app = web.Application(middlewares=[aiohttp_error_middleware])
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    return app


def main() -> None:
    try:
        app = create_app()
        logger.info("Starting Teams EID schedule bot on port %s", PORT)
        web.run_app(app, host="0.0.0.0", port=PORT)
    except Exception:
        logger.exception("Failed to start bot")
        sys.exit(1)


if __name__ == "__main__":
    main()
