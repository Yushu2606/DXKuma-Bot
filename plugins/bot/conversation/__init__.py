import re
from pathlib import Path
from random import SystemRandom

from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.rule import to_me

random = SystemRandom()

xc = on_regex(r"^(香草|想草)(迪拉熊|dlx)$", re.RegexFlag.I)
wxhn = on_regex(r"^(迪拉熊|dlx)我喜欢你$", re.RegexFlag.I)
wxhn2 = on_fullmatch("我喜欢你", rule=to_me())
roll = on_regex(r"^(?:.*?是)(.+)(?:还是(.+))+$", rule=to_me())
cum = on_regex(r"dlxcum", re.RegexFlag.I)
eatbreak = on_regex(r"^(绝赞(给|请)你吃|(给|请)你吃绝赞)$", rule=to_me())

conversations = {
    1: "变态！！！",
    2: "走开！！！",
    3: "别靠近迪拉熊！！！",
    4: "迪拉熊不和你玩了！",
    5: "信不信迪拉熊吃你绝赞！",
    6: "信不信迪拉熊吃你星星！",
    7: "你不能这样对迪拉熊！",
    8: "迪拉熊不想理你了，哼！",
    9: "不把白潘AP了就别想！",
    10: "……你会对迪拉熊负责的，对吧？",
}


@xc.handle()
async def _():
    weights = [11, 11, 11, 11, 11, 11, 11, 11, 11, 1]
    ran_number = random.choices(range(1, 11), weights=weights, k=1)[0]
    text = conversations[ran_number]
    if ran_number == 10:
        pic_path = "./src/kuma-pic/xc/1.png"
    else:
        pic_path = "./src/kuma-pic/xc/0.png"
    msg = (MessageSegment.text(text), MessageSegment.image(Path(pic_path)))
    await xc.send(msg)


@wxhn.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("迪拉熊也喜欢你❤️"),
        MessageSegment.image(Path("./src/kuma-pic/response/like.png")),
    )
    await wxhn.send(msg)


@wxhn2.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("迪拉熊也喜欢你❤️"),
        MessageSegment.image(Path("./src/kuma-pic/response/like.png")),
    )
    await wxhn2.send(msg)


@roll.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext()
    roll_list = re.search(r"是(.+)", text).group(1).split("还是")
    if not roll_list:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("没有选项要让迪拉熊怎么选嘛~"),
            MessageSegment.image(Path("./src/kuma-pic/roll/1.png")),
        )
        await roll.finish(msg)
    if len(set(roll_list)) == 1:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("就一个选项要让迪拉熊怎么选嘛~"),
            MessageSegment.image(Path("./src/kuma-pic/roll/1.png")),
        )
        await roll.finish(msg)
    output = random.choice(roll_list)
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text(f"迪拉熊建议你选择“{output}”呢~"),
        MessageSegment.image(Path("./src/kuma-pic/roll/0.png")),
    )
    await roll.send(msg)


@cum.handle()
async def _():
    weight = random.randint(0, 9)
    imgpath = "./src/kuma-pic/cum/0.png"
    if weight == 0:
        imgpath = "./src/kuma-pic/cum/1.png"
    msg = MessageSegment.image(Path(imgpath))
    await cum.send(msg)


@eatbreak.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text("谢谢~"),
        MessageSegment.image(Path("./src/kuma-pic/response/eatbreak.png")),
    )
    await eatbreak.send(msg)
