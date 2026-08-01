from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models  # noqa: F401
from app.api.router import api_router
from app.api.routes.webrtc import close_all_sessions
from app.core.config import get_settings
from app.core.responses import error_response, success_response
from app.db.session import Base, SessionLocal, engine, run_lightweight_migrations
from app.models.camera import Camera
from app.services.camera_stream_hub import start_camera_hub, stop_all_camera_hubs
from app.services.recording_service import start_recording, stop_all_recordings


settings = get_settings()
Base.metadata.create_all(bind=engine)
run_lightweight_migrations()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        for camera in db.query(Camera).all():
            start_camera_hub(camera.id, camera.rtsp_url)
            start_recording(camera.id, camera.rtsp_url)
    finally:
        db.close()

    yield

    stop_all_recordings()
    await stop_all_camera_hubs()
    await close_all_sessions()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORSMiddleware treats WebSocket upgrade requests like browser requests and
# rejects unknown origins with 403 — but robot nodes are server-side Python
# clients, not browsers, so CORS doesn't apply to them. Strip the Origin
# header from WebSocket scopes before CORS sees it; an absent Origin is
# always passed through unchanged by CORSMiddleware.
from starlette.types import ASGIApp, Receive, Scope, Send  # noqa: E402


class _StripWebSocketOrigin:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            scope = {
                **scope,
                "headers": [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"origin"],
            }
        await self.app(scope, receive, send)


app.add_middleware(_StripWebSocketOrigin)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and exc.detail.get("success") is False:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response("HTTP_ERROR", str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "reason": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_response("VALIDATION_ERROR", "요청 값이 올바르지 않습니다.", details),
    )

@app.get("/")
def read_root():
    return {"message": "Hello FastAPI!"}

@app.get("/health")
def health_check():
    return success_response(data={"status": "ok"})


app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.environment == "local",
    )
