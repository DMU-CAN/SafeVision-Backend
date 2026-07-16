from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import error_response
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "인증 토큰이 필요합니다."),
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "유효하지 않은 인증 토큰입니다."),
        ) from None

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "사용자를 찾을 수 없습니다."),
        )

    return user
