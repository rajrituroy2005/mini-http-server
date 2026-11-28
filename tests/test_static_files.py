import tempfile
import unittest
from pathlib import Path

import config
import static_files


class StaticFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name) / "www"
        root.mkdir()
        (root / "index.html").write_text("<h1>home</h1>")
        (root / "about.html").write_text("<h1>about</h1>")
        (root / "404.html").write_text("<h1>nf</h1>")
        (root / "style.css").write_text("body{}")
        (root / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (Path(self.tmp.name) / "secret.txt").write_text("secret")
        self._old = config.WEB_ROOT
        config.WEB_ROOT = str(root)

    def tearDown(self):
        config.WEB_ROOT = self._old
        self.tmp.cleanup()

    def test_root_serves_index(self):
        status, ctype, body = static_files.get_file_response("/")
        self.assertEqual(status, 200)
        self.assertTrue(ctype.startswith("text/html"))
        self.assertIn(b"home", body)

    def test_html_and_css_mime(self):
        self.assertTrue(static_files.get_file_response("/about.html")[1].startswith("text/html"))
        self.assertEqual(static_files.get_file_response("/style.css")[1], "text/css")

    def test_image_returns_bytes(self):
        status, ctype, body = static_files.get_file_response("/pic.png")
        self.assertEqual((status, ctype), (200, "image/png"))
        self.assertIsInstance(body, bytes)

    def test_missing_is_404(self):
        status, _, body = static_files.get_file_response("/missing.html")
        self.assertEqual(status, 404)
        self.assertIn(b"nf", body)

    def test_query_string_ignored(self):
        self.assertEqual(static_files.get_file_response("/about.html?x=1")[0], 200)

    def test_path_traversal_blocked(self):
        for p in ("/../secret.txt", "/../../etc/passwd", "/..%2fsecret.txt", "/%2e%2e/secret.txt"):
            status, _, body = static_files.get_file_response(p)
            self.assertNotEqual(status, 200, p)
            self.assertNotIn(b"secret", body, p)


if __name__ == "__main__":
    unittest.main()
