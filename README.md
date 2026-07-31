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
- Ultralytics YOLO

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
| `YOLO_ENABLED` | `true` | WebRTC 영상에 YOLO 객체 탐지 overlay를 기본 적용할지 여부 |
| `YOLO_MODEL_PATH` | `yolo11n-pose.pt` | 사용할 YOLO Pose 모델 파일 |
| `YOLO_CONFIDENCE` | `0.35` | YOLO 탐지 confidence 기준값 |
| `FALL_DETECTION_ENABLED` | `true` | YOLO `person` 감지 결과로 넘어짐 감지를 수행할지 여부 |
| `FALL_ASPECT_RATIO_THRESHOLD` | `0.8` | pose 낙상 판정 시 함께 확인할 bbox 가로/세로 비율 |
| `FALL_POSE_ANGLE_THRESHOLD` | `60.0` | 몸통 각도가 수직 기준 이 값 이상이면 넘어짐 후보로 판단 |
| `FALL_EVENT_COOLDOWN_SECONDS` | `10` | 같은 WebRTC track에서 넘어짐 이벤트를 다시 저장하기 전 대기 시간 |

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
- WebRTC 영상 YOLO 객체 탐지 overlay
- YOLO Pose 기반 넘어짐 감지 콘솔 로그 및 `safety_events` 저장

## 6. DB

기본 DB는 SQLite이며 서버 실행 시 `baro.db`가 자동 생성됩니다.

현재 실제 구현된 테이블은 아래와 같습니다.

- `users`
- `cameras`

ERD 기준의 `equipments`, `danger_zones`, `maintenance_modes`는 추후 기능 구현 시 SQLAlchemy model과 route를 추가해야 합니다.
`safety_events`는 YOLO Pose 넘어짐 감지 이력 저장과 조회 API까지 부분 구현되어 있습니다.

### 6.1 Lightweight migration 규칙

현재 프로젝트는 Alembic을 아직 사용하지 않고, `app/db/session.py`의
`run_lightweight_migrations()`에서 이미 배포된 SQLite 테이블에 필요한
신규 컬럼만 보수적으로 추가합니다.

- 새 nullable 컬럼을 추가할 때는 `_PENDING_COLUMNS`에
  `("column_name", "SQL_TYPE")` 형식으로 등록합니다.
- 기존 row가 있는 테이블에 `NOT NULL` 컬럼을 추가해야 한다면 SQLite
  제약 때문에 반드시 `DEFAULT`를 함께 지정합니다.
- UNIQUE 제약처럼 SQLite `ALTER TABLE ADD COLUMN`으로 처리하기 어려운
  변경은 별도 guarded SQL(`CREATE INDEX IF NOT EXISTS` 등)로 추가합니다.
- 테이블 이름 변경, 컬럼 삭제, 데이터 변환, 복잡한 제약조건 변경이
  필요해지는 시점에는 Alembic 도입을 별도 작업으로 진행합니다.

## 7. WebRTC 영상 소스

WebRTC 관련 코드는 아래 파일에 있습니다.

```text
app/api/routes/webrtc.py
app/services/camera_sources.py
app/services/yolo_detector.py
```

하드웨어 CCTV 또는 IP 카메라를 연결할 때는 카메라 등록 API에 `rtspUrl`을 저장한 뒤 WebRTC offer 요청에서 `cameraId`를 넘기면 됩니다.

### 7.1 다른 네트워크의 카메라를 push로 연결하기

카메라가 방화벽/NAT 뒤에 있어 백엔드가 직접 pull(연결)할 수 없는 경우, `docker-compose.yml`에 포함된 `mediamtx` 서비스로 카메라가 직접 push하게 할 수 있습니다.

1. `mediamtx.yml`의 `publishUser`/`publishPass`(기본값 `publisher`/`change-this-password`)를 실제 값으로 바꾸세요.
2. 카메라(또는 카메라 노드)에서 메인 서버로 push:
   ```bash
   ffmpeg -i <카메라 입력> -c copy -f rtsp rtsp://publisher:<비밀번호>@<메인서버IP>:8554/cam1
   ```
3. 백엔드에 카메라 등록 시 `rtspUrl`은 **로컬 주소**로 지정합니다 (백엔드와 mediamtx가 같은 호스트에서 `network_mode: host`로 돌기 때문):
   ```json
   { "name": "원격카메라-1", "rtspUrl": "rtsp://127.0.0.1:8554/cam1", "location": "..." }
   ```
4. 외부 카메라가 push할 수 있으려면 메인 서버의 8554/TCP·UDP 포트를 포트포워딩해야 합니다.

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

YOLO 객체 탐지를 켜려면 source에 `yoloEnabled`를 추가합니다.

```json
{
  "type": "offer",
  "sdp": "v=0...",
  "source": {
    "kind": "webcam",
    "deviceIndex": 0,
    "yoloEnabled": true,
    "yoloConfidence": 0.35
  }
}
```

기본값이 `YOLO_ENABLED=true`라서 프론트에서 `yoloEnabled`를 보내지 않아도 WebRTC 영상에 YOLO overlay가 적용됩니다.
특정 요청에서 끄려면 `source.yoloEnabled`를 `false`로 보내면 됩니다.

## 8. Git 업로드 제외 권장 항목

아래 항목은 저장소에 올리지 않는 것을 권장합니다.

```text
.venv/
__pycache__/
*.pyc
.env
baro.db
```
