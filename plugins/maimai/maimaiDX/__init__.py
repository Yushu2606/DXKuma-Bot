import json
import os
import random
import re
import shelve
from pathlib import Path

import requests
from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

from util.DivingFish import get_player_records
from .GenB50 import generateb50, generate_wcb, ratings
from .MusicInfo import music_info, play_info

best50 = on_regex(r"^(dlx50|dlxb50)( ?\[CQ:at,qq=(\d+)\] ?)?$")
ap50 = on_regex(r"^dlxap( ?\[CQ:at,qq=(\d+)\] ?)?$")
fc50 = on_regex(r"^dlxfc( ?\[CQ:at,qq=(\d+)\] ?)?$")
fit50 = on_regex(r"^dlxfit( ?\[CQ:at,qq=(\d+)\] ?)?$")

songinfo = on_regex(r"^id ?(\d+)$")
playinfo = on_regex(r"^info ?(.+)$")
playmp3 = on_regex(r"^dlx点歌 ?(.+)$")
randomsong = on_regex(r"^随(个|歌) ?(绿|黄|红|紫|白)?(\d+)(\.\d|\+)?$")
maiwhat = on_fullmatch("mai什么")

wcb = on_regex(r"^完成表 ?((\d+)(\.\d|\+)?)( ([0-9]+))?$")

whatSong = on_regex(r"^((search|查歌) ?(.+)|(.+)是什么歌)$")
aliasSearch = on_regex(r"^(查看别名 ?(\d+)|(\d+)有什么别名)$")

aliasAdd = on_regex(r"^添?加别名 ?(\d+) ?(.+)$")
aliasDel = on_regex(r"^删除?别名 ?(\d+) ?(.+)$")

all_plate = on_regex(r"^(plate|看牌子)$")
all_frame = on_regex(r"^(frame|看底板)$")

set_plate = on_regex(r"^(setplate|设置牌子) ?(\d{6})$")
set_frame = on_regex(r"^(setframe|设置底板) ?(\d{6})$")

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
                or str(name).lower() == str(info["Name"]).lower()
        ):
            matched_ids.append(id)

    # 芝士排序
    sorted_matched_ids = sorted(matched_ids, key=int)

    # 芝士输出
    return sorted_matched_ids


# id查歌
def find_song_by_id(song_id, songList=None):
    if not songList:
        songList = requests.get(
            "https://www.diving-fish.com/api/maimaidxprober/music_data"
        ).json()
    for song in songList:
        if song["id"] == song_id:
            return song

    # 如果没有找到对应 id 的歌曲，返回 None
    return None


def records_to_b50(
        records: list, rules: list | None = None, is_fit: bool = False
):
    if not rules:
        b_records = records
    else:
        b_records = []
        for record in records:
            if record["fc"] in rules:
                b_records.append(record)

    sd = []
    dx = []
    songList = requests.get(
        "https://www.diving-fish.com/api/maimaidxprober/music_data"
    ).json()
    charts = requests.get(
        "https://www.diving-fish.com/api/maimaidxprober/chart_stats"
    ).json()
    for record in b_records:
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
        if record["ra"] <= 0:
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
                "迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status == 200:
        records = data["records"]
        if not records:
            if match:
                msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
            await best50.finish((MessageSegment.reply(event.message_id), msg))
        nickname = data["nickname"]
        dani = data["additional_rating"]
        b35, b15 = records_to_b50(records)
        await best50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = generateb50(
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
                "迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status == 200:
        records = data["records"]
        if not records:
            if match:
                msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
            await ap50.finish((MessageSegment.reply(event.message_id), msg))
        ap35, ap15 = records_to_b50(records, ["ap", "app"])
        if not ap35 and not ap15:
            if match:
                msg = MessageSegment.text("他还没有ap任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有ap任何一个谱面呢~")
            await ap50.finish((MessageSegment.reply(event.message_id), msg))
        nickname = data["nickname"]
        dani = data["additional_rating"]
        await ap50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = generateb50(
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
                "迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status == 200:
        records = data["records"]
        if not records:
            if match:
                msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
            await fc50.finish((MessageSegment.reply(event.message_id), msg))
        fc35, fc15 = records_to_b50(records, ["fc", "fcp"])
        if not fc35 and not fc15:
            if match:
                msg = MessageSegment.text("他还没有fc任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有fc任何一个谱面呢~")
            await fc50.finish((MessageSegment.reply(event.message_id), msg))
        nickname = data["nickname"]
        dani = data["additional_rating"]
        await fc50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = generateb50(
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
                "迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/"
            ),
        )
    elif status == 200:
        records = data["records"]
        if not records:
            if match:
                msg = MessageSegment.text("他还没有游玩任何一个谱面呢~")
            else:
                msg = MessageSegment.text("你还没有游玩任何一个谱面呢~")
            await fit50.finish((MessageSegment.reply(event.message_id), msg))
        nickname = data["nickname"]
        dani = data["additional_rating"]
        b35, b15 = records_to_b50(records, is_fit=True)
        await fit50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = generateb50(
            b35=b35, b15=b15, nickname=nickname, qq=target_qq, dani=dani, type="fit50"
        )
        msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await fit50.send(msg)


@wcb.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r"^(完成表) ?((\d+)(\.\d|\+)?)( ([0-9]+))?"
    match = re.match(pattern, msg)
    if match is None:
        await wcb.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊觉得输入的信息好像有点问题呢"),
            )
        )
    level = match.group(2)
    if match.group(5) is not None:
        page = int(match.group(5).strip())
        if page <= 0:
            page = 1
    else:
        page = 1
    img = await generate_wcb(qq=qq, level=level, page=page)
    if isinstance(img, str):
        msg = MessageSegment.text(img)
    else:
        msg = MessageSegment.image(img)
    await wcb.send((MessageSegment.reply(event.message_id), msg))


@songinfo.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    song_id = re.search(r"\d+", msg).group(0)
    song_info = find_song_by_id(song_id)
    if not song_info:
        msg = MessageSegment.text(f"迪拉熊没找到 {song_id} 对应的乐曲")
    else:
        await songinfo.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊绘制中，稍等一下mai~"),
            )
        )
        img = music_info(song_id=song_id, qq=qq)
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
    song_info = find_song_by_id(song)
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
    img = play_info(song_id=str(song_id), qq=qq)
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
    if rep_ids:
        song_id = str(rep_ids[0])
        songinfo = find_song_by_id(song_id=song_id)
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
        songinfo = find_song_by_id(song)
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
    if match.group(4) is not None:
        level += match.group(4)
    s_type = "level"
    if "." in level:
        s_type = "ds"
    s_songs = []
    songList = requests.get(
        "https://www.diving-fish.com/api/maimaidxprober/music_data"
    ).json()
    for song in songList:
        song_id = song["id"]
        s_list = song[s_type]
        if s_type == "ds":
            level = float(level)
        if level_index is not None:
            if len(s_list) > level_index:
                if level == s_list[level_index]:
                    s_songs.append(song_id)
        elif level in s_list:
            s_songs.append(song_id)
    if len(s_songs) == 0:
        msg = MessageSegment.text("迪拉熊没有找到符合条件的乐曲")
        await randomsong.finish((MessageSegment.reply(event.message_id), msg))
    song_id = random.choice(s_songs)
    img = music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await randomsong.send((MessageSegment.reply(event.message_id), msg))


@maiwhat.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    songList = requests.get(
        "https://www.diving-fish.com/api/maimaidxprober/music_data"
    ).json()
    song = random.choice(songList)
    song_id = song["id"]
    img = music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await maiwhat.send((MessageSegment.reply(event.message_id), msg))


@whatSong.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    match = re.match(r"/?(search|查歌)\s*(.*)|(.*?)是什么歌", msg, re.IGNORECASE)
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
            img = music_info(rep_ids[0], qq=qq)
            msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
        else:
            output_lst = f"迪拉熊找到的 {name} 结果如下："
            songList = requests.get(
                "https://www.diving-fish.com/api/maimaidxprober/music_data"
            ).json()
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
