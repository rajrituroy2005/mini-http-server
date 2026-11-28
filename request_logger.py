"""Request logging for the mini HTTP server (Person 3).

Interface (shared with server.py):
    log_request(method, path, status, client_ip, duration)

`duration` is in seconds (as measured by time.perf_counter() in server.py).
Each call writes one line to logs/server.log and to the console, e.g.:

    2026-11-23 14:10:03 INFO 127.0.0.1 - GET / - 200 - 3.2ms
"""
import logging
import pathlib
import threading

DEFAULT_LOG_FILE = pathlib.Path(__file__).resolve().parent / "logs" / "server.log"
LOGGER_NAME = "mini_http_server.requests"
_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_lock = threading.Lock()
_configured = False


def configure(log_file=None, console=True):
    """(Re)configure the request logger. Safe to call more than once."""
    global _configured
    with _lock:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

        formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)
        path = pathlib.Path(log_file) if log_file else DEFAULT_LOG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if console:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        _configured = True
        return logger


def _clean(value):
    """Keep each request on one log line (stops log injection via CR/LF)."""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def log_request(method, path, status, client_ip, duration):
    if not _configured:
        configure()
    try:
        duration_ms = float(duration) * 1000.0
    except (TypeError, ValueError):
        duration_ms = 0.0
    logging.getLogger(LOGGER_NAME).info(
        "%s - %s %s - %s - %.1fms",
        _clean(client_ip), _clean(method), _clean(path), status, duration_ms,
    )
