"""
Home Automation Server
FastAPI application factory.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from home_automation_server.api import devices, pairing, automations, apps, webhooks, controls
from home_automation_server.api import ui
from home_automation_server.db.session import init_db
from home_automation_server.core.config import settings

import logging

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Home Automation Server…")
    init_db()
    yield
    logger.info("Shutting down Home Automation Server.")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Home Automation Server",
        description="Control Apple TVs via pyatv with a FastAPI backend.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Static files
    application.mount(
        "/static",
        StaticFiles(directory="home_automation_server/frontend/static"),
        name="static",
    )

    # API routers
    application.include_router(devices.router, prefix="/devices", tags=["Devices"])
    application.include_router(pairing.router, prefix="/pairing", tags=["Pairing"])
    application.include_router(automations.router, prefix="/automations", tags=["Automations"])
    application.include_router(apps.router, prefix="/apps", tags=["Apps"])
    application.include_router(controls.router, prefix="/controls", tags=["Controls"])
    application.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

    # UI router (Jinja2 pages)
    application.include_router(ui.router, prefix="/ui", tags=["UI"])

    @application.get("/", include_in_schema=False)
    async def root_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/ui")

    return application


app = create_app()

