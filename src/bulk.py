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
        if os.path.isdir(os.path.join(input, folder)):
            for subfolder in os.listdir(os.path.join(input, folder)):
                if os.path.isdir(os.path.join(input, folder, subfolder)):
                    for subsubfolder in os.listdir(os.path.join(input, folder, subfolder)):
                        if os.path.isdir(os.path.join(input, folder, subfolder, subsubfolder)):
                            if "S and R" in subsubfolder:
                                for subsubsubfolder in os.listdir(os.path.join(input, folder, subfolder, subsubfolder)):
                                    if os.path.isdir(os.path.join(input, folder, subfolder, subsubfolder, subsubsubfolder)):
                                        for subsubsubsubfolder in os.listdir(os.path.join(input, folder, subfolder, subsubfolder, subsubsubfolder, subsubsubsubfolder)):
                                            if os.path.isdir(os.path.join(input, folder, subfolder, subsubfolder, subsubsubfolder, subsubsubsubfolder)):
                                                if ("Rotation" in subsubsubsubfolder):
                                                    process_folders.append(
                                                        os.path.join(folder, subfolder, subsubfolder, subsubsubfolder, subsubsubsubfolder)
                                                    )
    return process_folders


def process_folders(input, dry_run):
    for folder in get_folders(input):
        input = folder
        name = os.path.basename(folder)
        output = os.path.join(input, "Bulk Rotation Output", folder)
        if not dry_run:
            os.makedirs(output, exist_ok=True)
            process_folder(os.path.join(input, folder), output)
        else:
            print(f"Dry run: {folder} -> {output}")


if "__main__" == __name__:
    parser = argparse.ArgumentParser(
        description="Bulk processing of Dynabead videos"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Dry run",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to input folder",
    )
    args = parser.parse_args()
    process_folders(args.input, args.dry_run)