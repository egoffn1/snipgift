import asyncio
from typing import Any

from config import settings
from utils.logger import get_logger

logger = get_logger("markets.http")


async def request_with_retry(
    session: Any,
    method: str,
    url: str,
    *,
    json: dict | None = None,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> Any:
    timeout = timeout or settings.REQUEST_TIMEOUT
    max_retries = max_retries or settings.MAX_RETRIES
    attempt = 0
    while True:
        attempt += 1
        try:
            if method.lower() == "get":
                response = await session.get(
                    url, params=params, headers=headers, timeout=timeout
                )
            else:
                response = await session.post(
                    url, json=json, params=params, headers=headers, timeout=timeout
                )

            if response.status == 429:
                retry_after = float(
                    response.headers.get("retry-after", "2").split(",")[0]
                )
                delay = min(retry_after, 30)
            elif response.status >= 500:
                delay = 2 * attempt
            else:
                break

            if attempt >= max_retries:
                logger.warning(
                    "Give up on %s %s after %d attempts (status=%s)",
                    method.upper(),
                    url,
                    attempt,
                    response.status,
                )
                break

            await asyncio.sleep(delay)
            continue
        except asyncio.TimeoutError:
            if attempt >= max_retries:
                logger.warning("Timeout on %s %s", method.upper(), url)
                break
            await asyncio.sleep(1.5 * attempt)
            continue
        except Exception as exc:
            if attempt >= max_retries:
                logger.warning("Request %s %s failed: %s", method.upper(), url, exc)
                break
            await asyncio.sleep(1.5 * attempt)
            continue

    return response
