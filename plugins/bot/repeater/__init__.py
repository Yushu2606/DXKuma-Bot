import re

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

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
    images = re.findall(r"\[CQ:image.*?\]", message)
    pattern = r"rkey=(.*?)[,\]&]"

    for i in images:
        image_url = re.findall(r"fileid=(.*?)[,\]&]", i)
        pattern_match = re.findall(pattern, i)
        if image_url and pattern_match:
            contained_images.update({i: [image_url[0], pattern_match[0]]})

    for i, v in contained_images.items():
        message = message.replace(i, f"[{v[0][2:35]}]")

    return message, raw_message


@m.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    # 检查是否在黑名单中
    if event.raw_message in blacklist:
        return
    gid = str(event.group_id)
    if gid in repeater_group or "all" in repeater_group:
        global last_message, message_times
        message, raw_message = message_preprocess(event.raw_message)
        qq = event.get_user_id()
        if last_message.get(gid) != message:
            message_times[gid] = set()
        message_times[gid].add(hash(qq))
        if len(message_times.get(gid)) == config.shortest_times:
            await bot.send_group_msg(
                group_id=event.group_id, message=event.get_message()
            )
        last_message[gid] = message
