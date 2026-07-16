# BARO BackEnd

BARO 현장 안전 관제 시스템의 FastAPI 백엔드입니다.

API 명세는 루트의 `API_SPEC.md`에서 관리하고, 이 문서는 백엔드 실행과 개발 환경만 설명합니다.

## 1. 기술 스택

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite
- JWT
- aiortc
- OpenCV

## 2. 실행 방법

```powershell
cd BackEnd
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

서버가 실행되면 아래 주소를 사용할 수 있습니다.

```text
API Base URL: http://localhost:8080/api/v1
Health Check: http://localhost:8080/health
Swagger UI:   http://localhost:8080/docs
```

## 3. 환경 변수

`.env.example`을 `.env`로 복사해서 사용합니다.

| 이름 | 기본값 | 설명 |
|---|---|---|
| `APP_NAME` | `BARO API` | 앱 이름 |
| `ENVIRONMENT` | `local` | 실행 환경 |
| `BACKEND_HOST` | `127.0.0.1` | 서버 host |
| `BACKEND_PORT` | `8080` | 서버 port |
| `DATABASE_URL` | `sqlite:///./baro.db` | DB 연결 주소 |
| `JWT_SECRET_KEY` | `change-this-secret-in-production` | JWT 서명 키 |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `3600` | accessToken 만료 시간 |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `1209600` | refreshToken 만료 시간 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 허용할 프론트엔드 origin |
| `DEFAULT_CAMERA_SOURCE_KIND` | `test_pattern` | 기본 WebRTC 영상 소스 |
| `DEFAULT_WEBCAM_INDEX` | `0` | 기본 웹캠 장치 번호 |

## 4. 폴더 구조

```text
BackEnd/
  app/
    api/
      routes/        # auth, cameras, webrtc route
      deps.py        # FastAPI dependency
      router.py      # API router 통합
    core/            # config, response, security
    db/              # SQLAlchemy session
    models/          # SQLAlchemy models
    schemas/         # Pydantic schemas
    services/        # WebRTC camera source adapters
    main.py          # FastAPI app entrypoint
  .env.example
  requirements.txt
  README.md
```

## 5. 현재 구현 범위

- 회원가입
- 로그인
- accessToken 재발급
- 로그아웃
- 카메라 등록/조회/수정/삭제
- WebRTC signaling
- WebRTC 영상 소스 어댑터
  - `test_pattern`
  - `webcam`
  - `rtsp`
  - `file`

## 6. DB

기본 DB는 SQLite이며 서버 실행 시 `baro.db`가 자동 생성됩니다.

현재 실제 구현된 테이블은 아래와 같습니다.

- `users`
- `cameras`

ERD 기준의 `equipments`, `danger_zones`, `safety_events`, `maintenance_modes`는 추후 기능 구현 시 SQLAlchemy model과 route를 추가해야 합니다.

## 7. WebRTC 영상 소스

WebRTC 관련 코드는 아래 파일에 있습니다.

```text
app/api/routes/webrtc.py
app/services/camera_sources.py
```

하드웨어 CCTV 또는 IP 카메라를 연결할 때는 카메라 등록 API에 `rtspUrl`을 저장한 뒤 WebRTC offer 요청에서 `cameraId`를 넘기면 됩니다.

직접 source를 넘기는 예시는 아래와 같습니다.

```json
{
  "type": "offer",
  "sdp": "v=0...",
  "source": {
    "kind": "rtsp",
    "url": "rtsp://user:pass@192.168.0.10:554/stream1"
  }
}
```

백엔드 서버에 연결된 웹캠을 사용할 때는 아래처럼 요청합니다.

```json
{
  "type": "offer",
  "sdp": "v=0...",
  "source": {
    "kind": "webcam",
    "deviceIndex": 0
  }
}
```

## 8. Git 업로드 제외 권장 항목

아래 항목은 저장소에 올리지 않는 것을 권장합니다.

```text
.venv/
__pycache__/
*.pyc
.env
baro.db
```
