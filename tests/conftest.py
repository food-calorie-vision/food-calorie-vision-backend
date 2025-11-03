import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """Create a dedicated event loop for pytest-asyncio."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTPX async test client."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

