"""Session management with retry logic."""

import logging
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import MAX_RETRIES, RETRY_BACKOFF_FACTOR, RETRY_STATUS_CODES, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def validate_url(url: str) -> None:
    """Validate URL format.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL is invalid

    Example:
        >>> validate_url("http://localhost:8080")
        >>> validate_url("not-a-url")  # raises ValueError
    """
    if not url:
        raise ValueError("URL cannot be empty")

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError(f"Invalid URL format: {url}")
        if result.scheme not in ["http", "https"]:
            raise ValueError(f"URL must use http or https scheme: {url}")
    except Exception as e:
        raise ValueError(f"Invalid URL: {url} - {e}")


def validate_api_key(api_key: str) -> None:
    """Validate API key format.

    Args:
        api_key: API key to validate

    Raises:
        ValueError: If API key is invalid

    Example:
        >>> validate_api_key("sk-abc123")
        >>> validate_api_key("")  # raises ValueError
    """
    if not api_key:
        raise ValueError("API key cannot be empty")
    if not api_key.startswith("sk-"):
        raise ValueError("API key must start with 'sk-'")
    if len(api_key) < 10:
        raise ValueError("API key is too short")


@contextmanager
def create_session(base_url: str, api_key: str) -> Generator[requests.Session, None, None]:
    """Create authenticated session with retry logic.

    Args:
        base_url: Open WebUI base URL (e.g., http://localhost:8080)
        api_key: Open WebUI API key (starts with sk-)

    Yields:
        Authenticated requests.Session with retry logic configured

    Raises:
        ValueError: If base_url or api_key are invalid
        ConnectionError: If authentication fails

    Example:
        >>> with create_session("http://localhost:8080", "sk-abc123") as session:
        ...     response = session.get("/api/v1/models")
    """
    # Validate inputs
    validate_url(base_url)
    validate_api_key(api_key)

    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET", "POST", "DELETE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set authentication
    session.headers["Authorization"] = f"Bearer {api_key}"

    try:
        # Authenticate
        logger.debug(f"Authenticating with {base_url}")
        response = session.get(f"{base_url}/api/v1/auths/", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        user = response.json()
        logger.info(f"Authenticated as {user.get('name', 'Unknown')}")

        yield session

    except requests.HTTPError as e:
        logger.error(f"Authentication failed: HTTP {e.response.status_code}")
        if e.response.status_code == 401:
            raise ConnectionError(f"Authentication failed: Invalid API key")
        raise ConnectionError(f"Authentication failed: {e}")
    except requests.RequestException as e:
        logger.error(f"Authentication failed: {e}")
        raise ConnectionError(f"Cannot connect to {base_url}: {e}")
    finally:
        session.close()
        logger.debug("Session closed")


def health_check(base_url: str, api_key: str) -> bool:
    """Check if Open WebUI API is healthy.

    Args:
        base_url: Open WebUI base URL
        api_key: Open WebUI API key

    Returns:
        True if healthy

    Raises:
        ValueError: If base_url or api_key are invalid
        ConnectionError: If health check fails

    Example:
        >>> health_check("http://localhost:8080", "sk-abc123")
        True
    """
    # Validate inputs
    validate_url(base_url)
    validate_api_key(api_key)

    logger.debug(f"Performing health check on {base_url}")
    try:
        response = requests.get(
            f"{base_url}/api/v1/auths/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        logger.info("Health check passed")
        return True
    except requests.HTTPError as e:
        logger.error(f"Health check failed: HTTP {e.response.status_code}")
        if e.response.status_code == 401:
            raise ConnectionError(f"Health check failed: Invalid API key")
        raise ConnectionError(f"Health check failed: HTTP {e.response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Health check failed: {e}")
        raise ConnectionError(f"Cannot connect to {base_url}: {e}")
