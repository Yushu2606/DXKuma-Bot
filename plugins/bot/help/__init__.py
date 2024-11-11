import re
from pathlib import Path

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment

all_help = on_regex(r"^((迪拉熊|dlx)(help|指令|帮助)|指令大全)$", re.I)


@all_help.handle()
async def _():
    msg = (
        MessageSegment.image(Path("./Static/Help/0.png")),
        MessageSegment.text("迪拉熊测试群：959231211"),
    )
    await all_help.send(msg)
