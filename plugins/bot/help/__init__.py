from pathlib import Path

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.rule import to_me

all_help = on_regex(r"(dlxhelp|迪拉熊指令|迪拉熊帮助|指令大全)$")
eatbreak = on_regex(r"^(绝赞给你吃|绝赞请你吃|给你吃绝赞|请你吃绝赞)$", rule=to_me())


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
