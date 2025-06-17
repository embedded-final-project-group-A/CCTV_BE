# yolo/detect.py

import torch
import numpy as np
from ultralytics import YOLO
import cv2
import os
import subprocess
from datetime import datetime, timedelta
import re

class YOLOEventClipper:
    def __init__(self, 
                 model_path="yolo/best.pt", 
                 video_path="videos/theft.mp4", 
                 output_dir="output", 
                 web_base_url="http://localhost:8000/",
                 start_time=datetime.now(),
                 confidence_threshold=0.90,
                 valid_labels=None,
                 base_clip_duration=5.0,
                 merge_gap_seconds=30.0,
                 max_buffer_seconds=30.0,
                 debug=False):
        
        self.DEBUG = debug
        self.model = YOLO(model_path)
        self.names = self.model.names
        self.video_path = video_path
        self.output_dir = output_dir
        self.web_base_url = web_base_url
        self.video_start_time = start_time

        self.CONFIDENCE_THERESHOLD = confidence_threshold
        self.VALID_EVENT_LABELS = valid_labels or {'theft', 'fall', 'fight', 'smoke'}
        self.BASE_CLIP_DURATION = base_clip_duration
        self.MERGE_GAP_SECONDS = merge_gap_seconds
        self.MAX_BUFFER_FRAMES = None
        self.padding_frames = None

        self.event_logs = []
        self.clip_counter = 0
        self.active_events = {}

        self._prepare_output_dirs()

    def _debug_log(self, *args):
        if self.DEBUG:
            print("[DEBUG]", *args)

    def _prepare_output_dirs(self):
        os.makedirs(os.path.join(self.output_dir, "captures"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "clips"), exist_ok=True)

    def _to_web_url(self, path):
        relative_path = path.replace(self.output_dir + "/", "")
        return f"{self.web_base_url}{relative_path}"

    def _safe_filename(self, s):
        return re.sub(r'[\\/*?:"<>|{}]', "_", str(s))

    def _convert_to_h264(self, input_path, output_path):
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vcodec", "libx264", "-profile:v", "baseline",
            "-level", "3.0", "-pix_fmt", "yuv420p",
            "-acodec", "aac", "-strict", "experimental", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _normalize_label(self, label_raw):
        if not isinstance(label_raw, str):
            return f"invalid_label_{type(label_raw).__name__}"
        for base_label in self.VALID_EVENT_LABELS:
            if base_label in label_raw:
                return base_label
        return label_raw

    def _save_clip(self, buffer, start_idx, end_idx, fps, output_base):
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
        self._convert_to_h264(temp_path, final_path)
        os.remove(temp_path)
        return os.path.exists(final_path), final_path

    def _save_event_clip(self, norm_label, start_frame, end_frame, frames_buffer, buffer_start_frame_idx, fps):
        start_idx = max(0, start_frame - self.padding_frames - buffer_start_frame_idx)
        end_idx = min(len(frames_buffer), end_frame + self.padding_frames - buffer_start_frame_idx)

        safe_label = self._safe_filename(norm_label)
        time_str = (self.video_start_time + timedelta(seconds=start_frame / fps)).strftime("%Y-%m-%dT%H-%M-%S")
        clip_base = os.path.join(self.output_dir, "clips", f"{time_str}_{norm_label}_clip_{self.clip_counter}")

        clip_saved, clip_path = self._save_clip(frames_buffer, start_idx, end_idx, fps, clip_base)

        img_path = None
        if start_idx < len(frames_buffer):
            img_path = os.path.join(self.output_dir, "captures", f"{time_str}_{safe_label}_capture_{self.clip_counter}.jpg")
            cv2.imwrite(img_path, frames_buffer[start_idx])

        if clip_saved and img_path:
            self.event_logs.append((time_str, self._to_web_url(img_path), self._to_web_url(clip_path)))
            print(f"[🟢 완료] {norm_label}: {time_str} → {clip_path}")

        self.clip_counter += 1

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.padding_frames = int(1.0 * fps)
        self.MAX_BUFFER_FRAMES = int(fps * 30)

        frame_count = 0
        buffer_start_frame_idx = 0
        frames_buffer = []

        while True:
            ret, frame = cap.read()
            if not ret or frame_count >= total_frames:
                break

            frames_buffer.append(frame.copy())
            if len(frames_buffer) > self.MAX_BUFFER_FRAMES:
                frames_buffer.pop(0)
                buffer_start_frame_idx += 1

            results = self.model(frame, verbose=False)
            detected_norm_labels = set()
            ended_labels = []

            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                classes = boxes.cls.cpu().numpy().astype(int)
                confidences = boxes.conf.cpu().numpy()

                for cls_idx, conf in zip(classes, confidences):
                    if conf < self.CONFIDENCE_THERESHOLD:
                        continue
                    raw_label = str(self.names.get(cls_idx, cls_idx))
                    norm_label = self._normalize_label(raw_label)
                    if norm_label not in self.VALID_EVENT_LABELS:
                        continue
                    detected_norm_labels.add(norm_label)

                    if norm_label not in self.active_events:
                        self.active_events[norm_label] = {
                            'start_frame': frame_count,
                            'end_frame': frame_count + int(self.BASE_CLIP_DURATION * fps),
                            'last_seen_frame': frame_count,
                            'max_confidence': conf
                        }
                    else:
                        ev = self.active_events[norm_label]
                        ev['last_seen_frame'] = frame_count
                        ev['end_frame'] = max(ev['end_frame'], frame_count + int(self.BASE_CLIP_DURATION * fps))
                        ev['max_confidence'] = max(ev['max_confidence'], conf)

            for norm_label, ev in list(self.active_events.items()):
                if norm_label not in detected_norm_labels:
                    if frame_count - ev['last_seen_frame'] > int(self.MERGE_GAP_SECONDS * fps):
                        ended_labels.append(norm_label)

            for norm_label in ended_labels:
                ev = self.active_events.pop(norm_label)
                if ev['max_confidence'] >= self.CONFIDENCE_THERESHOLD:
                    self._save_event_clip(norm_label, ev['start_frame'], ev['end_frame'],
                                          frames_buffer, buffer_start_frame_idx, fps)
                else:
                    print(f"[Error] {norm_label} 이벤트: confidence {ev['max_confidence']:.2f} < {self.CONFIDENCE_THERESHOLD}")

            frame_count += 1
            if cv2.waitKey(1) == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

        for norm_label, ev in list(self.active_events.items()):
            if norm_label not in self.VALID_EVENT_LABELS:
                continue
            if ev['max_confidence'] >= self.CONFIDENCE_THERESHOLD:
                self._save_event_clip(norm_label, ev['start_frame'], ev['end_frame'],
                                      frames_buffer, buffer_start_frame_idx, fps)
            else:
                print(f"[Error: ] {norm_label} 이벤트: confidence {ev['max_confidence']:.2f} < {self.CONFIDENCE_THERESHOLD}")

        print("\n[전체 처리 완료] 저장된 이벤트 로그:")
        for time_str, img_url, clip_url in self.event_logs:
            print(f"- {time_str} | 📸 {img_url} | 🎞️ {clip_url}")

    @classmethod
    def run_for_path(cls, video_path, output_dir="output", debug=False):
        filename = os.path.basename(video_path)
        match = re.search(r"(\d{4}-\d{2}-\d{2}[_T ]?\d{2}-\d{2}-\d{2})", filename)
        if match:
            time_str = match.group(1).replace("_", " ").replace("T", " ")
            start_time = datetime.strptime(time_str, "%Y-%m-%d %H-%M-%S")
        else:
            start_time = datetime.now()

        basename = os.path.splitext(os.path.basename(video_path))[0]
        specific_output_dir = os.path.join(output_dir, basename)

        clipper = cls(
            video_path=video_path,
            output_dir=specific_output_dir,
            start_time=start_time,
            debug=debug
        )
        clipper.run()
