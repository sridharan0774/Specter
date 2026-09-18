from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health", summary="System Health & Status Check")
def health_check(db: Session = Depends(get_db)):
    """
    Returns system operational status, database connectivity, and configured providers.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "version": settings.VERSION,
        "database": db_status,
        "providers_configured": {
            "tron": settings.TRONGRID_API_KEY is not None,
            "ethereum": settings.ETHERSCAN_API_KEY is not None,
            "polygon": settings.POLYGONSCAN_API_KEY is not None,
            "bsc": settings.BSCSCAN_API_KEY is not None,
        },
        "redis_configured": settings.REDIS_URL is not None,
    }
