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
| WebRTC | GET | `/api/v1/webrtc/sources` | 영상 소스 어댑터 목록 조회 | 구현완료 |
| WebRTC | POST | `/api/v1/webrtc/offer` | SDP offer를 받아 SDP answer 생성 | 구현완료 |
| WebRTC | GET | `/api/v1/webrtc/sessions/{sessionId}` | WebRTC 세션 상태 조회 | 구현완료 |
| WebRTC | DELETE | `/api/v1/webrtc/sessions/{sessionId}` | WebRTC 세션 종료 | 구현완료 |
| Equipment | GET | `/api/v1/equipments` | 장비 목록 조회 | 예정 |
| Equipment | POST | `/api/v1/equipments` | 장비 등록 | 예정 |
| Equipment | GET | `/api/v1/equipments/{equipmentId}` | 장비 상세 조회 | 예정 |
| Equipment | PUT | `/api/v1/equipments/{equipmentId}` | 장비 정보 수정 | 예정 |
| Equipment | DELETE | `/api/v1/equipments/{equipmentId}` | 장비 삭제 | 예정 |
| DangerZone | GET | `/api/v1/danger-zones` | 위험 구역 목록 조회 | 예정 |
| DangerZone | POST | `/api/v1/danger-zones` | 위험 구역 등록 | 예정 |
| DangerZone | GET | `/api/v1/danger-zones/{zoneId}` | 위험 구역 상세 조회 | 예정 |
| DangerZone | PUT | `/api/v1/danger-zones/{zoneId}` | 위험 구역 수정 | 예정 |
| DangerZone | DELETE | `/api/v1/danger-zones/{zoneId}` | 위험 구역 삭제 | 예정 |
| SafetyEvent | GET | `/api/v1/safety-events` | 안전 이벤트 목록 조회 | 예정 |
| SafetyEvent | POST | `/api/v1/safety-events` | 안전 이벤트 등록 | 예정 |
| SafetyEvent | GET | `/api/v1/safety-events/{eventId}` | 안전 이벤트 상세 조회 | 예정 |
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

권장 status 값:

```text
ONLINE, OFFLINE, MAINTENANCE
```

### 5.3 equipments

구현 예정.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 장비 PK |
| `name` | VARCHAR(100) | `name` | 장비 이름 |
| `control_protocol` | VARCHAR(50) | `controlProtocol` | 제어 프로토콜 |
| `control_address` | VARCHAR(100) | `controlAddress` | 제어 주소 |
| `updated_at` | TIMESTAMP | `updatedAt` | 수정 일시 |

### 5.4 danger_zones

구현 예정.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 위험 구역 PK |
| `camera_id` | BIGINT | `cameraId` | 연결 카메라 ID |
| `equipment_id` | BIGINT | `equipmentId` | 연결 장비 ID |
| `name` | VARCHAR(100) | `name` | 위험 구역 이름 |
| `polygon_coordinates` | JSON | `polygonCoordinates` | 화면 좌표 다각형 |
| `created_at` | TIMESTAMP | `createdAt` | 생성 일시 |

### 5.5 safety_events

구현 예정.

| DB 컬럼 | 타입 | API 필드 | 설명 |
|---|---|---|---|
| `id` | BIGINT | `id` | 이벤트 PK |
| `camera_id` | BIGINT | `cameraId` | 발생 카메라 ID |
| `equipment_id` | BIGINT | `equipmentId` | 관련 장비 ID |
| `zone_id` | BIGINT | `zoneId` | 관련 위험 구역 ID |
| `event_type` | VARCHAR(50) | `eventType` | 이벤트 유형 |
| `event_level` | VARCHAR(30) | `eventLevel` | 이벤트 등급 |

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
| `cameraId` | number | N | 등록된 카메라 ID. 지정 시 DB의 `rtspUrl` 사용 |
| `source` | object | N | 직접 지정하는 영상 소스 |

`source` object:

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kind` | string | Y | `test_pattern`, `webcam`, `rtsp`, `file` |
| `url` | string | N | `rtsp`, `file` 사용 시 필요 |
| `deviceIndex` | number | N | `webcam` 사용 시 장치 번호. 기본값 0 |

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

## 10. 구현 예정 API

아래 API는 ERD 기준으로 필요한 항목이지만 현재 백엔드 코드에는 아직 구현되어 있지 않습니다.

### 10.1 Equipment

장비 정보를 관리합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/equipments` | 장비 목록 조회 |
| POST | `/api/v1/equipments` | 장비 등록 |
| GET | `/api/v1/equipments/{equipmentId}` | 장비 상세 조회 |
| PUT | `/api/v1/equipments/{equipmentId}` | 장비 정보 수정 |
| DELETE | `/api/v1/equipments/{equipmentId}` | 장비 삭제 |

### 10.2 DangerZone

카메라 화면 기준 위험 구역 좌표를 관리합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/danger-zones` | 위험 구역 목록 조회 |
| POST | `/api/v1/danger-zones` | 위험 구역 등록 |
| GET | `/api/v1/danger-zones/{zoneId}` | 위험 구역 상세 조회 |
| PUT | `/api/v1/danger-zones/{zoneId}` | 위험 구역 수정 |
| DELETE | `/api/v1/danger-zones/{zoneId}` | 위험 구역 삭제 |

### 10.3 SafetyEvent

안전 이벤트를 저장하고 조회합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/safety-events` | 안전 이벤트 목록 조회 |
| POST | `/api/v1/safety-events` | 안전 이벤트 등록 |
| GET | `/api/v1/safety-events/{eventId}` | 안전 이벤트 상세 조회 |

### 10.4 MaintenanceMode

장비 정비 모드와 제어 잠금 상태를 관리합니다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/maintenance-modes` | 정비 모드 목록 조회 |
| POST | `/api/v1/equipments/{equipmentId}/maintenance-modes` | 정비 모드 시작 |
| PATCH | `/api/v1/maintenance-modes/{maintenanceModeId}/end` | 정비 모드 종료 |

## 11. 현재 구현 DB와 ERD 차이

현재 FastAPI 백엔드는 1차 구현 범위로 `users`, `cameras` 테이블만 실제 SQLAlchemy 모델로 구현되어 있습니다.

| ERD 테이블 | 현재 구현 상태 | 비고 |
|---|---|---|
| `users` | 구현완료 | 회원가입/로그인에서 사용 |
| `cameras` | 구현완료 | 카메라 등록 및 WebRTC RTSP 연결에서 사용 |
| `equipments` | 예정 | 장비 제어 기능 구현 시 추가 필요 |
| `danger_zones` | 예정 | 위험 구역 좌표 기능 구현 시 추가 필요 |
| `safety_events` | 예정 | 감지 이벤트 저장 기능 구현 시 추가 필요 |
| `maintenance_modes` | 예정 | 정비 모드/제어 잠금 기능 구현 시 추가 필요 |

