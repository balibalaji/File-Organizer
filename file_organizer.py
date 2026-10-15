"""
File Organizer

Sorts the files in a folder into category subfolders (Images, Documents, Videos, ...)
based on their file extension.

Usage examples:
    python file_organizer.py                          # organize ~/Downloads
    python file_organizer.py "C:/Users/me/Desktop"    # organize a specific folder
    python file_organizer.py ~/Downloads --dry-run    # preview only, no files moved
    python file_organizer.py ~/Downloads --by-date    # Category/YYYY-MM subfolders
    python file_organizer.py ~/Downloads --undo       # reverse the last organize run
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

LOG_NAME = ".organizer_log.json"
OTHER_CATEGORY = "Others"

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".odp"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".json", ".xml"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".apk"},
}


def get_category(file_path):
    """Return the category name for a file based on its extension."""
    extension = file_path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return OTHER_CATEGORY


def unique_destination(destination):
    """If a file with the same name exists, add _1, _2, ... to the name."""
    if not destination.exists():
        return destination
    counter = 1
    while True:
        candidate = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def get_files_to_organize(folder):
    """List top-level files, skipping hidden files, the log file and this script."""
    script_path = Path(__file__).resolve()
    files = []
    for item in folder.iterdir():
        if not item.is_file():
            continue
        if item.name.startswith(".") or item.name == LOG_NAME:
            continue
        if item.resolve() == script_path:
            continue
        files.append(item)
    return files


def organize(folder, by_date=False, dry_run=False):
    """Move files into category folders. Returns a dict of category -> count."""
    files = get_files_to_organize(folder)
    if not files:
        print("No files found to organize.")
        return {}

    moves = []
    counts = {}

    for file_path in files:
        category = get_category(file_path)
        target_dir = folder / category

        if by_date:
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            target_dir = target_dir / modified.strftime("%Y-%m")

        destination = unique_destination(target_dir / file_path.name)
        relative_dest = destination.relative_to(folder)
        print(f"  {file_path.name}  ->  {relative_dest}")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(destination))
            moves.append({"from": str(file_path), "to": str(destination)})

        counts[category] = counts.get(category, 0) + 1

    if not dry_run and moves:
        log_path = folder / LOG_NAME
        with log_path.open("w", encoding="utf-8") as f:
            json.dump(moves, f, indent=2)

    return counts


def undo(folder):
    """Move files back to where they came from, using the saved log."""
    log_path = folder / LOG_NAME
    if not log_path.exists():
        print("Nothing to undo (no log file found).")
        return

    with log_path.open("r", encoding="utf-8") as f:
        moves = json.load(f)

    restored = 0
    for move in reversed(moves):
        source = Path(move["to"])
        original = Path(move["from"])
        if not source.exists():
            print(f"  Skipped (missing): {source.name}")
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(unique_destination(original)))
        restored += 1

    log_path.unlink()
    print(f"Restored {restored} file(s).")


def print_summary(counts, dry_run):
    if not counts:
        return
    label = "Would organize" if dry_run else "Organized"
    total = sum(counts.values())
    print(f"\n{label} {total} file(s):")
    for category, count in sorted(counts.items()):
        print(f"  {category:<15} {count}")


def main():
    parser = argparse.ArgumentParser(description="Organize files into folders by type.")
    parser.add_argument(
        "folder",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="Folder to organize (default: your Downloads folder)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without moving any files")
    parser.add_argument("--by-date", action="store_true",
                        help="Also sort into YYYY-MM subfolders by modified date")
    parser.add_argument("--undo", action="store_true",
                        help="Undo the last organize run in this folder")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a valid folder.")
        sys.exit(1)

    print(f"Folder: {folder}")

    if args.undo:
        undo(folder)
        return

    if args.dry_run:
        print("DRY RUN: no files will be moved.\n")

    counts = organize(folder, by_date=args.by_date, dry_run=args.dry_run)
    print_summary(counts, args.dry_run)

    if counts and not args.dry_run:
        print("\nDone! Run with --undo to reverse this.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
