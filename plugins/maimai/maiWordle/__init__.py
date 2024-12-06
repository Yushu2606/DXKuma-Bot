from nonebot import on_command,on_message,on_regex
import re
from nonebot.adapters.onebot.v11 import GroupMessageEvent,MessageSegment,Bot
from .alias_db_handle import alias_handle as otherName
from .maimaidx_music import total_list
from nonebot.typing import T_State
from .database import openchars
from .utils import generate_message_state,check_music_id,generate_success_state

start_open_chars = on_command('dlx猜歌')
@start_open_chars.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    is_exist,game_data = openchars.start(group_id)
    if not is_exist:
        await start_open_chars.send("准备开始猜歌游戏~\n输入“开（字母）”开出字母\n输入“跳过猜歌”跳过\n输入“结束猜歌”结束\n直接发送别名或id即可猜歌")
        is_game_over,game_state,char_all_open,game_data = generate_message_state(game_data)
        # openchars.update_game_data(group_id,game_data)
        await start_open_chars.send(game_state)
        # if is_game_over:
        #     openchars.game_over(group_id)
        #     await start_open_chars.send('全部答对啦，恭喜各位🎉\n本轮猜歌已结束，可发送“dlx猜歌”再次游玩')


open_chars = on_regex(r"^开 ?(.+)$", re.I)
@open_chars.handle()
async def _(event: GroupMessageEvent):
    msg = event.get_plaintext()
    char = msg.replace("开", "").strip()
    group_id = event.group_id

    if len(char) != 1:
        await open_chars.finish()

    is_start,game_data = openchars.open_char(group_id,char)
    if is_start is not None:
        if is_start:
            is_game_over,game_state,char_all_open,game_data = generate_message_state(game_data)
            openchars.update_game_data(group_id,game_data)

            if char_all_open:
                await open_chars.send(char_all_open)
            await open_chars.send(game_state)
            if is_game_over:
                openchars.game_over(group_id)
                await open_chars.send('全部答对啦，恭喜各位🎉\n本轮猜歌已结束，可发送“dlx猜歌”再次游玩')
        else:
            await open_chars.send([MessageSegment.reply(event.message_id),MessageSegment.text("该字母已经开过了噢，换一个字母吧~")])


all_message_handle = on_message(priority=18,block=False)
@all_message_handle.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg_content = event.get_plaintext()
    group_id = event.group_id
    game_data = openchars.get_game_data(group_id)
    if game_data:
        songinfo = total_list.by_id(msg_content)
        if songinfo:
            music_ids = [int(songinfo.id)]
        elif not songinfo:
            music_ids = otherName.findSong(msg_content)

        if music_ids:
            guess_success,game_data = check_music_id(game_data,music_ids)
            print(game_data)
            if guess_success:
                await all_message_handle.send(guess_success)
                is_game_over,game_state,char_all_open,game_data = generate_message_state(game_data)
                if is_game_over:
                    openchars.game_over(group_id)
                    await start_open_chars.send('全部答对啦，恭喜各位🎉\n本轮猜歌已结束，可发送“dlx猜歌”再次游玩')
                else:
                    openchars.update_game_data(group_id,game_data)
                await start_open_chars.send(game_state)


pass_game = on_command('跳过猜歌',priority=20)
@pass_game.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    game_data = openchars.get_game_data(group_id)
    if game_data:
        await pass_game.send(generate_success_state(game_data))
        await pass_game.send("本次猜歌跳过，准备开始下一轮~")
        openchars.game_over(group_id)