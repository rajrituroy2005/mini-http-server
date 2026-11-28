import http.client
import logging
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import config
import request_logger
import server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name) / "www"
        root.mkdir()
        (root / "index.html").write_text("<h1>home</h1>")
        (root / "about.html").write_text("<h1>about</h1>")
        (root / "404.html").write_text("<h1>not found</h1>")
        (root / "style.css").write_text("body{}")
        (Path(cls.tmp.name) / "config_copy.py").write_text("SECRET=1")
        cls._old_root = config.WEB_ROOT
        config.WEB_ROOT = str(root)

        cls.log_file = Path(cls.tmp.name) / "server.log"
        request_logger.configure(cls.log_file, console=False)

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        logger = logging.getLogger(request_logger.LOGGER_NAME)
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()
        request_logger._configured = False
        config.WEB_ROOT = cls._old_root
        cls.tmp.cleanup()

    def request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path)
        resp = conn.getresponse()
        body = resp.read()
        headers = dict(resp.getheaders())
        conn.close()
        return resp.status, headers, body

    def log_lines(self):
        return self.log_file.read_text(encoding="utf-8").splitlines()

    def test_get_root(self):
        status, h, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"home", body)
        self.assertEqual(int(h["Content-Length"]), len(body))

    def test_get_about(self):
        self.assertEqual(self.request("GET", "/about.html")[0], 200)

    def test_get_css_mime(self):
        status, h, _ = self.request("GET", "/style.css")
        self.assertEqual(status, 200)
        self.assertEqual(h["Content-Type"], "text/css")

    def test_missing_404(self):
        self.assertEqual(self.request("GET", "/missing.html")[0], 404)

    def test_post_405(self):
        status, h, _ = self.request("POST", "/")
        self.assertEqual(status, 405)
        self.assertEqual(h["Allow"], "GET, HEAD")

    def test_other_methods_405(self):
        for m in ("PUT", "DELETE", "PATCH"):
            self.assertEqual(self.request(m, "/")[0], 405, m)

    def test_path_traversal_rejected(self):
        status, _, body = self.request("GET", "/../config.py")
        self.assertNotEqual(status, 200)
        self.assertNotIn(b"HOST", body)

    def test_head_has_no_body(self):
        status, h, body = self.request("HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(h["Content-Length"]), 0)

    def test_bad_request_400(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.putrequest("GET", "no-slash", skip_host=False)
        conn.endheaders()
        resp = conn.getresponse()
        resp.read()
        conn.close()
        self.assertEqual(resp.status, 400)

    def wait_for_lines(self, count, timeout=2.0):
        # The server logs just after sending the response, so poll briefly.
        deadline = time.time() + timeout
        while time.time() < deadline:
            lines = self.log_lines()
            if len(lines) >= count:
                return lines
            time.sleep(0.02)
        return self.log_lines()

    def test_every_request_is_logged_including_failures(self):
        time.sleep(0.2)  # let trailing log lines from earlier tests land
        before = len(self.log_lines())
        self.request("GET", "/")
        self.request("GET", "/missing.html")
        self.request("POST", "/")
        new = self.wait_for_lines(before + 3)[before:]
        self.assertEqual(len(new), 3)
        # Each connection runs in its own thread, so order is not guaranteed.
        for expected in ("GET / - 200", "GET /missing.html - 404", "POST / - 405"):
            self.assertTrue(any(expected in line for line in new), expected)
        for line in new:
            self.assertIn("127.0.0.1", line)
            self.assertTrue(line.endswith("ms"))


if __name__ == "__main__":
    unittest.main()
