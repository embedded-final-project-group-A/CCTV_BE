import torch
import numpy as np
from ultralytics import YOLO
import cv2
import os
from datetime import datetime, timedelta

# 디버깅 설정
DEBUG = False

def debug_log(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# 모델 로드
model = YOLO("./yolo/best.pt")
names = model.names

# 출력 디렉토리 생성
os.makedirs("output/captures", exist_ok=True)
os.makedirs("output/clips", exist_ok=True)

# 비디오 경로 설정
video_path = "videos/yolo_test.mp4"
cap = cv2.VideoCapture(video_path)

# 프레임 정보
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# 분석 구간 설정 (초 단위)
start_time_sec = 0   # 예: 0초부터
end_time_sec = 5     # 예: 5초까지 분석

# 분석 구간의 프레임 범위 계산
start_frame = int(fps * start_time_sec)
end_frame = int(fps * end_time_sec)
if end_frame > total_frames:
    end_frame = total_frames

# 클립 길이 설정 (초 단위)
clip_duration = 2.0
half_clip_frames = int(fps * (clip_duration / 2))

# 영상 시작 시간 (기준 시간, 필요시 변경)
video_start_time = datetime(2025, 5, 27, 12, 0, 0)

# 상태 변수 초기화
frame_count = 0
helmet_capture_count = 0
frames_buffer = []
buffer_start_frame_idx = 0  # frames_buffer[0]이 영상 내 몇 번째 프레임인지

# 로그 데이터 리스트
event_logs = []

# 클립 저장 함수
def save_clip(buffer, fps, output_path):
    if not buffer:
        return False
    height, width = buffer[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    for f in buffer:
        out.write(f)
    out.release()
    return True

# 탐지 결과 처리 함수 (저장 시 로그 데이터 반환)
def use_result(frame, results, current_idx):
    global helmet_capture_count
    captured = False

    if results and results[0].boxes is not None:
        bboxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        classes = results[0].boxes.cls.cpu().numpy().astype(int)
        pred_box = zip(classes, bboxes)

        for cls, bbox in pred_box:
            (x1, y1, x2, y2) = bbox
            label = names.get(cls, str(cls))
            debug_log(f"탐지: 클래스={label}, 위치=({x1},{y1})~({x2},{y2})")

            if label.lower() == "helmet" and not captured:
                # 이미지 저장 경로
                img_path = f"output/captures/helmet_capture_{helmet_capture_count}.jpg"
                img_saved = cv2.imwrite(img_path, frame)

                # 클립 저장 경로 및 클립 프레임 추출
                start = max(0, current_idx - half_clip_frames)
                end = min(len(frames_buffer), current_idx + half_clip_frames)
                clip_frames = frames_buffer[start:end]
                clip_path = f"output/clips/helmet_clip_{helmet_capture_count}.mp4"
                clip_saved = save_clip(clip_frames, fps, clip_path)

                if img_saved and clip_saved:
                    debug_log(f"[✅ 이미지 저장됨] {img_path}")
                    debug_log(f"[🎞️ 클립 저장됨] {clip_path}")

                    # 이벤트 시간 계산
                    event_time = video_start_time + timedelta(seconds=frame_count / fps)
                    event_time_str = event_time.strftime("%Y-%m-%dT%H:%M:%S")

                    # URL 경로 (http 형식)
                    image_url = f"https://localhost:8000/output/captures/helmet_capture_{helmet_capture_count}.jpg"
                    clip_url = f"https://localhost:8000/output/clips/helmet_clip_{helmet_capture_count}.mp4"

                    helmet_capture_count += 1
                    captured = True

                    # 로그 데이터 반환
                    return (event_time_str, image_url, clip_url)

                else:
                    debug_log(f"[❌ 저장 실패] 이미지: {img_saved}, 클립: {clip_saved}")

    return None

# 메인 루프
while True:
    ret, frame = cap.read()
    if not ret:
        debug_log("영상 끝")
        break

    # 현재 프레임이 분석 구간에 포함되는지 확인
    if frame_count < start_frame:
        frame_count += 1
        continue

    if frame_count > end_frame:
        debug_log("분석 종료 시간 도달")
        break

    # 버퍼에 프레임 추가
    frames_buffer.append(frame.copy())

    # 버퍼 길이 제한 및 시작 프레임 인덱스 업데이트
    max_buffer_len = int(fps * 10)  # 최대 10초 분량 버퍼 유지
    if len(frames_buffer) > max_buffer_len:
        frames_buffer.pop(0)
        buffer_start_frame_idx += 1

    results = model(frame, verbose=False)

    # 현재 프레임의 버퍼 내 인덱스 계산
    current_buffer_idx = frame_count - buffer_start_frame_idx

    event_log = use_result(frame, results, current_buffer_idx)
    if event_log is not None:
        event_logs.append(event_log)
        print(f"[이벤트 로그] Time: {event_log[0]}, Image URL: {event_log[1]}, Clip URL: {event_log[2]}")

    frame_count += 1

    if cv2.waitKey(1) == 27:  # ESC 키 종료
        break

cap.release()
cv2.destroyAllWindows()

print(f"총 {helmet_capture_count}개의 헬멧 탐지 이미지와 클립이 저장되었습니다.")
print("프로그램 종료")

# event_logs 리스트에 모든 탐지 이벤트의 (시간, 이미지 URL, 클립 URL) 정보가 담겨 있음
