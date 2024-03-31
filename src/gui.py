import os
import sys
import crop
import process
import argparse
import warnings
import tkinter as tk
import multiprocessing
from tqdm.tk import tqdm
from tkinter import filedialog, ttk
from tqdm import TqdmExperimentalWarning

if getattr(sys, "frozen", False):
    import pyi_splash


def select_folder(folder_path_var):
    folder_selected = filedialog.askdirectory(initialdir=".", title="Select Folder")
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
    else:
        tk.messagebox.showerror("Error", "No video files found in the selected folder.")


def run(input, output, absolute, plot, text, debug, button, progress):
    args = dict(
        input=input.get(),
        output=output.get(),
        video=debug.get(),
        plot=plot.get(),
        absolute=absolute.get(),
        text=text.get(),
    )
    args = argparse.Namespace(**args)
    button["state"] = "disabled"
    process.process_folder(args, progress)
    button["state"] = "normal"


def setup_track_tab(
    tab,
    track_input_path_var,
    track_output_path_var,
    text_var,
    plot_var,
    absolute_var,
    video_var,
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
    ).grid(row=0, column=2)

    # Output folder selection
    ttk.Label(frame, text="Select Output Folder:").grid(
        row=1, column=0, sticky=tk.W, pady=10
    )
    ttk.Entry(frame, textvariable=track_output_path_var, width=50).grid(row=1, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(track_output_path_var)
    ).grid(row=1, column=2)

    # Debug mode checkbox
    ttk.Checkbutton(
        frame,
        text="Export text",
        variable=text_var,
        onvalue=True,
        offvalue=False,
    ).grid(row=2, column=0, columnspan=3)
    # Debug mode checkbox
    ttk.Checkbutton(
        frame,
        text="Export plot",
        variable=plot_var,
        onvalue=True,
        offvalue=False,
    ).grid(row=3, column=0, columnspan=3)
    ttk.Checkbutton(
        frame,
        text="Export plot in absolute mode matching video dimensions",
        variable=absolute_var,
        onvalue=True,
        offvalue=False,
    ).grid(row=4, column=0, columnspan=3)
    # Debug mode checkbox
    ttk.Checkbutton(
        frame,
        text="Export annotated video",
        variable=video_var,
        onvalue=True,
        offvalue=False,
    ).grid(row=5, column=0, columnspan=3)

    processing_button = ttk.Button(
        frame,
        text="Start Processing",
        command=lambda: run(
            track_input_path_var,
            track_output_path_var,
            absolute_var,
            plot_var,
            text_var,
            video_var,
            processing_button,
            progress,
        ),
    )
    processing_button.grid(row=6, column=0, columnspan=3, pady=10)


def setup_crop_tab(root, tab, input_path_var, output_path_var, progress):
    frame = ttk.Frame(tab, padding="10")
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Select Folder for Cropping:").grid(
        row=0, column=0, sticky=tk.W
    )
    folder_entry = ttk.Entry(frame, textvariable=input_path_var, width=50)
    folder_entry.grid(row=0, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(input_path_var)
    ).grid(row=0, column=2)
    ttk.Label(frame, text="Select Output Folder:").grid(row=1, column=0, sticky=tk.W)
    folder_entry = ttk.Entry(frame, textvariable=output_path_var, width=50)
    folder_entry.grid(row=1, column=1)
    ttk.Button(
        frame, text="Browse", command=lambda: select_folder(output_path_var)
    ).grid(row=1, column=2)

    open_crop_tool_button = ttk.Button(
        frame,
        text="Open Crop Tool",
        command=lambda: open_crop_tool(root, input_path_var, output_path_var, progress),
    )
    open_crop_tool_button.grid(row=2, column=0, columnspan=3, pady=10)


def create_gui():
    root = tk.Tk()
    root.title("Video Processing")

    # Common variables
    track_input_path_var = tk.StringVar(value=os.getcwd() + "/videos")
    track_output_path_var = tk.StringVar(value=os.getcwd() + "/output")
    crop_input_path_var = tk.StringVar(value=os.getcwd() + "/raw")
    crop_output_path_var = tk.StringVar(value=os.getcwd() + "/exported_beads")

    text_var = tk.BooleanVar(value=True)
    plot_var = tk.BooleanVar()
    absolute_var = tk.BooleanVar()
    video_var = tk.BooleanVar()

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
        track_tab,
        track_input_path_var,
        track_output_path_var,
        text_var,
        plot_var,
        absolute_var,
        video_var,
        progress,
    )

    # New 'Crop' tab setup
    setup_crop_tab(root, crop_tab, crop_input_path_var, crop_output_path_var, progress)

    tab_control.pack(expand=1, fill="both")

    root.resizable(False, False)

    # Center the window
    root.update_idletasks()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    size = tuple(int(_) for _ in root.geometry().split("+")[0].split("x"))
    x = w // 2 - size[0] // 2
    y = h // 2 - size[1] // 2
    root.geometry(f"{size[0]}x{size[1]}+{x}+{y}")

    if getattr(sys, "frozen", False):
        pyi_splash.close()

    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    create_gui()
