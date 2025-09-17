# -*- coding: utf-8 -*-
import asyncio
import httpx
import time
from typing import Dict, Optional
from settings import RUSPROFILE_COOKIES, RUSPROFILE_HEADERS, REQUESTS_RPS, REQUEST_TIMEOUT
from core.logger import setup_logging

log = setup_logging()

class ThrottledClient:
    def __init__(self, base_url: str = "https://www.rusprofile.ru"):
        self.base_url = base_url.rstrip('/')
        self._last = 0.0
        self.min_interval = 1.0 / max(REQUESTS_RPS, 0.01)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=RUSPROFILE_HEADERS,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            cookies=RUSPROFILE_COOKIES
        )

    async def _wait_slot(self):
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval:
            await asyncio.sleep(self.min_interval - delta)
        self._last = time.time()

    async def get(self, url: str, **kw):
        await self._wait_slot()
        resp = await self.client.get(url, **kw)
        resp.raise_for_status()
        return resp

    async def close(self):
        await self.client.aclose()
