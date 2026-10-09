from __future__ import annotations

import io
import json
from collections.abc import Callable
from typing import Any
from wsgiref.util import setup_testing_defaults

from toy_service.app import WsgiApp


def call(
    app: WsgiApp, method: str, path: str, body: bytes = b""
) -> tuple[str, dict[str, str], dict[str, Any] | None]:
    environ: dict[str, Any] = {"REQUEST_METHOD": method, "PATH_INFO": path}
    setup_testing_defaults(environ)
    environ["wsgi.input"] = io.BytesIO(body)
    environ["CONTENT_LENGTH"] = str(len(body))
    seen: dict[str, Any] = {}

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None, /
    ) -> Callable[[bytes], object]:
        seen["status"], seen["headers"] = status, dict(headers)
        return lambda data: None

    raw = b"".join(app(environ, start_response))
    return seen["status"], seen["headers"], json.loads(raw) if raw else None
