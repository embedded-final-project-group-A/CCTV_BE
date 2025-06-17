import torch
import numpy as np
from ultralytics import YOLO
import cv2
import os
import subprocess
from datetime import datetime, timedelta
import re

DEBUG = False

def debug_log(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def to_web_url(path):
    return f"http://localhost:8000/{path.replace('output/', '')}"

def safe_filename(s):
    return re.sub(r'[\\/*?:"<>|{}]', "_", str(s))

# 유효 이벤트 라벨
VALID_EVENT_LABELS = {'theft', 'fall', 'fight', 'smoke'}

# 모델 로드
model = YOLO("./yolo/best.pt")
names = model.names

os.makedirs("output/captures", exist_ok=True)
os.makedirs("output/clips", exist_ok=True)

video_path = "videos/fall.mp4"
cap = cv2.VideoCapture(video_path)

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
video_start_time = datetime(2025, 5, 27, 12, 0, 0)

BASE_CLIP_DURATION = 5.0
MERGE_GAP_SECONDS = 30.0
CONFIDENCE_THERESHOLD = 0.90
padding_frames = int(1.0 * fps)

frame_count = 0
frames_buffer = []
buffer_start_frame_idx = 0

event_logs = []
clip_counter = 0
active_events = {}

def convert_to_h264(input_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vcodec", "libx264", "-profile:v", "baseline",
        "-level", "3.0", "-pix_fmt", "yuv420p",
        "-acodec", "aac", "-strict", "experimental", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def save_clip(buffer, start_idx, end_idx, fps, output_base):
    if start_idx >= len(buffer) or end_idx <= start_idx:
        return False, None
    clip_frames = buffer[start_idx:end_idx]
    if not clip_frames:
        return False, None

    height, width = clip_frames[0].shape[:2]
    temp_path = output_base + "_raw.mp4"

    out = cv2.VideoWriter(temp_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    for f in clip_frames:
        out.write(f)
    out.release()

    final_path = output_base + ".mp4"
    convert_to_h264(temp_path, final_path)
    os.remove(temp_path)
    return os.path.exists(final_path), final_path

def normalize_label(label_raw):
    if not isinstance(label_raw, str):
        return f"invalid_label_{type(label_raw).__name__}"
    for base_label in VALID_EVENT_LABELS:
        if base_label in label_raw:
            return base_label
    return label_raw

def save_event_clip(norm_label, start_frame, end_frame, frames_buffer, buffer_start_frame_idx, fps, clip_index):
    start_idx = max(0, start_frame - padding_frames - buffer_start_frame_idx)
    end_idx = min(len(frames_buffer), end_frame + padding_frames - buffer_start_frame_idx)

    safe_label = safe_filename(norm_label)
    time_str = (video_start_time + timedelta(seconds=start_frame / fps)).strftime("%Y-%m-%dT%H-%M-%S")
    clip_base = f"output/clips/{time_str}_{norm_label}_clip_{clip_index}"

    clip_saved, clip_path = save_clip(frames_buffer, start_idx, end_idx, fps, clip_base)

    img_path = None
    if start_idx < len(frames_buffer):
        img_path = f"output/captures/{time_str}_{safe_label}_capture_{clip_index}.jpg"
        cv2.imwrite(img_path, frames_buffer[start_idx])

    if clip_saved and img_path:
        event_logs.append((time_str, to_web_url(img_path), to_web_url(clip_path)))
        print(f"[🟢 완료] {norm_label}: {time_str} → {clip_path}")

    return clip_saved

# 메인 루프
while True:
    ret, frame = cap.read()
    if not ret or frame_count >= total_frames:
        break

    frames_buffer.append(frame.copy())
    if len(frames_buffer) > int(fps * 30):
        frames_buffer.pop(0)
        buffer_start_frame_idx += 1

    results = model(frame, verbose=False)
    detected_norm_labels = set()
    ended_labels = []

    if results and results[0].boxes is not None:
        boxes = results[0].boxes
        classes = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()

        for cls_idx, conf in zip(classes, confidences):
            if conf < CONFIDENCE_THERESHOLD:
                continue
            raw_label = str(names.get(cls_idx, cls_idx))
            norm_label = normalize_label(raw_label)
            if norm_label not in VALID_EVENT_LABELS:
                continue
            detected_norm_labels.add(norm_label)

            if norm_label not in active_events:
                active_events[norm_label] = {
                    'start_frame': frame_count,
                    'end_frame': frame_count + int(BASE_CLIP_DURATION * fps),
                    'last_seen_frame': frame_count,
                    'max_confidence': conf
                }
            else:
                ev = active_events[norm_label]
                ev['last_seen_frame'] = frame_count
                ev['end_frame'] = max(ev['end_frame'], frame_count + int(BASE_CLIP_DURATION * fps))
                ev['max_confidence'] = max(ev['max_confidence'], conf)

    # 종료된 이벤트 처리
    for norm_label, ev in list(active_events.items()):
        if norm_label not in detected_norm_labels:
            if frame_count - ev['last_seen_frame'] > int(MERGE_GAP_SECONDS * fps):
                ended_labels.append(norm_label)

    for norm_label in ended_labels:
        ev = active_events.pop(norm_label)
        if ev['max_confidence'] >= CONFIDENCE_THERESHOLD:
            save_event_clip(norm_label, ev['start_frame'], ev['end_frame'],
                            frames_buffer, buffer_start_frame_idx, fps, clip_counter)
            clip_counter += 1
        else:
            print(f"[Error] {norm_label} 이벤트: confidence {ev['max_confidence']:.2f} < {CONFIDENCE_THERESHOLD}")

    frame_count += 1
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()

# 종료 후 남아있는 이벤트 정리
for norm_label, ev in list(active_events.items()):
    if norm_label not in VALID_EVENT_LABELS:
        continue
    if ev['max_confidence'] >= CONFIDENCE_THERESHOLD:
        save_event_clip(norm_label, ev['start_frame'], ev['end_frame'],
                        frames_buffer, buffer_start_frame_idx, fps, clip_counter)
        clip_counter += 1
    else:
        print(f"[Error: ] {norm_label} 이벤트: confidence {ev['max_confidence']:.2f} < {CONFIDENCE_THERESHOLD}")

# 결과 저장
# print("\n[✅ 전체 처리 완료] 저장된 이벤트 로그:")
# for time_str, img_url, clip_url in event_logs:
#     print(f"- {time_str} | 📸 {img_url} | 🎞️ {clip_url}")
