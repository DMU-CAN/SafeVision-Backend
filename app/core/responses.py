from typing import Any


def success_response(data: Any = None, message: str = "요청이 정상 처리되었습니다.") -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def error_response(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }
