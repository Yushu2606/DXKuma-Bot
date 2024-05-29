import traceback
from typing import Optional

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, Event
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.internal.matcher import Matcher
from nonebot.message import run_postprocessor


@run_postprocessor
async def _(event: Event, matcher: Matcher, exception: Optional[Exception]):
    if not exception or (
            isinstance(exception, ActionFailed) and exception.info["retcode"] == 200
    ):
        return
    bot = get_bot()
    trace = "".join(traceback.format_exception(exception)).replace("\\n", "\n")
    msg = MessageSegment.text(f"{trace}{event.raw_message}")
    await bot.send_msg(group_id=236030263, message=msg)
    feedback = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("迪拉熊出了点问题呢x"),
        MessageSegment.image("./src/pleasewait.jpg"),
    )
    await matcher.send(feedback)
