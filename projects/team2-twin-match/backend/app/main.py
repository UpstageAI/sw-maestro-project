from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import config
from app.core.errors.error import BaseAPIException
from app.core.errors.handler import api_error_handler
from app.core.lifespan import lifespan
from app.routers import router


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, **config.fastapi_kwargs)

    app.include_router(router)
    app.add_exception_handler(BaseAPIException, api_error_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
