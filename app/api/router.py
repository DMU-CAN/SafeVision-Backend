from fastapi import APIRouter

from app.api.routes import auth, cameras, emergency, equipment, equipments, robots, safety_events, webrtc, zones

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(emergency.router, prefix="/emergency", tags=["emergency"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(equipments.router, prefix="/equipments", tags=["equipments"])
api_router.include_router(robots.router, prefix="/robots", tags=["robots"])
api_router.include_router(safety_events.router, prefix="/safety-events", tags=["safety-events"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])
api_router.include_router(zones.router, prefix="/zones", tags=["zones"])
