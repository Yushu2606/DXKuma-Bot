import json
import os
from datetime import date

import aiohttp

from util.Config import config


async def get_player_data(qq: str):
    payload = {"qq": qq, "b50": True}
    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://www.diving-fish.com/api/maimaidxprober/query/player", json=payload
        ) as resp:
            if resp.status == 200:
                obj = await resp.json()
                return obj, 200
            return None, resp.status


async def get_player_records(qq: str):
    headers = {"Developer-Token": config.dev_token}
    payload = {"qq": qq}
    async with aiohttp.ClientSession() as session:
        async with session.get(
                "https://www.diving-fish.com/api/maimaidxprober/dev/player/records",
                headers=headers,
                params=payload,
        ) as resp:
            if resp.status == 200:
                obj = await resp.json()
                return obj, 200
            return None, resp.status


async def get_player_record(qq: str, music_id):
    headers = {"Developer-Token": config.dev_token}
    payload = {"qq": qq, "music_id": music_id}
    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://www.diving-fish.com/api/maimaidxprober/dev/player/record",
                headers=headers,
                json=payload,
        ) as resp:
            if resp.status == 200:
                obj = await resp.json()
                return obj, 200
            return None, resp.status


async def get_music_data():
    cache_dir = "./Cache/Data/MusicData/"
    cache_path = f"{cache_dir}{date.today().isoformat()}.json"
    if not os.path.exists(cache_path):
        files = os.listdir(cache_dir)
        if files:
            for file in files:
                os.remove(f"{cache_dir}{file}")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "https://www.diving-fish.com/api/maimaidxprober/music_data"
            ) as resp:
                with open(cache_path, "wb") as fd:
                    async for chunk in resp.content.iter_chunked(1024):
                        fd.write(chunk)
    with open(cache_path) as fd:
        return json.loads(fd.read())


async def get_chart_stats():
    cache_dir = "./Cache/Data/ChartStats/"
    cache_path = f"{cache_dir}{date.today().isoformat()}.json"
    if not os.path.exists(cache_path):
        files = os.listdir(cache_dir)
        if files:
            for file in files:
                os.remove(f"{cache_dir}{file}")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "https://www.diving-fish.com/api/maimaidxprober/chart_stats"
            ) as resp:
                with open(cache_path, "wb") as fd:
                    async for chunk in resp.content.iter_chunked(1024):
                        fd.write(chunk)
    with open(cache_path) as fd:
        return json.loads(fd.read())
