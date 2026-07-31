# BARO API 명세서

## 1. 공통 정보

- Base URL: `http://localhost:8080/api/v1`
- 서버 상태 확인: `GET http://localhost:8080/health`
- Swagger UI: `http://localhost:8080/docs`
- API 문서 기준: FastAPI 백엔드 현재 구현 코드
- ERD 기준: `https://www.erdcloud.com/d/nT84ar7rBrhudAQaN`
- Content-Type: `application/json`
- 인증 방식: `Authorization: Bearer <accessToken>`

> 이 문서는 BARO 백엔드 API 명세서입니다. 백엔드 실행 방법, 가상환경 설치, 폴더 구조 설명은 `BackEnd/README.md`에서 관리합니다.

### 공통 구현 규칙

- request body는 JSON object를 사용합니다.
- response field는 프론트엔드 호출 방식에 맞춰 camelCase를 사용합니다.
- DB column은 SQLAlchemy 모델 기준 snake_case를 사용합니다.
- 날짜/시간 응답은 ISO 8601 string을 사용합니다.
- `DELETE` 성공 응답은 `204 No Content`이며 body를 반환하지 않습니다.
- 현재 인증 토큰 발급 기능은 구현되어 있으나, 카메라/WebRTC API에는 아직 인증 의존성이 강제 적용되어 있지 않습니다.
- SQLite 개발 환경에서는 `BIGINT`, `TIMESTAMP`가 각각 `INTEGER`, `DATETIME` 계열로 표현될 수 있습니다.

## 2. 구현 상태 기준

| 상태 | 의미 |
|---|---|
| 구현완료 | 현재 FastAPI 코드에 route, schema, DB 연동 또는 응답 흐름이 구현되어 있음 |
| 부분구현 | 기본 route는 있으나 운영 수준 검증, 인증 적용, 실제 장비 연동 등이 남아 있음 |
| 예정 | ERD 또는 기획 기준으로 필요하지만 아직 코드 구현 전 |

## 3. 공통 응답 포맷

### 성공

```json
{
  "success": true,
  "data": {},
  "message": "요청이 정상 처리되었습니다."
}
```

### 실패

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 값이 올바르지 않습니다.",
    "details": [
      {
        "field": "body.password",
        "reason": "String should have at least 8 characters"
      }
    ]
  }
}
```

### 공통 상태 코드

| Status | 설명 |
|---:|---|
| 200 | 조회/수정 성공 |
| 201 | 생성 성공 |
| 204 | 삭제/종료 성공, body 없음 |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 |
| 404 | 리소스 없음 |
| 409 | 중복 또는 충돌 |
| 422 | 요청 값 검증 실패 |
| 500 | 서버 오류 |

### 공통 에러 코드

| Status | Code | 설명 |
|---:|---|---|
| 400 | `INVALID_REQUEST` | 요청 형식이 올바르지 않음 |
| 401 | `UNAUTHORIZED` | 인증 정보가 없거나 유효하지 않음 |
| 404 | `NOT_FOUND` | 요청한 리소스를 찾을 수 없음 |
| 409 | `CONFLICT` | 중복 또는 상태 충돌 |
| 422 | `VALIDATION_ERROR` | 필수 값 누락, 타입 불일치, 길이 제한 위반 등 |
| 500 | `INTERNAL_SERVER_ERROR` | 처리되지 않은 서버 오류 |

## 4. 전체 API 목록

| Domain | Method | Path | 설명 | 상태 |
|---|---|---|---|---|
| System | GET | `/health` | 서버 상태 확인 | 구현완료 |
| Auth | POST | `/api/v1/auth/signup` | 회원가입 | 구현완료 |
| Auth | POST | `/api/v1/auth/login` | 로그인 및 토큰 발급 | 구현완료 |
| Auth | POST | `/api/v1/auth/refresh` | accessToken 재발급 | 구현완료 |
| Auth | POST | `/api/v1/auth/logout` | 로그아웃 | 구현완료 |
| Camera | GET | `/api/v1/cameras` | 카메라 목록 조회 | 구현완료 |
| Camera | POST | `/api/v1/cameras` | CCTV/RTSP 카메라 등록 | 구현완료 |
| Camera | GET | `/api/v1/cameras/{cameraId}` | 카메라 상세 조회 | 구현완료 |
| Camera | PUT | `/api/v1/cameras/{cameraId}` | 카메라 정보 수정 | 구현완료 |
| Camera | DELETE | `/api/v1/cameras/{cameraId}` | 카메라 삭제 | 구현완료 |
| Camera | GET | `/api/v1/cameras/{cameraId}/stream-url` | 카메라 RTSP URL 조회 | 구현완료 |
| Camera | GET | `/api/v1/cameras/{cameraId}/timeshift` | 과거 최대 30분 영상(mp4) 조회 | 구현완료 |
| WebRTC | GET | `/api/v1/webrtc/sources` | 영상 소스 어댑터 목록 조회 | 구현완료 |
| WebRTC | POST | `/api/v1/webrtc/offer` | SDP offer를 받아 SDP answer 생성 | 구현완료 |
| WebRTC | GET | `/api/v1/webrtc/sessions/{sessionId}` | WebRTC 세션 상태 조회 | 구현완료 |
| WebRTC | DELETE | `/api/v1/webrtc/sessions/{sessionId}` | WebRTC 세션 종료 | 구현완료 |
| Equipment | POST | `/api/v1/equipment/stop` | 설비 정지 명령 전송 | 구현완료 |
| Equipment | POST | `/api/v1/equipment/slow` | 설비 감속 명령 전송 | 구현완료 |
| Equipment | POST | `/api/v1/equipment/resume` | 설비 재가동 명령 전송 | 구현완료 |
| Equipment | GET | `/api/v1/equipments` | 다중 설비 목록 조회 | 구현완료 |
| Equipment | POST | `/api/v1/equipments` | 다중 설비 등록 | 구현완료 |
| Equipment | GET/PUT/DELETE | `/api/v1/equipments/{equipmentId}` | 다중 설비 상세/수정/삭제 | 구현완료 |
| Equipment | POST | `/api/v1/equipments/{equipmentId}/stop` \| `/slow` \| `/resume` | 설비별 제어 명령 전송 | 구현완료 |
| Zone | GET | `/api/v1/zones` | 위험 구역 목록 조회 | 구현완료 |
| Zone | POST | `/api/v1/zones` | 위험 구역 등록 | 구현완료 |
| Zone | DELETE | `/api/v1/zones/{zoneId}` | 위험 구역 삭제 | 구현완료 |
| SafetyEvent | GET | `/api/v1/safety-events` | 안전 이벤트 목록 조회 | 구현완료 |
| SafetyEvent | POST | `/api/v1/safety-events` | 안전 이벤트 등록 | 예정 |
| SafetyEvent | GET | `/api/v1/safety-events/{eventId}` | 안전 이벤트 상세 조회 | 구현완료 |
| SafetyEvent | GET | `/api/v1/safety-events/{eventId}/clip` | 이벤트 영상 클립 재생 | 구현완료 |
| Robot | GET | `/api/v1/robots` | 현장 로봇 목록 조회 | 구현완료 |
| Robot | POST | `/api/v1/robots` | 현장 로봇 등록 | 구현완료 |
| Robot | GET | `/api/v1/robots/{robotId}` | 현장 로봇 상세 조회 | 구현완료 |
| Robot | PUT | `/api/v1/robots/{robotId}` | 현장 로봇 정보 수정 | 구현완료 |
| Robot | DELETE | `/api/v1/robots/{robotId}` | 현장 로봇 삭제 | 구현완료 |
| Robot | POST | `/api/v1/robots/{robotId}/ptz` | PTZ/이동 명령 전송 | 구현완료 |
| Robot | POST | `/api/v1/robots/{robotId}/dispatch` | 로봇 출동 기록 생성 | 구현완료 |
| Robot | GET | `/api/v1/robots/{robotId}/dispatches` | 로봇 출동 이력 조회 | 구현완료 |
| Emergency | POST | `/api/v1/emergency/contact` | 응급센터 연결 요청 (스텁) | 구현완료 |
| Emergency | POST | `/api/v1/emergency/share` | 응급센터에 현장 상황 공유 (스텁) | 구현완료 |
| MaintenanceMode | GET | `/api/v1/maintenance-modes` | 정비 모드 목록 조회 | 예정 |
| MaintenanceMode | POST | `/api/v1/equipments/{equipmentId}/maintenance-modes` | 정비 모드 시작 | 예정 |
| MaintenanceMode | PATCH | `/api/v1/maintenance-modes/{maintenanceModeId}/end` | 정비 모드 종료 | 예정 |

## 5. ERD 기준 데이터 모델

ERDCloud 원본: `https://www.erdcloud.com/d/nT84ar7rBrhudAQaN`

### 5.1 users

현재 구현완료.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 사용자 PK |
| `username` | VARCHAR(50) | `username` | 로그인 ID |
| `password_hash` | VARCHAR(255) | 응답 제외 | 해시된 비밀번호 |
| `name` | VARCHAR(50) | `name` | 사용자 이름 |
| `phone_number` | VARCHAR(20) | `phoneNumber` | 연락처 |
| `department` | VARCHAR(100) | `department` | 부서 |
| `role` | VARCHAR(20) | `role` | 권한 |
| `created_at` | TIMESTAMP | `createdAt` | 생성 일시 |

권장 role 값:

```text
ADMIN, MANAGER, OPERATOR
```

### 5.2 cameras

현재 구현완료.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 카메라 PK |
| `name` | VARCHAR(100) | `name` | 카메라 이름 |
| `rtsp_url` | VARCHAR(255) | `rtspUrl` | CCTV/RTSP 스트림 주소 |
| `location` | VARCHAR(255) | `location` | 설치 위치 |
| `status` | VARCHAR(30) | `status` | 카메라 상태 |
| `location_x` | FLOAT, nullable | `locationX` | 실내 도면 좌표 (로봇 출동 목표 계산에 사용, 미설정 시 null) |
| `location_y` | FLOAT, nullable | `locationY` | 실내 도면 좌표 |

권장 status 값:

```text
ONLINE, OFFLINE, MAINTENANCE
```

### 5.3 equipments (설비 DB 테이블)

예정. 아래 `/api/v1/equipment/*` 제어 API는 이 DB 테이블 없이 시리얼 포트로 직접 명령을 전송하는 별도 기능이며, 여러 설비를 구분해 관리하려면 이 테이블 구현이 필요합니다.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 장비 PK |
| `name` | VARCHAR(100) | `name` | 장비 이름 |
| `control_protocol` | VARCHAR(50) | `controlProtocol` | 제어 프로토콜 |
| `control_address` | VARCHAR(100) | `controlAddress` | 제어 주소 |
| `updated_at` | TIMESTAMP | `updatedAt` | 수정 일시 |

### 5.4 zones

현재 구현완료. (ERD상 명칭은 `danger_zones`이지만 실제 테이블/엔드포인트명은 `zones`입니다.)

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 위험 구역 PK |
| `camera_id` | BIGINT, nullable | `cameraId` | 연결 카메라 ID |
| `name` | VARCHAR(100) | `name` | 위험 구역 이름 |
| `points` | JSON | `points` | `[{x, y}, ...]` 꼭짓점 배열. 프론트 `CameraFeed`의 1000x600 정규화 좌표 기준, 실제 카메라 해상도와 무관 |
| `is_active` | BOOLEAN | `isActive` | 활성 여부 (삭제는 실제로 row를 지움, soft-delete 필드는 아님) |

### 5.5 safety_events

현재 구현완료. (등록/생성 API는 아직 없고 백엔드 내부에서만 적재됩니다.)

- `FALL_DETECTED`: YOLO Pose로 넘어짐 감지 시 저장. 위험구역 설정 여부와 무관하게, 화면 어디서든 넘어짐이 감지되면 기록됨.
- `ZONE_INTRUSION`: 넘어짐 여부와 무관하게, 사람이 설정된 위험구역 안에 있는 것이 감지되면 저장. `zoneId`에 감지된 구역이 채워짐.

두 이벤트 모두 발생 시 설비 정지 명령을 전송하고, 각각 자체 쿨다운(기본 10초)으로 중복 기록을 방지합니다.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 이벤트 PK |
| `camera_id` | BIGINT, nullable | `cameraId` | 발생 카메라 ID |
| `equipment_id` | BIGINT, nullable | `equipmentId` | 관련 장비 ID |
| `zone_id` | BIGINT, nullable | `zoneId` | 관련 위험 구역 ID |
| `event_type` | VARCHAR(50) | `eventType` | 이벤트 유형 |
| `event_level` | INT | `eventLevel` | 이벤트 등급 |
| `clip_path` | VARCHAR(255), nullable | `clipPath` | 이벤트 영상 클립의 서버 내부 상대 경로. null이면 아직 준비 중이거나(발생 직후 최대 `RECORDING_CLIP_POST_ROLL_SECONDS`초) 카메라에 녹화 버퍼가 없던 경우. 클라이언트는 이 값 유무만 보고 `GET /safety-events/{eventId}/clip` 재생 가능 여부를 판단 |
| `created_at` | TIMESTAMP | `createdAt` | 생성 일시 |

카메라별로 백엔드가 RTSP를 항상 롤링 버퍼(기본 30초 세그먼트 x 20개 = 최근 10분)로 녹화합니다. `FALL_DETECTED` 이벤트 발생 시 그 시점의 버퍼 세그먼트를 이벤트 전후 맥락이 담기도록 잘라 `recordings/clips/event_{id}.mp4`로 보존합니다(발생 후 `RECORDING_CLIP_POST_ROLL_SECONDS`초 뒤 비동기로 처리).

### GET `/api/v1/safety-events/{eventId}/clip`

이벤트에 연결된 영상 클립(mp4)을 반환합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

`Content-Type: video/mp4` 바이너리 스트림.

#### Errors

| Status | Code | 설명 |
|---:|---|---|
| 404 | `SAFETY_EVENT_NOT_FOUND` | 해당 eventId의 이벤트 없음 |
| 404 | `CLIP_NOT_READY` | 이벤트는 있지만 클립이 아직 저장되지 않음 |
| 404 | `CLIP_NOT_FOUND` | `clipPath`는 있지만 실제 파일이 없음 |

### 5.6 maintenance_modes

구현 예정.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 정비 모드 PK |
| `equipment_id` | BIGINT | `equipmentId` | 대상 장비 ID |
| `user_id` | BIGINT | `userId` | 작업자 ID |
| `is_locked` | BOOLEAN | `isLocked` | 장비 제어 잠금 여부 |
| `start_time` | TIMESTAMP | `startTime` | 시작 일시 |
| `end_time` | TIMESTAMP | `endTime` | 종료 일시 |

## 6. System

### GET `/health`

서버 상태를 확인합니다.

- 인증: 불필요
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "app": "BARO API",
    "environment": "local"
  }
}
```

## 7. Auth

### POST `/api/v1/auth/signup`

관리자 계정을 생성합니다.

- 인증: 불필요
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `username` | string | Y | 로그인 ID. 3~50자 |
| `password` | string | Y | 비밀번호. 8~128자 |
| `name` | string | Y | 이름 |
| `phoneNumber` | string | Y | 연락처 |
| `department` | string | Y | 부서 |
| `role` | string | Y | `ADMIN`, `MANAGER`, `OPERATOR` |

#### Request Example

```json
{
  "username": "admin@example.com",
  "password": "password123",
  "name": "관리자",
  "phoneNumber": "010-0000-0000",
  "department": "안전관리팀",
  "role": "ADMIN"
}
```

#### Response 201

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin@example.com",
    "name": "관리자",
    "phoneNumber": "010-0000-0000",
    "department": "안전관리팀",
    "role": "ADMIN",
    "createdAt": "2026-07-16T12:00:00"
  },
  "message": "회원가입이 완료되었습니다."
}
```

#### Errors

| Status | 설명 |
|---:|---|
| 409 | 이미 사용 중인 username |
| 422 | 필수 값 누락 또는 검증 실패 |

### POST `/api/v1/auth/login`

로그인 후 accessToken과 refreshToken을 발급합니다.

- 인증: 불필요
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `username` | string | Y | 로그인 ID |
| `password` | string | Y | 비밀번호 |

#### Request Example

```json
{
  "username": "admin@example.com",
  "password": "password123"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "accessToken": "jwt-access-token",
    "refreshToken": "jwt-refresh-token",
    "tokenType": "bearer",
    "expiresIn": 3600,
    "user": {
      "id": 1,
      "username": "admin@example.com",
      "name": "관리자",
      "phoneNumber": "010-0000-0000",
      "department": "안전관리팀",
      "role": "ADMIN",
      "createdAt": "2026-07-16T12:00:00"
    }
  },
  "message": "로그인되었습니다."
}
```

#### Errors

| Status | 설명 |
|---:|---|
| 401 | username 또는 password가 올바르지 않음 |
| 422 | 필수 값 누락 또는 검증 실패 |

### POST `/api/v1/auth/refresh`

refreshToken으로 accessToken을 재발급합니다.

- 인증: 불필요
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `refreshToken` | string | Y | 로그인/재발급 시 받은 refreshToken |

#### Request Example

```json
{
  "refreshToken": "jwt-refresh-token"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "accessToken": "jwt-access-token",
    "tokenType": "bearer",
    "expiresIn": 3600
  },
  "message": "토큰이 재발급되었습니다."
}
```

### POST `/api/v1/auth/logout`

클라이언트에서 보관 중인 토큰을 폐기하는 용도로 호출합니다.

- 인증: 불필요
- 상태: 구현완료

#### Response 204

body 없음.

## 8. Camera

### GET `/api/v1/cameras`

등록된 카메라 목록을 조회합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "1번 CCTV",
      "rtspUrl": "rtsp://user:pass@192.168.0.10:554/stream1",
      "location": "1공장 입구",
      "status": "ONLINE"
    }
  ],
  "message": "요청이 정상 처리되었습니다."
}
```

### POST `/api/v1/cameras`

CCTV/RTSP 카메라 정보를 등록합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | Y | 카메라 이름 |
| `rtspUrl` | string | Y | RTSP URL |
| `location` | string | Y | 설치 위치 |
| `status` | string | N | 기본값 `ONLINE` |

#### Request Example

```json
{
  "name": "1번 CCTV",
  "rtspUrl": "rtsp://user:pass@192.168.0.10:554/stream1",
  "location": "1공장 입구",
  "status": "ONLINE"
}
```

#### Response 201

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "1번 CCTV",
    "rtspUrl": "rtsp://user:pass@192.168.0.10:554/stream1",
    "location": "1공장 입구",
    "status": "ONLINE"
  },
  "message": "카메라가 등록되었습니다."
}
```

### GET `/api/v1/cameras/{cameraId}`

카메라 상세 정보를 조회합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `cameraId` | number | 카메라 ID |

#### Response 200

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "1번 CCTV",
    "rtspUrl": "rtsp://user:pass@192.168.0.10:554/stream1",
    "location": "1공장 입구",
    "status": "ONLINE"
  },
  "message": "요청이 정상 처리되었습니다."
}
```

### PUT `/api/v1/cameras/{cameraId}`

카메라 정보를 수정합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | N | 카메라 이름 |
| `rtspUrl` | string | N | RTSP URL |
| `location` | string | N | 설치 위치 |
| `status` | string | N | 카메라 상태 |

#### Request Example

```json
{
  "name": "1번 CCTV 수정",
  "status": "MAINTENANCE"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "1번 CCTV 수정",
    "rtspUrl": "rtsp://user:pass@192.168.0.10:554/stream1",
    "location": "1공장 입구",
    "status": "MAINTENANCE"
  },
  "message": "카메라 정보가 수정되었습니다."
}
```

### DELETE `/api/v1/cameras/{cameraId}`

카메라를 삭제합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 204

body 없음.

### GET `/api/v1/cameras/{cameraId}/timeshift`

카메라의 롤링 녹화 버퍼(기본 30분, `RECORDING_BUFER_SEGMENT_COUNT * RECORDING_SEGMENT_SECONDS`)에서 `minutesAgo`분 전부터 지금까지의 영상을 즉석에서 이어붙여 mp4로 반환합니다. 접속 시점과 무관하게 항상 "최근 최대 30분"을 되돌려볼 수 있도록 하기 위한 용도이며, 요청마다 새로 생성됩니다(캐시 안 함).

- 인증: 현재 미적용
- 상태: 구현완료
- Query: `minutesAgo`(number, 0보다 크고 30 이하, 필수) — 몇 분 전 시점부터 볼지

#### Response 200

`Content-Type: video/mp4` 바이너리 스트림.

#### Errors

| Status | Code | 설명 |
|---:|---|---|
| 404 | `CAMERA_NOT_FOUND` | 해당 카메라 없음 |
| 404 | `TIMESHIFT_NOT_AVAILABLE` | 요청한 시점의 녹화 영상이 아직 없음(카메라 등록 직후 등) |

### GET `/api/v1/cameras/{cameraId}/stream-url`

카메라의 RTSP URL을 조회합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": {
    "cameraId": 1,
    "streamUrl": "rtsp://user:pass@192.168.0.10:554/stream1"
  },
  "message": "요청이 정상 처리되었습니다."
}
```

## 9. WebRTC

WebRTC API는 브라우저가 보낸 SDP offer를 FastAPI 백엔드가 받고, 백엔드의 카메라 소스 어댑터에서 생성한 영상 track을 붙인 뒤 SDP answer를 반환하는 구조입니다.

현재 지원하는 영상 소스:

| kind | 설명 |
|---|---|
| `test_pattern` | 백엔드에서 생성하는 테스트 패턴 영상 |
| `webcam` | 백엔드 서버에 연결된 웹캠 |
| `rtsp` | CCTV/하드웨어 카메라 RTSP 스트림 |
| `file` | 로컬 영상 파일 |

### GET `/api/v1/webrtc/sources`

사용 가능한 영상 소스 어댑터 목록을 조회합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": {
    "sources": [
      {
        "kind": "test_pattern",
        "name": "테스트 패턴",
        "description": "백엔드에서 생성하는 테스트 영상입니다."
      },
      {
        "kind": "webcam",
        "name": "서버 로컬 웹캠",
        "description": "백엔드 서버에 연결된 웹캠입니다."
      },
      {
        "kind": "rtsp",
        "name": "RTSP CCTV",
        "description": "CCTV 또는 하드웨어 카메라의 RTSP 스트림입니다."
      },
      {
        "kind": "file",
        "name": "영상 파일",
        "description": "서버 로컬 영상 파일입니다."
      }
    ]
  },
  "message": "요청이 정상 처리되었습니다."
}
```

### POST `/api/v1/webrtc/offer`

브라우저의 SDP offer를 받아 백엔드 영상 소스를 연결하고 SDP answer를 반환합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `sdp` | string | Y | 브라우저가 생성한 SDP offer |
| `type` | string | Y | `offer` |
| `cameraId` | number | N | 등록된 카메라 ID. 지정 시 DB의 `rtspUrl` 사용 (`robotId`와 둘 중 하나 필수) |
| `robotId` | number | N | 등록된 로봇 ID. 지정 시 로봇 탑재 카메라(`cameraRtspUrl`) 사용, YOLO 오버레이 항상 비적용 (`cameraId`와 둘 중 하나 필수) |
| `yoloEnabled` | boolean | N | `cameraId` 사용 시 YOLO 스켈레톤 오버레이 여부. 기본값 `true`. `false`로 주면 원본 CCTV 화면 |
| `source` | object | N | 직접 지정하는 영상 소스 |

`source` object:

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kind` | string | Y | `test_pattern`, `webcam`, `rtsp`, `file` |
| `url` | string | N | `rtsp`, `file` 사용 시 필요 |
| `deviceIndex` | number | N | `webcam` 사용 시 장치 번호. 기본값 0 |
| `yoloEnabled` | boolean | N | YOLO 객체 탐지 overlay 사용 여부 |
| `yoloConfidence` | number | N | YOLO 탐지 confidence 기준값 |

#### Request Example: 테스트 패턴

```json
{
  "type": "offer",
  "sdp": "v=0...",
  "source": {
    "kind": "test_pattern"
  }
}
```

#### Request Example: 백엔드 서버 웹캠

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

#### Request Example: 백엔드 서버 웹캠 + YOLO

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

#### Request Example: 등록된 카메라 사용

```json
{
  "type": "offer",
  "sdp": "v=0...",
  "cameraId": 1
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "sdp": "v=0...",
    "type": "answer",
    "sessionId": "uuid"
  },
  "message": "WebRTC 연결 응답이 생성되었습니다."
}
```

#### Errors

| Status | 설명 |
|---:|---|
| 400 | source 값이 잘못되었거나 WebRTC offer 처리 실패 |
| 404 | cameraId에 해당하는 카메라 없음 |
| 422 | 필수 값 누락 또는 검증 실패 |

### GET `/api/v1/webrtc/sessions/{sessionId}`

WebRTC 세션 상태를 조회합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": {
    "sessionId": "uuid",
    "connectionState": "connected"
  },
  "message": "요청이 정상 처리되었습니다."
}
```

### DELETE `/api/v1/webrtc/sessions/{sessionId}`

WebRTC 세션을 종료합니다.

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 204

body 없음.

## 10. Zone

카메라 화면 기준 위험 구역 좌표를 관리합니다. 실제 라우터 파일: `app/api/routes/zones.py`, prefix `/api/v1/zones`.

### GET `/api/v1/zones`

- 인증: 현재 미적용
- 상태: 구현완료
- Query: `cameraId`(number, optional) — 지정 시 해당 카메라 소속 구역 + 카메라 미지정 구역을 함께 반환

#### Response 200

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "cameraId": 1,
      "name": "기본 위험구역",
      "points": [{ "x": 420, "y": 245 }, { "x": 790, "y": 250 }, { "x": 860, "y": 510 }, { "x": 355, "y": 510 }],
      "isActive": true
    }
  ],
  "message": "요청이 정상 처리되었습니다."
}
```

### POST `/api/v1/zones`

- 인증: 현재 미적용
- 상태: 구현완료

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | Y | 위험 구역 이름 |
| `cameraId` | number | N | 연결 카메라 ID |
| `points` | array | Y | `{ x: number, y: number }` 객체 배열 |

#### Response 201

```json
{
  "success": true,
  "data": {
    "id": 1,
    "cameraId": 1,
    "name": "기본 위험구역",
    "points": [{ "x": 420, "y": 245 }],
    "isActive": true
  },
  "message": "위험구역이 저장되었습니다."
}
```

### DELETE `/api/v1/zones/{zoneId}`

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 204

body 없음.

#### Errors

| Status | 설명 |
|---:|---|
| 404 | 해당 zoneId의 위험 구역 없음 |

## 11. Equipment (설비 제어)

시리얼(Arduino)로 연결된 설비에 정지/감속/재가동 명령을 전송합니다. DB에 저장하지 않는 즉시 명령 API이며, 실제 라우터 파일: `app/api/routes/equipment.py`, prefix `/api/v1/equipment`. 설비를 여러 대 구분해 제어하는 기능은 아직 없습니다(장비 ID 파라미터 없음).

시리얼 포트 연결이 안 돼 있어도 에러를 던지지 않고 `sent: false`를 반환합니다(`MotorController`가 예외를 삼킴).

### POST `/api/v1/equipment/stop`

- 인증: 현재 미적용
- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": { "sent": true },
  "message": "설비 정지 명령을 전송했습니다."
}
```

### POST `/api/v1/equipment/slow`

- 인증: 현재 미적용
- 상태: 구현완료
- Response 형태는 `stop`과 동일 (`message`: "설비 감속 명령을 전송했습니다.")

### POST `/api/v1/equipment/resume`

- 인증: 현재 미적용
- 상태: 구현완료
- Response 형태는 `stop`과 동일 (`message`: "설비 재가동 명령을 전송했습니다.")

## 11.5 Robot (현장 로봇)

현장 로봇은 자체 라즈베리파이(와이파이 통신)를 탑재한 이동형 장치입니다. `controlAddress`(`host:port`)로 PTZ/이동 명령을 HTTP POST로 전송하고, `cameraRtspUrl`로 탑재 카메라 영상을 받습니다. 실제 라우터 파일: `app/api/routes/robots.py`, prefix `/api/v1/robots`.

로봇 Pi가 꺼져있거나 응답이 없어도 에러를 던지지 않고 `sent: false`를 반환합니다(`send_robot_command`가 예외를 삼킴, 타임아웃 기본 2초).

### GET `/api/v1/robots`

- 상태: 구현완료

#### Response 200

```json
{
  "success": true,
  "data": { "items": [
    {
      "id": 1,
      "hardwareId": "dc:a6:32:12:34:56",
      "name": "현장로봇-1",
      "controlAddress": "192.168.0.50:8081",
      "cameraRtspUrl": "rtsp://192.168.0.50:8554/cam",
      "locationX": 120.5,
      "locationY": 340.0,
      "status": "IDLE",
      "createdAt": "2026-07-29T11:49:21.149814Z"
    }
  ] },
  "message": "요청이 정상 처리되었습니다."
}
```

`status`: `IDLE` | `DISPATCHED` | `OFFLINE`. `locationX`/`locationY`는 실내 도면 좌표(카메라의 `locationX`/`locationY`와 동일한 좌표계), 로봇의 현재 위치.

### POST `/api/v1/robots`

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | Y | 로봇 이름 |
| `controlAddress` | string | Y | 로봇 Pi 주소, `host:port` |
| `cameraRtspUrl` | string | Y | 로봇 탑재 카메라 RTSP URL |
| `locationX` | number | N | 도면 좌표 |
| `locationY` | number | N | 도면 좌표 |

응답은 목록의 개별 항목과 동일한 형태. 관리자가 폼으로 직접 등록할 때 사용 — 로봇이 스스로 등록할 때는 아래 `/register`를 사용.

### POST `/api/v1/robots/register`

- 상태: 구현완료

로봇 자체(SafeVision-Robot repo)가 부팅 시 자기 자신을 등록/갱신하기 위해 호출하는 엔드포인트. 사람이 폼에 채워넣는 대신, 로봇이 자신의 `controlAddress`/`cameraRtspUrl`을 직접 보고합니다. `hardwareId`(로봇 Pi의 MAC 주소 등 불변 식별자) 기준으로 upsert하므로, 재부팅이나 DHCP로 IP가 바뀌어도 같은 로봇 레코드가 갱신되지 로봇이 중복 생성되지 않습니다.

#### Request Body

```json
{
  "hardwareId": "dc:a6:32:12:34:56",
  "name": "현장로봇-1",
  "controlAddress": "192.168.0.50:8081",
  "cameraRtspUrl": "rtsp://192.168.0.50:8554/cam"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `hardwareId` | string | Y | 로봇의 불변 식별자 (MAC 주소 권장) — upsert 키 |
| `name` | string | Y | 로봇 이름 |
| `controlAddress` | string | Y | 로봇 자신의 현재 `host:port` (매 등록 시 최신값으로 갱신됨) |
| `cameraRtspUrl` | string | Y | 로봇 탑재 카메라 RTSP URL |

같은 `hardwareId`로 재요청 시 기존 로봇의 `name`/`controlAddress`/`cameraRtspUrl`을 갱신하고 `status`를 `IDLE`로 리셋합니다(재부팅한 로봇은 더 이상 이전 출동 상태가 아니라고 간주). 응답은 목록의 개별 항목과 동일한 형태(`hardwareId` 필드 포함).

### PUT `/api/v1/robots/{robotId}` / DELETE `/api/v1/robots/{robotId}`

카메라 CRUD와 동일한 패턴 (부분 수정, 204 삭제).

### POST `/api/v1/robots/{robotId}/ptz`

#### Request Body

```json
{ "direction": "up" }
```

`direction`: `up` | `down` | `left` | `right` | `zoomIn` | `zoomOut` | `stop`. 로봇 Pi의 `http://{controlAddress}/command`로 `{"type":"ptz","direction":...}` JSON을 그대로 POST합니다 — 로봇 Pi 쪽에서 이 엔드포인트를 구현해야 합니다.

#### Response 200

```json
{ "success": true, "data": { "sent": true }, "message": "PTZ 명령을 전송했습니다." }
```

### POST `/api/v1/robots/{robotId}/dispatch`

로봇을 출동 상태로 바꾸고 출동 기록을 남깁니다. `safetyEventId`를 주면 그 이벤트가 발생한 카메라의 `locationX`/`locationY`를 출동 목표 좌표로 자동 채웁니다(카메라에 좌표가 설정되어 있어야 함).

#### Request Body

```json
{ "safetyEventId": 12 }
```

`safetyEventId`는 선택값(생략 가능, 이 경우 targetX/Y는 null).

#### Response 201

```json
{
  "success": true,
  "data": {
    "id": 1, "robotId": 1, "safetyEventId": 12,
    "targetX": 120.5, "targetY": 340.0,
    "dispatchedAt": "2026-07-29T11:49:36.102996Z"
  },
  "message": "로봇을 출동시켰습니다."
}
```

### GET `/api/v1/robots/{robotId}/dispatches`

최근 20건의 출동 이력을 위 응답과 같은 형태의 배열로 반환합니다.

## 11.6 Emergency (응급센터, 스텁)

실제 응급센터 연동 시스템이 아직 없어서, 이 두 엔드포인트는 서버 로그에 기록만 하고 성공 응답을 반환하는 스텁입니다. 실제 시스템이 생기면 이 안쪽 구현만 교체하면 되도록 요청/응답 형태를 맞춰뒀습니다. 실제 라우터 파일: `app/api/routes/emergency.py`.

### POST `/api/v1/emergency/contact`

#### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `robotId` | number | N | 관련 로봇 |
| `safetyEventId` | number | N | 관련 이벤트 |
| `message` | string | N | 상황 메모 |

#### Response 200

```json
{ "success": true, "data": { "connected": true }, "message": "응급센터에 연결 요청을 전송했습니다." }
```

### POST `/api/v1/emergency/share`

요청/응답 형태는 `contact`와 동일 (`data.shared`, `message`: "현장 상황을 공유했습니다.")

## 11.7 Equipment (DB 리소스, 다중 설비 제어)

11장의 `/equipment/*`는 설비 1대만 가정한 전역 명령 API이고(하위 호환용으로 계속 유지), 아래는 여러 설비를 등록해 각각 구분 제어하는 API입니다. 실제 라우터 파일: `app/api/routes/equipments.py`, prefix `/api/v1/equipments`.

`controlProtocol`: `SERIAL`(백엔드 호스트의 시리얼 포트, 예: `/dev/ttyACM0`, STOP/SLOW/RESUME 텍스트 라인 전송) 또는 `NETWORK`(로봇과 동일한 방식으로 `host:port`에 JSON POST). 장치가 꺼져있거나 응답 없어도 에러 없이 `sent: false` 반환.

### GET `/api/v1/equipments` / POST `/api/v1/equipments`

#### Request Body (POST)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | Y | 설비 이름 |
| `controlProtocol` | string | Y | `SERIAL` \| `NETWORK` |
| `controlAddress` | string | Y | `SERIAL`이면 포트 경로, `NETWORK`면 `host:port` |

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1, "name": "컨베이어-1",
    "controlProtocol": "SERIAL", "controlAddress": "/dev/ttyACM0",
    "updatedAt": "2026-07-30T12:00:00Z"
  },
  "message": "요청이 정상 처리되었습니다."
}
```

### GET/PUT/DELETE `/api/v1/equipments/{equipmentId}`

카메라/로봇 CRUD와 동일한 패턴.

### POST `/api/v1/equipments/{equipmentId}/stop` | `/slow` | `/resume`

```json
{ "success": true, "data": { "sent": true }, "message": "설비 정지 명령을 전송했습니다." }
```

## 12. 구현 예정 API

아래 API는 ERD 기준으로 필요한 항목이지만 현재 백엔드 코드에는 아직 구현되어 있지 않습니다.

### 12.2 SafetyEvent 등록

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/safety-events` | 안전 이벤트 등록 (현재는 YOLO 감지 시 백엔드 내부에서만 적재, 외부 등록 API 없음) |

### 12.3 MaintenanceMode

장비 정비 모드와 제어 잠금 상태를 관리합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/maintenance-modes` | 정비 모드 목록 조회 |
| POST | `/api/v1/equipments/{equipmentId}/maintenance-modes` | 정비 모드 시작 |
| PATCH | `/api/v1/maintenance-modes/{maintenanceModeId}/end` | 정비 모드 종료 |

## 13. 현재 구현 DB와 ERD 차이

현재 FastAPI 백엔드는 `users`, `cameras`, `zones`, `safety_events` 테이블이 실제 SQLAlchemy 모델로 구현되어 있습니다.

| ERD 테이블 | 현재 구현 상태 | 비고 |
|---|---|---|
| `users` | 구현완료 | 회원가입/로그인에서 사용. 프론트는 아직 미연동 |
| `cameras` | 구현완료 | 카메라 등록, MJPEG 스트리밍, WebRTC RTSP 연결에서 사용 |
| `equipments`(DB 리소스) | 구현완료 | 다중 설비 등록/구분 제어(`SERIAL`/`NETWORK`) 지원. 단일 설비 제어 명령(`/equipment/stop` 등)은 하위 호환용으로 별도 유지, 이 테이블과 무관 |
| `zones`(ERD상 `danger_zones`) | 구현완료 | 위험 구역 좌표 등록/조회/삭제 API 제공 |
| `safety_events` | 구현됨(등록 API 제외) | YOLO Pose 넘어짐 감지 시 `FALL_DETECTED` 이벤트 저장, 목록/상세 조회 API 제공. 외부에서 이벤트를 등록하는 API는 없음 |
| `maintenance_modes` | 예정 | 정비 모드/제어 잠금 기능 구현 시 추가 필요 |
## 14. Frontend Integration Contract

This section defines the contract required by `SafeVision-Frontend`. The frontend currently uses mock data; the mappings below are required when replacing it with API calls.

### 14.1 Common response handling

Successful JSON responses use `{ "success": true, "data": {}, "message": "" }`. The `data` shape is endpoint-specific: `GET /cameras` returns `{ "items": [...] }`, while `GET /safety-events` and `GET /zones` return arrays. Dates are ISO 8601 strings. DELETE success responses have status `204` and no body.

### 14.2 Camera mapping

Backend camera status values are `ONLINE`, `OFFLINE`, and `MAINTENANCE`. Frontend values must be mapped to `online`, `offline`, and `maintenance`. The frontend-only `alert` state is derived from recent unacknowledged safety events and is not a camera status returned by the backend.

Backend camera IDs are numeric. The frontend must retain the numeric ID for API calls and derive display labels such as `CAM-01` by padding the ID. `name` and `location` are separate backend fields; a frontend `label` must be composed from them.

Camera APIs:

```http
GET /api/v1/cameras
GET /api/v1/cameras/{cameraId}
GET /api/v1/cameras/{cameraId}/mjpeg
POST /api/v1/webrtc/offer
```

The WebRTC request body is `{ "sdp": string, "type": "offer", "cameraId": number, "yoloConfidence"?: number }`.

### 14.3 Safety event mapping

Backend events contain `id`, `cameraId`, `equipmentId`, `zoneId`, `eventType`, `eventLevel`, `clipPath`, and `createdAt`. The frontend display model (`severity`, `title`, `description`, `meta`, `actionLabel`) is a view model and must be built by the frontend:

| Backend | Frontend rule |
|---|---|
| `id` | Convert to string for UI keys if needed |
| `cameraId` | Resolve camera name from the camera list |
| `eventType` | Map to localized title/description |
| `eventLevel` | `1=danger`, `2=warning`, other values=`info` |
| `clipPath` | Presence (non-null) means `GET /safety-events/{id}/clip` is playable; null means not ready yet or unavailable |
| `createdAt` | Format as local display time |
| no backend field | `actionLabel` is a frontend fixed label (`확인`/`상세`) |

Clicking an event with a non-null `clipPath` should play `GET /api/v1/safety-events/{eventId}/clip` (returns `video/mp4`) — this covers roughly the last 10 minutes before the event plus a short post-roll, not just the instant of detection.

```http
GET /api/v1/safety-events?limit=50
GET /api/v1/safety-events/{eventId}
```

The backend currently generates `FALL_DETECTED` internally. Event acknowledgement, status changes, and external event creation are not implemented.

### 14.4 Zones

The frontend `CameraZone` grouping is a view model. Use `cameraId` to group backend zones and render `points` in the documented normalized 1000x600 coordinate space.

```http
GET /api/v1/zones?cameraId={cameraId}
POST /api/v1/zones
DELETE /api/v1/zones/{zoneId}
```

### 14.5 Authentication

The frontend must call `POST /auth/login`, store `accessToken`, `refreshToken`, and `user`, send `Authorization: Bearer <accessToken>`, refresh on `401` with `POST /auth/refresh`, and clear tokens after `POST /auth/logout`. Camera and WebRTC routes currently do not enforce the auth dependency; this must be decided before production deployment.

### 14.6 APIs required by current frontend screens but not implemented

The recording search, AI analysis, statistics, and system-health screens currently use mock data. The following APIs are required to replace those mocks:

| Feature | Proposed endpoint | Minimum response |
|---|---|---|
| Recording search | `GET /api/v1/recordings?cameraId=&date=&startTime=&endTime=&eventOnly=` | recording ID, camera ID, start/end time, playback URL, event data |
| Recording playback | `GET /api/v1/recordings/{recordingId}/stream` | stream response or playback URL |
| AI camera summary | `GET /api/v1/ai-analysis/cameras?from=&to=` | detection count, risk, last detected time per camera |
| Recent AI events | `GET /api/v1/ai-analysis/events?from=&to=&severity=` | event list or convertible safety events |
| Statistics summary | `GET /api/v1/statistics/summary?from=&to=` | total events, falls, average response time, camera uptime |
| Daily event trend | `GET /api/v1/statistics/events/daily?from=&to=` | date and count pairs |
| Event distribution | `GET /api/v1/statistics/events/distribution?from=&to=` | event type and count pairs |
| Camera performance | `GET /api/v1/statistics/cameras?from=&to=` | events, uptime, average response time per camera |
| System metrics | `GET /api/v1/system/health/metrics` | CPU, storage, and camera connection status |

All endpoints in this subsection are planned and are not currently implemented.

### 14.7 Equipment control

The emergency control UI should call:

```http
POST /api/v1/equipment/stop
POST /api/v1/equipment/slow
POST /api/v1/equipment/resume
```

These APIs currently control a single equipment target and accept no equipment ID. Multi-equipment control requires a separate resource and request contract.

### 14.8 Integration order

1. Authentication and shared API client
2. Camera list and status mapping
3. MJPEG/WebRTC video
4. Safety events
5. Zones
6. Equipment controls
7. Recording APIs
8. AI, statistics, and system metrics APIs
