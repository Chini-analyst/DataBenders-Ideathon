"""
StrategyShifu — FastAPI application entrypoint.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core.config import settings
from core.database import close_chroma_client, close_neo4j_driver, get_chroma_client, get_neo4j_driver
from core.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    setup_logger()

    # Ensure upload directory exists
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    logger.info("StrategyShifu starting up...")

    # Attempt connections — log warnings if unavailable, but don't block startup
    get_neo4j_driver()
    get_chroma_client()

    logger.info("StrategyShifu ready")

    yield

    # Shutdown
    logger.info("StrategyShifu shutting down...")
    close_neo4j_driver()
    close_chroma_client()
    logger.info("Shutdown complete")


app = FastAPI(
    title="StrategyShifu API",
    description="LightRAG Knowledge Graph API for strategy consulting intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from routers.health import router as health_router
from routers.upload import router as upload_router
from routers.graph import router as graph_router
from routers.query import router as query_router
from routers.data import router as data_router

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(graph_router)
app.include_router(query_router)
app.include_router(data_router)


@app.get("/")
def root():
    return {
        "app": "StrategyShifu",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
