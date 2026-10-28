"""
Unit tests for event protocol formatting using unittest.
"""
import io
import json
import sys
import unittest
from helper.utils import events


class TestEvents(unittest.TestCase):
    def test_emit_event(self):
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            events.emit_started(job="abc1", engine="libreoffice")
            events.emit_progress(job="abc1", percent=45, stage="Rendering")
            events.emit_done(job="abc1", output="/tmp/test.pdf")
            events.emit_error(job="abc1", code="NO_ENGINE", message="Not found")

            output = sys.stdout.getvalue().strip().split("\n")
            self.assertEqual(len(output), 4)

            line0 = json.loads(output[0])
            self.assertEqual(line0["event"], "started")
            self.assertEqual(line0["engine"], "libreoffice")

            line1 = json.loads(output[1])
            self.assertEqual(line1["event"], "progress")
            self.assertEqual(line1["percent"], 45)

            line2 = json.loads(output[2])
            self.assertEqual(line2["event"], "done")
            self.assertEqual(line2["output"], "/tmp/test.pdf")

            line3 = json.loads(output[3])
            self.assertEqual(line3["event"], "error")
            self.assertEqual(line3["code"], "NO_ENGINE")
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
