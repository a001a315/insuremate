import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, chat, claims, documents, health, hospital, misc, patients, policies, records
from app.core.config import get_settings
from app.services.errors import NotFound, ValidationFailed
from app.services.llm import LLMUnavailable
from app.services.reminders.service import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.rag import vectorstore
    vectorstore.stats()  # warm up the vector store before serving requests
    sched = start_scheduler()
    yield
    if sched:
        sched.shutdown(wait=False)


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    s = get_settings()
    app = FastAPI(title=s.app_name, version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(NotFound)
    async def _nf(_: Request, e: NotFound):
        return JSONResponse({"detail": str(e)}, status_code=404)  # also used for other users' resources

    @app.exception_handler(ValidationFailed)
    async def _vf(_: Request, e: ValidationFailed):
        return JSONResponse({"detail": str(e)}, status_code=422)

    @app.exception_handler(LLMUnavailable)
    async def _llm(_: Request, e: LLMUnavailable):
        return JSONResponse({"detail": str(e)}, status_code=503)

    for r in (health.router, auth.router, patients.router, hospital.router, policies.router, claims.router, records.router,
              documents.router, chat.router, misc.router):
        app.include_router(r, prefix="/api")
    return app


app = create_app()
