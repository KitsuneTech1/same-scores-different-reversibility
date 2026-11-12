import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def raw_cache_available():
    try:
        acquisition = json.loads((ROOT / "acquisition.json").read_text())
        plan = json.loads((ROOT / "analysis-plan.json").read_text())
        sources = acquisition["forecasts"] + acquisition["truths"] + [plan["outcome_source"]]
        return all((ROOT / ".cache" / (source["id"] + ".csv")).is_file() for source in sources)
    except (OSError, KeyError, json.JSONDecodeError):
        return False


RAW_CACHE_AVAILABLE = raw_cache_available()


class ReplayTests(unittest.TestCase):
    def test_current_artifacts_verify_offline(self):
        from replay import verify

        summary = verify(ROOT)

        self.assertEqual(summary["link_errors"], [])
        self.assertEqual(summary["group_errors"], [])
        self.assertEqual(summary["source_hash_errors"], [])

    @unittest.skipUnless(RAW_CACHE_AVAILABLE, "optional raw integration: run fetch_sources.py first")
    def test_current_cache_verifies_when_requested(self):
        from replay import verify

        summary = verify(ROOT, verify_raw=True)

        self.assertEqual(summary["raw_errors"], [])

    def test_outcome_source_mismatch_is_rejected(self):
        from replay import VerificationError, verify

        with tempfile.TemporaryDirectory() as directory:
            replica = Path(directory)
            for path in ROOT.glob("*.json"):
                shutil.copy2(path, replica / path.name)
            for name in json.loads((ROOT / "results.json").read_text())["source_hashes"]:
                shutil.copy2(ROOT / name, replica / name)
            outcome = json.loads((replica / "outcome.json").read_text())
            outcome["source"]["id"] = "tampered-outcome"
            (replica / "outcome.json").write_text(json.dumps(outcome))

            with self.assertRaises(VerificationError):
                verify(replica)

    def test_removed_group_is_rejected(self):
        from replay import VerificationError, verify

        with tempfile.TemporaryDirectory() as directory:
            replica = self._replica(directory)
            results = json.loads((replica / "results.json").read_text())
            results["groups"].pop("common_support")
            (replica / "results.json").write_text(json.dumps(results))

            with self.assertRaises(VerificationError):
                verify(replica)

    def test_modified_redundant_forecast_vector_is_rejected(self):
        from replay import VerificationError, verify

        with tempfile.TemporaryDirectory() as directory:
            replica = self._replica(directory)
            results = json.loads((replica / "results.json").read_text())
            results["groups"]["primary"]["forecasts"]["CU-select"][0] = "0"
            (replica / "results.json").write_text(json.dumps(results))

            with self.assertRaises(VerificationError):
                verify(replica)

    def test_modified_group_weeks_are_rejected(self):
        from replay import VerificationError, verify

        with tempfile.TemporaryDirectory() as directory:
            replica = self._replica(directory)
            results = json.loads((replica / "results.json").read_text())
            results["groups"]["common_support"]["weeks"] = ["2020-11-14"]
            (replica / "results.json").write_text(json.dumps(results))

            with self.assertRaises(VerificationError):
                verify(replica)

    def test_raw_emitted_identity_mismatch_is_rejected(self):
        from audit import source_identity, weekly_values
        from replay import raw_errors

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".cache").mkdir()
            (root / "access").mkdir()
            weeks = ["2020-01-04"]
            body = ("date,location,value\n2020-01-04,US,1\n2020-01-03,US,1\n"
                    "2020-01-02,US,1\n2020-01-01,US,1\n2019-12-31,US,1\n"
                    "2019-12-30,US,1\n2019-12-29,US,1\n").encode()
            source = {"id": "truth", "git_blob_sha1": source_identity(body)["git_blob_sha1"]}
            (root / ".cache" / "truth.csv").write_bytes(body)
            (root / "access" / "truth.json").write_text(json.dumps({"id": "truth", "identity": source_identity(body)}))
            emitted = {"id": "truth", "identity": {"sha256": "wrong"},
                       "weeks": weekly_values(body.decode(), weeks)}
            errors = raw_errors(root, {"forecasts": [], "truths": [source], "weeks": weeks},
                                {"forecasts": [], "truths": [emitted]}, emitted,
                                {"outcome_source": source})

            self.assertTrue(errors)

    @staticmethod
    def _replica(directory):
        replica = Path(directory)
        for path in ROOT.glob("*.json"):
            shutil.copy2(path, replica / path.name)
        for name in json.loads((ROOT / "results.json").read_text())["source_hashes"]:
            shutil.copy2(ROOT / name, replica / name)
        return replica
