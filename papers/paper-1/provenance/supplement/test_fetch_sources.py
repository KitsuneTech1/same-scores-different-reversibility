import json
import tempfile
import unittest
from pathlib import Path

from audit import source_identity


class FetchSourcesTests(unittest.TestCase):
    def test_validate_blob_requires_source_receipt_and_emitted_identity(self):
        from fetch_sources import ValidationError, validate_blob

        body = b"example,csv\n"
        identity = source_identity(body)
        source = {"id": "sample", "git_blob_sha1": identity["git_blob_sha1"]}
        receipt = {"id": "sample", "identity": identity}
        emitted = {"identity": identity}

        self.assertEqual(validate_blob(source, receipt, emitted, body), identity)
        with self.assertRaises(ValidationError):
            validate_blob(source, receipt, {"identity": {"sha256": "wrong"}}, body)

    def test_missing_cache_fetches_once_after_validation(self):
        from fetch_sources import fetch_source

        body = b"example,csv\n"
        identity = source_identity(body)
        source = {"id": "sample", "ref": "abc", "path": "data/sample.csv",
                  "git_blob_sha1": identity["git_blob_sha1"]}
        receipt = {"id": "sample", "identity": identity}
        emitted = {"identity": identity}
        calls = []

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fetcher(url, timeout):
                calls.append((url, timeout))
                return body

            action = fetch_source(root, source, receipt, emitted, fetcher)

            self.assertEqual(action, "fetched")
            self.assertEqual((root / ".cache" / "sample.csv").read_bytes(), body)
            self.assertEqual(len(calls), 1)

    def test_existing_cache_is_validated_without_fetch_or_overwrite(self):
        from fetch_sources import ValidationError, fetch_source

        original, replacement = b"original\n", b"replacement\n"
        identity = source_identity(original)
        source = {"id": "sample", "ref": "abc", "path": "data/sample.csv",
                  "git_blob_sha1": identity["git_blob_sha1"]}
        receipt = {"id": "sample", "identity": identity}
        emitted = {"identity": identity}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".cache").mkdir()
            path = root / ".cache" / "sample.csv"
            path.write_bytes(replacement)

            with self.assertRaises(ValidationError):
                fetch_source(root, source, receipt, emitted, lambda *_: original)
            self.assertEqual(path.read_bytes(), replacement)

