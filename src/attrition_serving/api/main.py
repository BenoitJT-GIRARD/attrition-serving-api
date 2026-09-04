"""The application object, its lifespan, and the one route that needs no key.

The engine is disposed on shutdown rather than left to the garbage collector: a pool that
outlives the process holds connections a managed PostgreSQL counts against a quota.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from attrition_serving.api.deps import dispose_engine
from attrition_serving.api.routers.predict import router as predict_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Hand the connection pool back on shutdown.

    Without this the pool outlived the application. It goes unnoticed in production, where
    the process ends anyway, and shows up in the test suite -- which reloads this module to
    reconfigure the app -- as a connection deleted while still open.
    """
    yield
    dispose_engine()


app = FastAPI(
    title="Attrition serving API",
    version="1.0.0",
    description=(
        "Attrition scoring with a logged decision: every prediction is written to "
        "PostgreSQL with the probability, the threshold and the model version that "
        "produced it."
    ),
    lifespan=lifespan,
)


# HF Space ouvre souvent "/". On redirige vers Swagger.
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(predict_router)
