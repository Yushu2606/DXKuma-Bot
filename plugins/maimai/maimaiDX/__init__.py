import json
import os
import random
import re
from pathlib import Path

from arclet.alconna import Alconna, Args
from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot_plugin_alconna import on_alconna, AlconnaMatch, Match

from util.DivingFish import get_player_records
from .GenB50 import generateb50, generate_wcb, songList, charts, ratings
from .MusicInfo import music_info, play_info

best50 = on_regex(r'^(dlx50|dlxb50)')
ap50 = on_regex(r'^(dlxap)')
fc50 = on_regex(r'^(dlxfc)')
fit50 = on_regex(r'^(dlxfit)')

songinfo = on_regex(r'^(id) ?(\d+)$')
playinfo = on_regex(r'^(info) ?(.*)$')
playmp3 = on_regex(r'^(dlx点歌) ?(.*)$')
randomsong = on_regex(r'^随(个|歌) ?(绿|黄|红|紫|白)?(\d+)(\.\d|\+)?')
maiwhat = on_regex(r'^(mai什么)')

wcb = on_regex(r'^(完成表)')

whatSong = on_regex(r'/?(search|查歌)\s*(.*)|(.*?)是什么歌')
aliasSearch = on_regex(r'^(查看别名) ?(\d+)$|(\d+)(有什么别名)$')

aliasAdd_alc = Alconna('添加别名', Args["songId", int], Args['alias', str])
aliasAdd = on_alconna(aliasAdd_alc, auto_send_output=True)

aliasDel_alc = Alconna('删除别名', Args["songId", int], Args['alias', str])
aliasDel = on_alconna(aliasDel_alc, auto_send_output=True)

all_plate = on_regex(r'^(plate|看牌子)$')
all_frame = on_regex(r'^(frame|看底板)$')

set_plate = on_regex(r'(setplate|设置牌子) ?(\d{6})$')
set_frame = on_regex(r'(setframe|设置底板) ?(\d{6})$')

ratj_on = on_fullmatch('开启分数推荐')
ratj_off = on_fullmatch('关闭分数推荐')


# 根据乐曲别名查询乐曲id列表
async def find_songid_by_alias(name):
    # 读取别名文件
    with open('./src/maimai/aliasList.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 芝士id列表
    matched_ids = []

    # 芝士查找
    for id, info in data.items():
        if (
                name in info['Alias']
                or name in info['Name']
                or str(name).lower() == str(info['Name']).lower()
        ):
            matched_ids.append(id)

    # 芝士排序
    sorted_matched_ids = sorted(matched_ids, key=int)

    # 芝士输出
    return sorted_matched_ids


# id查歌
async def find_song_by_id(song_id):
    for song in songList:
        if song['id'] == song_id:
            return song

    # 如果没有找到对应 id 的歌曲，返回 None
    return None


async def records_to_b50(
        records: list, rules: list | None = None, is_fit: bool = False
):
    if not rules:
        b_records = records
    else:
        b_records = []
        for record in records:
            if record['fc'] in rules:
                b_records.append(record)

    sd = []
    dx = []
    for record in b_records:
        song_id = record['song_id']
        is_new = [
            d["basic_info"]["is_new"] for d in songList if d["id"] == str(song_id)
        ]
        if is_fit:
            fit_diff = get_fit_diff(
                str(record["song_id"]), record["level_index"], record["ds"]
            )
            record["ds"] = round(fit_diff, 2)
            record["ra"] = int(
                fit_diff * record["achievements"] * get_ra_in(record["rate"]) * 0.01
            )
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


def get_fit_diff(song_id: str, level_index: int, ds: float) -> float:
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
    if match:
        target_qq = match.group(1)
    else:
        target_qq = event.get_user_id()
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                '迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/'
            ),
        )
    elif status == 200:
        records = data['records']
        if not records:
            if match:
                msg = MessageSegment.text('他还没有游玩任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有游玩任何一个谱面呢~')
            await best50.finish((MessageSegment.reply(event.message_id), msg))
        await best50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text('迪拉熊绘制中，稍等一下mai~'),
            )
        )
        nickname = data['nickname']
        dani = data['additional_rating']
        b35, b15 = await records_to_b50(records)
        img = await generateb50(
            b35=b35, b15=b15, nickname=nickname, qq=target_qq, dani=dani, type='b50'
        )
        msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await best50.send(msg)


@ap50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if match:
        target_qq = match.group(1)
    else:
        target_qq = event.get_user_id()
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                '迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/'
            ),
        )
    elif status == 200:
        records = data['records']
        if not records:
            if match:
                msg = MessageSegment.text('他还没有游玩任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有游玩任何一个谱面呢~')
            await ap50.finish((MessageSegment.reply(event.message_id), msg))
        ap35, ap15 = await records_to_b50(records, ['ap', 'app'])
        if not ap35 and not ap15:
            if match:
                msg = MessageSegment.text('他还没有ap任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有ap任何一个谱面呢~')
            await ap50.finish((MessageSegment.reply(event.message_id), msg))
        await ap50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text('迪拉熊绘制中，稍等一下mai~'),
            )
        )
        nickname = data['nickname']
        dani = data['additional_rating']
        img = await generateb50(
            b35=ap35,
            b15=ap15,
            nickname=nickname,
            qq=target_qq,
            dani=dani,
            type='ap50',
        )
        msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await ap50.send(msg)


@fc50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if match:
        target_qq = match.group(1)
    else:
        target_qq = event.get_user_id()
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                '迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/'
            ),
        )
    elif status == 200:
        records = data['records']
        if not records:
            if match:
                msg = MessageSegment.text('他还没有游玩任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有游玩任何一个谱面呢~')
            await fc50.finish((MessageSegment.reply(event.message_id), msg))
        fc35, fc15 = await records_to_b50(records, ['fc', 'fcp'])
        if not fc35 and not fc15:
            if match:
                msg = MessageSegment.text('他还没有fc任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有fc任何一个谱面呢~')
            await fc50.finish((MessageSegment.reply(event.message_id), msg))
        await fc50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text('迪拉熊绘制中，稍等一下mai~'),
            )
        )
        nickname = data['nickname']
        dani = data['additional_rating']
        img = await generateb50(
            b35=fc35,
            b15=fc15,
            nickname=nickname,
            qq=target_qq,
            dani=dani,
            type='fc50',
        )
        msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await fc50.send(msg)


@fit50.handle()
async def _(event: GroupMessageEvent):
    msg_text = str(event.raw_message)
    pattern = r"\[CQ:at,qq=(\d+)\]"
    match = re.search(pattern, msg_text)
    if match:
        target_qq = match.group(1)
    else:
        target_qq = event.get_user_id()
    data, status = await get_player_records(target_qq)
    if status == 400:
        msg = (
            MessageSegment.reply(event.message_id),
            MessageSegment.text(
                '迪拉熊未找到用户信息，可能是没有绑定查分器\n查分器网址：https://www.diving-fish.com/maimaidx/prober/'
            ),
        )
    elif status == 200:
        records = data['records']
        if not records:
            if match:
                msg = MessageSegment.text('他还没有游玩任何一个谱面呢~')
            else:
                msg = MessageSegment.text('你还没有游玩任何一个谱面呢~')
            await fit50.finish((MessageSegment.reply(event.message_id), msg))
        await fit50.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text('迪拉熊绘制中，稍等一下mai~'),
            )
        )
        nickname = data['nickname']
        dani = data['additional_rating']
        b35, b15 = await records_to_b50(records, is_fit=True)
        img = await generateb50(
            b35=b35, b15=b15, nickname=nickname, qq=target_qq, dani=dani, type='fit50'
        )
        msg = (MessageSegment.reply(event.message_id), MessageSegment.image(img))
    await fit50.send(msg)


@wcb.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    pattern = r'^(完成表) ?((\d+)(\.\d|\+)?)( ([0-9]+))?'
    match = re.match(pattern, msg)
    if match is None:
        wcb.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text('迪拉熊觉得输入的信息好像有点问题呢'),
            )
        )
    level = match.group(2)
    if match.group(5) is not None:
        page = int(match.group(5).strip())
        if page <= 0:
            page = 1
    else:
        page = 1
    await wcb.send(
        (
            MessageSegment.reply(event.message_id),
            MessageSegment.text('迪拉熊绘制中，稍等一下mai~'),
        )
    )
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
    song_id = re.search(r'\d+', msg).group(0)
    song_info = await find_song_by_id(song_id)
    if not song_info:
        msg = MessageSegment.text(f"迪拉熊没找到 {song_id} 对应的乐曲")
    else:
        img = await music_info(song_id=song_id, qq=qq)
        msg = MessageSegment.image(img)
    await songinfo.send((MessageSegment.reply(event.message_id), msg))


@playinfo.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    song = msg.replace('info', '').strip()
    if not song:
        await playinfo.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("请准确输入乐曲的id或别名哦"),
            )
        )
    rep_ids = await find_songid_by_alias(song)
    song_info = await find_song_by_id(song)
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
    song = msg.replace('dlx点歌', '').strip()
    if not song:
        await playmp3.finish(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("请准确输入乐曲的id或别名哦"),
            )
        )
    rep_ids = await find_songid_by_alias(song)
    song_info = await find_song_by_id(song)
    if rep_ids:
        song_id = str(rep_ids[0])
        songinfo = await find_song_by_id(song_id=song_id)
        if not songinfo:
            await playmp3.finish(
                (
                    MessageSegment.reply(event.message_id),
                    MessageSegment.text("请准确输入乐曲的id或别名哦"),
                )
            )
        songname = songinfo['title']
        await playmp3.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text(f'迪拉熊找到了~\n正在播放{song_id}.{songname}'),
            )
        )
        with open(f'./src/maimai/mp3/{song_id}.mp3', 'rb') as file:
            file_bytes = file.read()
        await playmp3.send(MessageSegment.record(file_bytes))
    elif song_info:
        song_id = song
        songinfo = await find_song_by_id(song_id=song_id)
        songname = songinfo['title']
        await playmp3.send(
            (
                MessageSegment.reply(event.message_id),
                MessageSegment.text(f'迪拉熊找到了~\n正在播放{song_id}.{songname}'),
            )
        )
        with open(f'./src/maimai/mp3/{song_id}.mp3', 'rb') as file:
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
    pattern = r'^随(个|歌) ?(绿|黄|红|紫|白)?(\d+)(\.\d|\+)?'
    match = re.match(pattern, msg)
    level_label = match.group(2)
    if level_label:
        level_index = (
            level_label.replace('绿', '0')
            .replace('黄', '1')
            .replace('红', '2')
            .replace('紫', '3')
            .replace('白', '4')
        )
        level_index = int(level_index)
    else:
        level_index = None
    level = match.group(3)
    if match.group(4) is not None:
        level += match.group(4)
    s_type = 'level'
    if '.' in level:
        s_type = 'ds'
    s_songs = []
    for song in songList:
        song_id = song['id']
        s_list = song[s_type]
        if s_type == 'ds':
            level = float(level)
        if level_index is not None:
            if len(s_list) > level_index:
                if level == s_list[level_index]:
                    s_songs.append(song_id)
        elif level in s_list:
            s_songs.append(song_id)
    if len(s_songs) == 0:
        msg = MessageSegment.text('迪拉熊没有找到符合条件的乐曲')
        await randomsong.finish((MessageSegment.reply(event.message_id), msg))
    song_id = random.choice(s_songs)
    img = await music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await randomsong.send((MessageSegment.reply(event.message_id), msg))


@maiwhat.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    song = random.choice(songList)
    song_id = song['id']
    img = await music_info(song_id=song_id, qq=qq)
    msg = MessageSegment.image(img)
    await randomsong.send((MessageSegment.reply(event.message_id), msg))


@whatSong.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.message)
    match = re.match(r'/?(search|查歌)\s*(.*)|(.*?)是什么歌', msg, re.IGNORECASE)
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

        rep_ids = await find_songid_by_alias(name)
        if not rep_ids:
            msg = (
                MessageSegment.reply(event.message_id),
                MessageSegment.text("迪拉熊什么都没找到……"),
            )
        elif len(rep_ids) == 1:
            img = await music_info(rep_ids[0], qq=qq)
            msg = MessageSegment.image(img)
        else:
            output_lst = f'迪拉熊找到的 {name} 结果如下：'
            for song_id in rep_ids:
                song_info = await find_song_by_id(song_id)
                if song_info:
                    song_title = song_info["title"]
                    output_lst += f"\n{song_id} - {song_title}"
            msg = MessageSegment.text(output_lst)
        await whatSong.send(msg)


# 查看别名
@aliasSearch.handle()
async def _(event: GroupMessageEvent):
    msg = str(event.get_message())
    song_id = re.search(r'\d+', msg).group(0)
    with open('./src/maimai/aliasList.json', 'r') as f:
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
        song_name = alias['Name']
        song_alias = '\n'.join(alias['Alias'])
        msg = MessageSegment.text(
            f'迪拉熊找到的 {song_id}.{song_name} 的别名有：\n{song_alias}'
        )
    await aliasSearch.send(msg)


@aliasAdd.handle()
async def _(
        event: GroupMessageEvent,
        song_id: Match[int] = AlconnaMatch("songId"),
        alias: Match[str] = AlconnaMatch("alias"),
):
    song_id = str(song_id.result)
    alias_name = alias.result
    with open('./src/maimai/aliasList.json', 'r') as f:
        alias_list = json.load(f)
    song_alias = alias_list.get(song_id, None)
    if not song_alias:
        msg = MessageSegment.text(
            f"迪拉熊没找到 {song_id} 对应的乐曲\n请准确输入乐曲的id"
        )
    elif alias_name in alias_list[str(song_id)]['Alias']:
        msg = MessageSegment.text(
            f"迪拉熊发现 {song_id}.{song_alias['Name']} 已有该别名：{alias_name}"
        )
    else:
        alias_list[str(song_id)]['Alias'].append(alias_name)
        with open('./src/maimai/aliasList.json', 'w', encoding='utf-8') as f:
            json.dump(alias_list, f, ensure_ascii=False, indent=4)
        msg = MessageSegment.text(
            f"迪拉熊已将 {alias_name} 添加到 {song_id}.{song_alias['Name']} 的别名"
        )
    await aliasAdd.send((MessageSegment.reply(event.message_id), msg))


@aliasDel.handle()
async def _(
        event: GroupMessageEvent,
        song_id: Match[int] = AlconnaMatch("songId"),
        alias: Match[str] = AlconnaMatch("alias"),
):
    song_id = str(song_id.result)
    alias_name = alias.result
    with open('./src/maimai/aliasList.json', 'r') as f:
        alias_list = json.load(f)
    song_alias = alias_list.get(song_id, None)
    if not song_alias:
        msg = MessageSegment.text(
            f"迪拉熊没找到 {song_id} 对应的乐曲\n请准确输入乐曲的id"
        )
    elif alias_name not in alias_list[str(song_id)]['Alias']:
        msg = MessageSegment.text(
            f"迪拉熊发现 {song_id}.{song_alias['Name']} 没有该别名：{alias_name}"
        )
    else:
        alias_list[str(song_id)]['Alias'].remove(alias_name)
        with open('./src/maimai/aliasList.json', 'w', encoding='utf-8') as f:
            json.dump(alias_list, f, ensure_ascii=False, indent=4)
        msg = MessageSegment.text(
            f"迪拉熊已从 {song_id}.{song_alias['Name']} 的别名中移除 {alias_name}"
        )
    await aliasDel.send((MessageSegment.reply(event.message_id), msg))


@all_frame.handle()
async def _():
    path = './src/maimai/allFrame.png'
    await all_frame.send(MessageSegment.image(Path(path)))


@all_plate.handle()
async def _():
    path = './src/maimai/allPlate.png'
    await all_plate.send(MessageSegment.image(Path(path)))


@set_plate.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    id = re.search(r'\d+', msg).group(0)
    dir_path = "./src/maimai/Plate/"
    file_name = f"UI_Plate_{id}.png"
    file_path = Path(dir_path) / file_name
    if os.path.exists(file_path):
        with open('./data/maimai/b50_config.json', 'r') as f:
            config = json.load(f)

        if qq not in config:
            config.setdefault(
                qq, {'frame': '200502', 'plate': '000101', 'rating_tj': True}
            )
        config[qq]['plate'] = id

        with open('./data/maimai/b50_config.json', 'w') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        msg = MessageSegment.text('迪拉熊帮你换好啦~')
    else:
        msg = MessageSegment.text('迪拉熊没换成功，再试试吧~（输入id有误）')
    await set_plate.send((MessageSegment.reply(event.message_id), msg))


@set_frame.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    msg = str(event.get_message())
    id = re.search(r'\d+', msg).group(0)
    dir_path = "./src/maimai/Frame/"
    file_name = f"UI_Frame_{id}.png"
    file_path = Path(dir_path) / file_name
    if os.path.exists(file_path):
        with open('./data/maimai/b50_config.json', 'r') as f:
            config = json.load(f)

        if qq not in config:
            config.setdefault(
                qq, {'frame': '200502', 'plate': '000101', 'rating_tj': True}
            )
        config[qq]['frame'] = id

        with open('./data/maimai/b50_config.json', 'w') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

        msg = MessageSegment.text('迪拉熊帮你换好啦~')
    else:
        msg = MessageSegment.text('迪拉熊没换成功，再试试吧~（输入id有误）')
    await set_plate.send((MessageSegment.reply(event.message_id), msg))


@ratj_on.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with open('./data/maimai/b50_config.json', 'r') as f:
        config = json.load(f)

    if qq not in config:
        config.setdefault(qq, {'frame': '200502', 'plate': '000101', 'rating_tj': True})
    config[qq]['rating_tj'] = True

    with open('./data/maimai/b50_config.json', 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    msg = MessageSegment.text('迪拉熊已为你开启分数推荐')
    await ratj_on.send((MessageSegment.reply(event.message_id), msg))


@ratj_off.handle()
async def _(event: GroupMessageEvent):
    qq = event.get_user_id()
    with open('./data/maimai/b50_config.json', 'r') as f:
        config = json.load(f)

    if qq not in config:
        config.setdefault(qq, {'frame': '200502', 'plate': '000101', 'rating_tj': True})
    config[qq]['rating_tj'] = False

    with open('./data/maimai/b50_config.json', 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    msg = MessageSegment.text('迪拉熊已为你关闭分数推荐')
    await ratj_off.send((MessageSegment.reply(event.message_id), msg))
