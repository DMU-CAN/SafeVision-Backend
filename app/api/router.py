from fastapi import APIRouter

from app.api.routes import auth, cameras, webrtc

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
