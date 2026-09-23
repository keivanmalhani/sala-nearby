#!/usr/bin/env python3
"""Cineteca ticket-link parser regression against the current public markup."""
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("refresh_cineteca", ROOT / "refresh-cineteca.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class SessionsTest(unittest.TestCase):
    def test_current_markup_from_all_three_sites(self):
        fixture = (ROOT / "fixtures/cineteca-sessions-2026-09-23.html").read_text()
        self.assertEqual(refresh.sessions_for(fixture, 2026), [
            ("002", "2026-09-23", "13:40", "52376"),
            ("001", "2026-09-23", "14:30", "14874"),
            ("003", "2026-09-24", "15:00", "49798"),
        ])

    def test_older_plain_time_and_unescaped_query(self):
        page = ("<a href='visSelectTickets.aspx?cinemacode=003&txtSessionId=12'>"
                "<div>Viernes 25 de Septiembre <br> 20:05 H</div></a>")
        self.assertEqual(refresh.sessions_for(page, 2026),
                         [("003", "2026-09-25", "20:05", "12")])

    def test_malformed_link_cannot_borrow_next_showing(self):
        page = ("<a href='visSelectTickets.aspx?cinemacode=003&amp;txtSessionId=12'>"
                "<div>Ticket information unavailable</div></a>"
                "<a href='visSelectTickets.aspx?cinemacode=002&amp;txtSessionId=34'>"
                "<div>Viernes 25 de Septiembre <br/> SALA 1 | <b>20:05 H</b></div></a>")
        self.assertEqual(refresh.sessions_for(page, 2026),
                         [("002", "2026-09-25", "20:05", "34")])

    def test_partial_detail_page_refuses_to_replace_published_board(self):
        good = (ROOT / "fixtures/cineteca-sessions-2026-09-23.html").read_text()
        broken = good + ("<a href='visSelectTickets.aspx?cinemacode=003&amp;"
                         "txtSessionId=999'><div>Time unavailable</div></a>")
        with tempfile.TemporaryDirectory() as temp:
            page = Path(temp) / "index.html"
            shutil.copyfile(ROOT / "docs/index.html", page)
            original = page.read_bytes()
            with (patch.object(refresh, "PAGE", str(page)),
                  patch.object(refresh, "fetch", side_effect=['{"html":"ignored"}', broken]),
                  patch.object(refresh, "film_cards", return_value=[
                      {"id": "HO00009798", "codes": ["002"], "title": "Test film", "meta": ""}]),
                  patch.object(sys, "argv", ["refresh-cineteca.py", "--dry-run"])):
                with self.assertRaisesRegex(SystemExit, "detail pages were incomplete"):
                    refresh.main()
            self.assertEqual(page.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
