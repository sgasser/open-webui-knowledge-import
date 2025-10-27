"""Directory scanning functions."""

import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class KBData(TypedDict):
    """Knowledge base data structure."""
    path: Path
    files: list[Path]


def scan_directory(
    directory: Path,
    extensions: list[str] | None = None
) -> dict[str, KBData]:
    """Scan directory and return KB structure.

    Args:
        directory: Directory to scan for knowledge bases
        extensions: Optional list of file extensions to filter (e.g., [".pdf", ".txt"])

    Returns:
        Dict mapping KB names to their data (path and files list)

    Raises:
        ValueError: If directory doesn't exist

    Example:
        >>> structure = scan_directory(Path("/docs"))
        >>> for kb_name, data in structure.items():
        ...     print(f"{kb_name}: {len(data['files'])} files")
        sales: 10 files
        marketing: 15 files
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        logger.warning(f"Path is not a directory: {directory}")
        return {}

    logger.debug(f"Scanning directory: {directory}")

    # Check if this is a leaf directory (has files)
    files = [
        f for f in directory.iterdir()
        if f.is_file() and (not extensions or f.suffix in extensions)
    ]

    if files:
        # This directory contains files - it's a single KB
        logger.debug(f"Found {len(files)} files in {directory.name}")
        return {directory.name: {"path": directory, "files": files}}

    # This directory contains subdirectories - scan them
    results = {}
    for subdir in directory.iterdir():
        if subdir.is_dir():
            subdir_files = [
                f for f in subdir.iterdir()
                if f.is_file() and (not extensions or f.suffix in extensions)
            ]
            if subdir_files:
                logger.debug(f"Found {len(subdir_files)} files in {subdir.name}")
                results[subdir.name] = {"path": subdir, "files": subdir_files}

    logger.info(f"Found {len(results)} knowledge base directories")
    return results
