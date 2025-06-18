| [English](../README.md) | [Korean](./README_ko.md) |

<img alt="Python" src="https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white" height="20"/> <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57.svg?style=for-the-badge&logo=SQLite&logoColor=white" height="20"/> <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688.svg?style=for-the-badge&logo=FastAPI&logoColor=white" height="20"/> <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-5C3EE8.svg?style=for-the-badge&logo=OpenCV&logoColor=white" height="20"/> <img alt="YOLO" src="https://img.shields.io/badge/YOLO-111F68.svg?style=for-the-badge&logo=YOLO&logoColor=white" height="20"/> 

</br>

# 🚨 **스마트 무인매장: YOLO AI 이상행동 감지 & 알람 앱**

### 개발 기간

- **전체 개발 기간**: 2025.04.29 - 2025.06.19
- **UI 구현**: 2025.05.02 - 2025.05.15
- **기능 구현**: 2025.05.13 - 2025.06.19

</br>

자세한 프로젝트 내용은 [CCTV_FE 레포지토리](https://github.com/embedded-final-project-group-A/CCTV_FE)를 참고하세요.

YOLO 모델과 관련된 내용은 [YOLO 레포지토리](https://github.com/embedded-final-project-group-A/YOLO?tab=readme-ov-file)를 참고하세요.

</br>

## 1. 프로젝트 구조

프로젝트에서 주요 파일들의 구조는 다음과 같습니다. 

```markdown
📁 CCTV_BE/
├── README.md
├── cctv_system.db                # SQLite DB 파일 (test_db.py 결과)
├── main.py                       # FastAPI 메인 실행 파일
├── requirements.txt              # Python 의존성 목록
├── test_db.py                    # 테스트 DB 생성
├── test_db_android.py            # 안드로이드 에뮬레이터 테스트 DB 생성
│
├── 📁 dependencies/              # 데이터베이스 및 스키마 관련 코드
│   ├── crud.py                   # CRUD 로직
│   ├── db.py                     # DB 세션 연결 설정
│   ├── models.py                 # SQLAlchemy 모델 정의
│   └── schemas.py                # Pydantic 스키마 정의
│
├── 📁 routes/                   # FastAPI 라우트 (엔드포인트)
│   ├── alert.py                 # Alert 관련 API
│   ├── auth.py                  # Auth (회원가입/로그인) API
│   ├── camera.py                # Camera 등록/조회 API
│   ├── store.py                 # Store 등록/조회 API
│   └── user.py                  # User 프로필 API
│
├── 📁 videos/                   # 저장된 테스트 비디오 및 이미지
│   ├── store1_main.mp4
│   └── store1_main.png
│
└── 📁 yolo/                     # YOLO 객체 탐지 관련
    ├── best.pt                  # 훈련된 YOLO 모델
    ├── detect.py                # YOLO 이벤트 감지 및 클립 저장
    └── process_videos.py        # 영상 폴더 전체 병렬 처리 스크립트
```

</br>

## 2. 백엔드 서버 설치 및 실행 방법

---

### 📁 프로젝트 설치

**프로젝트 저장소 클론**

```bash
git clone https://github.com/embedded-final-project-group-A/CCTV_BE.git
cd CCTV_BE
```

</br>

**가상환경**

```bash
conda create -n "cctv"
conda activate cctv
pip install -r requirements.txt
```

</br>

### 💽 DB 생성

- `test_db.py` 파일을 실행하여 데이터베이스 생성
- `test_db.py`의 데이터베이스는 `https://localhost:8000`를 서버 주소로 저장
- android emulator로 실행하고 싶다면 `test_db_android.py`를 실행하여 데이터베이스 생성
- 테스트용 데이터가 필요 없다면 `insert_sample_data()`는 주석처리하여 실행

</br>

### 🖥️서버 실행

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 위의 코드를 사용하거나 `main.py` 코드를 실행하여 서버를 실행

</br>

## 3. 데이터베이스 설계

### CCTV Event Monitoring Database Schema

이 데이터베이스는 사용자, 매장, 카메라, 이벤트 유형, 그리고 이벤트 데이터를 저장하기 위한 스키마를 정의합니다. 주로 CCTV 기반 이상 감지 및 이벤트 관리 시스템에 활용할 수 있습니다.

### 테이블 구조

<img alt="테이블 구조" src="./db_table.png" width="800"/>

</br>

**user**
- **설명**: 시스템 사용자 정보를 저장합니다.
- **컬럼**
    - `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): 사용자 고유 ID
    - `username` (TEXT, UNIQUE, NOT NULL): 사용자 이름 (중복 불가)
    - `email` (TEXT, UNIQUE, NOT NULL): 사용자 이메일 (중복 불가)
    - `password_hash` (TEXT, NOT NULL): SHA-256으로 해시된 비밀번호

</br>

**store**
- **설명**: 사용자가 등록한 매장 정보를 저장합니다.
- **컬럼**
    - `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): 매장 고유 ID
    - `user_id` (INTEGER, NOT NULL): 매장을 등록한 사용자 ID (`user.id` 참조)
    - `name` (TEXT, NOT NULL): 매장명
    - `location` (TEXT, NULL 가능): 매장 위치 정보
- **제약조건**
    - `(user_id, name)` 조합에 대해 유니크 제약조건이 있어, 한 사용자는 동일 이름의 매장을 중복 등록할 수 없습니다.

</br>

**camera**
- **설명**: 매장에 설치된 카메라 정보를 저장합니다.
- **컬럼**
    - `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): 카메라 고유 ID
    - `user_id` (INTEGER, NOT NULL): 카메라 등록 사용자 ID (`user.id` 참조)
    - `store_id` (INTEGER, NOT NULL): 카메라가 속한 매장 ID (`store.id` 참조)
    - `name` (TEXT, NOT NULL): 카메라 이름
    - `video_url` (TEXT, NULL 가능): 카메라 영상 스트림 또는 저장 영상 URL
    - `image_url` (TEXT, NULL 가능): 카메라 썸네일 또는 이미지 URL
- **제약조건**
    - `(user_id, store_id, name)` 조합에 대해 유니크 제약조건이 있어, 동일 사용자 매장의 동일 이름 카메라는 중복될 수 없습니다.

</br>

**event_type**
- **설명**: 이벤트 유형과 위험도 정보를 저장합니다.
- **컬럼**
    - `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): 이벤트 유형 고유 ID
    - `type` (TEXT, UNIQUE, NOT NULL): 이벤트 유형명 (예: 침입, 화재 등)
    - `risk_level` (TEXT, NOT NULL): 위험 수준 (예: low, medium, high)

</br>

**event**
- **설명**: 발생한 이벤트 데이터를 저장합니다.
- **컬럼**
    - `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): 이벤트 고유 ID
    - `user_id` (INTEGER, NOT NULL): 이벤트를 소유한 사용자 ID (`user.id` 참조)
    - `store_id` (INTEGER, NOT NULL): 이벤트가 발생한 매장 ID (`store.id` 참조)
    - `camera_id` (INTEGER, NOT NULL): 이벤트를 감지한 카메라 ID (`camera.id` 참조)
    - `type_id` (INTEGER, NOT NULL): 이벤트 유형 ID (`event_type.id` 참조)
    - `event_time` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP): 이벤트 발생 시간
    - `video_url` (TEXT, NOT NULL): 이벤트 관련 영상 URL

</br>

### password 해시
비밀번호는 평문이 아닌 SHA-256 해시 형태로 저장됩니다. 해시 함수는 Python `hashlib` 모듈을 사용하며, 다음과 같이 구현되어 있습니다:

```python
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
```

</br>

## 4. YOLO
본 프로젝트의 핵심은 `detect.py` 파일에 정의된 `YOLOEventClipper` 클래스입니다. 이 클래스는 Ultralytics YOLO 모델을 사용해 CCTV 영상에서 특정 이벤트를 실시간으로 탐지하고, 이벤트 발생 구간을 자동으로 **클립(.mp4)과 이미지(.jpg)** 로 저장합니다.

</br>

### 🔍 핵심 구성요소

- **`YOLOEventClipper` 클래스**
    
    이벤트 탐지, 프레임 버퍼 관리, 이벤트 병합 및 클립 저장까지 모든 로직을 담당합니다.
    
- **`run()` 메서드**
    
    단일 영상에서 이벤트를 탐지하고 결과를 저장하는 실행 함수입니다. 직접 사용할 수 있습니다.
    
- **`run_for_path()` 클래스 메서드**
    
    영상 경로만 주면 자동으로 실행 시각을 추정하고 적절한 디렉터리를 생성해 `run()`을 호출합니다.
    
- **`process_videos.py`**
    
    여러 영상 파일을 동시에 병렬 처리할 수 있는 스크립트입니다. `multiprocessing` 기반으로 처리 성능을 높입니다.
    
</br>

### 🔧 YOLO 코드 활용 방법

**단일 영상 처리 (detect.py)**

```powershell
# 1. pwoershell로 실행
python detect.py
```

```python
# 2. python 코드 내에서 직접 실행
from detect import YOLOEventClipper

YOLOEventClipper.run_for_path(
    video_path="videos/theft.mp4",
    output_dir="output",
    debug=True
)
```

- `video_path`: 입력 영상 경로
- `output_dir`: 결과물 저장 폴더 (없으면 자동 생성됨)
- `debug`: True 설정 시 탐지 및 이벤트 병합 과정 상세 출력

</br>

이 함수는 내부적으로:

1. 영상 파일명에서 타임스탬프를 추출 (`2025-06-18T14-32-00.mp4` 형식)
2. `YOLOEventClipper` 인스턴스를 생성
3. `.run()`을 실행하여 탐지 및 저장을 수행

</br>

**폴더 전체 병렬 처리 (process_videos.py)**

```powershell
python process_videos.py --video_dir videos --output_base output --debug
```

- `-video_dir`: `.mp4` 영상들이 저장된 폴더
- `-output_base`: 결과를 저장할 루트 폴더
- `-debug`: 디버깅 로그 출력 여부

</br>

이 스크립트는 내부적으로:

1. `videos` 폴더에서 `.mp4` 파일 목록을 가져온 후
2. 각각을 별도의 프로세스로 `YOLOEventClipper.run_for_path()`에 전달합니다
3. 병렬 처리로 다수의 영상도 빠르게 처리할 수 있습니다

</br>

### ⚙️ 주요 매개변수

`YOLOEventClipper` 클래스 생성 시 아래 매개변수들을 조절

| **매개변수** | **설명** | **기본값** |
| --- | --- | --- |
| `model_path` | YOLO 모델 파일 경로 (`.pt`) | `yolo/best.pt` |
| `video_path` | 처리할 영상 경로 | `videos/theft.mp4` |
| `output_dir` | 결과 저장 디렉토리 | `output/` |
| `confidence_threshold` | 탐지 확신도 기준 | `0.90` |
| `valid_labels` | 탐지할 이벤트 라벨 목록 | `{'theft', 'fall', 'fight', 'smoke'}` |
| `merge_gap_seconds` | 동일 이벤트로 간주할 최대 공백 시간 | `30초` |
| `base_clip_duration` | 기본 클립 확장 시간 (초) | `5.0초` |
| `debug` | 디버그 출력 여부 | `False` |

</br>

### 5. FastAPI 백엔드 API 명세서
| Category | Endpoint | Method | Description | Params/Body | Response |
| --- | --- | --- | --- | --- | --- |
| Auth | `/signup` | POST | 회원가입 및 사용자 폴더 생성 | `username`, `email`, `password` (JSON) | `200 OK` – `{ "message": "User created successfully" }400 Bad Request` – 중복된 username 또는 email |
| Auth | `/login` | POST | 로그인, 사용자 YOLO 분석 자동 실행 및 알림 스케줄러 실행 | `identifier`, `password` (JSON) | `200 OK` – `{ "message": "Login successful", "username": ..., "user_id": ... }401 Unauthorized` – 잘못된 로그인 정보`<br>`500 Internal Server Error` – 후처리 실패 |
| Camera | `/api/cameras` | POST | 카메라 등록 및 YOLO 처리 자동 실행 | `user_id`, `store_id`, `name`, `video_url`, `image_url` (JSON) | `200 OK` – 카메라 정보 (`CameraOut`)`404 Not Found` – 사용자 또는 매장 없음 |
| Camera | `/api/store/events` | GET | 매장-카메라 이벤트 조회 | `store`, `camera_label` (Query) | `200 OK` – `[ { date, url, type, risk_level }, ... ]404 Not Found` – 매장 또는 카메라 없음 |
| Camera | `/api/store/cameras` | GET | 매장의 카메라 목록 조회 | `user_id`, `store` (Query) | `200 OK` – `[CameraOut, ...]404 Not Found` – 매장 없음 또는 사용자 소유 아님 |
| Event | `/api/user/alerts/` | GET | 사용자의 로그인 이후 발생한 이벤트 목록 조회 | `user_id` (Query param) | `200 OK` – `[Alert, ...]401 Unauthorized` – 로그인 정보 없음 |
| Event | `/api/user/alerts/` | POST | 수동 이벤트 생성 및 알림 전송 | `EventCreate` JSON (user_id, store_id, camera_id, type_id, video_url) | `200 OK` – 메시지 |
| Event | `/api/start-detection/` | POST | YOLO 탐지 스크립트 실행 요청 (비동기) | `store_id`, `camera_id` (Query or form data) | `200 OK` – 메시지 |
| Store | `/api/user/stores` | GET | 사용자의 스토어 이름 목록 조회 | `user_id` (Query) | `200 OK` – `[ "store1", "store2", ... ]404 Not Found` – 사용자 없음 또는 스토어 없음 |
| Store | `/api/user/stores/detail` | GET | 사용자의 스토어 상세 목록 조회 (id, name) | `user_id` (Query) | `200 OK` – `[{"id": 1, "name": "store1"}, ...]400 Bad Request` – `user_id` 형식 오류`404 Not Found` – 사용자 없음 또는 스토어 없음 |
| Store | `/api/store/register` | POST | 새로운 스토어 등록 및 사용자별 폴더 생성 | `StoreCreate` JSON (user_id, name) | `200 OK` – 등록된 스토어 정보 (`StoreResponse`)`404 Not Found` – 사용자 없음 |
| User | `/api/user/profile` | GET | 사용자 프로필 조회 | `user_id` (Query) | `200 OK` – `UserProfile` (id, username, email)`404 Not Found` – 사용자 없음 |