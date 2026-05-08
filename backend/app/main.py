from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.settings import get_settings
from app.db.sqlite import init_db


settings = get_settings()

app = FastAPI(
    title="Agentic Job Hunt Pipeline API",
    version="0.1.0",
    description="Human-in-the-loop job application automation assistant.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db(settings.database_url)


app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
