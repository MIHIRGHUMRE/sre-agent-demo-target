from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LOG_FILE = Path(__file__).with_name("app_logs.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("demo_service")

app = FastAPI(title="Safe Demo SRE Target")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(
        "HTTP %s %s -> %s in %.2f ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(KeyError)
async def keyerror_exception_handler(request: Request, exc: KeyError):
    logger.exception("KeyError for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {
        "service": "safe-demo-sre-target",
        "status": "ok",
        "endpoints": ["/", "/health", "/api/data"],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "safe-demo-sre-target"}


@app.get("/api/data")
async def get_data(request: Request):
    trigger_bug = request.headers.get("X-Trigger-Bug", "").lower() == "true"
    logger.info("Processing /api/data request with X-Trigger-Bug=%s", trigger_bug)

    if trigger_bug:
        demo_config = {}
        _ = demo_config["api_key"]

    return {
        "status": "success",
        "data": {
            "message": "Normal data response",
            "source": "demo-service",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
