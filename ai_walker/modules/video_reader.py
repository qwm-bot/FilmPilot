# modules/video_reader.py
import cv2
import time
import os

def extract_frames(video_path, frame_rate=1):
    cap = cv2.VideoCapture(video_path)
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if count % frame_rate == 0:
            frame_path = f"ai_walker/assets/frame_{count}.jpg"
            cv2.imwrite(frame_path, frame)
            yield frame_path
            time.sleep(0.5) 
        count += 1
    cap.release()

if __name__ == "__main__":
    video_file = "ai_walker/video_input/obstacle_input.mp4"
    for frame_path in extract_frames(video_file, frame_rate=30):
        print("Extracted frame saved to:", frame_path)
