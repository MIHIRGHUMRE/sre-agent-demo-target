"""
Fixed FastAPI Application.

This FastAPI app simulates a production service and includes defensive
programming to avoid crashes when the optional "X-Trigger-Bug" header is set.
If the header is present, the code now validates the presence of the required
`api_key` in the simulated user configuration and returns a clear 400 Bad
Request response instead of raising an unhandled KeyError.
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

_log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_file_handler = RotatingFileHandler(
    settings.log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(_log_formatter)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_log_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# FastAPI app definition
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="SRE Demo Service",
    description="A mock service with a fixed bug for testing self‑healing",
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
    """Log incoming requests and their responses."""
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
        "endpoints": {
            "health": "/health",
            "data": "/api/data",
        },
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

    If the optional ``X-Trigger-Bug`` header is set to ``true``, the endpoint
    validates that the simulated ``user_config`` contains an ``api_key``.
    Missing keys now result in a **400 Bad Request** response instead of an
    unhandled ``KeyError``.
    """
    logger.info(f"Data endpoint called with X-Trigger-Bug={x_trigger_bug}")

    # Simulated user configuration
    user_config = {
        "user_id": 12345,
        "username": "demo_user",
        "preferences": {"theme": "dark", "notifications": True},
        # "api_key" is intentionally omitted to demonstrate validation
    }

    # ------------------------------------------------------------------- #
    # Bug‑trigger path – now defensive
    # ------------------------------------------------------------------- #
    if x_trigger_bug and x_trigger_bug.lower() == "true":
        logger.warning("Bug trigger detected – validating presence of 'api_key'")
        api_key = user_config.get("api_key")
        if not api_key:
            # Return a clear client‑error response instead of raising KeyError
            error_content = {
                "error": "Bad Request",
                "message": "Missing required field 'api_key' in user configuration.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.error(
                "Missing 'api_key' in user_config while bug trigger was active",
                extra={"request_path": request.url.path},
            )
            return JSONResponse(status_code=400, content=error_content)

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
    Fallback handler for unexpected ``KeyError`` occurrences.
    Returns a 500 response but logs detailed information for debugging.
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
        f"Unexpected KeyError in {request.url.path}: Missing key {exc}",
        exc_info=True,
    )
    return JSONResponse(status_code=500, content=error_details)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch‑all handler for any other unexpected errors."""
    logger.error(
        f"Unexpected error in {request.url.path}: {str(exc)}",
        exc_info=True,
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