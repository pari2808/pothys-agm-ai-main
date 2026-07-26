# Import models registry to ensure all schemas are loaded on startup
from app.db import base  # noqa

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.auth import router as auth_router
from app.api.v1.reports import router as reports_router
from app.api.v1.branches import router as branches_router
from app.api.v1.ai import router as ai_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.emails import router as emails_router
from app.api.v1.notifications import router as notifications_router
from app.db.seed import seed_database

app = FastAPI(
    title="Pothys AGM AI Executive Assistant API",
    description="Domain-restricted enterprise operational monitoring and RAG copilot API",
    version="1.0.0",
)

@app.on_event("startup")
def startup_event():
    import sys
    if "pytest" in sys.modules:
        print("Bypassing database auto-seeding in testing environment.")
        return
    try:
        seed_database()
        print("Database auto-seeding completed successfully on startup.")
    except Exception as e:
        print(f"Database auto-seeding failed on startup: {e}")

# CORS configuration for mobile and web cross-platform requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_origin_regex="http://(localhost|127\\.0\\.0\\.1)(:\\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check status endpoint for load balancer / network gateway."""
    return {"status": "healthy", "service": "Pothys AGM AI Executive Assistant"}

# Mount API Routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication Root"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(reports_router, prefix="/api/v1/reports", tags=["Daily Reports"])
app.include_router(branches_router, prefix="/api/v1/branches", tags=["Branch Monitoring"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Copilot"])
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["Task Management"])
app.include_router(meetings_router, prefix="/api/v1/meetings", tags=["Meeting Management"])
app.include_router(emails_router, prefix="/api/v1/emails", tags=["Email Assistant"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["Notifications"])
