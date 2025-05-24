import cv2
import os
import uuid

def run_yolo_on_video(video_path: str, output_dir: str = "static/clips"):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"영상 파일 열기에 실패했습니다: {video_path}")

    # 입력 영상의 프레임 속성과 해상도 확인
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None:
        fps = 24.0  # 기본값 fallback

    # 출력 파일 경로 설정
    out_path = os.path.join(output_dir, f"{uuid.uuid4()}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        out.write(frame)

    cap.release()
    out.release()
    return out_path
