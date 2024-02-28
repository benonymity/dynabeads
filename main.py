import cv2
import numpy as np
import matplotlib.pyplot as plt
import time
import os
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

def detect_center(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 2, 2)
    _, thresh = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    center = None
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            center = (M["m10"] / M["m00"], M["m01"] / M["m00"])
    return center

def calculate_center(centers):
    sum_x = sum([c[0] for c in centers])
    sum_y = sum([c[1] for c in centers])
    count = len(centers)
    return (int(sum_x/count), int(sum_y/count))

def process(video_path):
    video = cv2.VideoCapture(video_path)
    centers = []

    start_time = time.time()
    
    while video.isOpened():
        read, frame = video.read()
        if not read:
            break
        center = detect_center(frame)
        if center:
            centers.append(center)

    video.release()

    end_time = time.time()
    processing_time = end_time - start_time
    return video_path, centers, processing_time

def plot(video_name, centers):
    center_of_rotation = calculate_center(centers)
    translated_centers = [(x - center_of_rotation[0], y - center_of_rotation[1]) for x, y in centers]

    distances = [np.sqrt(x**2 + y**2) for x, y in translated_centers]
    max_distance = max(distances)
    normalized_centers = [(x / max_distance, y / max_distance) for x, y in translated_centers]
    x_coords = [pt[0] for pt in normalized_centers]
    y_coords = [pt[1] for pt in normalized_centers]

    fig, ax = plt.subplots()
    ax.plot(x_coords, y_coords, c='blue', label='Bead Path', linewidth=0.5)
    ax.scatter([0], [0], c='red', label='Center of Rotation', edgecolors='black', zorder=5)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('X Position (um)')
    ax.set_ylabel('Y Position (um)')
    ax.set_title('Bead Tracking')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.invert_yaxis()

    plt.tight_layout(pad=2)
    plt.savefig(f"output/{video_name}_plot.png")

def save_to_text(video_name, centers):
    center_of_rotation = calculate_center(centers)
    translated_centers = [(x - center_of_rotation[0], y - center_of_rotation[1]) for x, y in centers]
    
    df = pd.DataFrame(translated_centers, columns=['X Position (px)', 'Y Position (px)'])
    df['Angle (deg)'] = np.degrees(np.arctan2(df['Y Position (px)'], df['X Position (px)']))
    df['Angle (deg)'] = df['Angle (deg)'].apply(lambda x: x if x >= 0 else 360 + x)
    df.insert(0, 'Frames', range(1, len(df) + 1))
    
    df.to_csv(f"output/{video_name}_tracking.csv", index=False)

def process_folder(folder_path):
    video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.mp4')]
    results = []

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process, video_files))

    for result in results:
        video_path, centers, processing_time = result
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        print(f"Processing of {video_name} took {processing_time:.2f} seconds.")
        if centers:
            plot(video_name, centers)
            save_to_text(video_name, centers)
        else:
            print(f"No bead detected in {video_name}.")

def main():
    folder_path = "videos"
    process_folder(folder_path)

if __name__ == "__main__":
    main()
