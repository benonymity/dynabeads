import os
import cv2
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed


# Function to the detect the center of the dot
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


# Calculate the center of rotation from tracking data
def calculate_center(centers):
    sum_x = sum([c[0] for c in centers])
    sum_y = sum([c[1] for c in centers])
    count = len(centers)
    return ((sum_x / count), (sum_y / count))


# Complete video processing function
def process(video_path, args):
    video = cv2.VideoCapture(video_path)
    centers = []
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if args.video:
        # Define the codec and create VideoWriter object to visualize tracking
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        out = cv2.VideoWriter(
            f'{args.output}/{os.path.basename(video_path).split(".")[0]}_debug.mp4',
            fourcc,
            fps,
            (frame_width, frame_height),
        )

    # Process each frame
    for frame_index in range(frame_count):
        read, frame = video.read()
        if not read:
            break
        try:
            center = detect_center(frame)
            if center is not None:
                centers.append(center)
                if args.video:
                    # Draw a cross on the detected center of the dot.
                    # However this isn't perfect as this function can't go subpixel,
                    # unlike the bead itself. So the actual detected center will
                    # be more accurate than the cross on the debug video.
                    cv2.drawMarker(
                        frame,
                        (int(round(center[0])), int(round(center[1]))),
                        (0, 0, 255),
                        cv2.MARKER_CROSS,
                        markerSize=5,
                        thickness=1,
                    )
                    out.write(frame)
            elif args.video:
                out.write(frame)
        except Exception as e:
            print("error!")
            cv2.imwrite(f"error_frame_{frame_index}.png", frame)

    video.release()
    if args.video:
        out.release()

    return video_path, centers, (frame_width, frame_height)


def plot(video_name, centers, args, video_dims=(100, 100)):
    # Centers are already in pixel units from the detection process
    x_coords = [pt[0] for pt in centers]
    y_coords = [pt[1] for pt in centers]

    fig, ax = plt.subplots()
    center_x, center_y = calculate_center(centers)

    if args.absolute:
        # Scale graph based on video size
        ax.set_xlim(0, video_dims[0])
        ax.set_ylim(0, video_dims[1])
        # And draw a tinier dot
        ax.scatter(
            center_x,
            center_y,
            c="red",
            edgecolors="black",
            label="Center",
            zorder=5,
            s=10,
        )
    else:
        # Draw a big dot if relative scaling
        ax.scatter(
            center_x,
            center_y,
            c="red",
            edgecolors="black",
            label="Center",
            zorder=5,
            s=50,
        )

    ax.set_xlabel("X Position (px)")
    ax.set_ylabel("Y Position (px)")
    ax.set_title(f"{video_name} Bead Tracking")
    ax.legend(loc="upper right")
    ax.set_aspect("equal", "box")
    ax.plot(x_coords, y_coords, c="blue", label="Bead Path", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(f"{args.output}/{video_name}_plot.png")


def save_to_text(video_name, centers, args):
    df = pd.DataFrame(centers, columns=["X Position (px)", "Y Position (px)"])

    center_of_rotation = calculate_center(centers)

    # Calculate the angles using the center of rotation
    df["Angle (deg)"] = np.degrees(
        np.arctan2(
            df["Y Position (px)"] - center_of_rotation[1],
            df["X Position (px)"] - center_of_rotation[0],
        )
    )

    # Normalize the angle values to be in the range of [0, 360)
    df["Angle (deg)"] = df["Angle (deg)"].apply(lambda x: x if x >= 0 else 360 + x)

    df.insert(0, "Frames", range(1, len(df) + 1))

    df_string = df.to_string(index=False, justify="left")

    # Save the DataFrame string to a text file.
    with open(f"{args.output}/{video_name}.txt", "w") as f:
        f.write(df_string)


def process_video(video_file, args):
    video_path, centers, video_dims = process(video_file, args)

    if not centers:
        print(f"No bead detected in {video_file}.")
        return video_path, None, None

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    center_of_rotation = calculate_center(centers)

    if args.plot:
        # Generate the plot
        plot(video_name, centers, args, video_dims)

    if args.text:
        # Save the results to a text file
        save_to_text(video_name, centers, args)

    return video_path, centers, center_of_rotation


def process_folder(args, progress, button=None):
    video_files = [
        os.path.join(args.input, f)
        for f in os.listdir(args.input)
        if f.endswith(".avi")
    ]
    # if not progress:
    #     from tqdm import tqdm
    #     progress = tqdm(
    #         total=len(video_files), desc="Overall Progress", unit="video"
    #     )
    # else:
    progress.reset(total=len(video_files))
    try:
        progress._tk_window.deiconify()
    except:
        pass
    with ProcessPoolExecutor() as executor:
        # Map futures to video file names
        future_to_video = {
            executor.submit(process_video, video_file, args): video_file
            for video_file in video_files
        }

        for future in as_completed(future_to_video):
            # Update the progress bar manually
            progress.update(1)

            try:
                result = future.result()
            except Exception as exc:
                video_name = future_to_video[future]
                print(f"{video_name} generated an exception: {exc}")

        # Finish the progress bar
        progress.n = progress.total
        progress.refresh()
        progress._tk_window.withdraw()


if __name__ == "__main__":
    # Handle CLI input
    parser = argparse.ArgumentParser(
        description="Process video files for bead tracking."
    )
    parser.add_argument(
        "-a",
        "--absolute",
        action="store_true",
        help="Export plot in absolute mode matching video dimensions.",
    )
    parser.add_argument(
        "-d",
        "--video",
        action="store_true",
        help="Enable debug mode to output video with overlays.",
    )
    parser.add_argument(
        "-t",
        "--text",
        action="store_true",
        help="Export only text files for use in MatLab",
    )
    parser.add_argument(
        "-p",
        "--plot",
        action="store_true",
        help="Export only position plots for visualization purposes",
    )
    parser.add_argument(
        "input", type=str, help="Path to the folder containing video files."
    )
    # optional output string
    parser.add_argument(
        "output", type=str, help="Path to the output folder.", nargs="?"
    )
    args = parser.parse_args()

    process_folder(args, None)
