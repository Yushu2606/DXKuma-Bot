from pathlib import Path

from nonebot import on_type, Bot
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent,
    GroupDecreaseNoticeEvent,
    FriendRequestEvent,
    GroupRequestEvent,
    MessageSegment,
)

groupIncrease = on_type(GroupIncreaseNoticeEvent)
groupDecrease = on_type(GroupDecreaseNoticeEvent)
friendRequest = on_type(FriendRequestEvent)
groupRequest = on_type(GroupRequestEvent)


@groupIncrease.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    qq = event.get_user_id()
    if qq == bot.self_id:
        return
    group_id = event.group_id
    user_name = (await bot.get_stranger_info(user_id=int(qq), no_cache=False))[
        "nickname"
    ]
    if group_id == 967611986:
        msg = MessageSegment.text(
            f"恭喜{user_name}（{qq}）发现了迪拉熊宝藏地带，发送dlxhelp试一下吧~"
        )
    else:
        msg = MessageSegment.text(
            f"欢迎{user_name}（{qq}）加入本群，发送dlxhelp和迪拉熊一起玩吧~"
        )
    await groupIncrease.send(
        (msg, MessageSegment.image(Path("./Static/MemberChange/0.png")))
    )


@groupDecrease.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    qq = event.get_user_id()
    if qq == bot.self_id:
        return
    group_id = event.group_id
    user_name = (await bot.get_stranger_info(user_id=int(qq), no_cache=False))[
        "nickname"
    ]
    if group_id == 967611986:
        msg = MessageSegment.text(f"很遗憾，{user_name}（{qq}）离开了迪拉熊的小窝QAQ")
    else:
        msg = MessageSegment.text(f"{user_name}（{qq}）离开了迪拉熊QAQ")
    await groupDecrease.send(
        (msg, MessageSegment.image(Path("./Static/MemberChange/1.png")))
    )


@friendRequest.handle()
async def _(event: FriendRequestEvent):
    event.approve()


@groupRequest.handle()
async def _(event: GroupRequestEvent):
    if event.sub_type != "invite":
        return
    event.approve()
