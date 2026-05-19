import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

# Constants and initial setup
DEFAULT_FRAMERATE = 25
fieldstrength = [20, 40, 60, 80, 100]
testedfreqs = np.arange(1, 10.5, 0.5)
viscosity = 0.001
munot = 4 * np.pi * 1e-7
bead_radius = 0.5e-6
lever_length = 1e-6
lever_err = 0.1e-6
bead_err = 0.05 * bead_radius

LONG_VIDEO_SEGMENT_RE = re.compile(
    r"_(?P<index>\d{2})_(?:(?P<freq>\d+(?:\.\d+)?)Hz_precess|hold)\.txt$"
)


def load_data(data_dir):
    files = sorted(f for f in os.listdir(data_dir) if f.endswith(".txt"))
    return [np.loadtxt(os.path.join(data_dir, f), skiprows=1) for f in files], files


def preprocess_data(data):
    min_length = min(map(len, data))
    return [d[:min_length] for d in data]


def calculate_corrected_angles(data):
    angles = []
    for d in data:
        corrected_x = d[:, 1] - np.mean(d[:, 1])
        corrected_y = d[:, 2] - np.mean(d[:, 2])
        angles.append(np.arctan2(corrected_y, corrected_x))
    return angles


def frequency_analysis(angle_data, framerate):
    freqs = fftfreq(len(angle_data), 1 / framerate)
    fft_data = np.abs(fft(angle_data))
    peaks, _ = find_peaks(fft_data, height=np.max(fft_data) / 4, distance=5)
    peak_freqs = freqs[peaks]
    peak_powers = fft_data[peaks]
    return peak_freqs, peak_powers


def analyze_data(angles, framerate):
    crit_freqs = []
    for angle_data in angles:
        freqs, powers = frequency_analysis(angle_data, framerate)
        if len(freqs) > 0:
            max_power = max(powers)
            crit_freq = max(f for f, p in zip(freqs, powers) if p > max_power / 2)
        else:
            crit_freq = 0
        crit_freqs.append(crit_freq)
    return crit_freqs


def parse_long_video_filename(filename):
    match = LONG_VIDEO_SEGMENT_RE.search(filename)
    if not match:
        return None
    segment_index = int(match.group("index"))
    freq = float(match.group("freq")) if match.group("freq") else None
    kind = "precess" if match.group("freq") else "hold"
    return segment_index, kind, freq


def load_long_video_data(data_dir, framerate):
    """Load precess segments from long-video tracking output."""
    segments = []
    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith(".txt") or filename.endswith("_manifest.txt"):
            continue
        parsed = parse_long_video_filename(filename)
        if parsed is None:
            continue
        segment_index, kind, driving_freq = parsed
        if kind != "precess":
            continue
        path = os.path.join(data_dir, filename)
        data = np.loadtxt(path, skiprows=1)
        angles = calculate_corrected_angles([data])
        measured = analyze_data(angles, framerate)[0]
        segments.append(
            {
                "filename": filename,
                "segment_index": segment_index,
                "driving_freq_hz": driving_freq,
                "measured_freq_hz": measured,
            }
        )
    segments.sort(key=lambda s: s["segment_index"])
    return segments


def plot_long_video_frequency_response(segments, output_path=None):
    driving = [s["driving_freq_hz"] for s in segments]
    measured = [s["measured_freq_hz"] for s in segments]

    plt.figure(figsize=(10, 6))
    plt.plot(driving, driving, "k--", alpha=0.4, label="Ideal lock (1:1)")
    plt.scatter(driving, measured, label="Measured critical frequency")
    plt.xlabel("Driving frequency (Hz)")
    plt.ylabel("Measured frequency (Hz)")
    plt.title("Long video: driving vs measured precession frequency")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path)
    else:
        plt.show()


def calculate_magnetic_moment(crit_freqs, lever_length, field_strengths, viscosity, bead_radius, munot):
    mag_moments = []
    for crit_freq, field_strength in zip(crit_freqs, field_strengths):
        H = field_strength * 1000 / (4 * np.pi)
        term = (4 * np.pi**2 * viscosity) / (munot * H)
        moment = term * crit_freq * (4 * bead_radius**3 + 3 * bead_radius * lever_length**2)
        mag_moments.append(moment)
    return mag_moments


def propagate_errors(crit_freqs, lever_length, bead_radius, field_strengths, lever_err, bead_err):
    errors = []
    for crit_freq, field_strength in zip(crit_freqs, field_strengths):
        error = np.sqrt((crit_freq * lever_err) ** 2 + (field_strength * bead_err) ** 2)
        errors.append(error)
    return errors


def linear_fit(x, a, b):
    return a * x + b


def plot_magnetic_moments(field_strengths, mag_moments, errors, output_path=None):
    plt.figure(figsize=(10, 6))
    mag_moments = [moment * 1e15 for moment in mag_moments]
    plt.errorbar(
        field_strengths,
        mag_moments,
        yerr=errors,
        fmt="o",
        capsize=5,
        label="Bead Magnetization",
        ecolor="blue",
        marker="o",
        linestyle="None",
    )
    popt, _ = curve_fit(linear_fit, field_strengths, mag_moments, sigma=errors)
    fit_values = linear_fit(np.array(field_strengths), *popt)
    plt.plot(
        field_strengths,
        fit_values,
        "r-",
        label=f"Linear Fit: y = {popt[0]:.2e}x + {popt[1]:.2e}",
    )
    plt.xlabel("External Field Strength (Oe)")
    plt.ylabel("Magnetic Moment (Am²)")
    plt.title("Magnetic Moment vs Field Strength")
    plt.grid(True)
    plt.legend()
    if output_path:
        plt.savefig(output_path)
    else:
        plt.show()


def run_batch_analysis(data_dir, framerate):
    data, _ = load_data(data_dir)
    standardized_data = preprocess_data(data)
    angles = calculate_corrected_angles(standardized_data)
    crit_freqs = [analyze_data([angle], framerate)[0] for angle in angles]
    mag_moments = calculate_magnetic_moment(
        crit_freqs, lever_length, fieldstrength, viscosity, bead_radius, munot
    )
    errors = propagate_errors(
        crit_freqs, lever_length, bead_radius, fieldstrength, lever_err, bead_err
    )
    plot_magnetic_moments(fieldstrength, mag_moments, errors)
    for moment, error in zip(mag_moments, errors):
        print(f"Magnetic Moment: {moment:.3e} Am², Error: {error:.3e} Am²")


def framerate_from_manifest(data_dir):
    for filename in os.listdir(data_dir):
        if not filename.endswith("_long_video_manifest.txt"):
            continue
        manifest_path = os.path.join(data_dir, filename)
        with open(manifest_path) as manifest:
            for line in manifest:
                if line.startswith("fps="):
                    return float(line.strip().split("=", 1)[1])
    return None


def run_long_video_analysis(data_dir, framerate, plot_path=None):
    manifest_fps = framerate_from_manifest(data_dir)
    if manifest_fps is not None:
        framerate = manifest_fps
        print(f"Using framerate {framerate:.3f} Hz from long-video manifest")
    segments = load_long_video_data(data_dir, framerate)
    if not segments:
        raise SystemExit(
            f"No long-video precess segments found in {data_dir}. "
            "Expected files like *_01_1Hz_precess.txt"
        )

    print(f"{'Segment':>8} {'Drive (Hz)':>12} {'Measured (Hz)':>14}")
    for seg in segments:
        print(
            f"{seg['segment_index']:8d} "
            f"{seg['driving_freq_hz']:12g} "
            f"{seg['measured_freq_hz']:14g}"
        )

    plot_long_video_frequency_response(segments, output_path=plot_path)


def main():
    parser = argparse.ArgumentParser(description="Analyze Dynabeads tracking output.")
    parser.add_argument(
        "data_dir",
        nargs="?",
        default=os.getcwd(),
        help="Directory containing .txt tracking files",
    )
    parser.add_argument(
        "--long-video",
        action="store_true",
        help="Analyze long-video segment exports (precess blocks only)",
    )
    parser.add_argument(
        "--framerate",
        type=float,
        default=DEFAULT_FRAMERATE,
        help="Camera framerate used for FFT (default: 25)",
    )
    parser.add_argument(
        "--plot",
        type=str,
        default=None,
        help="Save plot to this path instead of showing interactively",
    )
    args = parser.parse_args()

    if args.long_video:
        run_long_video_analysis(args.data_dir, args.framerate, plot_path=args.plot)
    else:
        run_batch_analysis(args.data_dir, args.framerate)


if __name__ == "__main__":
    main()
