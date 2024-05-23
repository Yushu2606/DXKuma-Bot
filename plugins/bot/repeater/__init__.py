import re

from nonebot import on_message, Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from . import config

repeater_group = config.repeater_group
shortest = config.shortest_length
blacklist = config.blacklist

m = on_message(priority=10, block=False)

last_message = {}
message_times = {}


# 消息预处理
def message_preprocess(message: str):
    raw_message = message
    contained_images = {}
    images = re.findall(r"\[CQ:image.*?]", message)
    pattern = r"file=http://gchat.qpic.cn/gchatpic_new/\d+/\d+-\d+-(.*?)/.*?[,\]]"

    for i in images:
        image_url = re.findall(r"url=(.*?)[,\]]", i)
        pattern_match = re.findall(pattern, i)
        if image_url and pattern_match:
            contained_images.update({i: [image_url[0], pattern_match[0]]})

    for i, v in contained_images.items():
        message = message.replace(i, f"[{v[1]}]")

    return message, raw_message


@m.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    # 检查是否在黑名单中
    if event.raw_message in blacklist:
        return
    gid = str(event.group_id)
    if gid in repeater_group or "all" in repeater_group:
        global last_message, message_times
        message, raw_message = message_preprocess(str(event.message))
        if last_message.get(gid) != message:
            message_times[gid] = 1
        else:
            message_times[gid] += 1
        if message_times.get(gid) == config.shortest_times:
            await bot.send_group_msg(
                group_id=event.group_id, message=raw_message, auto_escape=False
            )
        last_message[gid] = message
