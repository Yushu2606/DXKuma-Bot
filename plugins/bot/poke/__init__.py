from pathlib import Path
from random import SystemRandom

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment

random = SystemRandom()

poke = on_regex(r"^(戳屁)(屁|股)$")

POKE_PIC = Path("./src/kuma-pic/poke")

conversations = {
    1: "不可以戳迪拉熊的屁股啦~",
    2: "你怎么能戳迪拉熊的屁股！",
    3: "为什么要戳迪拉熊的屁股呢？",
    4: "再戳我屁股迪拉熊就不跟你玩了！",
    5: "你再戳一个试试！",
    6: "讨厌啦~不要戳迪拉熊的屁股啦~",
    7: "你觉得戳迪拉熊的屁股很好玩吗？",
    8: "不许戳迪拉熊的屁股啦！",
    9: "迪拉熊懂你的意思~",
    10: "再戳迪拉熊就跟你绝交！",
}


@poke.handle()
async def _():
    weights = [9, 9, 9, 9, 9, 9, 9, 9, 4, 4]
    ran_number = random.choices(range(1, 11), weights=weights, k=1)[0]
    text = conversations[ran_number]
    filename = str(ran_number).zfill(2) + ".png"
    file_path = POKE_PIC / filename
    msg = (MessageSegment.text(text), MessageSegment.image(file_path))
    await poke.finish(msg)
