from fastapi import APIRouter
from app.api.routes import appointment_requests, audit, graph_reviews, health, reference, reviews, workflows

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(reference.router)
api_router.include_router(appointment_requests.router)
api_router.include_router(workflows.router)
api_router.include_router(reviews.router)
api_router.include_router(graph_reviews.router)
api_router.include_router(audit.router)
