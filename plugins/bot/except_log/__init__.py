import traceback

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.message import run_postprocessor


@run_postprocessor
async def _(event, matcher, exception):
    if not exception:
        return
    bot = get_bot()
    msg = MessageSegment.text(
        f"检测到未捕获的异常：\n{"".join(traceback.format_exception(exception))}"
    )
    await bot.send_msg(group_id=236030263, message=msg)
