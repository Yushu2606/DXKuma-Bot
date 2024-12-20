from asyncio import Event

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.message import run_postprocessor, event_preprocessor, event_postprocessor

from util.exceptions import NotAllowedException, SkipException

locks: dict[int, Event] = {}


@event_preprocessor
async def _(event: GroupMessageEvent):
    if f"{event.group_id}{event.user_id}{event.time}".__hash__() in locks:
        await locks[f"{event.group_id}{event.user_id}{event.time}".__hash__()].wait()
        if f"{event.group_id}{event.user_id}{event.time}".__hash__() not in locks:
            raise SkipException
        return

    locks[f"{event.group_id}{event.user_id}{event.time}".__hash__()] = Event()


@run_postprocessor
async def _(event: GroupMessageEvent, exception: Exception | None):
    if not isinstance(exception, NotAllowedException) and not isinstance(exception, ActionFailed):
        return

    locks[f"{event.group_id}{event.user_id}{event.time}".__hash__()].set()


@event_postprocessor
async def _(event: GroupMessageEvent):
    if f"{event.group_id}{event.user_id}{event.time}".__hash__() in locks:
        locks.pop(f"{event.group_id}{event.user_id}{event.time}".__hash__()).set()
