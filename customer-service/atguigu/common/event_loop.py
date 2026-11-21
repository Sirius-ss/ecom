import asyncio
import selectors
from typing import Coroutine


def run_async(coro: Coroutine):
    asyncio.run(coro, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))


# import asyncio
# import sys
# from typing import Coroutine
#
#
# def run_async(coro: Coroutine):
#     # 如果是 Windows 系统，强制使用 SelectorEventLoop
#     if sys.platform == 'win32':
#         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#
#     # 正常调用 run，去掉 loop_factory 参数
#     return asyncio.run(coro)
