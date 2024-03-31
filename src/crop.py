import os
import sys
import cv2
import argparse
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog, ttk
from concurrent.futures import ProcessPoolExecutor, as_completed


# Define a function to get sorted list of video files
def get_sorted_video_files(input):
    video_files = [f for f in os.listdir(input) if f.endswith((".mp4", ".avi"))]
    video_files.sort()
    return [os.path.join(input, f) for f in video_files]


# Extract the first frame from a video
def get_first_frame(video_path, target_width=960, target_height=540):
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    if success:
        # Convert to RGB for PIL
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get original frame size
        orig_height, orig_width = frame.shape[:2]

        # Calculate the scaling factor to fit the frame within the target size, maintaining aspect ratio
        scale_w = target_width / orig_width
        scale_h = target_height / orig_height
        scale = min(scale_w, scale_h)

        # Calculate the new size
        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)

        # Resize the frame
        resized_frame = cv2.resize(
            frame, (new_width, new_height), interpolation=cv2.INTER_AREA
        )

        return resized_frame

    return None


# Assuming you have a method to get the frame size
def get_frame_size(video_path):
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()
        return int(width), int(height)
    return None, None


def detect_beads(frame):
    """Detect the centers of beads in a frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for cnt in contours:
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            centers.append((int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])))
    return centers


def export_selected_beads(input, output, video_path, selections):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"{video_path} does not exist.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise cv2.error("Error opening video capture.", "export_selected_beads")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    os.makedirs(output, exist_ok=True)

    writers = []
    for i, selected in enumerate(selections):
        i += 1
        if selected:
            cx, cy = selected
            out_dir = os.path.join(output, f"bead_{i}")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, os.path.basename(video_path))
            writers.append(
                (cv2.VideoWriter(out_path, fourcc, fps, (100, 100)), (cx, cy))
            )

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        for writer, (cx, cy) in writers:
            y1 = max(0, cy - 50)
            y2 = min(cy + 50, frame.shape[0])
            x1 = max(0, cx - 50)
            x2 = min(cx + 50, frame.shape[1])
            writer.write(frame[y1:y2, x1:x2])

    cap.release()
    for writer, _ in writers:
        writer.release()


class VideoFrameExplorer:
    def __init__(self, root, input, output, progress=None):
        video_paths = get_sorted_video_files(input)
        self.root = root
        self.progress = progress
        self.video_paths = video_paths
        self.input = input
        self.output = output
        self.current_index = 0
        self.detected_centers = []

        self.canvas = tk.Canvas(root, width=960, height=540)
        self.canvas.pack()

        # Frame for export buttons, placed correctly below the navigation frame
        self.export_button_frame = ttk.Frame(root)
        self.export_button_frame.pack(side=tk.BOTTOM, pady=(5, 10))

        self.export_all_button = ttk.Button(
            self.export_button_frame, text="Export All", command=self.export
        )
        self.export_all_button.pack(side=tk.LEFT)
        self.export_single_button = ttk.Button(
            self.export_button_frame,
            text=f"Export up to Video {self.current_index+1}",
            command=self.export,
        )
        self.export_single_button.pack(side=tk.LEFT)

        self.nav_button_frame = ttk.Frame(root)
        self.nav_button_frame.pack(side=tk.BOTTOM, pady=(5, 0))

        # Navigation buttons
        self.first_button = ttk.Button(
            self.nav_button_frame, text="<< First", command=self.show_first_frame
        )
        self.first_button.pack(side=tk.LEFT)

        self.prev_button = ttk.Button(
            self.nav_button_frame, text="< Prev", command=self.show_prev_frame
        )
        self.prev_button.pack(side=tk.LEFT)

        self.next_button = ttk.Button(
            self.nav_button_frame, text="Next >", command=self.show_next_frame
        )
        self.next_button.pack(side=tk.LEFT)

        self.last_button = ttk.Button(
            self.nav_button_frame, text="Last >>", command=self.show_last_frame
        )
        self.last_button.pack(side=tk.LEFT)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-2>", self.on_canvas_right_click)
        # Different systems have different default bindings, so checking both here
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        self.show_frame(self.current_index)
        self.update_button_states()

        root.resizable(False, False)

        # Center the window
        root.update_idletasks()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        size = tuple(int(_) for _ in root.geometry().split("+")[0].split("x"))
        x = (w / 2) - (size[0] / 2)
        y = (h / 2) - (size[1] / 2)
        root.geometry("%dx%d+%d+%d" % (size + (x, y)))

        root.deiconify()

    def update_button_states(self):
        # Disable "First" and "Prev" buttons if on the first video
        if self.current_index == 0:
            self.first_button["state"] = "disabled"
            self.prev_button["state"] = "disabled"
        else:
            self.first_button["state"] = "normal"
            self.prev_button["state"] = "normal"

        # Disable "Next" and "Last" buttons if on the last video
        if self.current_index >= len(self.video_paths) - 1:
            self.next_button["state"] = "disabled"
            self.last_button["state"] = "disabled"
        else:
            self.next_button["state"] = "normal"
            self.last_button["state"] = "normal"

        if self.current_index == len(self.video_paths) - 1:
            self.export_single_button.pack_forget()
            self.export_all_button.pack(side=tk.LEFT)
        else:
            self.export_single_button.pack(side=tk.LEFT)
            self.export_all_button.pack_forget()

    def update_canvas(self, img):
        self.canvas.delete("all")
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.redraw_rectangles()

    def detect_and_draw_centers(self, frame):
        if self.current_index == 0 and not self.detected_centers:
            centers = detect_beads(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))
            self.detected_centers = [(center, False) for center in centers]

    def redraw_rectangles(self):
        for center, clicked in self.detected_centers:
            self.draw_rectangle(center, clicked)

    def draw_rectangle(self, center, clicked):
        # Get original frame size
        orig_width, orig_height = get_frame_size(self.video_paths[self.current_index])
        disp_width, disp_height = 960, 540

        # Calculate scaling factors for width and height
        scale_w = disp_width / orig_width if orig_width else 1
        scale_h = disp_height / orig_height if orig_height else 1
        scale = min(scale_w, scale_h)

        # Scale the rectangle size (100x100) according to the scaling factor
        half_side_length_scaled = 50 * scale

        x, y = center
        # Apply scaled half_side_length for rectangle coordinates
        x1, y1 = x - half_side_length_scaled, y - half_side_length_scaled
        x2, y2 = x + half_side_length_scaled, y + half_side_length_scaled
        outline_color = "light green" if clicked else "red"
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline_color, tags="rect")

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        orig_width, orig_height = get_frame_size(self.video_paths[self.current_index])
        disp_width = 960
        scale = disp_width / orig_width if orig_width else 1
        half_side_length_scaled = scale * 50
        for i, (center, clicked) in enumerate(self.detected_centers):
            x1, y1 = (
                center[0] - half_side_length_scaled,
                center[1] - half_side_length_scaled,
            )
            x2, y2 = (
                center[0] + half_side_length_scaled,
                center[1] + half_side_length_scaled,
            )
            if x1 <= x <= x2 and y1 <= y <= y2:
                # Toggle the clicked state and redraw the canvas
                self.detected_centers[i] = (center, not clicked)
                self.redraw_rectangles()
                break

    def on_canvas_right_click(self, event):
        x, y = event.x, event.y
        orig_width, orig_height = get_frame_size(self.video_paths[self.current_index])
        disp_width = 960
        scale = disp_width / orig_width if orig_width else 1
        half_side_length_scaled = scale * 50
        for i, (center, clicked) in enumerate(self.detected_centers):
            x1, y1 = (
                center[0] - half_side_length_scaled,
                center[1] - half_side_length_scaled,
            )
            x2, y2 = (
                center[0] + half_side_length_scaled,
                center[1] + half_side_length_scaled,
            )
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.detected_centers[i]
                self.show_frame(
                    self.current_index
                )  # More emphatic redraw, the normal redraw doesn't remove already existing ones
                break

    def show_frame(self, index):
        self.current_index = index
        frame = get_first_frame(self.video_paths[index])
        if frame is not None:
            self.update_canvas(frame)
            self.detect_and_draw_centers(frame)
            self.export_single_button.config(
                text=f"Export up to Video {self.current_index+1}"
            )
            self.redraw_rectangles()
        self.update_button_states()

    def export(self):
        orig_width, orig_height = get_frame_size(self.video_paths[self.current_index])
        disp_width = 960
        scale = disp_width / orig_width if orig_width else 1
        selected_centers = [
            (int(center[0] / scale), int(center[1] / scale))
            for center, clicked in self.detected_centers
            if clicked
        ]
        self.progress.reset(total=self.current_index + 1)

        if selected_centers:
            try:
                self.progress._tk_window.deiconify()
            except:
                pass
            with ProcessPoolExecutor() as executor:
                # Map futures to video file names
                future_to_video = {
                    executor.submit(
                        export_selected_beads,
                        self.input,
                        self.output,
                        video_file,
                        selected_centers,
                    ): video_file
                    for video_file in self.video_paths[0 : self.current_index + 1]
                }

                for future in as_completed(future_to_video):
                    # Update the progress bar manually
                    self.progress.update(1)

                    try:
                        result = future.result()
                    except Exception as exc:
                        video_name = future_to_video[future]
                        print(f"{video_name} generated an exception: {exc}")

                # Finish the progress bar
                self.progress.n = self.progress.total
                self.progress.refresh()
                try:
                    self.progress._tk_window.withdraw()
                except:
                    pass
        else:
            print("No centers selected for this video.")

    def show_first_frame(self):
        self.current_index = 0
        self.show_frame(self.current_index)

    def show_prev_frame(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_frame(self.current_index)

    def show_next_frame(self):
        if self.current_index < len(self.video_paths) - 1:
            self.current_index += 1
            self.show_frame(self.current_index)

    def show_last_frame(self):
        self.current_index = len(self.video_paths) - 1
        self.show_frame(self.current_index)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.title("Crop Tool")
    parser = argparse.ArgumentParser(
        description="Crop videos down to individual beads for tracking."
    )
    # Integration with the file dialog to choose the folder
    input = filedialog.askdirectory(initialdir=".", title="Select Input Folder")
    if not input:
        tk.messagebox.showerror("Error", "You must select an input folder")
        sys.exit(0)
    output = filedialog.askdirectory(initialdir=".", title="Select Output Folder")
    if not output:
        tk.messagebox.showerror("Error", "You must select an output folder")
        sys.exit(0)
    explorer = VideoFrameExplorer(root, input, output)

    root.mainloop()
