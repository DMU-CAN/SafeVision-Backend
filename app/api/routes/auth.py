from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.responses import error_response, success_response
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RefreshRequest, SignupRequest, TokenBundle, UserResponse


router = APIRouter()


def serialize_model(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.scalar(select(User).where(User.username == payload.username))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response("DUPLICATE_USERNAME", "이미 사용 중인 username입니다."),
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone_number=payload.phone_number,
        department=payload.department,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    data = serialize_model(UserResponse.model_validate(user))
    return success_response(data=data, message="회원가입이 완료되었습니다.")


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("INVALID_CREDENTIALS", "username 또는 password가 올바르지 않습니다."),
        )

    access_token = create_token(
        subject=str(user.id),
        token_type="access",
        expires_delta=timedelta(seconds=settings.access_token_expire_seconds),
    )
    refresh_token = create_token(
        subject=str(user.id),
        token_type="refresh",
        expires_delta=timedelta(seconds=settings.refresh_token_expire_seconds),
    )
    bundle = TokenBundle(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_seconds,
        user=UserResponse.model_validate(user),
    )
    return success_response(data=serialize_model(bundle), message="로그인되었습니다.")


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = int(token_payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("INVALID_REFRESH_TOKEN", "refreshToken이 유효하지 않습니다."),
        ) from None

    if db.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("INVALID_REFRESH_TOKEN", "사용자를 찾을 수 없습니다."),
        )

    access_token = create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(seconds=settings.access_token_expire_seconds),
    )
    data = serialize_model(AccessTokenResponse(access_token=access_token, expires_in=settings.access_token_expire_seconds))
    return success_response(data=data, message="액세스 토큰이 재발급되었습니다.")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
