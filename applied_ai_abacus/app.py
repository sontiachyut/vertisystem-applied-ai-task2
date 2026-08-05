from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .config import AbacusSettings
from .db import build_engine, build_session_factory
from .models import AddNumberRequest, SumResponse
from .repository import AbacusRepository, SumOverflowError
from .service import AbacusService


DATABASE_UNAVAILABLE_DETAIL = "Authoritative database is unavailable."


def create_app(*, database_url: str | None = None) -> FastAPI:
    settings = AbacusSettings.from_env(database_url=database_url)
    engine = build_engine(settings.database_url)
    repository = AbacusRepository(engine=engine, session_factory=build_session_factory(engine))
    service = AbacusService(repository=repository)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Iterator[None]:
        service.bootstrap()
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Abacus Service", lifespan=lifespan)
    app.state.abacus_service = service

    @app.exception_handler(OperationalError)
    def handle_operational_error(_: Request, __: OperationalError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": DATABASE_UNAVAILABLE_DETAIL})

    @app.post("/abacus/number", response_model=SumResponse)
    def add_number(
        payload: AddNumberRequest,
        abacus_service: AbacusService = Depends(_get_abacus_service),
    ) -> SumResponse:
        try:
            return SumResponse(sum=abacus_service.add_number(payload.number))
        except SumOverflowError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/abacus/sum", response_model=SumResponse)
    def get_sum(abacus_service: AbacusService = Depends(_get_abacus_service)) -> SumResponse:
        return SumResponse(sum=abacus_service.get_sum())

    @app.delete("/abacus/sum", response_model=SumResponse)
    def reset_sum(abacus_service: AbacusService = Depends(_get_abacus_service)) -> SumResponse:
        return SumResponse(sum=abacus_service.reset_sum())

    return app


def _get_abacus_service(request: Request) -> AbacusService:
    return request.app.state.abacus_service
