"""
Fixed FastAPI Application.

This FastAPI app simulates a production service and includes a fix for the
previous bug where accessing a missing 'api_key' caused a KeyError.
The endpoint now validates the presence of the key and returns a clear
400 Bad Request response when it is absent.
"""

import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings

# --------------------------------------------------------------------------- #
# Logging configuration
# --------------------------------------------------------------------------- #
os.makedirs(
    os.path.dirname(settings.log_file) if os.path.dirname(settings.log_file) else ".",
    exist_ok=True,
)

_fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_file_handler = RotatingFileHandler(
    settings.log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# FastAPI app definition
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="SRE Demo Service",
    description="A mock service with a fixed bug for testing self-healing",
    version="1.0.0",
)


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    timestamp: str
    service: str


class DataResponse(BaseModel):
    """Response model for successful data requests."""

    data: dict
    message: str
    timestamp: str


# --------------------------------------------------------------------------- #
# Middleware
# --------------------------------------------------------------------------- #
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses."""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")

    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed with error: {str(e)}", exc_info=True)
        raise


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/", response_model=dict)
async def root():
    """Root endpoint returning basic service information."""
    return {
        "service": "SRE Demo Service",
        "status": "running",
        "endpoints": {"health": "/health", "data": "/api/data"},
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint – always reports healthy."""
    logger.info("Health check requested")
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service="SRE Demo Service",
    )


@app.get("/api/data", response_model=DataResponse)
async def get_data(
    request: Request,
    x_trigger_bug: Optional[str] = Header(None, alias="X-Trigger-Bug"),
):
    """
    Main data endpoint.

    If the optional ``X-Trigger-Bug`` header is set to ``true`` the endpoint
    attempts to use an ``api_key`` from the simulated user configuration.
    The original implementation accessed ``user_config["api_key"]`` directly,
    which raised a ``KeyError`` because the key is missing.

    The fix:
        * Use ``dict.get`` to safely retrieve the key.
        * If the key is absent, return a ``400 Bad Request`` with a clear
          error payload instead of crashing.
    """
    logger.info(f"Data endpoint called with X-Trigger-Bug={x_trigger_bug}")

    # Simulated user configuration (intentionally missing "api_key")
    user_config = {
        "user_id": 12345,
        "username": "demo_user",
        "preferences": {"theme": "dark", "notifications": True},
    }

    # When the bug‑trigger header is present, validate the presence of api_key
    if x_trigger_bug and x_trigger_bug.lower() == "true":
        logger.warning("Bug trigger detected – validating presence of api_key...")
        api_key = user_config.get("api_key")  # Safe access; returns None if missing
        if not api_key:
            # Return a client‑error response instead of raising an exception
            logger.info(
                "Missing 'api_key' in user_config – returning 400 Bad Request"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing required field 'api_key'",
                    "code": "invalid_request",
                },
            )
        logger.info(f"Using API key: {api_key}")

    # Normal successful response
    return DataResponse(
        data=user_config,
        message="Data retrieved successfully",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# --------------------------------------------------------------------------- #
# Exception handlers
# --------------------------------------------------------------------------- #
@app.exception_handler(KeyError)
async def keyerror_exception_handler(request: Request, exc: KeyError):
    """
    Fallback handler for unexpected KeyError occurrences.
    This should rarely be hit after the bug fix, but we keep it for safety.
    """
    error_details = {
        "error": "Internal Server Error",
        "error_type": "KeyError",
        "missing_key": str(exc),
        "path": request.url.path,
        "method": request.method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.error(
        f"CRITICAL ERROR - Unexpected KeyError in {request.url.path}: Missing key {exc}",
        exc_info=True,
    )
    return JSONResponse(status_code=500, content=error_details)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch‑all handler for any other unexpected errors."""
    logger.error(
        f"Unexpected error in {request.url.path}: {str(exc)}", exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# --------------------------------------------------------------------------- #
# Application entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logger.info("Starting SRE Demo Service...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,
        log_level="info",
    )