import traceback
from typing import Optional

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, Event
from nonebot.internal.matcher import Matcher
from nonebot.message import run_postprocessor


@run_postprocessor
async def _(event: Event, matcher: Matcher, exception: Optional[Exception]):
    if not exception:
        return
    bot = get_bot()
    trace = "".join(traceback.format_exception(exception)).replace("\\n", "\n")
    msg = MessageSegment.text(f"{trace}\n{event.raw_message}")
    await bot.send_msg(group_id=236030263, message=msg)
