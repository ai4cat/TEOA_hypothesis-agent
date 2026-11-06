"""Exercise the archived builder with synthetic PDFs; no research data or API."""
import json
from contextlib import closing
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


class BuildLibraryTest(unittest.TestCase):
    def test_index_deduplicates_and_preserves_page_grounding(self):
        builder = Path(__file__).resolve().parents[1] / 'engine/build_library.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source'
            source.mkdir()
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((72, 72), 'TEOA synthetic evidence for offline indexing.')
                pdf.save(source / 'one.pdf')
            shutil.copyfile(source / 'one.pdf', source / 'duplicate.pdf')
            command = [sys.executable, str(builder), '--source-dir', str(source),
                       '--output-dir', str(root / 'build')]
            subprocess.run(command, check=True, capture_output=True, text=True)
            report = json.loads((root / 'build/build_report.json').read_text())
            self.assertEqual(report['counts']['unique_pdfs'], 1)
            self.assertEqual(report['counts']['duplicate_files'], 1)
            self.assertEqual(report['counts']['parse_errors'], 0)
            with closing(sqlite3.connect(root / 'build/index.sqlite')) as db:
                self.assertEqual(db.execute('pragma integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('select count(*) from papers').fetchone()[0], 1)
                self.assertEqual(db.execute('select count(*) from provenance').fetchone()[0], 2)
                self.assertEqual(db.execute('select page from chunks').fetchone()[0], 1)
                self.assertIn('TEOA', db.execute('select text from chunks').fetchone()[0])
                self.assertEqual(db.execute("select count(*) from search where search match 'TEOA'").fetchone()[0], 1)
            before = (root / 'build/index.sqlite').read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(before, (root / 'build/index.sqlite').read_bytes())


if __name__ == '__main__':
    unittest.main()
