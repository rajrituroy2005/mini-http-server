import pathlib
import mimetypes
import urllib.parse
import config


def get_file_response(path: str):
    """Return HTTP status, content type, and body bytes for the requested *path*.

    The function:
    * Strips the query string using ``urllib.parse.urlsplit``.
    * Maps ``/`` or any directory request to ``index.html``.
    * Resolves the file against ``config.WEB_ROOT`` and blocks any path traversal.
    * Uses ``mimetypes.guess_type`` to determine the ``Content-Type`` header.
    * Returns a ``404`` response with ``www/404.html`` when the file is missing.
    """
    # Strip query and fragment
    clean_path = urllib.parse.urlsplit(path).path
    # Map root or directory to index.html
    if clean_path == "/" or clean_path.endswith("/"):
        clean_path = clean_path.rstrip("/") + "/index.html"
    # Build absolute path within the web root
    relative_path = pathlib.Path(config.WEB_ROOT) / clean_path.lstrip("/")
    # Resolve and ensure it stays inside the web root
    try:
        resolved = relative_path.resolve()
        web_root_resolved = pathlib.Path(config.WEB_ROOT).resolve()
        if not resolved.is_relative_to(web_root_resolved):
            raise FileNotFoundError
    except Exception:
        # Path traversal or other error – treat as missing
        return _serve_404()
    # If the path points to a directory (shouldn't happen after mapping), serve index.html inside it
    if resolved.is_dir():
        resolved = resolved / "index.html"
    # Serve the file if it exists
    if resolved.is_file():
        content_type, _ = mimetypes.guess_type(str(resolved))
        if content_type is None:
            content_type = "application/octet-stream"
        body = resolved.read_bytes()
        return 200, content_type, body
    # File missing – serve 404 page
    return _serve_404()


def _serve_404():
    """Helper to load the 404 page from the web root.

    Returns a tuple ``(404, "text/html", body_bytes)``. If the custom 404
    page does not exist, a minimal fallback HTML is used.
    """
    web_root = pathlib.Path(config.WEB_ROOT).resolve()
    not_found_path = web_root / "404.html"
    if not_found_path.is_file():
        body = not_found_path.read_bytes()
        content_type = "text/html"
    else:
        body = b"<html><body><h1>404 Not Found</h1></body></html>"
        content_type = "text/html"
    return 404, content_type, body
