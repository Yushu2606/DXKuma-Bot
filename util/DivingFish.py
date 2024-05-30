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
