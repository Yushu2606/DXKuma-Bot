import asyncio
import datetime
import os
import re
import shelve
from pathlib import Path
from random import SystemRandom

import toml
from PIL import Image, UnidentifiedImageError
from dill import Pickler, Unpickler
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment

from util import Config

shelve.Pickler = Pickler
shelve.Unpickler = Unpickler

random = SystemRandom()

kuma_pic = on_regex(r"^(随机)?(迪拉熊|dlx)((涩|色|瑟)图|st)?$", re.I)
rank = on_regex(r"^(迪拉熊|dlx)(排行榜|rank)$", re.I)
addNSFW = on_regex(r"^加色图 *(\d+)$")

KUMAPIC = "./Static/Gallery/SFW"
KUMAPIC_R18 = "./Static/Gallery/NSFW"
DATA_PATH = "./data/random_pic/count.db"

config = toml.load("./dxkuma.toml")


def get_time():
    today = datetime.date.today()

    # 获取当前年份
    year = today.year

    # 获取当前日期所在的周数
    week_number = today.isocalendar()[1]

    # 将年份和周数拼接成字符串
    result = str(year) + str(week_number)
    return result


def update_count(qq: str, type: str):
    time = get_time()

    with shelve.open(DATA_PATH) as count_data:
        if qq not in count_data:
            count = count_data.setdefault(qq, {})
        else:
            count = count_data[qq]
        if time not in count:
            times = count.setdefault(time, {"kuma": 0, "kuma_r18": 0})
        else:
            times = count[time]

        times[type] += 1
        count_data[qq] = count


def gen_rank(data, time):
    leaderboard = []

    for qq, qq_data in data.items():
        if time in qq_data:
            total_count = qq_data[time]["kuma"] + qq_data[time]["kuma_r18"]
            leaderboard.append((qq, total_count))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    return leaderboard[:5]


def check_image(imgpath: Path):
    try:
        image = Image.open(imgpath)
    except UnidentifiedImageError:
        return False
    try:
        image.verify()
    except OSError:
        return False
    image.close()
    return True


@kuma_pic.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    qq = event.get_user_id()
    msg = event.get_plaintext()
    type = "kuma"
    path = KUMAPIC
    if "涩图" in msg or "色图" in msg or "瑟图" in msg or "st" in msg:
        type = "kuma_r18"
        path = KUMAPIC_R18
    if group_id == config["special_group"]:  # 不被限制的 group_id
        pass
    elif (
        type == "kuma_r18" and group_id not in config["nsfw_groups"]
    ):  # type 为 'kuma_r18' 且非指定 group_id
        msg = (
            MessageSegment.text("迪拉熊不准你看"),
            MessageSegment.image(Path("./Static/Gallery/0.png")),
        )
        await kuma_pic.finish(msg)
    else:
        weight = random.randint(0, 9)
        if weight == 0:
            if type == "kuma":
                msg = MessageSegment.text(
                    "迪拉熊提醒你：不要发太多刷屏啦，休息下再试试吧~"
                )
            elif type == "kuma_r18":
                msg = MessageSegment.text("迪拉熊关心你的身体健康，所以图就先不发了~")
            await kuma_pic.finish(msg)

    files = os.listdir(path)
    if not files:
        msg = (
            MessageSegment.text("迪拉熊不准你看"),
            MessageSegment.image(Path("./Static/Gallery/0.png")),
        )
        await kuma_pic.finish(msg)
    for _ in range(3):
        file = random.choice(files)
        pic_path = os.path.join(path, file)
        if check_image(pic_path):
            break
    else:
        msg = (
            MessageSegment.text("迪拉熊不准你看"),
            MessageSegment.image(Path("./Static/Gallery/0.png")),
        )
        await kuma_pic.finish(msg)
    with open(pic_path, "rb") as fd:
        send_msg = await kuma_pic.send(MessageSegment.image(fd.read()))
    update_count(qq=qq, type=type)
    if type == "kuma_r18":
        msg_id = send_msg["message_id"]
        await asyncio.sleep(10)
        await bot.delete_msg(message_id=msg_id)


@rank.handle()
async def _(bot: Bot):
    time = get_time()

    with shelve.open(DATA_PATH) as count_data:
        leaderboard = gen_rank(count_data, time)

    leaderboard_output = []
    count = min(len(leaderboard), 5)  # 最多显示5个人，取实际人数和5的较小值
    for i, (qq, total_count) in enumerate(leaderboard[:count], start=1):
        user_name = (await bot.get_stranger_info(user_id=int(qq), no_cache=False))[
            "nickname"
        ]
        rank_str = f"{i}. {user_name}：{total_count}"
        leaderboard_output.append(rank_str)

    msg = "\n".join(leaderboard_output)
    msg = f"本周迪拉熊厨力最高的人是……\n{msg}\n迪拉熊给上面{count}个宝宝一个大大的拥抱~\n（积分每周一重算）"
    await rank.finish(msg)


@addNSFW.handle()
async def _(event: GroupMessageEvent):
    if event.group_id != Config.config.dev_group:
        return
    gid = int(re.search(r"\d+", event.get_plaintext()).group())
    config["nsfw_groups"].append(gid)
    with open("./dxkuma.toml", "w") as f:
        toml.dump(config, f)
        f.close()
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("成功"),
    )
    await addNSFW.finish(msg)
