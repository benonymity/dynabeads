import os
import track
import argparse


def process_folder(input, output):
    args = dict(
        input=input,
        output=output,
        video=False,
        threshold=175,
        plot=True,
        absolute=False,
        text=True,
    )
    args = argparse.Namespace(**args)
    track.process_folder(args, None)


def get_folders(input):
    process_folders = []
    for folder in os.listdir(input):
        for subfolder in os.listdir(os.path.join(input, folder)):
            for subsubfolder in os.listdir(os.path.join(input, folder, subfolder)):
                if "S and R" in subsubfolder:
                    for subsubsubfolder in os.listdir(os.path.join(input, folder, subfolder, subsubfolder)):
                        for subsubsubsubfolder in os.listdir(os.path.join(input, folder, subfolder, subsubsubfolder)):
                            if ("Rotation" in subfolder and ".avi" in os.listdir(os.path.join(input, folder, subfolder, subsubsubfolder, subsubsubsubfolder))[3]):
                                process_folders.append(
                                    os.path.join(input, folder, subfolder, subsubsubfolder, subsubsubsubfolder)
                                )
    return process_folders


def process_folders(input, dry_run):
    for folder in get_folders(input):
        input = folder
        name = os.path.basename(folder)
        output = os.path.join(os.path.split(os.path.split(folder)[0])[0], "Bulk Rotation Output", name)
        if not dry_run:
            os.makedirs(output, exist_ok=True)
            process_folder(input, output)
        else:
            print(f"Dry run: {input} -> {output}")


if "__main__" == __name__:
    parser = argparse.ArgumentParser(
        description="Bulk processing of Dynabead videos"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Path to input folder",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Dry run",
    )
    args = parser.parse_args()
    process_folders(args.input, args.dry_run)