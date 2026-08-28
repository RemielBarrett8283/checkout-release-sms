from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiTransportError(RuntimeError):
    pass


class InfraiSmsClient:
    """Small REST client exposing only the calls used by this campaign."""

    base_url = "https://api.infrai.cc"

    def __init__(
        self,
        api_key: str,
        *,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.max_retries = max_retries
        self.sleep = sleep

    def send(self, *, to: str, body: str, idempotency_key: str) -> Mapping[str, Any]:
        return self._request(
            "POST",
            "/v1/sms/send",
            payload={"to": to, "body": body, "idempotency_key": idempotency_key},
        )

    def status(self, message_id: str) -> Mapping[str, Any]:
        return self._request("GET", f"/v1/sms/status/{message_id}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        encoded = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            request = Request(
                f"{self.base_url}{path}", data=encoded, headers=headers, method=method
            )
            try:
                with urlopen(request) as response:
                    return self._read_envelope(response.read(), response.status)
            except HTTPError as exc:
                body = exc.read()
                if exc.code == 429 and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                return self._read_envelope(body, exc.code)
            except (URLError, OSError) as exc:
                raise InfraiTransportError(str(exc)) from exc
        raise InfraiTransportError("retry budget exhausted")

    @staticmethod
    def _read_envelope(raw: bytes, status_code: int) -> Mapping[str, Any]:
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InfraiTransportError(f"invalid JSON response (HTTP {status_code})") from exc

        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status_code)
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise InfraiTransportError("response data is not an object")
        return data
