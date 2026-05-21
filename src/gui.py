import os
import sys
import cv2
import crop
import track
import warnings
import requests
import argparse
import json
import webbrowser
import tkinter as tk
import multiprocessing
from tqdm.tk import tqdm
from tkinter import filedialog, messagebox, ttk
from matplotlib import pyplot as plt
from tqdm import TqdmExperimentalWarning
from matplotlib.widgets import Slider, Button


# Define the version
__version__ = "3.1.0"


if getattr(sys, "frozen", False):
    import pyi_splash


def select_folder(folder_path_var):
    folder_selected = filedialog.askdirectory(
        initialdir=folder_path_var.get(), title="Select Folder"
    )
    if folder_selected:
        folder_path_var.set(folder_selected)


def open_crop_tool(root, input_path_var, output_path_var, progress):
    # Placeholder for the crop tool functionality
    # This function needs to be implemented or linked to the actual cropping tool you intend to use.
    video_files = crop.get_sorted_video_files(input_path_var.get())
    if video_files:
        child = tk.Toplevel(root)
        icon = tk.PhotoImage(file="icon.png")
        child.iconphoto(False, icon)

        child.title("Crop Tool")
        crop.VideoFrameExplorer(
            child, input_path_var.get(), output_path_var.get(), progress
        )
        root.eval(f"tk::PlaceWindow {str(child)} center")
    else:
        tk.messagebox.showerror("Error", "No video files found in the selected folder.")


def run(
    input,
    output,
    absolute,
    plot,
    text,
    video,
    threshold,
    long_video,
    long_video_protocol,
    button,
    progress,
):
    args = dict(
        input=input.get(),
        output=output.get(),
        video=video.get(),
        threshold=threshold.get(),
        plot=plot.get(),
        absolute=absolute.get(),
        text=text.get(),
        long_video=long_video.get(),
        long_video_protocol=long_video_protocol,
    )
    args = argparse.Namespace(**args)
    button["state"] = "disabled"
    track.process_folder(args, progress)
    button["state"] = "normal"


def track_settings(
    root,
    parent,
    text_var,
    plot_var,
    absolute_var,
    video_var,
    threshold_var,
    input_folder_var,
):
    top = tk.Toplevel(parent)
    top.title("Settings")
    icon = tk.PhotoImage(file="icon.png")
    top.iconphoto(False, icon)

    frame = ttk.Frame(top, padding=(20, 10, 20, 10))
    frame.pack(fill="both", expand=True)
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Settings checkboxes
    ttk.Checkbutton(frame, text="Export text", variable=text_var).grid(
        row=0, column=0, sticky=tk.W
    )
    ttk.Checkbutton(frame, text="Export plot", variable=plot_var).grid(
        row=1, column=0, sticky=tk.W
    )
    ttk.Checkbutton(frame, text="Match video dimensions", variable=absolute_var).grid(
        row=2, column=0, sticky=tk.W
    )
    ttk.Checkbutton(frame, text="Export annotated video", variable=video_var).grid(
        row=3, column=0, sticky=tk.W
    )

    threshold_text_var = tk.StringVar()
    threshold_text_var.set(f"Threshold: {threshold_var.get()}")
    ttk.Label(frame, textvariable=threshold_text_var).grid(
        row=4, column=0, pady=(20, 0)
    )
    ttk.Button(
        frame,
        text="Adjust Threshold",
        command=lambda: threshold_settings(
            root, threshold_var, threshold_text_var, input_folder_var
        ),
    ).grid(row=5, column=0)

    # Ok button to close the dialog
    ttk.Button(frame, text="Ok", command=top.destroy).grid(
        row=6, column=0, pady=(20, 0)
    )

    # Make the dialog modal
    top.transient(parent)
    top.grab_set()
    root.eval(f"tk::PlaceWindow {str(top)} center")
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
        ax_thresh.imshow(thresh, cmap="gray")
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
    axcolor = "lightgoldenrodyellow"
    ax_thresh_slider = plt.axes([0.25, 0.1, 0.65, 0.03], facecolor=axcolor)
    s_thresh = Slider(
        ax_thresh_slider, "Threshold", 0, 255, valinit=threshold_var.get()
    )
    update(175)

    # Call update function when slider value is changed
    s_thresh.on_changed(update)

    plt.subplots_adjust(bottom=0.2)
    button_ax = plt.axes([0.5, 0.01, 0.1, 0.075])
    button = Button(button_ax, "Close", color="red", hovercolor="salmon")

    def close(event):
        plt.close()

    # Event to close the plot
    button.on_clicked(close)

    plt.show()

    threshold_text_var.set(f"Threshold: {round(s_thresh.val)}")
    threshold_var.set(round(s_thresh.val))


def _format_protocol_summary(protocol):
    total_sec = sum(step["duration_sec"] for step in protocol)
    precess_count = sum(1 for step in protocol if step["kind"] == "precess")
    hold_count = sum(1 for step in protocol if step["kind"] == "hold")
    minutes = total_sec / 60
    return (
        f"{len(protocol)} steps ({precess_count} precess, {hold_count} hold) · "
        f"{minutes:.1f} min total"
    )


def segment_settings(root, parent, long_video_var, protocol_steps):
    top = tk.Toplevel(parent)
    top.title("Long Video Segments")
    icon = tk.PhotoImage(file="icon.png")
    top.iconphoto(False, icon)
    top.resizable(True, True)

    working_steps = [dict(step) for step in protocol_steps]
    row_widgets = []

    outer = ttk.Frame(top, padding=(12, 10, 12, 10))
    outer.pack(fill="both", expand=True)

    ttk.Checkbutton(
        outer,
        text="Enable long video mode (split video into segments, starting the timer with inital movement)",
        variable=long_video_var,
    ).pack(anchor="w", pady=(0, 8))

    summary_var = tk.StringVar()
    ttk.Label(outer, textvariable=summary_var).pack(anchor="w", pady=(0, 8))

    toolbar = ttk.Frame(outer)
    toolbar.pack(fill="x", pady=(0, 8))

    table_container = ttk.Frame(outer)
    table_container.pack(fill="both", expand=True)

    canvas = tk.Canvas(table_container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)
    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    header = ttk.Frame(scroll_frame)
    header.pack(fill="x", pady=(0, 4))
    ttk.Label(header, text="#", width=3).grid(row=0, column=0, padx=(0, 4))
    ttk.Label(header, text="Type", width=10).grid(row=0, column=1, padx=4)
    ttk.Label(header, text="Freq (Hz)", width=10).grid(row=0, column=2, padx=4)
    ttk.Label(header, text="Duration (sec)", width=14).grid(row=0, column=3, padx=4)

    rows_frame = ttk.Frame(scroll_frame)
    rows_frame.pack(fill="both", expand=True)

    def refresh_summary():
        summary_var.set(_format_protocol_summary(working_steps))

    def on_kind_changed(row):
        kind = row["kind_var"].get()
        if kind == "hold":
            row["freq_entry"].configure(state="disabled")
            row["freq_var"].set("")
        else:
            row["freq_entry"].configure(state="normal")
            if not row["freq_var"].get().strip():
                row["freq_var"].set("1")

    def try_sync_from_widgets():
        if not row_widgets:
            return True
        try:
            working_steps[:] = collect_steps()
            return True
        except ValueError:
            return False

    def remove_row(index):
        if not try_sync_from_widgets():
            messagebox.showwarning(
                "Protocol", "Fix invalid values before removing a step."
            )
            return
        if len(working_steps) <= 1:
            messagebox.showwarning("Protocol", "At least one step is required.")
            return
        working_steps.pop(index)
        rebuild_rows()

    def add_row(kind="precess", freq_hz=1.0, duration_sec=None):
        if duration_sec is None:
            duration_sec = (
                track.DEFAULT_PRECESS_DURATION_SEC
                if kind == "precess"
                else track.DEFAULT_HOLD_DURATION_SEC
            )
        if not try_sync_from_widgets():
            messagebox.showwarning(
                "Protocol", "Fix invalid values before adding a step."
            )
            return
        working_steps.append(
            {"kind": kind, "freq_hz": freq_hz, "duration_sec": duration_sec}
        )
        rebuild_rows()

    def rebuild_rows():
        for row in row_widgets:
            row["frame"].destroy()
        row_widgets.clear()

        for index, step in enumerate(working_steps):
            row_frame = ttk.Frame(rows_frame)
            row_frame.pack(fill="x", pady=2)

            kind_var = tk.StringVar(value=step["kind"])
            freq_var = tk.StringVar(
                value="" if step["kind"] == "hold" else f"{step.get('freq_hz', 1):g}"
            )
            duration_var = tk.StringVar(value=str(step["duration_sec"]))

            ttk.Label(row_frame, text=str(index + 1), width=3).grid(
                row=0, column=0, padx=(0, 4)
            )
            kind_combo = ttk.Combobox(
                row_frame,
                textvariable=kind_var,
                values=("precess", "hold"),
                state="readonly",
                width=10,
            )
            kind_combo.grid(row=0, column=1, padx=4)
            freq_entry = ttk.Entry(row_frame, textvariable=freq_var, width=10)
            freq_entry.grid(row=0, column=2, padx=4)
            duration_entry = ttk.Entry(row_frame, textvariable=duration_var, width=14)
            duration_entry.grid(row=0, column=3, padx=4)
            ttk.Button(
                row_frame,
                text="Remove",
                command=lambda i=index: remove_row(i),
                width=8,
            ).grid(row=0, column=4, padx=(8, 0))

            row = {
                "frame": row_frame,
                "kind_var": kind_var,
                "freq_var": freq_var,
                "duration_var": duration_var,
                "freq_entry": freq_entry,
            }
            kind_combo.bind(
                "<<ComboboxSelected>>",
                lambda _e, r=row: on_kind_changed(r),
            )
            on_kind_changed(row)
            row_widgets.append(row)

        refresh_summary()

    def collect_steps():
        collected = []
        for index, row in enumerate(row_widgets):
            kind = row["kind_var"].get().strip().lower()
            if kind not in ("precess", "hold"):
                raise ValueError(f"Step {index + 1}: type must be precess or hold")

            duration_text = row["duration_var"].get().strip()
            try:
                duration_sec = float(duration_text)
            except ValueError as exc:
                raise ValueError(
                    f"Step {index + 1}: duration must be a number"
                ) from exc
            if duration_sec <= 0:
                raise ValueError(f"Step {index + 1}: duration must be positive")

            freq_hz = None
            if kind == "precess":
                freq_text = row["freq_var"].get().strip()
                if not freq_text:
                    raise ValueError(f"Step {index + 1}: precess steps need a frequency")
                try:
                    freq_hz = float(freq_text)
                except ValueError as exc:
                    raise ValueError(
                        f"Step {index + 1}: frequency must be a number"
                    ) from exc

            collected.append(
                {"kind": kind, "freq_hz": freq_hz, "duration_sec": duration_sec}
            )
        track.protocol_to_segments(collected)
        return collected

    def reset_default():
        working_steps.clear()
        working_steps.extend(track.default_long_video_protocol())
        rebuild_rows()

    def load_protocol():
        path = filedialog.askopenfilename(
            title="Load protocol",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            loaded = track.load_protocol_file(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Protocol", f"Could not load protocol:\n{exc}")
            return
        working_steps.clear()
        working_steps.extend(loaded)
        rebuild_rows()

    def save_protocol():
        try:
            collected = collect_steps()
        except ValueError as exc:
            messagebox.showerror("Protocol", str(exc))
            return
        path = filedialog.asksaveasfilename(
            title="Save protocol",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            track.save_protocol_file(path, collected)
        except OSError as exc:
            messagebox.showerror("Protocol", f"Could not save protocol:\n{exc}")
            return
        messagebox.showinfo("Protocol", f"Saved protocol to:\n{path}")

    def apply_duration_to_all():
        if not try_sync_from_widgets():
            messagebox.showwarning(
                "Protocol", "Fix invalid values before changing durations."
            )
            return
        dialog = tk.Toplevel(top)
        dialog.title("Set All Durations")
        dialog.transient(top)
        dialog.grab_set()
        ttk.Label(dialog, text="Duration for every step (sec):").pack(
            padx=12, pady=(12, 4)
        )
        duration_var = tk.StringVar(value="60")
        ttk.Entry(dialog, textvariable=duration_var, width=10).pack(padx=12, pady=4)

        def apply():
            try:
                duration = float(duration_var.get())
                if duration <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Protocol", "Enter a positive number.", parent=dialog)
                return
            for step in working_steps:
                step["duration_sec"] = duration
            dialog.destroy()
            rebuild_rows()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(8, 12))
        ttk.Button(btn_frame, text="Apply", command=apply).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=4)
        root.eval(f"tk::PlaceWindow {str(dialog)} center")

    def confirm():
        try:
            collected = collect_steps()
        except ValueError as exc:
            messagebox.showerror("Protocol", str(exc))
            return
        protocol_steps.clear()
        protocol_steps.extend(collected)
        top.destroy()

    ttk.Button(toolbar, text="Add Step", command=lambda: add_row()).pack(side="left")
    ttk.Button(toolbar, text="Set All Durations", command=apply_duration_to_all).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(toolbar, text="Reset Default", command=reset_default).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(toolbar, text="Load JSON", command=load_protocol).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(toolbar, text="Save JSON", command=save_protocol).pack(
        side="left", padx=(8, 0)
    )

    button_row = ttk.Frame(outer)
    button_row.pack(fill="x", pady=(12, 0))
    ttk.Button(button_row, text="Cancel", command=top.destroy).pack(side="right")
    ttk.Button(button_row, text="OK", command=confirm).pack(side="right", padx=(0, 8))

    rebuild_rows()
    top.transient(parent)
    top.grab_set()
    root.eval(f"tk::PlaceWindow {str(top)} center")
    parent.wait_window(top)


def show_help(type):
    tk.messagebox.showinfo("Help", "No help to be had as of yet.")


def new_version_check():
    try:
        response = requests.get("https://api.github.com/repos/benonymity/Dynabeads/releases/latest")
        latest_version = response.json()["tag_name"].replace("v", "")
    except:
        latest_version = __version__

    if latest_version != __version__:
        return True
    else:
        return False

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
    long_video_var,
    long_video_protocol,
    progress,
):
    frame = ttk.Frame(tab, padding="10")
    frame.pack(fill="both", expand=True)
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Input folder selection
    ttk.Label(frame, text="Select Input Folder/File:").grid(row=0, column=0, sticky=tk.W)

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

    actions = ttk.Frame(frame)
    actions.grid(row=2, column=0, columnspan=3, pady=15)

    settings_button = ttk.Button(
        actions,
        text="Settings",
        command=lambda: track_settings(
            root,
            frame,
            text_var,
            plot_var,
            absolute_var,
            video_var,
            threshold_var,
            track_input_path_var,
        ),
    )
    settings_button.pack(side=tk.LEFT, padx=(0, 8))

    ttk.Button(
        actions,
        text="Segments",
        command=lambda: segment_settings(root, frame, long_video_var, long_video_protocol),
    ).pack(side=tk.LEFT, padx=(0, 8))

    processing_button = ttk.Button(
        actions,
        text="Start Processing",
        command=lambda: run(
            track_input_path_var,
            track_output_path_var,
            absolute_var,
            plot_var,
            text_var,
            video_var,
            threshold_var,
            long_video_var,
            long_video_protocol,
            processing_button,
            progress,
        ),
    )
    processing_button.pack(side=tk.LEFT)

    help_button = ttk.Button(frame, text="Help", command=lambda: show_help("Track"))
    help_button.grid(row=3, column=2, sticky=tk.E, pady=(10, 0))

    if new_version_check():
        update_button = ttk.Button(
            frame, text="Update Available", command=lambda: webbrowser.open("https://github.com/benonymity/Dynabeads/releases/latest")
        )
        update_button.grid(row=3, column=0, sticky=tk.W, pady=(10, 0))


def setup_crop_tab(root, tab, input_path_var, output_path_var, progress):
    frame = ttk.Frame(tab, padding="10")
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Select Input Folder:").grid(row=0, column=0, sticky=tk.W)
    folder_entry = ttk.Entry(frame, textvariable=input_path_var, width=50)
    folder_entry.grid(row=0, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(input_path_var)
    ).grid(row=0, column=2, padx=(10, 0))
    ttk.Label(frame, text="Select Output Folder:").grid(
        row=1, column=0, sticky=tk.W, pady=10
    )
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

    if new_version_check():
        update_button = ttk.Button(
            frame, text="Update Available", command=lambda: webbrowser.open("https://github.com/benonymity/Dynabeads/releases/latest")
        )
        update_button.grid(row=3, column=0, sticky=tk.W)


def create_gui():
    root = tk.Tk()
    root.title("Dynabead Tools")
    icon = tk.PhotoImage(file="icon.png")
    root.iconphoto(False, icon)

    # Common variables
    track_input_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "videos"))
    track_output_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
    crop_input_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "raw"))
    crop_output_path_var = tk.StringVar(
        value=os.path.join(os.getcwd(), "exported_beads")
    )

    text_var = tk.BooleanVar(value=True)
    plot_var = tk.BooleanVar()
    absolute_var = tk.BooleanVar()
    video_var = tk.BooleanVar()

    threshold_var = tk.IntVar(value=175)
    long_video_var = tk.BooleanVar(value=False)
    long_video_protocol = track.default_long_video_protocol()

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
        long_video_var,
        long_video_protocol,
        progress,
    )

    # New 'Crop' tab setup
    setup_crop_tab(root, crop_tab, crop_input_path_var, crop_output_path_var, progress)

    tab_control.pack(expand=1, fill="both")

    root.resizable(False, False)

    # Center the window
    root.eval("tk::PlaceWindow . center")

    if getattr(sys, "frozen", False):
        pyi_splash.close()

    if new_version_check():
        tk.messagebox.showinfo("Update Available", "A new version is available!")

    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    create_gui()
