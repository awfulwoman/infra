"""
ZFS Status API - REST API for ZFS pool, dataset, and snapshot monitoring

This FastAPI application provides read-only access to ZFS status information
including pools, datasets, snapshots, and backup status.
"""
import os
import logging
import yaml
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import pools, datasets, snapshots, backups

# Configure logging
log_level = os.getenv("ZFS_API_LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load custom OpenAPI schema from swagger.yaml
def load_custom_openapi():
    """Load custom OpenAPI specification from swagger.yaml"""
    swagger_file = Path(__file__).parent / "swagger.yaml"
    if swagger_file.exists():
        with open(swagger_file, 'r') as f:
            return yaml.safe_load(f)
    return None

# Create FastAPI application
app = FastAPI(
    title="ZFS Status API",
    description="REST API for ZFS pool, dataset, and snapshot monitoring",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Override OpenAPI schema with custom swagger.yaml
custom_openapi_schema = load_custom_openapi()
if custom_openapi_schema:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = custom_openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    logger.info("Loaded custom OpenAPI schema from swagger.yaml")

# CORS middleware configuration
cors_origins = os.getenv("ZFS_API_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.utcnow()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Log request details
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )

    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("ZFS_API_LOG_LEVEL") == "debug" else "An error occurred"
        }
    )

# Include routers
app.include_router(pools.router, prefix="/api/v1/pools", tags=["pools"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
app.include_router(snapshots.router, prefix="/api/v1/snapshots", tags=["snapshots"])
app.include_router(backups.router, prefix="/api/v1/backups", tags=["backups"])

@app.get("/api/v1/health", tags=["health"])
async def health_check():
    """
    API health check endpoint.

    Returns basic status information about the API service.
    """
    return {
        "status": "healthy",
        "service": "zfs-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/")
async def root():
    """
    Root endpoint.

    Provides basic information and links to API documentation.
    """
    return {
        "message": "ZFS Status API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "openapi": "/api/openapi.json"
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("ZFS_API_HOST", "0.0.0.0")
    port = int(os.getenv("ZFS_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
