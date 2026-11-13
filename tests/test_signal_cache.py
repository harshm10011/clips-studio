"""Analysis signal caches remain source-aware and safe to re-use."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.signal_cache import load_or_extract
from core.housekeeping import survey


class SignalCacheTests(unittest.TestCase):
    def test_reuses_completed_signals_for_an_unchanged_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            source.write_bytes(b"source")
            cache_dir = root / "transcripts"
            calls = {"audio": 0, "visual": 0}

            def audio(_path):
                calls["audio"] += 1
                return {"loudness": np.asarray([0.2, 0.5], dtype=np.float32)}

            def visual(_path):
                calls["visual"] += 1
                return {"motion": np.asarray([0.1, 0.3], dtype=np.float32)}

            first = load_or_extract(source, "video_1", cache_dir, audio, visual)
            second = load_or_extract(
                source,
                "video_1",
                cache_dir,
                lambda _path: self.fail("audio extractor should use the cache"),
                lambda _path: self.fail("visual extractor should use the cache"),
            )

            self.assertEqual(calls, {"audio": 1, "visual": 1})
            np.testing.assert_array_equal(first[0]["loudness"], second[0]["loudness"])
            np.testing.assert_array_equal(first[1]["motion"], second[1]["motion"])

    def test_invalidates_cache_when_source_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            source.write_bytes(b"first")
            cache_dir = root / "transcripts"
            calls = 0

            def audio(_path):
                nonlocal calls
                calls += 1
                return {"loudness": np.asarray([calls], dtype=np.float32)}

            visual = lambda _path: {}
            load_or_extract(source, "video_1", cache_dir, audio, visual)
            source.write_bytes(b"second source")
            result = load_or_extract(source, "video_1", cache_dir, audio, visual)
            self.assertEqual(calls, 2)
            self.assertEqual(float(result[0]["loudness"][0]), 2.0)

    def test_storage_cleanup_only_marks_orphan_signal_caches(self):
        class DB:
            class Connection:
                @staticmethod
                def execute(query):
                    if "FROM videos" in query:
                        return [{"video_id": "known"}]
                    return []

            conn = Connection()

        with tempfile.TemporaryDirectory() as tmp:
            transcripts = Path(tmp) / "transcripts"
            transcripts.mkdir()
            (transcripts / "known.signals.npz").write_bytes(b"kept")
            (transcripts / "gone.signals.npz").write_bytes(b"orphan")
            found = survey(DB(), Path(tmp))
            self.assertEqual(
                [p.name for p in found["_groups"]["orphan_transcripts"]],
                ["gone.signals.npz"],
            )


if __name__ == "__main__":
    unittest.main()
