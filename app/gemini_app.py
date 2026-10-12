"""
gemini_app.py
=============
Optional entry point: the existing app plus the Gemini router. app/main.py is untouched.

    uvicorn app.gemini_app:app --reload

To remove the Gemini feature, delete this file, app/api/gemini_router.py,
app/services/gemini_service.py and app/services/gemini_pipeline.py
(and frontend/study-planner.html + frontend/src/gemini/).
"""

from app.main import app
from app.api.core.config import settings
from app.api.gemini_router import router as gemini_router

app.include_router(gemini_router, prefix=settings.API_V1_STR)
