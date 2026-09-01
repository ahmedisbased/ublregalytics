"""
Adds the security response headers that the assessment flagged as missing.

Maps to the findings:
  - Clickjacking (5.5): X-Frame-Options: DENY + CSP frame-ancestors 'none'
  - Missing Security Headers (5.6): Content-Security-Policy, Referrer-Policy,
    Permissions-Policy, X-Content-Type-Options, and HSTS.

These are applied centrally so EVERY response carries them, regardless of which
route produced it. In a deployment that sits behind a reverse proxy (nginx /
IIS) you would typically also set these at the edge; doing it here as well is
defence in depth and means the app is safe even if the proxy config drifts.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core import config

# A strict policy suitable for an API. The CSP frame-ancestors directive is the
# modern, more flexible replacement for X-Frame-Options; we send both for
# maximum browser coverage.
_CSP_DEFAULT = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)


_CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self' "
)


_HEADERS = {
    "X-Frame-Options": "DENY",
    # "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in _HEADERS.items():
            response.headers.setdefault(header, value)
        # Only advertise HSTS when actually served over HTTPS, otherwise it is
        # meaningless (and can cause issues during local HTTP testing).
        req_path = request.url.path or ""
        if req_path.startswith(("/docs", "/static", "redoc")):
            response.headers.setdefault("Content-Security-Policy", _CSP_DOCS)
        else:
            response.headers.setdefault("Content-Security-Policy", _CSP_DEFAULT)
        if config.ENABLE_HSTS and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        # Remove the framework's server banner if present (minor info leak).
        if "server" in response.headers:
            del response.headers["server"]
        return response
