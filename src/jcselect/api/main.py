"""Main FastAPI application for the sync server."""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from jcselect.api import auth, health, sync
from jcselect.api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DependencyConflictError,
    InvalidTokenError,
    SyncConflictError,
)
from jcselect.utils.settings import sync_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting jcselect sync server")

    # Initialize any resources here if needed

    yield

    # Shutdown
    logger.info("Shutting down jcselect sync server")


# Create FastAPI application
app = FastAPI(
    title="jcselect Sync API",
    description="Synchronization API for jcselect voter tracking system",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("DEBUG") == "true" else None,
    redoc_url="/redoc" if os.getenv("DEBUG") == "true" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=sync_settings.cors_origins,
    allow_credentials=sync_settings.cors_allow_credentials,
    allow_methods=sync_settings.cors_allow_methods,
    allow_headers=sync_settings.cors_allow_headers,
)


# Global exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    logger.warning(f"Authentication error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    logger.warning(f"Authorization error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(InvalidTokenError)
async def invalid_token_exception_handler(request: Request, exc: InvalidTokenError):
    """Handle invalid token errors."""
    logger.warning(f"Invalid token error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.exception_handler(SyncConflictError)
async def sync_conflict_exception_handler(request: Request, exc: SyncConflictError):
    """Handle sync conflict errors."""
    logger.info(f"Sync conflict: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(DependencyConflictError)
async def dependency_conflict_exception_handler(request: Request, exc: DependencyConflictError):
    """Handle dependency conflict errors."""
    logger.warning(f"Dependency conflict: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Log request details
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- {process_time:.2f}ms"
    )

    return response


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "jcselect Sync API",
        "version": "0.1.0",
        "status": "running"
    }


# Health check endpoint (no auth required)
@app.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "jcselect.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
