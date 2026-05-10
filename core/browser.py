import webbrowser
import logging
import time
import threading
import os

logger = logging.getLogger(__name__)

def open_browser(url: str, delay: float = 0.0):
    """Opens a browser to the specified URL, optionally after a delay."""
    if delay > 0:
        def _target():
            time.sleep(delay)
            _open(url)
        threading.Thread(target=_target, daemon=True).start()
    else:
        _open(url)

def _open(url: str):
    # Skip if running in a headless environment or Docker container
    if os.getenv("IN_DOCKER") == "true" or os.getenv("HEADLESS") == "true":
        logger.info(f"Skipping browser open to {url} (headless/Docker environment detected).")
        return

    try:
        logger.info(f"Opening browser to {url}...")
        webbrowser.open(url)
    except Exception:
        logger.exception(f"Failed to open browser to {url}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        _open(sys.argv[1])