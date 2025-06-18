## 🚨 Smart Unmanned Store: YOLO AI Abnormal Behavior Detection & Alert App

**Development Period**
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

<img alt="테이블 구조" src="./readme_images/테이블 구조.png" width="800"/>

### **Table: `user`**
* **Description**: Stores system user information.

| Column          | Type                               | Description             |
| :-------------- | :--------------------------------- | :---------------------- |
| `id`            | INTEGER, PRIMARY KEY, AUTOINCREMENT | Unique user ID          |
| `username`      | TEXT, UNIQUE, NOT NULL             | User's name (unique)    |
| `email`         | TEXT, UNIQUE, NOT NULL             | User's email (unique)   |
| `password_hash` | TEXT, NOT NULL                     | SHA-256 hashed password |


### **Table: `store`**
* **Description**: Stores store information registered by users.
* **Constraints**: A unique constraint on the combination of (`user_id`, `name`) ensures that a user cannot register multiple stores with the same name.

| Column     | Type                               | Description                             |
| :--------- | :--------------------------------- | :-------------------------------------- |
| `id`       | INTEGER, PRIMARY KEY, AUTOINCREMENT | Unique store ID                         |
| `user_id`  | INTEGER, NOT NULL                  | User ID who registered the store (FK to `user.id`) |
| `name`     | TEXT, NOT NULL                     | Store name                              |
| `location` | TEXT, NULLABLE                     | Store location information              |

### **Table: `camera`**
* **Description**: Stores information about cameras installed in stores.
* **Constraints**: A unique constraint on the combination of (`user_id`, `store_id`, `name`) ensures that cameras within the same user's store cannot have duplicate names.

| Column      | Type                               | Description                               |
| :---------- | :--------------------------------- | :---------------------------------------- |
| `id`        | INTEGER, PRIMARY KEY, AUTOINCREMENT | Unique camera ID                          |
| `user_id`   | INTEGER, NOT NULL                  | User ID who registered the camera (FK to `user.id`) |
| `store_id`  | INTEGER, NOT NULL                  | Store ID the camera belongs to (FK to `store.id`) |
| `name`      | TEXT, NOT NULL                     | Camera name                               |
| `video_url` | TEXT, NULLABLE                     | URL of the camera's video stream or stored video |
| `image_url` | TEXT, NULLABLE                     | URL of the camera's thumbnail or image    |

### **Table: `event_type`**
* **Description**: Stores event type and risk level information.

| Column      | Type                               | Description                            |
| :---------- | :--------------------------------- | :------------------------------------- |
| `id`        | INTEGER, PRIMARY KEY, AUTOINCREMENT | Unique event type ID                   |
| `type`      | TEXT, UNIQUE, NOT NULL             | Event type name (e.g., intrusion, fire) |
| `risk_level` | TEXT, NOT NULL                     | Risk level (e.g., low, medium, high)   |

### **Table: `event`**
* **Description**: Stores data for detected events.

| Column       | Type                                   | Description                                  |
| :----------- | :------------------------------------- | :------------------------------------------- |
| `id`         | INTEGER, PRIMARY KEY, AUTOINCREMENT    | Unique event ID                              |
| `user_id`    | INTEGER, NOT NULL                      | User ID owning the event (FK to `user.id`)   |
| `store_id`   | INTEGER, NOT NULL                      | Store ID where the event occurred (FK to `store.id`) |
| `camera_id`  | INTEGER, NOT NULL                      | Camera ID that detected the event (FK to `camera.id`) |
| `type_id`    | INTEGER, NOT NULL                      | Event type ID (FK to `event_type.id`)        |
| `event_time` | TIMESTAMP, DEFAULT CURRENT_TIMESTAMP   | Time of event occurrence                     |
| `video_url`  | TEXT, NOT NULL                         | URL of video related to the event            |

### **Password Hashing**
Passwords are stored in SHA-256 hash form rather than plain text. The hashing function uses Python's `hashlib` module and is implemented as follows:

```bash
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
```


## 4. YOLO
---



## 5. FastAPI Backend API Specification
---
### **🔐 Auth API**

**User Registration (Sign Up)**
* **URL**: `/signup`
* **Method**: `POST`
* **Description**: Registers a new user.


**Request Body:**
```json
{
	"username": "string",
	"email": "string (email)",
	"password": "string"
}
```

**Response:**
```json
{ "message": "User created successfully" }
```

**User Login (Sign In)**
* **URL**: `/login`
* **Method**: `POST`
* **Description**: Authenticates a user (can use either username or email).


**Request Body:**
```json
{
  "identifier": "string (username 또는 email)",
  "password": "string"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "username": "string",
  "user_id": 1
}
```

### **🏪 Store API**

**Get User's Store Names**
* **URL**: `/api/user/stores`
* **Method**: `GET`
* **Query**: `user_id: string`
* **Response**: `["Store A", "Store B"]`

**Get User's Detailed Store List**
* **URL**: `/api/user/stores/detail`
* **Method**: `GET`
* **Query**: `user_id: string`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Store A"
  },
  {
    "id": 2,
    "name": "Store B"
  }
]
```

**Register Store**
* **URL**: `/api/store/register`
* **Method**: `POST`

**Request Body:**
```json
{
  "user_id": 1,
  "name": "New Store",
  "location": "Seoul"
}
```

**Response:**
```json
{
  "id": 3,
  "user_id": 1,
  "name": "New Store",
  "location": "Seoul"
}
```

### **🎥 Camera API**

**Register Camera**
* **URL**: `/api/cameras`
* **Method**: `POST`

**Request Body:**
```json
{
  "user_id": 1,
  "store_id": 3,
  "name": "Front Door Cam",
  "video_url": "http://example.com/video.mp4",
  "image_url": "http://example.com/thumbnail.png"
}
```

**Response**:
```json
{
  "id": 10,
  "user_id": 1,
  "store_id": 3,
  "name": "Front Door Cam",
  "video_url": "http://example.com/video.mp4",
  "image_url": "http://example.com/thumbnail.png"
}
```

**Get Specific Store-Camera Events**
* **URL**: `/api/store/events`
* **Method**: `GET`
* **Query**: `store: string`, `camera_label: string`

**Response**:
```json
[
  {
    "date": "2024-10-05",
    "url": "http://example.com/video1.mp4",
    "type": "Fire",
    "risk_level": "High"
  },
  {
    "date": "2024-10-04",
    "url": "http://example.com/video2.mp4",
    "type": "Intrusion",
    "risk_level": "Medium"
  }
]
```

**Get Camera List by Store Name**
* **URL**: `/api/store/cameras`
* **Method**: `GET`
* **Query**: `store: string`

**Response**:
```json
[
  {
    "id": 10,
    "user_id": 1,
    "store_id": 3,
    "name": "Front Door Cam",
    "video_url": "http://example.com/video.mp4",
    "image_url": "http://example.com/thumbnail.png"
  }
]
```


### **👤 User API**

**Get User Profile**
* **URL**: `/api/user/profile`
* **Method**: `GET`
* **Query**: `user_id: int`

**Response**:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "johndoe@example.com"
}
```


### **📡 Events API 명세서**

**Get Notification List**
* **URL**: `/api/user/alerts`
* **Method**: `GET`

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "store_id": 1,
    "camera_id": 1,
    "type_id": 1,
    "event_time": "2025-06-01T10:00:00",
    "video_url": "http://localhost:8000/output/clips/theft_clip_123.mp4"
  },
]
```

**Create Event & Send Notification**
* **URL**: `/api/user/alerts`
* **Method**: `POST`
* **Body** (JSON):
```json
{
  "user_id": 1,
  "store_id": 1,
  "camera_id": 1,
  "type_id": 1,
  "video_url": "http://localhost:8000/output/clips/theft_clip_456.mp4"
}
```

**Response:**
```json
{
  "message": "Event saved and alert sent"
}
```


### **FastAPI Backend API Specification (Summary)**

| Category | Endpoint                     | Method | Description                         | Parameters/Request Body                                 | Response   |
| :------- | :--------------------------- | :----- | :---------------------------------- | :------------------------------------------------------ | :--------- |
| **Auth** | `/signup`                    | `POST` | User Registration                   | `username`, `email`, `password`                         | `200 OK`   |
|          | `/login`                     | `POST` | User Login                          | `identifier` (username or email), `password`            | `200 OK`   |
| **Store**| `/api/user/stores`           | `GET`  | Get User's Store Names              | Query: `user_id`                                        | `200 OK`   |
|          | `/api/user/stores/detail`    | `GET`  | Get User's Detailed Store List      | Query: `user_id`                                        | `200 OK`   |
|          | `/api/store/register`        | `POST` | Register Store                      | Body: `user_id`, `name`, `location`                     | `200 OK`   |
| **Camera**| `/api/cameras`               | `POST` | Register Camera                     | Body: `user_id`, `store_id`, `name`, `video_url`, `image_url` | `200 OK`   |
|          | `/api/store/events`          | `GET`  | Get Store-Camera Events             | Query: `store`, `camera_label`                          | `200 OK`   |
|          | `/api/store/cameras`         | `GET`  | Get Camera List by Store Name       | Query: `store`                                          | `200 OK`   |
| **User** | `/api/user/profile`          | `GET`  | Get User Profile                    | Query: `user_id`                                        | `200 OK`   |
| **Events**| `/api/user/alerts/`          | `GET`  | Get Notification List               | None                                                    | `200 OK`   |
|          | `/api/user/alerts/`          | `POST` | Create Event & Send Notification    | Body: `user_id`, `store_id`, `camera_id`, `type_id`, `video_url` | `200 OK`   |


### **FastAPI Backend API Specification (Detailed)**

| Category | Method | Path                      | Description                          | Request Params/Body Example                                                                         | Response Example                                                                                                                                                                                                            |
| :------- | :----- | :------------------------ | :----------------------------------- | :-------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auth** | `POST` | `/signup`                 | User Registration                    | `{'username': 'string', 'email': 'string (email)', 'password': 'string'}`                         | `{'message': 'User created successfully'}`                                                                                                                                                                                  |
| **Auth** | `POST` | `/login`                  | User Login                           | `{'identifier': 'string (username 또는 email)', 'password': 'string'}`                              | `{'message': 'Login successful', 'username': 'string', 'user_id': 'int'}`                                                                                                                                                   |
| **Store**| `GET`  | `/api/user/stores`        | Get User's Store Names               | Query: `user_id`: `string`                                                                          | `['string']` (e.g., `["Store A", "Store B"]`)                                                                                                                                                                               |
| **Store**| `GET`  | `/api/user/stores/detail` | Get User's Detailed Store List       | Query: `user_id`: `string`                                                                          | `[{'id': 'int', 'name': 'string', 'location': 'string', 'user_id': 'int'}]` (e.g., `[{'id': 1, 'name': 'Store A', 'location': 'Seoul', 'user_id': 1}]`) |
| **Store**| `POST` | `/api/store/register`     | Register Store                       | Body: `{'user_id': 'int', 'name': 'string', 'location': 'string'}`                                | `{'message': 'Store registered successfully', 'store_id': 'int'}`                                                                                                                                                        |
| **Camera**| `POST` | `/api/cameras`            | Register Camera                      | Body: `{'user_id': 'int', 'store_id': 'int', 'name': 'string', 'video_url': 'string', 'image_url': 'string'}` | `{'message': 'Camera registered successfully', 'camera_id': 'int'}`                                                                                                                                                        |
| **Camera**| `GET`  | `/api/store/events`       | Get Specific Store-Camera Events     | Query: `store`: `string`, `camera_label`: `string`                                                | `[{'id': 'int', 'event_time': 'string', 'video_url': 'string', 'event_type_name': 'string', 'risk_level': 'string'}]` (e.g., `[{'id': 101, 'event_time': '2025-06-01T12:00:00Z', 'video_url': '...', 'event_type_name': 'Theft', 'risk_level': 'high'}]`) |
| **Camera**| `GET`  | `/api/store/cameras`      | Get Camera List by Store Name        | Query: `store`: `string`                                                                            | `[{'id': 'int', 'user_id': 'int', 'store_id': 'int', 'name': 'string', 'video_url': 'string', 'image_url': 'string'}]` |
| **User** | `GET`  | `/api/user/profile`       | Get User Profile                     | Query: `user_id`: `int`                                                                             | `{'id': 'int', 'username': 'string', 'email': 'string'}`                                                                                                                                                                    |
| **Events**| `GET`  | `/api/user/alerts/`       | Get Notification List                | None                                                                                                | `[{'id': 'int', 'user_id': 'int', 'store_id': 'int', 'camera_id': 'int', 'type_id': 'int', 'event_time': 'string', 'video_url': 'string'}]` (e.g., `[{'id': 1, 'user_id': 1, 'store_id': 1, 'camera_id': 1, 'type_id': 1, 'event_time': '2025-06-01T12:00:00', 'video_url': 'http://localhost:8000/output/clips/theft_clip_123.mp4'}]`) |
| **Events**| `POST` | `/api/user/alerts/`       | Create Event & Send Notification     | Body: `{'user_id': 'int', 'store_id': 'int', 'camera_id': 'int', 'type_id': 'int', 'video_url': 'string (URL)'}` | `{'message': 'Event saved and alert sent'}`                                                                                                                                                                             |