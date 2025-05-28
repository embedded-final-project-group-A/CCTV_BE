import sqlite3
import hashlib

def hash_password(password: str) -> str:
    """SHA-256 기반 비밀번호 해시 함수"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_database(conn):
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        location TEXT,
        UNIQUE(user_id, name)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS camera (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        store_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        video_url TEXT,
        image_url TEXT,
        UNIQUE(user_id, store_id, name)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event_type (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT UNIQUE NOT NULL,
        risk_level TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        store_id INTEGER NOT NULL,
        camera_id INTEGER NOT NULL,
        type_id INTEGER NOT NULL,
        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        video_url TEXT NOT NULL
    )
    ''')

    conn.commit()

def insert_sample_data(conn):
    cursor = conn.cursor()

    # 사용자 추가 (비밀번호는 해싱됨)
    users = [
        ("user1", "user1@example.com", hash_password("password1")),
        ("user2", "user2@example.com", hash_password("password2")),
        ("user3", "user3@example.com", hash_password("password3"))
    ]
    cursor.executemany("INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)", users)

    # 사용자 ID 조회
    cursor.execute("SELECT id FROM user WHERE username = 'user1'")
    user1_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM user WHERE username = 'user2'")
    user2_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM user WHERE username = 'user3'")
    user3_id = cursor.fetchone()[0]

    # Store 추가
    stores = [
        (user1_id, "store1", "Seoul"),
        (user1_id, "store2", "Busan"),
        (user1_id, "store3", "Incheon"),
        (user1_id, "store4", "Daegu"),
        (user2_id, "storeA", "Gwangju"),
        (user2_id, "storeB", "Daejeon")
    ]
    cursor.executemany("INSERT INTO store (user_id, name, location) VALUES (?, ?, ?)", stores)

    # Store ID 조회 함수
    def get_store_id(name):
        cursor.execute("SELECT id FROM store WHERE name = ?", (name,))
        return cursor.fetchone()[0]

    store1_id = get_store_id("store1")
    store2_id = get_store_id("store2")
    store3_id = get_store_id("store3")
    store4_id = get_store_id("store4")
    storeA_id = get_store_id("storeA")
    storeB_id = get_store_id("storeB")

    # Camera 추가
    cameras = [
        (user1_id, store1_id, "Main Camera", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user1_id, store1_id, "Back Camera", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user1_id, store1_id, "Entrance Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user1_id, store2_id, "Aisle Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user1_id, store3_id, "Exit Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user1_id, store4_id, "Parking Lot Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user2_id, storeA_id, "Entrance Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user2_id, storeA_id, "Back Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png"),
        (user2_id, storeB_id, "Security Cam", "http://localhost:8000/videos/store1_main.mp4", "http://localhost:8000/videos/store1_main.png")
    ]
    cursor.executemany("INSERT INTO camera (user_id, store_id, name, video_url, image_url) VALUES (?, ?, ?, ?, ?)", cameras)

    def get_camera_id(user_id, store_id, name):
        cursor.execute(
            "SELECT id FROM camera WHERE user_id = ? AND store_id = ? AND name = ?",
            (user_id, store_id, name)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    cam1_id = get_camera_id(user1_id, store1_id, "Main Camera")
    cam2_id = get_camera_id(user1_id, store1_id, "Back Camera")
    cam3_id = get_camera_id(user1_id, store1_id, "Entrance Cam")
    cam4_id = get_camera_id(user1_id, store2_id, "Aisle Cam")
    cam5_id = get_camera_id(user1_id, store3_id, "Exit Cam")
    cam6_id = get_camera_id(user1_id, store4_id, "Parking Lot Cam")
    cam7_id = get_camera_id(user2_id, storeA_id, "Entrance Cam")
    cam8_id = get_camera_id(user2_id, storeA_id, "Back Cam")
    cam9_id = get_camera_id(user2_id, storeB_id, "Security Cam")

    # Event type 추가
    event_types = [
        ("도난", "high"),
        ("유기", "medium"),
        ("폭행", "high"),
        ("흡연", "low")
    ]
    cursor.executemany("INSERT OR IGNORE INTO event_type (type, risk_level) VALUES (?, ?)", event_types)

    def get_type_id(event_type):
        cursor.execute("SELECT id FROM event_type WHERE type = ?", (event_type,))
        return cursor.fetchone()[0]

    # Event 추가
    events = [
        (user1_id, store1_id, cam1_id, get_type_id("도난"), "http://localhost:8000/videos/test.mp4", "2025-05-27T12:00:00"),
        (user1_id, store1_id, cam1_id, get_type_id("유기"), "http://localhost:8000/videos/test.mp4", "2025-05-26T12:05:00"),
        (user1_id, store1_id, cam2_id, get_type_id("폭행"), "http://localhost:8000/videos/test.mp4", "2025-05-28T12:02:00"),
        (user1_id, store1_id, cam3_id, get_type_id("흡연"), "http://localhost:8000/videos/test.mp4", "2025-05-27T12:07:00"),
        (user1_id, store2_id, cam4_id, get_type_id("폭행"), "http://localhost:8000/videos/test.mp4", "2025-05-29T12:10:00"),
        (user1_id, store3_id, cam5_id, get_type_id("흡연"), "http://localhost:8000/videos/test.mp4", "2025-05-26T12:15:00"),
        (user2_id, storeA_id, cam7_id, get_type_id("흡연"), "http://localhost:8000/videos/test.mp4", "2025-05-27T12:20:00"),
        (user2_id, storeA_id, cam8_id, get_type_id("유기"), "http://localhost:8000/videos/test.mp4", "2025-05-28T12:25:00"),
        (user2_id, storeB_id, cam9_id, get_type_id("도난"), "http://localhost:8000/videos/test.mp4", "2025-05-26T12:30:00")
    ]
    for user_id, store_id, cam_id, type_id, video_url, ts in events:
        cursor.execute(
            "INSERT INTO event (user_id, store_id, camera_id, type_id, video_url, event_time) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, store_id, cam_id, type_id, video_url, ts)
        )

    conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect('cctv_system.db')
    create_database(conn)
    print("Database created successfully.")

    insert_sample_data(conn)
    conn.close()
    print("Sample data inserted successfully.")
