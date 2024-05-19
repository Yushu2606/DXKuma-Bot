import random
from pathlib import Path

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.rule import to_me

xc = on_regex(r'(香草|想草)(迪拉熊|滴蜡熊|dlx)')
wxhn = on_regex(r'^(我喜欢你)$', rule=to_me())
wxhn2 = on_regex(r'^(迪拉熊|dlx)我喜欢你$')

roll = on_regex(r'^(?:是)(.+)(?:还是(.+))+')

# morning = on_regex(r'^(早安|早上好|早好|哦哈哟|上午好|午好|中午好|午安|下午好|晚好|晚上好|晚安|安安)$')

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
    weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 0.1]
    ran_number = random.choices(range(1, 11), weights=weights, k=1)[0]
    text = conversations[ran_number]
    if ran_number >= 10:
        pic_path = "./src/可怜.png"
    else:
        pic_path = "./src/啊.png"
    msg = (MessageSegment.text(text), MessageSegment.image(Path(pic_path)))
    await xc.send(msg)


@wxhn.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text('迪拉熊也喜欢你❤️'),
        MessageSegment.image(Path('./src/like.png')),
    )
    await wxhn.send(msg)


@wxhn2.handle()
async def _(event: GroupMessageEvent):
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text('迪拉熊也喜欢你❤️'),
        MessageSegment.image(Path('./src/like.png')),
    )
    await wxhn2.send(msg)


@roll.handle()
async def _(event: GroupMessageEvent):
    text = str(event.raw_message)
    roll_list = text[1:].split('还是')
    if not roll_list:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text('没有选项要让迪拉熊怎么选嘛~'),
            MessageSegment.image(Path('./src/选不了.png')),
        )
        await roll.finish(msg)
    if len(set(roll_list)) == 1:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text('就一个选项要让迪拉熊怎么选嘛~'),
            MessageSegment.image(Path('./src/选不了.png')),
        )
        await roll.finish(msg)
    output = random.SystemRandom().choice(roll_list)
    msg = (
        MessageSegment.reply(event.message_id),
        MessageSegment.text(f'迪拉熊建议你选择“{output}”呢~'),
        MessageSegment.image(Path('./src/选择.png')),
    )
    await roll.send(msg)

# @morning.handle()
# async def _(event:GroupMessageEvent):
#     msg = str(event.message)
#     current_hour = datetime.now().hour
#     if current_hour >= 6 and current_hour < 9:
#         text = "还早着呢，迪拉熊想再睡会zzzZ.."
#         if msg in ['早安','早上好','早好','哦哈哟','上午好']:
#             text = "早安~迪拉熊想再睡会zzzZ.."
#     elif current_hour >= 9 and current_hour < 12:
#         text = "哎呀，还早着呢~"
#         if msg in ['早安','早上好','早好','哦哈哟','上午好']:
#             text = "早上好！又是精神满满的一天~"
#     elif current_hour >= 12 and current_hour < 14:
#         text = random.choice(["迪拉熊现在只想吃点绝赞","别闹，让迪拉熊歇一会~"])
#         if msg in ['午好','中午好']:
#             text = "午好呀~今天中午吃什么呢~"
#         if msg in ['午安']:
#             text = "午安，迪拉熊也想歇一下呢~"
#     elif current_hour >= 14 and current_hour < 18:
#         text = "其实现在是下午呢~"
#         if msg in ['下午好']:
#             text = "下午好~想和迪拉熊一起玩吗"
#     elif current_hour >= 18 or current_hour < 12:
#         text = '已经晚上啦'
#         if msg in ['晚好','晚上好']:
#             text = "晚好呀~今天的成绩如何呢~"
#         if current_hour >= 23 or current_hour <= 1:
#             text = "时间有点晚了呢，早点睡吧~"
#             if msg in ['晚安','安安']:
#                 text = "晚安，迪拉熊祝你有个好梦zzzZ.."
#     else:
#         texts = ["太晚了，可以不打扰迪拉熊睡觉嘛zzzZ", "再吵迪拉熊睡觉明早就拿你绝赞当早餐！"]
#         weights = [9, 1]
#         text = random.choices(texts, weights=weights)[0]

#     msg = (MessageSegment.reply(event.message_id), MessageSegment.text(text))
#     await morning.finish(msg)
