from pathlib import Path

from nonebot import on_notice, Bot
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent,
    GroupDecreaseNoticeEvent,
)
from nonebot.adapters.onebot.v11 import MessageSegment


def is_group_increase(event: GroupIncreaseNoticeEvent):
    return True


def is_group_decrease(event: GroupDecreaseNoticeEvent):
    return True


groupIncrease = on_notice(rule=is_group_increase)
groupDecrease = on_notice(rule=is_group_decrease)


@groupIncrease.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    qq = event.get_user_id()
    group_id = event.group_id
    user_name = (await bot.get_stranger_info(user_id=int(qq), no_cache=False))["nickname"]
    if group_id == 967611986:
        msg = MessageSegment.text(f"恭喜{user_name}（{qq}）发现了迪拉熊宝藏地带，发送dlxhelp试一下吧~")
    else:
        msg = MessageSegment.text(f"欢迎{user_name}（{qq}）加入本群，发送dlxhelp和迪拉熊一起玩吧~")
    await groupIncrease.send((msg, MessageSegment.image(Path("./src/kuma-pic/crease/0.png"))))


@groupDecrease.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    qq = event.get_user_id()
    group_id = event.group_id
    user_name = (await bot.get_stranger_info(user_id=int(qq), no_cache=False))["nickname"]
    if group_id == 967611986:
        msg = MessageSegment.text(f"很遗憾，{user_name}（{qq}）离开了迪拉熊的小窝QAQ")
    else:
        msg = MessageSegment.text(f"{user_name}（{qq}）离开了迪拉熊QAQ")
    await groupDecrease.send((msg, MessageSegment.image(Path("./src/kuma-pic/crease/1.png"))))
