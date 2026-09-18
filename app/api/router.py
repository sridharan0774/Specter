from fastapi import APIRouter
from app.api.endpoints import health, cases, trace, vasp, patterns, investigation

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases Management"])
api_router.include_router(trace.router, tags=["Multi-Hop Tracing Engine"])
api_router.include_router(vasp.router, tags=["VASP Attribution Engine"])
api_router.include_router(patterns.router, tags=["Velocity & Typologies Engine"])
api_router.include_router(investigation.router, tags=["Investigation Orchestrator & Evidence Engine"])




