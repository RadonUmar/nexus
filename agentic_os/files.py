from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .settings import settings


@dataclass
class FileMatch:
    path: str
    match_type: str
    line_count: int = 0
    sample_lines: Optional[List[int]] = None


@dataclass
class ReadFileResult:
    path: str
    content: str
    size: int
    lines: int


DATA_DIR = settings.data_dir


def resolve_data_path(path: str) -> Path:
    safe_path = Path(path)
    target = (DATA_DIR / safe_path).resolve()
    target.relative_to(DATA_DIR.resolve())
    return target


def ensure_desktop_path(path: Path) -> Path:
    if not str(path).startswith("Desktop/"):
        return Path("Desktop") / path
    return path


def list_files(path: str = "") -> List[Dict[str, Any]]:
    target_dir = resolve_data_path(path) if path else DATA_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError("Directory not found")

    items: List[Dict[str, Any]] = []
    for item in sorted(target_dir.iterdir()):
        if item.name.startswith('.'):
            continue
        items.append(
            {
                "name": item.name,
                "path": str(item.relative_to(DATA_DIR)),
                "type": "folder" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": item.stat().st_mtime,
            }
        )
    return items


def read_text_file(path: str) -> str:
    target_file = resolve_data_path(path)
    if not target_file.exists() or not target_file.is_file():
        raise FileNotFoundError("File not found")
    return target_file.read_text(encoding="utf-8")


def write_text_file(path: str, content: str) -> None:
    target_file = resolve_data_path(path)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")


def create_file(path: str, content: str) -> Path:
    safe_path = ensure_desktop_path(Path(path))
    target_file = resolve_data_path(str(safe_path))
    if target_file.exists():
        raise FileExistsError("File already exists")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    return safe_path


def create_folder(path: str) -> Path:
    safe_path = ensure_desktop_path(Path(path))
    target_folder = resolve_data_path(str(safe_path))
    if target_folder.exists():
        raise FileExistsError("Folder already exists")
    target_folder.mkdir(parents=True, exist_ok=True)
    return safe_path


def delete_item(path: str) -> None:
    target_item = resolve_data_path(path)
    if not target_item.exists():
        raise FileNotFoundError("Item not found")
    if target_item.is_file():
        target_item.unlink()
    else:
        import shutil

        shutil.rmtree(target_item)


def get_available_files(limit: int = 20) -> List[Dict[str, str]]:
    files = []
    for root, _, filenames in os.walk(DATA_DIR):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), DATA_DIR)
            files.append({"name": filename, "path": rel_path.replace(os.sep, "/")})
            if len(files) >= limit:
                return files
    return files


def _collect_files() -> List[Dict[str, str]]:
    all_files = []
    for root, _, filenames in os.walk(DATA_DIR):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, DATA_DIR)
            all_files.append({"path": rel_path.replace(os.sep, "/"), "full_path": full_path})
    return all_files


def find_files(pattern: str, search_content: bool = True) -> List[FileMatch]:
    if not pattern:
        return []

    pattern_lower = pattern.lower()
    pattern_words = pattern_lower.split()

    all_files = _collect_files()
    found_by_name: List[FileMatch] = []
    found_by_content: List[FileMatch] = []

    for file_info in all_files:
        path_lower = file_info["path"].lower()
        if pattern_lower in path_lower or (
            len(pattern_words) > 1 and all(word in path_lower for word in pattern_words)
        ):
            found_by_name.append(FileMatch(path=file_info["path"], match_type="filename"))

    if search_content:
        def search_file_content(file_info: Dict[str, str]) -> Optional[FileMatch]:
            try:
                with open(file_info["full_path"], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    content_lower = content.lower()

                matches_pattern = pattern_lower in content_lower
                matches_words = len(pattern_words) > 1 and all(word in content_lower for word in pattern_words)

                if matches_pattern or matches_words:
                    lines = content.split("\n")
                    matching_lines = []
                    for i, line in enumerate(lines, 1):
                        line_lower = line.lower()
                        if pattern_lower in line_lower or (
                            len(pattern_words) > 1 and all(word in line_lower for word in pattern_words)
                        ):
                            matching_lines.append(i)
                    return FileMatch(
                        path=file_info["path"],
                        match_type="content",
                        line_count=len(matching_lines),
                        sample_lines=matching_lines[:3],
                    )
            except Exception:
                return None
            return None

        found_name_paths = {f.path for f in found_by_name}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(search_file_content, file_info): file_info
                for file_info in all_files
                if file_info["path"] not in found_name_paths
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found_by_content.append(result)

    found_files: List[FileMatch] = list(found_by_name)
    found_paths = {f.path for f in found_by_name}
    for content_match in found_by_content:
        if content_match.path not in found_paths:
            found_files.append(content_match)

    return found_files


def read_files(paths: List[str]) -> List[ReadFileResult]:
    results: List[ReadFileResult] = []
    for file_path in paths:
        target_file = resolve_data_path(file_path)
        if not target_file.exists() or not target_file.is_file():
            continue
        content = target_file.read_text(encoding="utf-8", errors="ignore")
        results.append(
            ReadFileResult(
                path=file_path,
                content=content,
                size=len(content),
                lines=len(content.split("\n")),
            )
        )
    return results
