## 🚨 Smart Unmanned Store: YOLO AI Abnormal Behavior Detection & Alert App

*8Development Period**
* **Overall Development Period**: 2025.04.29 - 2025.06.20
* **UI Implementation**: 2025.05.02 - 2025.05.15
* **Feature Implementation**: 2025.05.13 - 2025.06.20  

For detailed project information, please refer to the `CCTV_FE` repository.


## 1. Project Structure
---
The main file structure of the project is as follows:

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
    └── detect.py                # YOLO 객체 탐지 스크립트
```


## 2. Backend Server Setup and Execution
---

### **Project Installation**

**Clone the Project Repository**
```bash
git clone https://github.com/embedded-final-project-group-A/CCTV_BE.git
cd CCTV_BE
```

**Set up Virtual Environment**
```bash
conda create -n "cctv"
conda activate cctv
pip install -r requirements.txt
```

### **Create Database**

* Execute the `test_db.py` file to create the database.
* The database in `test_db.py` saves `https://localhost:8000` as the server address.
* If you wish to run on an Android emulator, execute `test_db_android.py` to create the database.
* If test data is not required, comment out `insert_sample_data()` before execution.


## 3. Database Design
---
### **CCTV Event Monitoring Database Schema**
This database defines schemas for storing user, store, camera, event type, and event data. It can primarily be utilized in CCTV-based abnormal detection and event management systems.


