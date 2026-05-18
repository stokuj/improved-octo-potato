from enum import Enum

import httpx


class SendOutcome(str, Enum):
    SUCCESS = "success"  # advance offset
    SKIP = "skip"  # advance offset (4xx — data was bad, retry pointless)
    RETRY = "retry"  # do not advance, back off


class IngestClient:
    def __init__(self, api_url: str, timeout: float = 10.0):
        self.api_url = api_url
        self.timeout = timeout

    async def send_batch(self, rows: list[dict]) -> SendOutcome:
        body = {"rows": rows}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, json=body)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
            return SendOutcome.RETRY

        if 200 <= response.status_code < 300:
            return SendOutcome.SUCCESS
        if response.status_code == 429:
            return SendOutcome.RETRY
        if 400 <= response.status_code < 500:
            return SendOutcome.SKIP
        return SendOutcome.RETRY
