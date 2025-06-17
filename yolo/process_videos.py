import os
import argparse
from multiprocessing import Pool
from detect import YOLOEventClipper

def get_video_list(video_dir):
    return [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(".mp4")]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_dir", required=True)
    parser.add_argument("--output_base", required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    video_paths = get_video_list(args.video_dir)
    yolo_args = [(path, args.output_base, args.debug) for path in video_paths]

    with Pool(processes=4) as pool:
        pool.starmap(YOLOEventClipper.run_for_path, yolo_args)
