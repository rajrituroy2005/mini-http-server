import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import config
from static_files import get_file_response
from request_logger import log_request


class Handler(BaseHTTPRequestHandler):
    server_version = "MiniHTTP/1.0"

    def _send(self, status, content_type, body, head_only=False, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

        start = getattr(self, "_start", time.perf_counter())
        duration = time.perf_counter() - start
        log_request(
            self.command or "-",
            getattr(self, "path", "-"),
            status,
            self.client_address[0],
            duration,
        )

    def _send_error_page(self, status, message, extra_headers=None):
        body = (
            f"<html><body><h1>{status} {message}</h1></body></html>"
        ).encode("utf-8")
        self._send(
            status,
            "text/html; charset=utf-8",
            body,
            head_only=(self.command == "HEAD"),
            extra_headers=extra_headers,
        )

    def _handle(self, head_only):
        if not self.path.startswith("/"):
            self._send_error_page(400, "Bad Request")
            return
        path = urlsplit(self.path).path
        status, content_type, body = get_file_response(path)
        self._send(status, content_type, body, head_only)

    def _method_not_allowed(self):
        self._send_error_page(
            405, "Method Not Allowed", extra_headers={"Allow": "GET, HEAD"}
        )

    def parse_request(self):
        self._start = time.perf_counter()
        return super().parse_request()

    def log_message(self, format, *args):
        pass
    def do_GET(self):
        self._handle(head_only=False)

    def do_HEAD(self):
        self._handle(head_only=True)

    def do_POST(self):
        self._method_not_allowed()

    def do_PUT(self):
        self._method_not_allowed()

    def do_DELETE(self):
        self._method_not_allowed()

    def do_PATCH(self):
        self._method_not_allowed()

    def send_error(self, code, message=None, explain=None):
        self._send_error_page(code, message or self.responses[code][0])

    def do_OPTIONS(self):
        self._method_not_allowed()

    def do_TRACE(self):
        self._method_not_allowed()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else config.PORT
    server = ThreadingHTTPServer((config.HOST, port), Handler)
    print(f"Serving on http://{config.HOST}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()