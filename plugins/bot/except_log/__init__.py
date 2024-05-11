import traceback

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.message import run_postprocessor


@run_postprocessor
async def _(event, matcher, exception):
    if not exception:
        return
    bot = get_bot()
    trace = "".join(traceback.format_exception(exception)).replace("\\n", "\n")
    msg = MessageSegment.text(trace)
    await bot.send_msg(group_id=236030263, message=msg)
