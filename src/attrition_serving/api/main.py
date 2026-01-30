from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from attrition_serving.api.routers.predict import router as predict_router

app = FastAPI(
    title="Attrition serving API",
    version="1.0.0",
    description="API de scoring de probabilité de démission (POC) avec traçabilité DB.",
)


# HF Space ouvre souvent "/". On redirige vers Swagger.
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


app.include_router(predict_router)
