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
    ]
    cursor.executemany("INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)", users)

    # 사용자 ID 조회
    cursor.execute("SELECT id FROM user WHERE username = 'user1'")
    user1_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM user WHERE username = 'user2'")
    user2_id = cursor.fetchone()[0]

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
        (user1_id, store1_id, "Main", "http://localhost:8000/videos/user1/store1/clips/main.mp4", "http://localhost:8000/videos/user1/store1/captures/main.jpg"),
        (user1_id, store1_id, "Back", "http://localhost:8000/videos/user1/store1/clips/back.mp4", "http://localhost:8000/videos/user1/store1/captures/back.jpg"),
        (user1_id, store1_id, "Entrance", "http://localhost:8000/videos/user1/store1/clips/entrance.mp4", "http://localhost:8000/videos/user1/store1/captures/entrance.jpg"),
        (user1_id, store2_id, "Aisle", "http://localhost:8000/videos/user1/store2/clips/aisle.mp4", "http://localhost:8000/videos/user1/store2/captures/aisle.jpg"),
        (user1_id, store3_id, "Exit", "http://localhost:8000/videos/user1/store3/exit.mp4", "http://localhost:8000/videos/user1/store3/captures/exit.jpg"),
        (user1_id, store4_id, "Parking Lot", "http://localhost:8000/videos/user1/store4/parking_lot.mp4", "http://localhost:8000/videos/user1/store4/captures/parking_lot.jpg"),
        (user2_id, storeA_id, "Entrance", "http://localhost:8000/videos/user2/storea/entrance.mp4", "http://localhost:8000/videos/user2/storea/captures/entrance.jpg"),
        (user2_id, storeA_id, "Back", "http://localhost:8000/videos/user2/storea/back.mp4", "http://localhost:8000/videos/user2/storea/captures/back.jpg"),
        (user2_id, storeB_id, "Security", "http://localhost:8000/videos/user2/storeb/security.mp4", "http://localhost:8000/videos/user2/storeb/captures/security.jpg")
    ]
    cursor.executemany("INSERT INTO camera (user_id, store_id, name, video_url, image_url) VALUES (?, ?, ?, ?, ?)", cameras)

    # Event type 추가
    event_types = [
        ("theft", "high"),
        ("fall", "medium"),
        ("fight", "high"),
        ("smoke", "low")
    ]
    cursor.executemany("INSERT OR IGNORE INTO event_type (type, risk_level) VALUES (?, ?)", event_types)

    conn.commit()

    events = [
        (1, 3, 5, 1, "2025-06-18 08:46:23.933254", "http://localhost:8000/output/user1/store3/exit/clips/2025-06-18T17-45-52_theft_clip_0.mp4"),
        (1, 4, 6, 4, "2025-06-18 08:46:54.284087", "http://localhost:8000/output/user1/store4/parking_lot/clips/2025-06-18T17-45-47_smoke_clip_0.mp4")
    ]
    cursor.executemany(
        "INSERT INTO event (user_id, store_id, camera_id, type_id, event_time, video_url) VALUES (?, ?, ?, ?, ?, ?)",
        events
    )

    conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect('cctv_system.db')
    create_database(conn)
    print("Database created successfully.")

    insert_sample_data(conn)
    conn.close()
    print("Sample data inserted successfully.")
