import logging
import re
import tempfile
import unittest
from pathlib import Path

import request_logger

LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO "
    r"(\S+) - (\S+) (\S+) - (\d{3}) - (\d+\.\d)ms$"
)


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log_file = Path(self.tmp.name) / "logs" / "server.log"
        request_logger.configure(self.log_file, console=False)

    def tearDown(self):
        logger = logging.getLogger(request_logger.LOGGER_NAME)
        for h in list(logger.handlers):
            logger.removeHandler(h)
            h.close()
        request_logger._configured = False
        self.tmp.cleanup()

    def lines(self):
        return self.log_file.read_text(encoding="utf-8").splitlines()

    def test_format_and_fields(self):
        request_logger.log_request("GET", "/", 200, "127.0.0.1", 0.0032)
        m = LINE.match(self.lines()[0])
        self.assertIsNotNone(m, self.lines()[0])
        self.assertEqual(m.group(1), "127.0.0.1")
        self.assertEqual(m.group(2), "GET")
        self.assertEqual(m.group(3), "/")
        self.assertEqual(m.group(4), "200")
        self.assertEqual(m.group(5), "3.2")

    def test_seconds_converted_to_ms(self):
        request_logger.log_request("GET", "/x", 404, "127.0.0.1", 1.5)
        self.assertTrue(self.lines()[0].endswith("- 404 - 1500.0ms"))

    def test_failures_are_logged(self):
        request_logger.log_request("POST", "/", 405, "127.0.0.1", 0.001)
        request_logger.log_request("GET", "/nope", 404, "127.0.0.1", 0.001)
        self.assertEqual(len(self.lines()), 2)
        self.assertIn(" INFO ", self.lines()[0])  # matches the plan's example format

    def test_level_is_info_for_all_statuses(self):
        request_logger.log_request("GET", "/", 200, "127.0.0.1", 0.001)
        self.assertIn(" INFO ", self.lines()[0])

    def test_newlines_cannot_forge_entries(self):
        request_logger.log_request("GET", "/a\r\nINFO fake - GET / - 200", 400, "127.0.0.1", 0.001)
        self.assertEqual(len(self.lines()), 1)

    def test_bad_duration_does_not_crash(self):
        request_logger.log_request("GET", "/", 200, "127.0.0.1", None)
        self.assertTrue(self.lines()[0].endswith("0.0ms"))


if __name__ == "__main__":
    unittest.main()
