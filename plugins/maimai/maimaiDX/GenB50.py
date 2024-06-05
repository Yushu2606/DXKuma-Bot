import json
import math
import shelve
from io import BytesIO
from random import SystemRandom

import aiohttp
from PIL import Image, ImageFont, ImageDraw

from .Config import (
    font_path,
    maimai_Static,
    maimai_Jacket,
    maimai_Frame,
    maimai_Plate,
    maimai_Dani,
    maimai_Rating,
)

random = SystemRandom()

ratings = {
    "ap+": [
        1.01,
        0
    ],
    "sssp": [
        1.005,
        22.4
    ],
    "sss": [
        1.0,
        21.6
    ],
    "ssp": [
        0.995,
        21.1
    ],
    "ss": [
        0.99,
        20.8
    ],
    "sp": [
        0.98,
        20.3
    ],
    "s": [
        0.97,
        20.0
    ],
    "aaa": [
        0.94,
        16.8
    ],
    "aa": [
        0.9,
        13.6
    ],
    "a": [
        0.8,
        12.8
    ],
    "bbb": [
        0.75,
        12.0
    ],
    "bb": [
        0.7,
        11.2
    ],
    "b": [
        0.6,
        9.6
    ],
    "c": [
        0.5,
        8.0
    ],
    "d": [
        0.4,
        6.4
    ]
}

# 字体路径
ttf_bold_path = font_path / "SourceHanSans-Bold.ttc"
ttf_heavy_path = font_path / "SourceHanSans-Heavy.ttc"
ttf_regular_path = font_path / "SourceHanSans-Regular.ttc"


# id查歌
def find_song_by_id(song_id, songList):
    for song in songList:
        if song_id in [song["id"], song["id"][1:]]:
            return song

    # 如果没有找到对应 id 的歌曲，返回 None
    return None


def resize_image(image, scale):
    # 计算缩放后的目标尺寸
    width = int(image.width * scale)
    height = int(image.height * scale)

    # 缩放图像
    resized_image = image.resize((width, height))

    return resized_image


def format_songid(id):
    id_str = str(id)
    if len(id_str) == 5 and id_str.startswith("10"):
        # 五位数且以"10"开头，去掉"10"然后补齐前导零
        return id_str[2:].zfill(6)
    if len(id_str) == 5 and id_str.startswith("1"):
        # 五位数且以"1"开头，去掉"1"然后补齐前导零
        return id_str[1:].zfill(6)
    # 直接补齐前导零至六位
    return id_str.zfill(6)


def compute_record(records: list):
    output = {
        "sssp": 0,
        "sss": 0,
        "ssp": 0,
        "ss": 0,
        "sp": 0,
        "s": 0,
        "clear": 0,
        "app": 0,
        "ap": 0,
        "fcp": 0,
        "fc": 0,
        "fsdp": 0,
        "fsd": 0,
        "fsp": 0,
        "fs": 0,
    }

    for record in records:
        achieve = record["achievements"]
        fc = record["fc"]
        fs = record["fs"]

        if achieve >= 80.0000:
            output["clear"] += 1
        if achieve >= 97.0000:
            output["s"] += 1
        if achieve >= 98.0000:
            output["sp"] += 1
        if achieve >= 99.0000:
            output["ss"] += 1
        if achieve >= 99.5000:
            output["ssp"] += 1
        if achieve >= 100.0000:
            output["sss"] += 1
        if achieve >= 100.5000:
            output["sssp"] += 1

        if fc:
            output["fc"] += 1
            if fc == "app":
                output["app"] += 1
                output["ap"] += 1
                output["fcp"] += 1
            if fc == "ap":
                output["ap"] += 1
                output["fcp"] += 1
            if fc == "fcp":
                output["fcp"] += 1
        if fs:
            output["fs"] += 1
            if fs == "fsdp":
                output["fsdp"] += 1
                output["fsd"] += 1
                output["fsp"] += 1
            if fs == "fsd":
                output["fsd"] += 1
                output["fsp"] += 1
            if fs == "fsp":
                output["fsp"] += 1

    return output


def get_min_score(notes: list[int]):
    weight = [1, 2, 3, 1, 5]
    base_score = 5
    sum_score = 0
    for i in range(0, 5):
        if i == 3 and len(notes) < 5:
            sum_score += notes[i] * weight[4] * base_score
            break
        sum_score += notes[i] * weight[i] * base_score
    return (1 - ((sum_score - 1) / sum_score)) * 100


def records_filter(
        records: list,
        level: str | None = None,
        is_sun: bool = False,
        is_lock: bool = False,
        songList=None,
):
    filted_records = []
    for record in records:
        if level and record["level"] != level:
            continue
        if is_sun:
            passed = False
            for _, ra_dt in ratings.items():
                max_acc = ra_dt[0] * 100
                song_data = find_song_by_id(str(record["song_id"]), songList)
                min_acc = max_acc - get_min_score(
                    song_data["charts"][record["level_index"]]["notes"]
                )
                if min_acc <= record["achievements"] < max_acc:
                    passed = True
            if not passed:
                continue
        if is_lock:
            ra_in = ratings[record["rate"]][0]
            min_acc = ra_in * 100
            song_data = find_song_by_id(str(record["song_id"]), songList)
            max_acc = min_acc + get_min_score(song_data["charts"][record["level_index"]]["notes"])
            if max_acc <= record["achievements"] < min_acc:
                continue
        filted_records.append(record)
    filted_records = sorted(
        filted_records, key=lambda x: (x["achievements"], x["ra"]), reverse=True
    )
    return filted_records


def song_list_filter(level: str, songList):
    filted_song_list = []
    for song in songList:
        for song_level in song["level"]:
            if level == song_level:
                filted_song_list.append(song)
    return filted_song_list


def get_page_records(records, page):
    items_per_page = 55
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    page_data = records[start_index:end_index]
    return page_data


def dxscore_proc(dxscore, sum_dxscore):
    percentage = (dxscore / sum_dxscore) * 100

    if percentage < 85.00:
        return 0, 0
    if percentage < 90.00:
        return 1, 1
    if percentage < 93.00:
        return 1, 2
    if percentage < 95.00:
        return 2, 3
    if percentage < 97.00:
        return 2, 4
    return 3, 5


def rating_proc(ra: int, rate: str):
    try:
        if ra < 232:
            return "------"

        achieve = ratings[rate][0]
        num = ratings[rate][1]

        result = math.ceil((ra / (achieve * num)) * 10) / 10

        if result > 15.0:
            return "------"

        return result
    except (KeyError, ZeroDivisionError):
        return "-----"


def compute_ra(ra: int):
    if ra < 999:
        return 1
    if ra < 1999:
        return 2
    if ra < 3999:
        return 3
    if ra < 6999:
        return 4
    if ra < 9999:
        return 5
    if ra < 11999:
        return 6
    if ra < 12999:
        return 7
    if ra < 13999:
        return 8
    if ra < 14499:
        return 9
    if ra < 14999:
        return 10
    return 11


def music_to_part(
        achievements: float,
        ds: float,
        dxScore: int,
        fc: str,
        fs: str,
        level: str,
        level_index: int,
        level_label: str,
        ra: int,
        rate: str,
        song_id: str,
        title: str,
        type: str,
        index: int,
        b_type: str,
        songList,
):
    color = (255, 255, 255)
    if level_index == 4:
        color = (88, 140, 204)

    # 根据难度 底图
    partbase_path = maimai_Static / f"PartBase_{level_label}.png"
    partbase = Image.open(partbase_path)

    # 歌曲封面
    jacket_path = maimai_Jacket / f"UI_Jacket_{format_songid(song_id)}.png"
    jacket = Image.open(jacket_path)
    jacket = resize_image(jacket, 0.56)
    partbase.paste(jacket, (36, 41), jacket)

    # 歌曲分类 DX / SD
    icon_path = maimai_Static / f"music_{type}.png"
    icon = Image.open(icon_path)
    icon = resize_image(icon, 1.39)
    partbase.paste(icon, (797, 16), icon)

    # 歌名
    ttf = ImageFont.truetype(ttf_bold_path, size=40)
    text_position = (305.4, 16.8)
    draw = ImageDraw.Draw(partbase)
    text_bbox = draw.textbbox(text_position, title, font=ttf)
    max_width = 750
    ellipsis = "..."

    # 检查文本的宽度是否超过最大宽度
    if text_bbox[2] <= max_width:
        # 文本未超过最大宽度，直接绘制
        draw.text(text_position, title, font=ttf, fill=color)
    else:
        # 文本超过最大宽度，截断并添加省略符号
        truncated_title = title
        while text_bbox[2] > max_width and len(truncated_title) > 0:
            truncated_title = truncated_title[:-1]
            text_bbox = draw.textbbox(
                text_position, truncated_title + ellipsis, font=ttf
            )
        draw.text(text_position, truncated_title + ellipsis, font=ttf, fill=color)

    # 达成率
    ttf = ImageFont.truetype(ttf_heavy_path, size=73)
    draw = ImageDraw.Draw(partbase)
    if "." not in str(achievements):
        achievements = f"{achievements}.0"
    achievements = f"{achievements}".split(".")
    achievements1 = f"{achievements[0]}.        %"
    achievements2 = (str(achievements[1]).ljust(4, "0"))[:4]
    text_position = (375, 90)
    text_content = f"{achievements1}"
    draw.text(text_position, text_content, font=ttf, fill=color)
    ttf = ImageFont.truetype(ttf_heavy_path, size=55)
    draw = ImageDraw.Draw(partbase)
    match len(achievements[0]):
        case 3:
            text_position = (532, 106)
        case 2:
            text_position = (488, 106)
        case 1:
            text_position = (444, 106)
    text_content = f"{achievements2}"
    draw.text(text_position, text_content, font=ttf, fill=color)

    # 一些信息
    ttf = ImageFont.truetype(ttf_bold_path, size=30)
    # best序号
    ImageDraw.Draw(partbase).text(
        (308, 245), f"#{index}", font=ttf, fill=(255, 255, 255)
    )
    # 乐曲ID
    ImageDraw.Draw(partbase).text(
        (388, 245), f"ID:{song_id}", font=ttf, fill=(28, 43, 120)
    )
    # 定数和ra
    if b_type == "fit50" and ((ds * 10) % 1) == 0:
        ds_str = f"{ds}0"
    else:
        ds_str = str(ds)
    ImageDraw.Draw(partbase).text((375, 182), f"{ds_str} -> {ra}", font=ttf, fill=color)
    # dx分数和星星
    song_data = [d for d in songList if d["id"] == str(song_id)][0]
    sum_dxscore = sum(song_data["charts"][level_index]["notes"]) * 3
    ImageDraw.Draw(partbase).text(
        (568, 245), f"{dxScore}/{sum_dxscore}", font=ttf, fill=(28, 43, 120)
    )
    star_level, stars = dxscore_proc(dxScore, sum_dxscore)
    if star_level:
        star_width = 30
        star_path = maimai_Static / f"dxscore_star_{star_level}.png"
        star = Image.open(star_path)
        star = resize_image(star, 1.3)
        for i in range(stars):
            x_offset = i * star_width
            partbase.paste(star, (x_offset + 570, 178), star)

    # 评价
    rate_path = maimai_Static / f"bud_music_icon_{rate}.png"
    rate = Image.open(rate_path)
    rate = resize_image(rate, 0.87)
    partbase.paste(rate, (770, 72), rate)

    # fc ap
    if fc:
        fc_path = maimai_Static / f"music_icon_{fc}.png"
        fc = Image.open(fc_path)
        fc = resize_image(fc, 2.22)
        partbase.paste(fc, (782, 187), fc)
    if fs:
        fs_path = maimai_Static / f"music_icon_{fs}.png"
        fs = Image.open(fs_path)
        fs = resize_image(fs, 2.22)
        partbase.paste(fs, (876, 187), fs)

    partbase = partbase.resize((340, 110))
    return partbase


def draw_best(bests: list, type: str, songList):
    index = 0
    # 计算列数
    queue_nums = int(len(bests) / 4) + 1
    # 初始化行列标号
    queue_index = 0
    row_index = 0
    # 初始化坐标
    x = 350
    y = 0
    # 初始化底图
    base = Image.new(
        "RGBA", (1440, queue_nums * 110 + (queue_nums - 1) * 10), (0, 0, 0, 0)
    )
    # 通过循环构建列表并传入数据
    # 遍历列表中的选项
    # 循环生成列
    while queue_index < queue_nums:
        # 设置每行的列数
        if queue_index == 0:
            max_row_index = 3  # 第一行3个
        else:
            max_row_index = 4  # 其他行4个

        # 循环生成行
        while row_index < max_row_index:
            if index < len(bests):
                # 根据索引从列表中抽取数据
                song_data = bests[index]
                # 传入数据生成图片
                part = music_to_part(
                    **song_data, index=index + 1, b_type=type, songList=songList
                )
                # 将图片粘贴到底图上
                base.paste(part, (x, y), part)
                # 增加x坐标，序列自增
                x += 350
                row_index += 1
                index += 1
            else:
                break

        # 重置x坐标，增加y坐标
        x = 0
        y += 120
        row_index = 0
        queue_index += 1

    return base


def rating_tj(b35max, b35min, b15max, b15min):
    ratingbase_path = maimai_Static / "rating_base.png"
    ratingbase = Image.open(ratingbase_path)
    ttf = ImageFont.truetype(ttf_bold_path, size=30)

    b35max_diff = b35max - b35min
    b35min_diff = random.randint(1, 5)
    b15max_diff = b15max - b15min
    b15min_diff = random.randint(1, 5)

    draw = ImageDraw.Draw(ratingbase)
    draw.text((155, 72), font=ttf, text=f"+{str(b35max_diff)}", fill=(255, 255, 255))
    draw.text((155, 112), font=ttf, text=f"+{str(b35min_diff)}", fill=(255, 255, 255))
    draw.text((155, 178), font=ttf, text=f"+{str(b15max_diff)}", fill=(255, 255, 255))
    draw.text((155, 218), font=ttf, text=f"+{str(b15min_diff)}", fill=(255, 255, 255))

    b35max_ra_sssp = rating_proc(b35max, "sssp")
    b35min_ra_sssp = rating_proc((b35min + b35min_diff), "sssp")
    b15max_ra_sssp = rating_proc(b15max, "sssp")
    b15min_ra_sssp = rating_proc((b15min + b15min_diff), "sssp")
    draw.text((270, 72), font=ttf, text=str(b35max_ra_sssp), fill=(255, 255, 255))
    draw.text((270, 112), font=ttf, text=str(b35min_ra_sssp), fill=(255, 255, 255))
    draw.text((270, 178), font=ttf, text=str(b15max_ra_sssp), fill=(255, 255, 255))
    draw.text((270, 218), font=ttf, text=str(b15min_ra_sssp), fill=(255, 255, 255))

    b35max_ra_sss = rating_proc(b35max, "sss")
    b35min_ra_sss = rating_proc((b35min + b35min_diff), "sss")
    b15max_ra_sss = rating_proc(b15max, "sss")
    b15min_ra_sss = rating_proc((b15min + b15min_diff), "sss")
    draw.text((390, 72), font=ttf, text=str(b35max_ra_sss), fill=(255, 255, 255))
    draw.text((390, 112), font=ttf, text=str(b35min_ra_sss), fill=(255, 255, 255))
    draw.text((390, 178), font=ttf, text=str(b15max_ra_sss), fill=(255, 255, 255))
    draw.text((390, 218), font=ttf, text=str(b15min_ra_sss), fill=(255, 255, 255))

    b35max_ra_ssp = rating_proc(b35max, "ssp")
    b35min_ra_ssp = rating_proc((b35min + b35min_diff), "ssp")
    b15max_ra_ssp = rating_proc(b15max, "ssp")
    b15min_ra_ssp = rating_proc((b15min + b15min_diff), "ssp")
    draw.text((510, 72), font=ttf, text=str(b35max_ra_ssp), fill=(255, 255, 255))
    draw.text((510, 112), font=ttf, text=str(b35min_ra_ssp), fill=(255, 255, 255))
    draw.text((510, 178), font=ttf, text=str(b15max_ra_ssp), fill=(255, 255, 255))
    draw.text((510, 218), font=ttf, text=str(b15min_ra_ssp), fill=(255, 255, 255))

    b35max_ra_ss = rating_proc(b35max, "ss")
    b35min_ra_ss = rating_proc((b35min + b35min_diff), "ss")
    b15max_ra_ss = rating_proc(b15max, "ss")
    b15min_ra_ss = rating_proc((b15min + b15min_diff), "ss")
    draw.text((630, 72), font=ttf, text=str(b35max_ra_ss), fill=(255, 255, 255))
    draw.text((630, 112), font=ttf, text=str(b35min_ra_ss), fill=(255, 255, 255))
    draw.text((630, 178), font=ttf, text=str(b15max_ra_ss), fill=(255, 255, 255))
    draw.text((630, 218), font=ttf, text=str(b15min_ra_ss), fill=(255, 255, 255))

    return ratingbase


async def generateb50(
        b35: list, b15: list, nickname: str, qq, dani: int, type: str, songList
):
    with shelve.open("./data/maimai/b50_config") as config:
        if qq not in config:
            frame = "200502"
            plate = "000101"
            is_rating_tj = True
        else:
            if "frame" not in config[qq]:
                frame = "200502"
            else:
                frame = config[qq]["frame"]
            if "plate" not in config[qq]:
                plate = "000101"
            else:
                plate = config[qq]["plate"]
            if "rating_tj" not in config[qq]:
                is_rating_tj = True
            else:
                is_rating_tj = config[qq]["rating_tj"]

    b35_ra = sum(item["ra"] for item in b35)
    b15_ra = sum(item["ra"] for item in b15)
    rating = b35_ra + b15_ra

    b50 = Image.new("RGBA", (1440, 2560), "#FFFFFF")

    # BG
    background = Image.open(maimai_Static / "b50_bg.png")
    b50.paste(background)

    # 底板
    frame_path = maimai_Frame / f"UI_Frame_{frame}.png"
    frame = Image.open(frame_path)
    frame = resize_image(frame, 0.95)
    b50.paste(frame, (45, 45))

    # 牌子
    plate_path = maimai_Plate / f"UI_Plate_{plate}.png"
    plate = Image.open(plate_path)
    b50.paste(plate, (60, 60), plate)

    # 头像框
    iconbase_path = maimai_Static / "icon_base.png"
    iconbase = Image.open(iconbase_path)
    iconbase = resize_image(iconbase, 0.308)
    b50.paste(iconbase, (60, 46), iconbase)
    # 头像
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"http://q.qlogo.cn/headimg_dl?dst_uin={qq}&spec=640&img_type=png"
        ) as resp:
            icon = await resp.read()
    icon = Image.open(BytesIO(icon)).resize((88, 88))
    b50.paste(icon, (73, 75))

    # 姓名框
    namebase_path = maimai_Static / "namebase.png"
    namebase = Image.open(namebase_path)
    b50.paste(namebase, (0, 0), namebase)

    # 段位
    dani_path = maimai_Dani / f"UI_DNM_DaniPlate_{dani:02d}.png"
    dani = Image.open(dani_path)
    dani = resize_image(dani, 0.2)
    b50.paste(dani, (400, 110), dani)

    # rating推荐
    if type == "b50":
        if is_rating_tj:
            b35max = b35[0]["ra"] if b35 else 0
            b35min = b35[-1]["ra"] if b35 else 0
            b15max = b15[0]["ra"] if b15 else 0
            b15min = b15[-1]["ra"] if b15 else 0
            ratingbase = rating_tj(b35max, b35min, b15max, b15min)
            b50.paste(ratingbase, (60, 197), ratingbase)

    # rating框
    ratingbar = compute_ra(rating)
    ratingbar_path = maimai_Rating / f"UI_CMN_DXRating_{ratingbar:02d}.png"
    ratingbar = Image.open(ratingbar_path)
    ratingbar = resize_image(ratingbar, 0.26)
    b50.paste(ratingbar, (175, 70), ratingbar)

    # rating数字
    rating_str = str(rating).zfill(5)
    num1 = Image.open(f"./src/maimai/number/{rating_str[0]}.png").resize((18, 21))
    num2 = Image.open(f"./src/maimai/number/{rating_str[1]}.png").resize((18, 21))
    num3 = Image.open(f"./src/maimai/number/{rating_str[2]}.png").resize((18, 21))
    num4 = Image.open(f"./src/maimai/number/{rating_str[3]}.png").resize((18, 21))
    num5 = Image.open(f"./src/maimai/number/{rating_str[4]}.png").resize((18, 21))

    b50.paste(num1, (253, 77), num1)
    b50.paste(num2, (267, 77), num2)
    b50.paste(num3, (280, 77), num3)
    b50.paste(num4, (294, 77), num4)
    b50.paste(num5, (308, 77), num5)

    # 名字
    ttf = ImageFont.truetype(ttf_regular_path, size=27)
    ImageDraw.Draw(b50).text((180, 113), nickname, font=ttf, fill=(0, 0, 0))

    # rating合计
    ttf = ImageFont.truetype(ttf_bold_path, size=14)
    ImageDraw.Draw(b50).text(
        (188, 148),
        f"过往版本：{b35_ra} + 现行版本：{b15_ra} = {rating}",
        font=ttf,
        fill=(255, 255, 255),
    )

    # b50
    b35 = draw_best(b35, type, songList)
    b15 = draw_best(b15, type, songList)
    b50.paste(b35, (25, 795), b35)
    b50.paste(b15, (25, 1985), b15)

    img_byte_arr = BytesIO()
    b50.save(img_byte_arr, format="PNG", quality=90)
    img_byte_arr.seek(0)
    img_bytes = img_byte_arr.getvalue()

    return img_bytes


async def generate_wcb(
        qq: str,
        page: int,
        nickname: str,
        dani: int,
        rating: int,
        input_records,
        all_page_num,
        songList,
        level: str | None = None,
        rate_count=None,
):
    with shelve.open("./data/maimai/b50_config") as config:
        if qq not in config or "plate" not in config[qq]:
            plate = "000101"
        else:
            plate = config[qq]["plate"]
        if not level:
            if qq not in config or "frame" not in config[qq]:
                frame = "200502"
            else:
                frame = config[qq]["frame"]

    bg = Image.open("./src/maimai/wcb_bg.png")

    # 底板
    if level:
        frame_path = "./src/maimai/wcb_frame.png"
    else:
        frame_path = maimai_Frame / f"UI_Frame_{frame}.png"
    frame = Image.open(frame_path)
    frame = resize_image(frame, 0.95)
    bg.paste(frame, (45, 45))

    # 牌子
    plate_path = maimai_Plate / f"UI_Plate_{plate}.png"
    plate = Image.open(plate_path)
    bg.paste(plate, (60, 60), plate)

    # 头像框
    iconbase_path = maimai_Static / "icon_base.png"
    iconbase = Image.open(iconbase_path)
    iconbase = resize_image(iconbase, 0.308)
    bg.paste(iconbase, (60, 46), iconbase)
    # 头像
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"http://q.qlogo.cn/headimg_dl?dst_uin={qq}&spec=640&img_type=png"
        ) as resp:
            icon = await resp.read()
    icon = Image.open(BytesIO(icon)).resize((88, 88))
    bg.paste(icon, (73, 75))

    # 姓名框
    namebase_path = maimai_Static / "namebase.png"
    namebase = Image.open(namebase_path)
    bg.paste(namebase, (0, 0), namebase)

    # 段位
    dani_path = maimai_Dani / f"UI_DNM_DaniPlate_{dani:02d}.png"
    dani = Image.open(dani_path)
    dani = resize_image(dani, 0.2)
    bg.paste(dani, (400, 110), dani)

    # rating框
    ratingbar = compute_ra(rating)
    ratingbar_path = maimai_Rating / f"UI_CMN_DXRating_{ratingbar:02d}.png"
    ratingbar = Image.open(ratingbar_path)
    ratingbar = resize_image(ratingbar, 0.26)
    bg.paste(ratingbar, (175, 70), ratingbar)

    # rating数字
    rating_str = str(rating).zfill(5)
    num1 = Image.open(f"./src/maimai/number/{rating_str[0]}.png").resize((18, 21))
    num2 = Image.open(f"./src/maimai/number/{rating_str[1]}.png").resize((18, 21))
    num3 = Image.open(f"./src/maimai/number/{rating_str[2]}.png").resize((18, 21))
    num4 = Image.open(f"./src/maimai/number/{rating_str[3]}.png").resize((18, 21))
    num5 = Image.open(f"./src/maimai/number/{rating_str[4]}.png").resize((18, 21))

    bg.paste(num1, (253, 77), num1)
    bg.paste(num2, (267, 77), num2)
    bg.paste(num3, (280, 77), num3)
    bg.paste(num4, (294, 77), num4)
    bg.paste(num5, (308, 77), num5)

    # 名字
    ttf = ImageFont.truetype(ttf_regular_path, size=27)
    ImageDraw.Draw(bg).text((180, 113), nickname, font=ttf, fill=(0, 0, 0))

    if level:
        # 绘制的完成表的等级贴图
        level_icon_path = maimai_Static / f"level_icon_{level}.png"
        level_icon = Image.open(level_icon_path)
        level_icon = resize_image(level_icon, 0.70)
        bg.paste(level_icon, (755 - (len(level) * 8), 45), level_icon)

        # 绘制各达成数目
        all_count = len(song_list_filter(level, songList))
        ttf = ImageFont.truetype(font=ttf_bold_path, size=20)
        rate_list = ["sssp", "sss", "ssp", "ss", "sp", "s", "clear"]
        fcfs_list = ["app", "ap", "fcp", "fc", "fsdp", "fsd", "fsp", "fs"]
        rate_x = 202
        rate_y = 264
        fcfs_x = 203
        fcfs_y = 362
        for rate in rate_list:
            rate_num = rate_count[rate]
            ImageDraw.Draw(bg).text(
                (rate_x, rate_y),
                f"{rate_num}/{all_count}",
                font=ttf,
                fill=(255, 255, 255),
                anchor="mm",
            )
            rate_x += 118
        for fcfs in fcfs_list:
            fcfs_num = rate_count[fcfs]
            ImageDraw.Draw(bg).text(
                (fcfs_x, fcfs_y),
                f"{fcfs_num}/{all_count}",
                font=ttf,
                fill=(255, 255, 255),
                anchor="mm",
            )
            fcfs_x += 102

    # 页码
    page_text = f"{page} / {all_page_num}"
    ttf = ImageFont.truetype(font=ttf_heavy_path, size=70)
    ImageDraw.Draw(bg).text(
        (260, 850), page_text, font=ttf, fill=(255, 255, 255), anchor="mm"
    )

    # 绘制当前页面的成绩
    records_parts = draw_best(input_records, type="wcb", songList=songList)
    bg.paste(records_parts, (25, 795), records_parts)

    img_byte_arr = BytesIO()
    bg.save(img_byte_arr, format="PNG", quality=90)
    img_byte_arr.seek(0)
    img_bytes = img_byte_arr.getvalue()

    return img_bytes
