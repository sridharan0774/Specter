from app.core.config import settings


def test_settings_load():
    """Verify that settings are loaded with sensible default values."""
    assert settings.PROJECT_NAME == "SPECTER — Blockchain Intelligence & VASP Attribution Engine"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DATABASE_URL is not None
    assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
