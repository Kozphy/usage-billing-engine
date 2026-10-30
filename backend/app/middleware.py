from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_setup import correlation_id_var


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        token = correlation_id_var.set(incoming)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = incoming
            return response
        finally:
            correlation_id_var.reset(token)
