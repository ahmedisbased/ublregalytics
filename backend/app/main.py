import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app.core import config
from app.db import close_db_pool, close_str_pool
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routes import auth_router, str_router, ctr_router, rcoa_router

logging.basicConfig(
    filename="debug.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

app = FastAPI(
    title="Regalytics",
    docs_url=None,
)


@app.on_event("shutdown")
def shutdown_database_pool():
    close_db_pool()
    close_str_pool()

# Security response headers (CSP, X-Frame-Options, Referrer-Policy, etc.).
app.add_middleware(SecurityHeadersMiddleware)

# CORS: explicit allow-list instead of "*". A wildcard origin combined with
# allow_credentials is both insecure and rejected by browsers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Portable static path (was a Windows-only "app\\static" literal).
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Docs",
        swagger_js_url="static/swagger/swagger-ui-bundle.js",
        swagger_css_url="static/swagger/swagger-ui.css",
        swagger_favicon_url="static/swagger/favicon-32x32.png",
        oauth2_redirect_url="static/swagger/oauth-redirect.html",
    )


@app.get("/")
def home():
    return {"message": "Homepage"}


app.include_router(auth_router)
app.include_router(str_router)
app.include_router(ctr_router)
app.include_router(rcoa_router)
