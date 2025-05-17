import cv2
import uuid
import os

def run_yolo_on_video(video_path: str, output_dir: str = "static/clips"):
    cap = cv2.VideoCapture(video_path)
    out_path = os.path.join(output_dir, f"{uuid.uuid4()}.mp4")

    # YOLO 대체용 (실제 YOLO 모델로 바꾸기)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, 20.0, (640, 480))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # 여기에 YOLO 로직 삽입 (예: 사람 감지)
        out.write(frame)

    cap.release()
    out.release()
    return out_path
