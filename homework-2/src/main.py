"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routers.categories import router as categories_router
from .routers.tickets import router as tickets_router

app = FastAPI(title="Intelligent Customer Support System", version="1.0.0")
app.include_router(tickets_router)
app.include_router(categories_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content=jsonable_encoder({"detail": exc.errors()}))


@app.get("/health")
def health_check():
    return {"status": "ok"}
