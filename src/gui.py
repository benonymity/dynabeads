import os
import sys
import cv2
import crop
import process
import argparse
import warnings
import tkinter as tk
import multiprocessing
from tqdm.tk import tqdm
from tkinter import filedialog, ttk
from matplotlib import pyplot as plt
from tqdm import TqdmExperimentalWarning
from matplotlib.widgets import Slider, Button

if getattr(sys, "frozen", False):
    import pyi_splash


def select_folder(folder_path_var):
    folder_selected = filedialog.askdirectory(initialdir=folder_path_var.get(), title="Select Folder")
    if folder_selected:
        folder_path_var.set(folder_selected)


def open_crop_tool(root, input_path_var, output_path_var, progress):
    # Placeholder for the crop tool functionality
    # This function needs to be implemented or linked to the actual cropping tool you intend to use.
    video_files = crop.get_sorted_video_files(input_path_var.get())
    if video_files:
        child = tk.Toplevel(root)
        child.title("Crop Tool")
        crop.VideoFrameExplorer(
            child, input_path_var.get(), output_path_var.get(), progress
        )
        root.eval(f'tk::PlaceWindow {str(child)} center')
    else:
        tk.messagebox.showerror("Error", "No video files found in the selected folder.")


def run(input, output, absolute, plot, text, video, threshold, button, progress):
    args = dict(
        input=input.get(),
        output=output.get(),
        video=video.get(),
        threshold=threshold.get(),
        plot=plot.get(),
        absolute=absolute.get(),
        text=text.get(),
    )
    args = argparse.Namespace(**args)
    button["state"] = "disabled"
    process.process_folder(args, progress)
    button["state"] = "normal"

def track_settings(root, parent, text_var, plot_var, absolute_var, video_var, threshold_var, input_folder_var):
        top = tk.Toplevel(parent)
        top.title("Settings")
        frame = ttk.Frame(top, padding=(20, 10, 20, 10))
        frame.pack(fill="both", expand=True)
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        
        # Settings checkboxes
        ttk.Checkbutton(frame, text="Export text", variable=text_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(frame, text="Export plot", variable=plot_var).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(frame, text="Match plot dimensions", variable=absolute_var).grid(row=2, column=0, sticky=tk.W)
        ttk.Checkbutton(frame, text="Export annotated video", variable=video_var).grid(row=3, column=0, sticky=tk.W)

        threshold_text_var = tk.StringVar()
        threshold_text_var.set(f"Threshold: {threshold_var.get()}")
        ttk.Label(frame, textvariable=threshold_text_var).grid(row=4, column=0, pady=(20, 0))
        ttk.Button(frame, text="Adjust Threshold", command=lambda: threshold_settings(root, threshold_var, threshold_text_var, input_folder_var)).grid(row=5, column=0)
        
        # Ok button to close the dialog
        ttk.Button(frame, text="Ok", command=top.destroy).grid(row=6, column=0, pady=(20, 0))
        
        # Make the dialog modal
        top.transient(parent)
        top.grab_set()
        root.eval(f'tk::PlaceWindow {str(top)} center')
        parent.wait_window(top)

def threshold_settings(root, threshold_var, threshold_text_var, input_folder_var):
    # Load the image
    video_files = crop.get_sorted_video_files(input_folder_var.get())
    video_path = os.path.join(input_folder_var.get(), video_files[0])
    cap = cv2.VideoCapture(video_path)
    
    success, img = cap.read()
    # img = cv2.imread(input)
    if not success:
        root.messagebox.showerror("Error", "Could not load image.")

    # Define a function to update the plot based on the threshold
    def update(val):
        THRESHOLD = s_thresh.val  # Get the current value of the slider
        center = detect_center(img, THRESHOLD)
        if center is not None:
            img_with_center = img.copy()
            cv2.drawMarker(
                img_with_center,
                (int(round(center[0])), int(round(center[1]))),
                (0, 0, 255),
                cv2.MARKER_CROSS,
                markerSize=5,
                thickness=1,
            )
            ax_img.imshow(cv2.cvtColor(img_with_center, cv2.COLOR_BGR2RGB))
        plt.draw()

    # Modified detect_center function to accept a threshold value
    def detect_center(frame, threshold):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        _, thresh = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY)
        ax_thresh.imshow(thresh, cmap='gray')
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        center = None
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                center = (M["m10"] / M["m00"], M["m01"] / M["m00"])
        return center

    # Setup figure and axis
    fig, (ax_thresh, ax_img) = plt.subplots(1, 2)
    # plt.subplots_adjust(left=0.25, bottom=0.25)
    ax_img.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ax_img.set_title("Detected Center")
    ax_thresh.set_title("Thresholding")

    # Create the slider
    axcolor = 'lightgoldenrodyellow'
    ax_thresh_slider = plt.axes([0.25, 0.1, 0.65, 0.03], facecolor=axcolor)
    s_thresh = Slider(ax_thresh_slider, 'Threshold', 0, 255, valinit=threshold_var.get())
    update(175)

    # Call update function when slider value is changed
    s_thresh.on_changed(update)

    plt.subplots_adjust(bottom=0.2)
    button_ax = plt.axes([0.5, 0.01, 0.1, 0.075])
    button = Button(button_ax, 'Close', color='red', hovercolor='salmon')

    def close(event):
        plt.close()

    # Event to close the plot
    button.on_clicked(close)

    plt.show()

    threshold_text_var.set(f"Threshold: {round(s_thresh.val)}")
    threshold_var.set(round(s_thresh.val))


def show_help():
    tk.messagebox.showinfo("Help", "This is the help message.")

def setup_track_tab(
    root,
    tab,
    track_input_path_var,
    track_output_path_var,
    text_var,
    plot_var,
    absolute_var,
    video_var,
    threshold_var,
    progress,
):
    frame = ttk.Frame(tab, padding="10")
    frame.pack(fill="both", expand=True)
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Input folder selection
    ttk.Label(frame, text="Select Input Folder:").grid(row=0, column=0, sticky=tk.W)
    ttk.Entry(frame, textvariable=track_input_path_var, width=50).grid(row=0, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(track_input_path_var)
    ).grid(row=0, column=2, padx=(10, 0))

    # Output folder selection
    ttk.Label(frame, text="Select Output Folder:").grid(
        row=1, column=0, sticky=tk.W, pady=10
    )
    ttk.Entry(frame, textvariable=track_output_path_var, width=50).grid(row=1, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(track_output_path_var)
    ).grid(row=1, column=2, padx=(10, 0))

    settings_button = ttk.Button(frame, text="Settings", command=lambda: track_settings(root, frame, text_var, plot_var, absolute_var, video_var, threshold_var, track_input_path_var))
    settings_button.grid(row=3, column=0, columnspan=3, padx=(0, 140), pady=10)
    
    # help_button = ttk.Button(frame, text="Help", command=lambda: show_help())  # Implement show_help() as needed
    # help_button.grid(row=2, column=1, pady=10)
    
    # Processing button
    processing_button = ttk.Button(frame, text="Start Processing", command=lambda: run(track_input_path_var, track_output_path_var, absolute_var, plot_var, text_var, video_var, threshold_var, processing_button, progress))
    processing_button.grid(row=3, column=0, columnspan=3, padx=(110, 0), pady=10)

    help_button = ttk.Button(frame, text="Help", command=lambda: show_help("Track"))
    help_button.grid(row=4, column=2, sticky=tk.E)


def setup_crop_tab(root, tab, input_path_var, output_path_var, progress):
    frame = ttk.Frame(tab, padding="10")
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Select Input Folder:").grid(
        row=0, column=0, sticky=tk.W
    )
    folder_entry = ttk.Entry(frame, textvariable=input_path_var, width=50)
    folder_entry.grid(row=0, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(input_path_var)
    ).grid(row=0, column=2, padx=(10, 0))
    ttk.Label(frame, text="Select Output Folder:").grid(row=1, column=0, sticky=tk.W, pady=10)
    folder_entry = ttk.Entry(frame, textvariable=output_path_var, width=50)
    folder_entry.grid(row=1, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(output_path_var)
    ).grid(row=1, column=2, padx=(10, 0))

    open_crop_tool_button = ttk.Button(
        frame,
        text="Open Crop Tool",
        command=lambda: open_crop_tool(root, input_path_var, output_path_var, progress),
    )
    open_crop_tool_button.grid(row=2, column=0, columnspan=3, pady=10)
    help_button = ttk.Button(frame, text="Help", command=lambda: show_help("Track"))
    help_button.grid(row=3, column=2, sticky=tk.E)


def create_gui():
    root = tk.Tk()
    root.title("Dynabead Tools")

    # Common variables
    track_input_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "videos"))
    track_output_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
    crop_input_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "raw"))
    crop_output_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "exported_beads"))

    text_var = tk.BooleanVar(value=True)
    plot_var = tk.BooleanVar()
    absolute_var = tk.BooleanVar()
    video_var = tk.BooleanVar()

    threshold_var = tk.IntVar(value=175)

    warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
    progress = tqdm(
        tk_parent=root,
        desc="Overall Progress",
        unit="video",
    )
    progress._tk_window.withdraw()

    tab_control = ttk.Notebook(root)

    track_tab = ttk.Frame(tab_control)
    crop_tab = ttk.Frame(tab_control)

    tab_control.add(track_tab, text="Track")
    tab_control.add(crop_tab, text="Crop")

    # Existing setup now under 'Track' tab
    setup_track_tab(
        root,
        track_tab,
        track_input_path_var,
        track_output_path_var,
        text_var,
        plot_var,
        absolute_var,
        video_var,
        threshold_var,
        progress,
    )

    # New 'Crop' tab setup
    setup_crop_tab(root, crop_tab, crop_input_path_var, crop_output_path_var, progress)

    tab_control.pack(expand=1, fill="both")

    root.resizable(False, False)

    # Center the window
    root.eval('tk::PlaceWindow . center')

    if getattr(sys, "frozen", False):
        pyi_splash.close()

    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    create_gui()
