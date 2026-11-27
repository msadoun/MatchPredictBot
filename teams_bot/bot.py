"""Microsoft Teams activity handler for the EID schedule bot."""

from __future__ import annotations

import logging

from botbuilder.core import MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import ChannelAccount

from config import TIMEZONE
from messages import build_date_message, is_date_command, strip_teams_mentions

logger = logging.getLogger(__name__)


class EidScheduleBot(TeamsActivityHandler):
    """Responds to /date with UAE emirate EID opening hours."""

    async def on_members_added_activity(
        self, members_added: list[ChannelAccount], turn_context: TurnContext
    ) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "Welcome! Type /date to see today's EID schedule "
                        "for Abu Dhabi, Sharjah, Ajman, and Dubai."
                    )
                )

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        text = turn_context.activity.text or ""

        if is_date_command(text):
            reply = build_date_message(timezone=TIMEZONE)
            await turn_context.send_activity(MessageFactory.text(reply))
            return

        normalized = strip_teams_mentions(text).lower()
        if normalized in {"help", "/help", "hi", "hello", "start", "/start"}:
            await turn_context.send_activity(
                MessageFactory.text(
                    "Commands:\n"
                    "/date — Today's EID hours (Abu Dhabi, Sharjah, Ajman, Dubai)"
                )
            )
            return

        await turn_context.send_activity(
            MessageFactory.text(
                "I only understand /date right now. "
                "Send /date for today's EID schedule."
            )
        )
