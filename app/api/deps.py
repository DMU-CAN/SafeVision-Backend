from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.responses import error_response
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    # <video>/<img> src="..." requests (timeshift clips, event clips) can't
    # set an Authorization header, so they pass the token as a query param
    # instead — the header takes priority whenever both are present.
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "인증 토큰이 필요합니다."),
        )

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
