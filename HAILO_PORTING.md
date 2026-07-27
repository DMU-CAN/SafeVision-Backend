# Hailo-8 포팅 작업 현황 (2026-07-26 기준)

다른 기기에서 이어서 작업하기 위한 정리 문서. 커밋은 직접 하지 않았으니, 이 파일 포함해서 확인 후 원하는 대로 커밋/푸시하면 됨.

## 프로젝트 목표 (큰 그림)

- 메인 라즈베리파이(Hailo-8 AI 가속기 탑재)가 모든 영상 분석/추론을 전담
- CCTV 카메라(같은 WiFi의 IP 카메라)는 영상만 스트리밍
- 프론트에서 지정한 위험구역 안에서 쓰러짐 등 이벤트 발생 시, 메인 파이가 판단 → 아두이노 제어 스텝모터로 컨베이어 정지/감속
- 로봇(자체 라즈베리파이 + 카메라/마이크/스피커, 같은 WiFi)은 이벤트 발생 시 출동 + 영상통화 지원
- 로봇/카메라는 스트리밍만, 추론은 전부 메인 파이의 Hailo-8에서

## 지금까지 완료한 것

### 1. 프론트-백엔드 이벤트 연동
- `SafeVision-Frontend/src/App.jsx`: 3초 간격 폴링으로 `GET /api/v1/safety-events` 조회 → 새 이벤트를 이벤트 로그에 반영
- `SafeVision-Backend/app/models/safety_event.py`: `created_at` 컬럼 추가 (원래 발생 시각 필드가 없었음)

### 2. YOLO pose 기반 낙상 감지 (PC 개발환경, ultralytics/torch CPU)
- `SafeVision-Backend/app/services/yolo_detector.py`
  - `yolo11n-pose.pt`로 관절(keypoint) 추출, 스켈레톤 오버레이 그림
  - 어깨-엉덩이 중점 이은 선의 수직 기울기(`torso_angle`) + 박스 가로/세로 비율(`aspect_ratio`)로 낙상 판정
  - 화면에 `angle .../60 ratio .../0.80` 디버그 텍스트 표시 (임계값 튜닝용)
  - 낙상 판정 시 `fall_event_cooldown_seconds`(기본 10초) 간격으로 DB에 `FALL_DETECTED` 이벤트 기록

### 3. IP 카메라(DroidCam) 소스 지원
- `SafeVision-Backend/app/services/camera_sources.py`: `IpCameraSource` 추가, `OpenCVCameraTrack`이 device index뿐 아니라 URL 문자열도 받도록 확장
- 프레임 지연 문제 해결: 백그라운드 스레드로 계속 최신 프레임만 유지(`_grab_loop`)하는 방식으로 변경 — 기존엔 OpenCV 내부 버퍼에 프레임이 쌓여 지연이 계속 누적되는 문제가 있었음
- 프론트 `App.jsx`에 IP 카메라 URL 입력창 + "IP 카메라 연결 (DroidCam)" 버튼 추가

### 4. 위험구역(Zone) 백엔드 연동
- `SafeVision-Backend/app/models/zone.py`, `schemas/zone.py`, `api/routes/zones.py`: `GET/POST /api/v1/zones`, `DELETE /api/v1/zones/{id}`
- `SafeVision-Backend/app/services/zone_service.py`: 다각형 내부 판정(ray casting). 좌표계는 프론트 `CameraFeed`의 SVG viewBox(1000×600) 기준 정규화 공간 — **`CameraFeed`의 viewBox를 바꾸면 `zone_service.py`의 `ZONE_SPACE_WIDTH/HEIGHT`도 같이 바꿔야 함**
- `yolo_detector.py`: 낙상 감지된 사람의 발밑 좌표를 정규화해서 구역 내부일 때만 이벤트 기록 (구역이 하나도 없으면 기존처럼 항상 감지 — 하위호환)
- 프론트: 앱 시작 시 저장된 구역 로드, 저장 버튼이 실제 백엔드에 저장 (현재는 카메라별이 아니라 전역 구역 1개만 지원하는 단순한 형태)

### 5. 라즈베리파이 Hailo-8 런타임 설치 (완료, 검증됨)

환경: Raspberry Pi 5, Ubuntu 26.04 arm64, 공식 AI HAT+ (classic Hailo-8, PCI ID `1e60:2864`)

- **커널 드라이버**: `hailo-ai/hailort-drivers` 레포의 **`hailo8` 브랜치**(v4.24.0) 사용 — `master` 브랜치는 최신 "1x" 칩(Hailo-10/15)용이라 우리 칩과 안 맞음. DKMS로 등록 완료 (커널 업데이트돼도 자동 재빌드, 실제로 커널 `1009`→`1014` 업데이트 후에도 자동 로드 확인됨)
- **펌웨어**: `download_firmware.sh`로 받아서 `/lib/firmware/hailo/hailo8_fw.bin`에 배치
- **HailoRT C++ 런타임**: `hailo-ai/hailort` 레포 `hailo8` 브랜치를 소스에서 빌드 (`cmake . -Bbuild -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ...` — CMake가 너무 최신이라 이 플래그 필요). `hailortcli fw-control identify`로 장치 인식 확인됨 (Firmware 4.24.0, HAILO8)
- **pyhailort (Python 바인딩)**: 공개 레포 소스로는 빌드 불가 (`libhailort/bindings/python/src/internal/` 디렉터리가 공개 미러에서 아예 빠져있음, `HAILO_BUILD_PYHAILORT_INTERNAL=ON` 켜도 소스가 없어서 실패). **Hailo Developer Zone에서 미리 빌드된 wheel을 받아야 함** (무료 가입 필요). Python 3.14(시스템 기본)는 wheel 미지원이라 `deadsnakes` PPA로 Python 3.13 설치 후 venv(`~/hailo-venv`)에 설치. `from hailo_platform import Device; Device.scan()` → `['0001:01:00.0']` 확인됨

자세한 트러블슈팅 기록은 Claude의 메모리 파일에도 있음: `hailo8-pi-setup.md` (별도 저장소, 이 세션의 어시스턴트가 관리)

### 6. Docker 배포 (완료, 검증됨)
- `SafeVision-Backend/Dockerfile`: `python:3.13-bookworm` 베이스, 이미지 안에서 HailoRT를 직접 재빌드 (호스트에서 빌드한 `.so`를 복사하면 베이스 OS가 달라 glibc/ABI 불일치 위험이 있어서, 항상 이미지 자체 안에서 컴파일하는 방식 채택)
- `SafeVision-Backend/vendor/`: pyhailort wheel을 여기 넣고 빌드 시 `COPY` (Developer Zone 다운로드라 git에는 안 올림, `.gitignore` 처리됨)
- `SafeVision-Backend/docker-compose.yml`: `/dev/hailo0` 디바이스 패스스루
- 검증 완료: 컨테이너 안에서 `docker exec ... python -c "from hailo_platform import Device; print(Device.scan())"` → `['0001:01:00.0']`, `/health` 엔드포인트도 정상 응답
- **주의(바인드마운트 함정)**: `./baro.db:/app/baro.db` 바인드마운트 시, 파일이 없는 상태(새로 git clone한 경우)에서 `docker compose up`을 하면 Docker가 그 경로에 **디렉터리**를 만들어버려서 `sqlite3.OperationalError: unable to open database file` 에러가 남. 매번 처음 배포할 때 `rm -rf baro.db && touch baro.db` 먼저 실행해야 함

## 지금 막힌 지점 / 다음 작업

**목표**: `yolo_detector.py`의 추론을 ultralytics/torch(CPU) 대신 Hailo-8 가속기로 실행

### 알아낸 것
- Ultralytics가 Hailo HEF 익스포트를 공식 지원함: `model = YOLO("yolo11n-pose.pt"); model.export(format="hailo", name="hailo8")` (우리 칩은 classic Hailo-8이므로 `name="hailo8"`, `"hailo8l"`은 다른 칩)
- **중요한 제약**: 이 HEF 컴파일(Hailo Dataflow Compiler, DFC)은 **x86_64 Linux에서만 가능**. 라즈베리파이(ARM)에서도, 지금 작업 중이던 Windows PC(ARM64)에서도 안 됨
- 변환 결과(.hef)는 다시 `ultralytics` API로 그대로 추론 가능하다고 함: `model = YOLO("yolo11n_hailo_model"); model.predict(...)` — 즉 `yolo_detector.py`의 구조(관절 추출, 낙상 판정 로직)는 거의 그대로 두고 모델 로딩 부분만 바꾸면 될 가능성이 높음 (단, 실제로 우리 pose 커스텀 로직과 호환되는지는 직접 테스트 필요)
- DFC 설치도 Hailo Developer Zone 가입/다운로드 필요 (HailoRT 받을 때 쓴 계정 재사용 가능). Python 버전 등 정확한 요구사항은 다운로드 페이지에서 wheel 파일명으로 확인 필요 (HailoRT wheel 받을 때처럼 `cpXXX` 표기 확인)

### 다음에 할 일 (x86_64 Linux 머신에서)
1. Ubuntu(네이티브 또는 WSL2 x86_64) 준비
2. Hailo Developer Zone → Software Downloads → **Dataflow Compiler** 에서 버전 확인 후 wheel 다운로드, `pip install hailo_dataflow_compiler-*.whl`
3. `pip install ultralytics`
4. `yolo export model=yolo11n-pose.pt format=hailo name=hailo8` 실행 (calibration 데이터셋 필요 — 지정 안 하면 자동으로 task용 기본 데이터셋 다운로드됨, 정확도 중요하면 최소 1024장 권장)
5. 결과 `.hef` 파일을 라즈베리파이로 전송
6. `yolo_detector.py`에서 `YoloDetector.__init__`이 `.pt` 대신 `.hef`를 로드하도록 수정, 실제 추론 결과 포맷이 기존 코드(`detect()`가 기대하는 `Detection`/`Keypoint` 구조)와 맞는지 확인 및 조정
7. Docker 이미지에 실제 라즈베리파이용 requirements(ultralytics는 이미 있음, torch/opencv는 계속 필요한지 재검토 — Hailo 추론이면 torch 없이도 될 수도 있음) 재구성

### 그 외 남은 큰 작업 (memory 파일 `project_architecture.md` 참고)
- 아두이노 스텝모터 제어 연동 (미착수)
- 로봇 출동 로직 + 로봇 카메라/마이크/스피커 영상통화 (미착수)
- 위험구역이 현재 카메라별이 아니라 전역 1개뿐 — 실제 카메라 관리(`cameraId`)와 연결 필요
