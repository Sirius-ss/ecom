import uvicorn

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings


async def start_uvicorn():
    settings = get_settings()
    server = uvicorn.Server(
        config=uvicorn.Config(
            app="app.app:app",
            host=settings.api_host,
            port=settings.api_port,
            loop="none"
        )
    )
    await server.serve()


if __name__ == '__main__':
    run_async(start_uvicorn())
