import logging

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.v1.administration.routes import router as administration_router
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.care.routes import router as care_router
from app.api.v1.clients.documents import router as intake_documents_router
from app.api.v1.clients.routes import router as clients_router
from app.api.v1.clinical.routes import router as clinical_router
from app.api.v1.medication.routes import router as medication_router
from app.api.v1.rehabilitation.routes import router as rehabilitation_router
from app.api.v1.billing.routes import router as billing_router
from app.api.v1.finance.routes import router as finance_router
from app.api.v1.residential.routes import router as residential_router
from app.api.v1.discharge.routes import router as discharge_router
from app.api.v1.inventory.routes import router as inventory_router
from app.api.v1.reporting.routes import router as reporting_router
from app.api.v1.compliance.routes import router as compliance_router
from app.api.v1.staff.routes import router as staff_router
from app.api.v1.administration.jobs import router as jobs_router
from app.api.v1.clinical.governance import router as clinical_governance_router
from app.api.v1.privacy.routes import router as privacy_router
from app.api.v1.search.routes import router as search_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.observability import check_database, check_redis, init_error_tracking

configure_logging()
init_error_tracking()
settings = get_settings()
app = FastAPI(
    title="ARS RMS API",
    version="1.0.0",
    docs_url="/api/v1/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(administration_router, prefix="/api/v1")
for router in [
    clients_router,
    intake_documents_router,
    rehabilitation_router,
    clinical_router,
    clinical_governance_router,
    medication_router,
    care_router,
    billing_router,
    finance_router,
    residential_router,
    discharge_router,
    inventory_router,
    reporting_router,
    compliance_router,
    staff_router,
    jobs_router,
    privacy_router,
    search_router,
]:
    app.include_router(router, prefix="/api/v1")


@app.middleware("http")
async def correlation_and_observability(request: Request, call_next):
    import time
    import uuid

    # Request Correlation ID
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id

    # Security check for browser writes
    origin = request.headers.get("origin")
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and origin
        and origin not in settings.backend_cors_origins
    ):
        return JSONResponse(status_code=403, content={"error": {"message": "Origin not allowed"}})

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Attach correlation & security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"

    # Structured request logging
    logging.getLogger("ars.http").info(
        f"{request.method} {request.url.path} {response.status_code}",
        extra={
            "request_id": request_id,
            "route": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(HTTPException)
async def domain_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code, content={"error": {"message": exc.detail}}, headers=exc.headers
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422, content={"error": {"message": "Validation failed", "fields": errors}}
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={"error": {"message": "This change conflicts with an existing record"}},
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger("ars").error("unexpected_error", extra={"exception_type": type(exc).__name__})
    return JSONResponse(
        status_code=500, content={"error": {"message": "An unexpected error occurred"}}
    )


@app.get("/health/live", tags=["Observability"])
def health_live():
    """Liveness probe indicating process is responsive."""
    return {"status": "live"}


@app.get("/health/ready", tags=["Observability"])
def health_ready(response: Response):
    """Readiness probe checking database and critical runtime dependencies."""
    db_ok, db_msg = check_database()
    redis_ok, redis_msg = check_redis()

    # In production, DB is strictly required for readiness
    is_ready = db_ok
    if not is_ready:
        response.status_code = 503
        return {
            "status": "not_ready",
            "checks": {"database": db_msg, "redis": redis_msg},
        }

    return {
        "status": "ready",
        "version": "1.0.0",
        "checks": {"database": db_msg, "redis": redis_msg},
    }


@app.get("/api/v1/health", tags=["Health"])
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy"}


@app.get("/api/v1/system/version", tags=["System"])
def system_version():
    """Returns application release and build version metadata."""
    return {
        "name": "ReHUB Rehabilitation Management System",
        "version": "1.0.0",
        "release": "v1.0.0-rc1",
        "environment": settings.environment,
        "build_date": "2026-10-12",
    }

