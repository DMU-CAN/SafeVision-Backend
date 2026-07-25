from fastapi import APIRouter

from app.api.routes import auth, cameras, safety_events, webrtc

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(safety_events.router, prefix="/safety-events", tags=["safety-events"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
