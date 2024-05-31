import json
import math
import os
import re
import shelve
from pathlib import Path
from random import SystemRandom

from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

from util.DivingFish import get_chart_stats, get_music_data, get_player_records
from .GenB50 import (
    compute_record,
    generateb50,
    generate_wcb,
    get_page_records,
    ratings,
    records_filter,
    find_song_by_id,
)
from .MusicInfo import music_info, play_info

random = SystemRandom()

best50 = on_regex(r"^dlxb?50( ?\[CQ:at,qq=(\d+)\] ?)?$", re.RegexFlag.I)
fit50 = on_regex(r"^dlxf50( ?\[CQ:at,qq=(\d+)\] ?)?$", re.RegexFlag.I)
rate50 = on_regex(
    r"^dlxr50( ?(s{1,3}(p|\+)?|a{1,3}|b{1,3}|[cd]))+?( ?\[CQ:at,qq=(\d+)\] ?)?$",
    re.RegexFlag.I,
)
ap50 = on_regex(r"^dlxap(50)?( ?\[CQ:at,qq=(\d+)\] ?)?$", re.RegexFlag.I)
fc50 = on_regex(r"^dlxfc(50)?( ?\[CQ:at,qq=(\d+)\] ?)?$", re.RegexFlag.I)
sunlist = on_regex(r"^dlx([sc]un|寸|🤏)( ?(\d+?))?$", re.RegexFlag.I)
locklist = on_regex(r"^dlx(suo|锁|🔒)( ?(\d+?))?$", re.RegexFlag.I)

songinfo = on_regex(r"^id ?(\d+)$", re.RegexFlag.I)
playinfo = on_regex(r"^info ?(.+)$", re.RegexFlag.I)
playmp3 = on_regex(r"^dlx点歌 ?(.+)$", re.RegexFlag.I)
randomsong = on_regex(r"^随(个|歌) ?(绿|黄|红|紫|白)?(\d+)(\.\d|\+)?$")
maiwhat = on_fullmatch("mai什么")

wcb = on_regex(r"^(dlx)?完成表 ?((\d+)(\.\d|\+)?)( (\d+))?$")

whatSong = on_regex(r"^((search|查歌) ?(.+)|(.+)是什么歌)$", re.RegexFlag.I)
aliasSearch = on_regex(r"^(查看别名 ?(\d+)|(\d+)有什么别名)$")

aliasAdd = on_regex(r"^添?加别名 ?(\d+) ?(.+)$")
aliasDel = on_regex(r"^删除?别名 ?(\d+) ?(.+)$")

all_plate = on_regex(r"^(plate|看牌子)$", re.RegexFlag.I)
all_frame = on_regex(r"^(frame|看底板)$", re.RegexFlag.I)

set_plate = on_regex(r"^(setplate|设置牌子) ?(\d{6})$", re.RegexFlag.I)
set_frame = on_regex(r"^(setframe|设置底板) ?(\d{6})$", re.RegexFlag.I)

ratj_on = on_regex(r"^(开启|启用)分数推荐$")
ratj_off = on_regex(r"^(关闭|禁用)分数推荐$")

allow_other_on = on_regex(r"^(开启|启用|允许)代查$")
allow_other_off = on_regex(r"^(关闭|禁用|禁止)代查$")


# 根据乐曲别名查询乐曲id列表
def find_songid_by_alias(name):
    # 芝士id列表
    matched_ids = []

    with open("./src/maimai/aliasList.json", "r") as f:
        alias_list = json.load(f)

    # 芝士查找
    for id, info in alias_list.items():
        if (
                name in info["Alias"]
                or name in info["Name"]
                or str(name).lower() in str(info["Name"]).lower()
        ):
            matched_ids.append(id)
            continue
        for alias in info["Alias"]:
            if name in alias or str(name).lower() in str(alias).lower():
                matched_ids.append(id)
                break

    # 芝士排序
    sorted_matched_ids = sorted(matched_ids, key=int)

    # 芝士输出
    return sorted_matched_ids


async def records_to_b50(
        records: list,
        fc_rules: list | None = None,
        rate_rules: list | None = None,
        is_fit: bool = False,
):
    sd = []
    dx = []
    songList, _ = await get_music_data()
    charts, _ = await get_chart_stats()
    for record in records:
        if fc_rules and record["fc"] not in fc_rules:
            continue
        if rate_rules and record["rate"] not in rate_rules:
            continue
        song_id = record["song_id"]
        is_new = [
            d["basic_info"]["is_new"] for d in songList if d["id"] == str(song_id)
        ]
        if is_fit:
            fit_diff = get_fit_diff(
                str(record["song_id"]), record["level_index"], record["ds"], charts
            )
            record["ds"] = round(fit_diff, 2)
            record["ra"] = int(
                fit_diff * record["achievements"] * get_ra_in(record["rate"]) * 0.01
            )
        if record["ra"] == 0:
            continue
        if is_new[0]:
            dx.append(record)
        else:
            sd.append(record)
    b35 = (
              sorted(
                  sd,
                  key=lambda x: (x["ra"], get_ra_in(x["rate"]), x["ds"], x["achievements"]),
                  reverse=True,
              )
          )[:35]
    b15 = (
              sorted(
                  dx,
                  key=lambda x: (x["ra"], get_ra_in(x["rate"]), x["ds"], x["achievements"]),
                  reverse=True,
              )
          )[:15]
    return b35, b15


def get_fit_diff(song_id: str, level_index: int, ds: float, charts) -> float:
    if song_id not in charts["charts"]:
        return ds
    level_data = charts["charts"][song_id][level_index]
    if "fit_diff" not in level_data:
        return ds
    fit_diff = level_data["fit_diff"]
    return fit_diff


def get_ra_in(rate: str) -> float:
    return ratings[rate][1]


@best50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if not match:
        target_qq = event.get_user_id()
    else:
        target_qq = match.group(1)
        if target_qq != event.get_user_id():
            with shelve.open("./data/maimai/b50_config.db") as config:
                if (
                        target_qq in config
                        and "allow_other" in config[target_qq]
                        and not config[target_qq]["allow_other"]
                ):
                    msg = (
                        MessageSegment.reply(event.message_id),
                        MessageSegment.text("他还没有允许其他人查询他的成绩呢"),
                    )
                    await best50.finish(msg)
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await best50.finish(msg)
    records = data["records"]
    if not records:
        if match:
            msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await best50.finish((MessageSegment.reply(event.message_id), msg))
    nickname = data["nickname"]
    dani = data["additional_rating"]
    b35, b15 = await records_to_b50(records)
    await best50.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generateb50(
        b35=b35, b15=b15, nickname=nickname, qq=target_qq, dani=dani, type="b50"
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await best50.send(msg)


@ap50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if not match:
        target_qq = event.get_user_id()
    else:
        target_qq = match.group(1)
        if target_qq != event.get_user_id():
            with shelve.open("./data/maimai/b50_config.db") as config:
                if (
                        target_qq in config
                        and "allow_other" in config[target_qq]
                        and not config[target_qq]["allow_other"]
                ):
                    msg = (
                        MessageSegment.reply(event.message_id),
                        MessageSegment.text("他还没有允许其他人查询他的成绩呢"),
                    )
                    await ap50.finish(msg)
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await ap50.finish(msg)
    records = data["records"]
    if not records:
        if match:
            msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await ap50.finish((MessageSegment.reply(event.message_id), msg))
    ap35, ap15 = await records_to_b50(records, ["ap", "app"])
    if not ap35 and not ap15:
        if match:
            msg = MessageSegment.text("他还没有全完美任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有全完美任何一个谱面呢~")
        await ap50.finish((MessageSegment.reply(event.message_id), msg))
    nickname = data["nickname"]
    dani = data["additional_rating"]
    await ap50.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generateb50(
        b35=ap35, b15=ap15, nickname=nickname, qq=target_qq, dani=dani, type="ap50"
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await ap50.send(msg)


@fc50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if not match:
        target_qq = event.get_user_id()
    else:
        target_qq = match.group(1)
        if target_qq != event.get_user_id():
            with shelve.open("./data/maimai/b50_config.db") as config:
                if (
                        target_qq in config
                        and "allow_other" in config[target_qq]
                        and not config[target_qq]["allow_other"]
                ):
                    msg = (
                        MessageSegment.reply(event.message_id),
                        MessageSegment.text("他还没有允许其他人查询他的成绩呢"),
                    )
                    await fc50.finish(msg)
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await fc50.finish(msg)
    records = data["records"]
    if not records:
        if match:
            msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await fc50.finish((MessageSegment.reply(event.message_id), msg))
    fc35, fc15 = await records_to_b50(records, ["fc", "fcp"])
    if not fc35 and not fc15:
        if match:
            msg = MessageSegment.text("他还没有全连任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有全连任何一个谱面呢~")
        await fc50.finish((MessageSegment.reply(event.message_id), msg))
    nickname = data["nickname"]
    dani = data["additional_rating"]
    await fc50.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generateb50(
        b35=fc35, b15=fc15, nickname=nickname, qq=target_qq, dani=dani, type="fc50"
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await fc50.send(msg)


@fit50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if not match:
        target_qq = event.get_user_id()
    else:
        target_qq = match.group(1)
        if target_qq != event.get_user_id():
            with shelve.open("./data/maimai/b50_config.db") as config:
                if (
                        target_qq in config
                        and "allow_other" in config[target_qq]
                        and not config[target_qq]["allow_other"]
                ):
                    msg = (
                        MessageSegment.reply(event.message_id),
                        MessageSegment.text("他还没有允许其他人查询他的成绩呢"),
                    )
                    await fit50.finish(msg)
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await fit50.finish(msg)
    records = data["records"]
    if not records:
        if match:
            msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await fit50.finish((MessageSegment.reply(event.message_id), msg))
    nickname = data["nickname"]
    dani = data["additional_rating"]
    b35, b15 = await records_to_b50(records, is_fit=True)
    await fit50.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generateb50(
        b35=b35, b15=b15, nickname=nickname, qq=target_qq, dani=dani, type="fit50"
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await fit50.send(msg)


@rate50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if not match:
        target_qq = event.get_user_id()
    else:
        target_qq = match.group(1)
        if target_qq != event.get_user_id():
            with shelve.open("./data/maimai/b50_config.db") as config:
                if (
                        target_qq in config
                        and "allow_other" in config[target_qq]
                        and not config[target_qq]["allow_other"]
                ):
                    msg = (
                        MessageSegment.reply(event.message_id),
                        MessageSegment.text("他还没有允许其他人查询他的成绩呢"),
                    )
                    await rate50.finish(msg)
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await rate50.finish(msg)
    records = data["records"]
    if not records:
        if match:
            msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
        else:
            msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await rate50.finish((MessageSegment.reply(event.message_id), msg))
    msg_text = msg_text.replace("+", "p").lower()
    rate_rules = re.findall(r"s{1,3}p?|a{1,3}|b{1,3}|[cd]", msg_text)
    rate35, rate15 = await records_to_b50(records, rate_rules=rate_rules)
    if not rate35 and not rate15:
        if match:
            msg = MessageSegment.text("他还没有任何匹配的成绩呢~")
        else:
            msg = MessageSegment.text("你还没有任何匹配的成绩呢~")
        await rate50.finish((MessageSegment.reply(event.message_id), msg))
    nickname = data["nickname"]
    dani = data["additional_rating"]
    await rate50.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generateb50(
        b35=rate35,
        b15=rate15,
        nickname=nickname,
        qq=target_qq,
        dani=dani,
        type="rate50",
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await rate50.send(msg)


@sunlist.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r"\d+?"
    match = re.search(pattern, msg)
    if match:
        page = int(match.group())
        if page == 0:
            page = 1
    else:
        page = 1
    data, status = await get_player_records(qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await sunlist.finish(msg)
    records = data["records"]
    if not records:
        msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await sunlist.finish((MessageSegment.reply(event.message_id), msg))
    songList, _ = await get_music_data()
    filted_records = records_filter(records=records, is_sun=True, songList=songList)
    if not filted_records:
        msg = MessageSegment.text("你还没有任何匹配的成绩呢~")
        await sunlist.finish((MessageSegment.reply(event.message_id), msg))
    all_page_num = math.ceil(len(filted_records) / 55)
    if page > all_page_num:
        msg = MessageSegment.text(f"迪拉熊发现你的寸止表的最大页码为{all_page_num}")
        await sunlist.finish((MessageSegment.reply(event.message_id), msg))
    input_records = get_page_records(filted_records, page=page)
    nickname = data["nickname"]
    rating = data["rating"]
    dani = data["additional_rating"]
    await sunlist.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generate_wcb(
        qq=qq,
        page=page,
        nickname=nickname,
        dani=dani,
        rating=rating,
        input_records=input_records,
        all_page_num=all_page_num,
        songList=songList,
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await sunlist.send(msg)


@locklist.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r"\d+?"
    match = re.search(pattern, msg)
    if match:
        page = int(match.group())
        if page == 0:
            page = 1
    else:
        page = 1
    data, status = await get_player_records(qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await locklist.finish(msg)
    records = data["records"]
    if not records:
        msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await locklist.finish((MessageSegment.reply(event.message_id), msg))
    songList, _ = await get_music_data()
    filted_records = records_filter(records=records, is_lock=True, songList=songList)
    if not filted_records:
        msg = MessageSegment.text("你还没有任何匹配的成绩呢~")
        await locklist.finish((MessageSegment.reply(event.message_id), msg))
    all_page_num = math.ceil(len(filted_records) / 55)
    if page > all_page_num:
        msg = MessageSegment.text(f"迪拉熊发现你的锁血表的最大页码为{all_page_num}")
        await locklist.finish((MessageSegment.reply(event.message_id), msg))
    input_records = get_page_records(filted_records, page=page)
    nickname = data["nickname"]
    rating = data["rating"]
    dani = data["additional_rating"]
    await locklist.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generate_wcb(
        qq=qq,
        page=page,
        nickname=nickname,
        dani=dani,
        rating=rating,
        input_records=input_records,
        all_page_num=all_page_num,
        songList=songList,
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await locklist.send(msg)


@wcb.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r"(完成表) ?((\d+)(\.\d|\+)?)( (\d+))?"
    match = re.match(pattern, msg)
    if not match:
        await wcb.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊觉得输入的信息好像有点问题呢"),
            )
        )
    level = match.group(2)
    if match.group(5):
        page = int(match.group(5).strip())
        if page == 0:
            page = 1
    else:
        page = 1
    data, status = await get_player_records(qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                "迪拉熊未找到用户信息，可能是没有绑定水鱼\n水鱼网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status != 200 or not data:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("水鱼好像出了点问题呢"),
            MessageSegment.image(Path("./src/pleasewait.jpg")),
        )
        await wcb.finish(msg)
    records = data["records"]
    if not records:
        msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
        await wcb.finish((MessageSegment.reply(event.message_id), msg))
    filted_records = records_filter(records=records, level=level)
    if len(filted_records) == 0:
        msg = MessageSegment.text("迪拉熊未找到该难度或未游玩过该难度的歌曲")
        await wcb.finish((MessageSegment.reply(event.message_id), msg))

    all_page_num = math.ceil(len(filted_records) / 55)
    if page > all_page_num:
        msg = MessageSegment.text(
            f"迪拉熊发现你的 {level} 完成表的最大页码为{all_page_num}"
        )
        await wcb.finish((MessageSegment.reply(event.message_id), msg))
    songList, _ = await get_music_data()
    input_records = get_page_records(filted_records, page=page)
    nickname = data["nickname"]
    rating = data["rating"]
    dani = data["additional_rating"]
    rate_count = compute_record(records=filted_records)
    await wcb.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
        )
    )
    img = await generate_wcb(
        qq=qq,
        level=level,
        page=page,
        nickname=nickname,
        dani=dani,
        rating=rating,
        input_records=input_records,
        rate_count=rate_count,
        all_page_num=all_page_num,
        songList=songList,
    )
    msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await wcb.send(msg)


@songinfo.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    song_id = re.search(r"\d+", msg).group(0)
    songList, _ = await get_music_data()
    song_info = find_song_by_id(song_id, songList)
    if not song_info:
        msg = MessageSegment.text(f"迪拉熊没找到 {song_id} 对应的乐曲")
    else:
        await songinfo.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = await music_info(song_id=song_id, qq=qq)
        msg = MessageSegment.image(img)
    await songinfo.send((MessageSegment.reply(event.message_id), msg))


@playinfo.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    song = msg.replace("info", "").strip()
    if not song:
        await playinfo.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("请准确输入乐曲的id或别名哦"),
            )
        )
    rep_ids = find_songid_by_alias(song)
    songList, _ = await get_music_data()
    song_info = find_song_by_id(song, songList)
    if rep_ids:
        song_id = str(rep_ids[0])
    elif song_info:
        song_id = song
    else:
        await playinfo.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text(
                    f"迪拉熊没找到 {song} 对应的乐曲\n请准确输入乐曲的id或别名"
                ),
            )
        )
    img = await play_info(song_id=str(song_id), qq=qq)
    if isinstance(img, str):
        msg = MessageSegment.text(img)
    else:
        msg = MessageSegment.image(img)
    await playinfo.send((MessageSegment.reply(event.message_id), msg))


@playmp3.handle()
async def _(event: GroupMessageEvent):
    msg = str(event.get_message())
    song = msg.replace("dlx点歌", "").strip()
    if not song:
        await playmp3.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("请准确输入乐曲的id或别名哦"),
            )
        )
    rep_ids = find_songid_by_alias(song)
    songList, _ = await get_music_data()
    if rep_ids:
        song_id = str(rep_ids[0])
        songinfo = find_song_by_id(song_id=song_id, songList=songList)
        if not songinfo:
            await playmp3.finish(
                (
                    MessageSegment.reply(event.message_id),
                    MessageSegment.text("请准确输入乐曲的id或别名哦"),
                )
            )
        songname = songinfo["title"]
        await playmp3.send(
            MessageSegment.text(f"迪拉熊找到了~\n正在播放{song_id}.{songname}")
        )
        with open(f"./src/maimai/mp3/{song_id}.mp3", "rb") as file:
            file_bytes = file.read()
        await playmp3.send(MessageSegment.record(file_bytes))
    else:
        songinfo = find_song_by_id(song, songList)
        if songinfo:
            song_id = song
            songname = songinfo["title"]
            await playmp3.send(
                MessageSegment.text(f"迪拉熊找到了~\n正在播放{song_id}.{songname}")
            )
            with open(f"./src/maimai/mp3/{song_id}.mp3", "rb") as file:
                file_bytes = file.read()
            await playmp3.send(MessageSegment.record(file_bytes))
        else:
            await playmp3.send(
                (
                    MessageSegment.reply(event.message_id),
                    MessageSegment.text("迪拉熊好像没找到，换一个试试吧~"),
                )
            )


@randomsong.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r"^随(个|歌) ?(绿|黄|红|紫|白)?(\d+)(\.\d|\+)?"
    match = re.match(pattern, msg)
    level_label = match.group(2)
    if level_label:
        level_index = (
            level_label.replace("绿", "0")
            .replace("黄", "1")
            .replace("红", "2")
            .replace("紫", "3")
            .replace("白", "4")
        )
        level_index = int(level_index)
    else:
        level_index = None
    level = match.group(3)
    if match.group(4):
        level += match.group(4)
    s_type = "level"
    if "." in level:
        s_type = "ds"
    s_songs = []
    songList, _ = await get_music_data()
    for song in songList:
        song_id = song["id"]
        s_list = song[s_type]
        if s_type == "ds":
            level = float(level)
        if level_index:
            if len(s_list) > level_index:
                if level == s_list[level_index]:
                    s_songs.append(song_id)
        elif level in s_list:
            s_songs.append(song_id)
    if len(s_songs) == 0:
        msg = MessageSegment.text("迪拉熊没有找到符合条件的乐曲")
        await randomsong.finish((MessageSegment.reply(event.message_id), msg))
    song_id = random.choice(s_songs)
    img = await music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await randomsong.send((MessageSegment.reply(event.message_id), msg))


@maiwhat.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    songList, _ = await get_music_data()
    song = random.choice(songList)
    song_id = song["id"]
    img = await music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await maiwhat.send((MessageSegment.reply(event.message_id), msg))


@whatSong.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    match = re.match(r"/?(search|查歌)\s*(.*)|(.*?)是什么歌", msg, re.I)
    if match:
        if match.group(2):
            name = match.group(2)
        elif match.group(3):
            name = match.group(3)
        else:
            await whatSong.finish(
                (
                    MessageSegment.reply(event.message_id),
                    MessageSegment.text("迪拉熊什么都没找到……"),
                )
            )

        rep_ids = find_songid_by_alias(name)
        if not rep_ids:
            msg = (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊什么都没找到……"),
            )
        elif len(rep_ids) == 1:
            img = await music_info(rep_ids[0], qq=qq)
            msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
        else:
            output_lst = f"迪拉熊找到的 {name} 结果如下："
            songList, _ = await get_music_data()
            for song_id in rep_ids:
                song_info = find_song_by_id(song_id, songList)
                if song_info:
                    song_title = song_info["title"]
                    output_lst += f"\n{song_id} - {song_title}"
            msg = MessageSegment.text(output_lst)
        await whatSong.send(msg)


# 查看别名
@aliasSearch.handle()
async def _(event: GroupMessageEvent):
    msg = str(event.get_message())
    song_id = re.search(r"\d+", msg).group(0)

    with open("./src/maimai/aliasList.json", "r") as f:
        alias_list = json.load(f)
    alias = alias_list.get(song_id, None)
    if not alias:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                f"迪拉熊没找到 {song_id} 对应的乐曲\n请准确输入乐曲的id"
            ),
        )
    else:
        song_name = alias["Name"]
        song_alias = "\n".join(alias["Alias"])
        msg = MessageSegment.text(
            f"迪拉熊找到的 {song_id}.{song_name} 的别名有：\n{song_alias}"
        )
    await aliasSearch.send(msg)


@aliasAdd.handle()
async def _(event: GroupMessageEvent):
    msg = str(event.get_message())
    args = re.search(r"^添加别名 ?(\d+) ?(.+)$", msg)
    song_id = args.group(1)
    alias_name = args.group(2)

    with open("./src/maimai/aliasList.json", "r") as f:
        alias_list = json.load(f)
    song_alias = alias_list.get(song_id, None)
    if not song_alias:
        msg = MessageSegment.text(
            f"迪拉熊没找到 {song_id} 对应的乐曲\n请准确输入乐曲的id"
        )
    elif alias_name in alias_list[str(song_id)]["Alias"]:
        msg = MessageSegment.text(
            f"迪拉熊发现 {song_id}.{song_alias['Name']} 已有该别名：{alias_name}"
        )
    else:
        alias_list[str(song_id)]["Alias"].append(alias_name)
        with open("./src/maimai/aliasList.json", "w", encoding="utf-8") as f:
            json.dump(alias_list, f, ensure_ascii=False, indent=4)
        msg = MessageSegment.text(
            f"迪拉熊已将 {alias_name} 添加到 {song_id}.{song_alias['Name']} 的别名"
        )
    await aliasAdd.send((MessageSegment.reply(event.message_id), msg))


@aliasDel.handle()
async def _(event: GroupMessageEvent):
    msg = str(event.get_message())
    args = re.search(r"^删除别名 ?(\d+) ?(.+)$", msg)
    song_id = args.group(1)
    alias_name = args.group(2)

    with open("./src/maimai/aliasList.json", "r") as f:
        alias_list = json.load(f)
    song_alias = alias_list.get(song_id, None)
    if not song_alias:
        msg = MessageSegment.text(
            f"迪拉熊没找到 {song_id} 对应的乐曲\n请准确输入乐曲的id"
        )
    elif alias_name not in alias_list[str(song_id)]["Alias"]:
        msg = MessageSegment.text(
            f"迪拉熊发现 {song_id}.{song_alias['Name']} 没有该别名：{alias_name}"
        )
    else:
        alias_list[str(song_id)]["Alias"].remove(alias_name)
        with open("./src/maimai/aliasList.json", "w", encoding="utf-8") as f:
            json.dump(alias_list, f, ensure_ascii=False, indent=4)
        msg = MessageSegment.text(
            f"迪拉熊已从 {song_id}.{song_alias['Name']} 的别名中移除 {alias_name}"
        )
    await aliasDel.send((MessageSegment.reply(event.message_id), msg))


@all_frame.handle()
async def _():
    path = "./src/maimai/allFrame.png"
    await all_frame.send(MessageSegment.image(Path(path)))


@all_plate.handle()
async def _():
    path = "./src/maimai/allPlate.png"
    await all_plate.send(MessageSegment.image(Path(path)))


@set_plate.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    id = re.search(r"\d+", msg).group(0)
    dir_path = "./src/maimai/Plate/"
    file_name = f"UI_Plate_{id}.png"
    file_path = Path(dir_path) / file_name
    if os.path.exists(file_path):
        with shelve.open("./data/maimai/b50_config.db") as config:
            if qq not in config:
                config.setdefault(qq, {"plate": id})
            else:
                cfg = config[qq]
                if "plate" not in config[qq]:
                    cfg.setdefault("plate", id)
                else:
                    cfg["plate"] = id
                config[qq] = cfg

        msg = MessageSegment.text("迪拉熊帮你换好啦~")
    else:
        msg = MessageSegment.text("迪拉熊没换成功，再试试吧~（输入id有误）")
    await set_plate.send((MessageSegment.reply(event.message_id), msg))


@set_frame.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    id = re.search(r"\d+", msg).group(0)
    dir_path = "./src/maimai/Frame/"
    file_name = f"UI_Frame_{id}.png"
    file_path = Path(dir_path) / file_name
    if os.path.exists(file_path):
        with shelve.open("./data/maimai/b50_config.db") as config:
            if qq not in config:
                config.setdefault(qq, {"frame": id})
            else:
                cfg = config[qq]
                if "frame" not in config[qq]:
                    cfg.setdefault("frame", id)
                else:
                    cfg["frame"] = id
                config[qq] = cfg

        msg = MessageSegment.text("迪拉熊帮你换好啦~")
    else:
        msg = MessageSegment.text("迪拉熊没换成功，再试试吧~（输入id有误）")
    await set_frame.send((MessageSegment.reply(event.message_id), msg))


@ratj_on.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with shelve.open("./data/maimai/b50_config.db") as config:
        if qq not in config:
            config.setdefault(qq, {"rating_tj": True})
        else:
            cfg = config[qq]
            if "rating_tj" not in config[qq]:
                cfg.setdefault("rating_tj", True)
            else:
                cfg["rating_tj"] = True
            config[qq] = cfg

    msg = MessageSegment.text("迪拉熊帮你启用了分数推荐~")
    await ratj_on.send((MessageSegment.reply(event.message_id), msg))


@ratj_off.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with shelve.open("./data/maimai/b50_config.db") as config:
        if qq not in config:
            config.setdefault(qq, {"rating_tj": False})
        else:
            cfg = config[qq]
            if "rating_tj" not in config[qq]:
                cfg.setdefault("rating_tj", False)
            else:
                cfg["rating_tj"] = False
            config[qq] = cfg

    msg = MessageSegment.text("迪拉熊帮你禁用了分数推荐~")
    await ratj_off.send((MessageSegment.reply(event.message_id), msg))


@allow_other_on.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with shelve.open("./data/maimai/b50_config.db") as config:
        if qq not in config:
            config.setdefault(qq, {"allow_other": True})
        else:
            cfg = config[qq]
            if "allow_other" not in config[qq]:
                cfg.setdefault("allow_other", True)
            else:
                cfg["allow_other"] = True
            config[qq] = cfg

    msg = MessageSegment.text("迪拉熊帮你启用了代查~")
    await allow_other_on.send((MessageSegment.reply(event.message_id), msg))


@allow_other_off.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with shelve.open("./data/maimai/b50_config.db") as config:
        if qq not in config:
            config.setdefault(qq, {"allow_other": False})
        else:
            cfg = config[qq]
            if "allow_other" not in config[qq]:
                cfg.setdefault("allow_other", False)
            else:
                cfg["allow_other"] = False
            config[qq] = cfg

    msg = MessageSegment.text("迪拉熊帮你禁用了代查~")
    await allow_other_off.send((MessageSegment.reply(event.message_id), msg))
