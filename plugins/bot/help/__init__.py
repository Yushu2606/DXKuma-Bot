import re
from pathlib import Path

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.rule import to_me

all_help = on_regex(r"^((迪拉熊|dlx)(help|指令|帮助)|指令大全)$", re.RegexFlag.I)
eatbreak = on_regex(r"^(绝赞(给|请)你吃|(给|请)你吃绝赞)$", rule=to_me())


@all_help.handle()
async def _():
    msg = (
        MessageSegment.image(Path("./src/allcommands.png")),
        MessageSegment.text("迪拉熊测试群：959231211"),
    )
    await all_help.send(msg)


@eatbreak.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("谢谢~"),
        MessageSegment.image(Path("./src/eatbreak.png")),
    )
    await eatbreak.send(msg)
