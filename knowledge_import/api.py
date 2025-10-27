"""Open WebUI API operations."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional, TypedDict

import requests

from .config import (
    PROCESSING_TIMEOUT_SECONDS,
    PROCESSING_CHECK_INTERVAL,
    REQUEST_TIMEOUT,
    MAX_CONCURRENT_UPLOADS,
)

logger = logging.getLogger(__name__)


class UploadResult(TypedDict):
    """Result of file upload operation."""
    file_id: Optional[str]
    success: bool
    error: Optional[str]
    processing_time: float


def upload_file(
    session: requests.Session,
    base_url: str,
    file_path: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> UploadResult:
    """Upload file and wait for processing.

    Args:
        session: Authenticated requests session
        base_url: Open WebUI base URL
        file_path: Path to file to upload
        progress_callback: Optional callback for progress updates (e.g., print)

    Returns:
        UploadResult dict with file_id, success, error, and processing_time

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be read

    Example:
        >>> result = upload_file(session, "http://localhost:8080", Path("doc.pdf"))
        >>> print(result["file_id"])
        'file-abc123'
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    start_time = time.time()
    logger.debug(f"Uploading {file_path.name}")

    if progress_callback:
        progress_callback(f"  ⬆ Uploading {file_path.name}...")

    try:
        # Upload file
        with file_path.open("rb") as f:
            response = session.post(
                f"{base_url}/api/v1/files/",
                files={"file": f},
                timeout=REQUEST_TIMEOUT
            )
        response.raise_for_status()
        file_id = response.json()["id"]
        logger.debug(f"File uploaded with ID: {file_id}")

        # Wait for processing
        timeout_iterations = PROCESSING_TIMEOUT_SECONDS // PROCESSING_CHECK_INTERVAL
        for i in range(timeout_iterations):
            time.sleep(PROCESSING_CHECK_INTERVAL)
            status_resp = session.get(
                f"{base_url}/api/v1/files/{file_id}",
                timeout=REQUEST_TIMEOUT
            )
            if status_resp.ok:
                file_data = status_resp.json()
                if file_data.get("data", {}).get("status") == "completed":
                    elapsed = time.time() - start_time
                    logger.info(f"File {file_path.name} processed in {elapsed:.1f}s")
                    if progress_callback:
                        progress_callback(f"✓ ({elapsed:.1f}s)")
                    return {
                        "file_id": file_id,
                        "success": True,
                        "error": None,
                        "processing_time": elapsed
                    }

        # Timeout
        elapsed = time.time() - start_time
        logger.warning(f"File {file_path.name} processing timeout after {elapsed:.1f}s")
        if progress_callback:
            progress_callback(f"⚠ timeout ({elapsed:.1f}s)")
        return {
            "file_id": file_id,
            "success": True,  # Still return ID
            "error": "Processing timeout",
            "processing_time": elapsed
        }

    except requests.HTTPError as e:
        elapsed = time.time() - start_time
        error_msg = f"HTTP {e.response.status_code}: {e}"
        logger.error(f"Upload failed for {file_path.name}: {error_msg}")
        if progress_callback:
            progress_callback(f"✗ {error_msg}")
        return {
            "file_id": None,
            "success": False,
            "error": error_msg,
            "processing_time": elapsed
        }
    except requests.RequestException as e:
        elapsed = time.time() - start_time
        error_msg = f"Network error: {e}"
        logger.error(f"Upload failed for {file_path.name}: {error_msg}")
        if progress_callback:
            progress_callback(f"✗ {error_msg}")
        return {
            "file_id": None,
            "success": False,
            "error": error_msg,
            "processing_time": elapsed
        }


def upload_files_concurrent(
    session: requests.Session,
    base_url: str,
    file_paths: list[Path],
    progress_callback: Optional[Callable[[str], None]] = None
) -> list[UploadResult]:
    """Upload multiple files concurrently.

    Args:
        session: Authenticated requests session
        base_url: Open WebUI base URL
        file_paths: List of file paths to upload
        progress_callback: Optional callback for progress updates

    Returns:
        List of UploadResult dicts

    Example:
        >>> results = upload_files_concurrent(session, url, [Path("a.pdf"), Path("b.pdf")])
        >>> successful = [r for r in results if r["success"]]
        >>> print(f"Uploaded {len(successful)} files")
    """
    logger.info(f"Uploading {len(file_paths)} files concurrently (max {MAX_CONCURRENT_UPLOADS} workers)")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPLOADS) as executor:
        future_to_file = {
            executor.submit(upload_file, session, base_url, fp, progress_callback): fp
            for fp in file_paths
        }
        for future in as_completed(future_to_file):
            results.append(future.result())

    return results


def get_existing_kb(session: requests.Session, base_url: str, name: str) -> Optional[str]:
    """Check if knowledge base with name already exists.

    Args:
        session: Authenticated requests session
        base_url: Open WebUI base URL
        name: Knowledge base name to check

    Returns:
        KB ID if exists, None otherwise

    Example:
        >>> kb_id = get_existing_kb(session, url, "My Documents")
        >>> if kb_id:
        ...     print(f"KB already exists: {kb_id}")
    """
    logger.debug(f"Checking if KB '{name}' already exists")
    try:
        response = session.get(
            f"{base_url}/api/v1/knowledge/",
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        knowledge_bases = response.json()

        # Search for KB with matching name
        for kb in knowledge_bases:
            if kb.get("name") == name:
                kb_id = kb.get("id")
                logger.info(f"Found existing KB '{name}' with ID: {kb_id}")
                return kb_id

        return None
    except requests.RequestException as e:
        logger.warning(f"Could not check existing KBs: {e}")
        return None


def create_kb(session: requests.Session, base_url: str, name: str) -> str:
    """Create knowledge base.

    Args:
        session: Authenticated requests session
        base_url: Open WebUI base URL
        name: Name for the knowledge base

    Returns:
        Knowledge base ID

    Raises:
        ValueError: If name is empty
        ConnectionError: If KB creation fails

    Example:
        >>> kb_id = create_kb(session, "http://localhost:8080", "My Documents")
        >>> print(kb_id)
        'kb-abc123'
    """
    if not name or not name.strip():
        raise ValueError("Knowledge base name cannot be empty")

    logger.debug(f"Creating knowledge base: {name}")
    try:
        response = session.post(
            f"{base_url}/api/v1/knowledge/create",
            json={"name": name, "description": f"Knowledge base for {name}", "data": {}},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        kb_id = response.json()["id"]
        logger.info(f"Created knowledge base '{name}' with ID: {kb_id}")
        return kb_id
    except requests.HTTPError as e:
        logger.error(f"Failed to create KB '{name}': HTTP {e.response.status_code}")
        raise ConnectionError(f"Failed to create KB '{name}': HTTP {e.response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Failed to create KB '{name}': {e}")
        raise ConnectionError(f"Failed to create KB '{name}': {e}")


def add_files_to_kb(session: requests.Session, base_url: str, kb_id: str, file_ids: list[str]) -> None:
    """Add files to knowledge base.

    Args:
        session: Authenticated requests session
        base_url: Open WebUI base URL
        kb_id: Knowledge base ID
        file_ids: List of file IDs to add

    Raises:
        ValueError: If kb_id or file_ids are invalid
        ConnectionError: If adding files fails

    Example:
        >>> add_files_to_kb(session, url, "kb-123", ["file-1", "file-2"])
    """
    if not kb_id:
        raise ValueError("Knowledge base ID cannot be empty")
    if not file_ids:
        raise ValueError("File IDs list cannot be empty")

    logger.debug(f"Adding {len(file_ids)} files to KB {kb_id}")
    try:
        for file_id in file_ids:
            response = session.post(
                f"{base_url}/api/v1/knowledge/{kb_id}/file/add",
                json={"file_id": file_id},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
        logger.info(f"Added {len(file_ids)} files to KB {kb_id}")
    except requests.HTTPError as e:
        logger.error(f"Failed to add files to KB: HTTP {e.response.status_code}")
        raise ConnectionError(f"Failed to add files to KB: HTTP {e.response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Failed to add files to KB: {e}")
        raise ConnectionError(f"Failed to add files: {e}")
