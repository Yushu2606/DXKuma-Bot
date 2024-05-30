import traceback
from pathlib import Path

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, Event
from nonebot.internal.matcher import Matcher
from nonebot.message import run_postprocessor


@run_postprocessor
async def _(event: Event, matcher: Matcher, exception: Exception | None):
    if not exception:
        return
    bot = get_bot()
    trace = "".join(traceback.format_exception(exception)).replace("\\n", "\n")
    msg = MessageSegment.text(f"{trace}{event.raw_message}\n{event.get_session_id()}")
    await bot.send_msg(group_id=236030263, message=msg)
    feedback = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("迪拉熊出了点问题呢x"),
        MessageSegment.image(Path("./src/pleasewait.jpg")),
    )
    await matcher.send(feedback)
