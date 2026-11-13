"""The reason that ranked a moment must stay with its rendered clip."""

import json
from pathlib import Path
from types import SimpleNamespace

from core.models import ClipCandidate
from core.pipeline import _register_clip


class CaptureDB:
    def add_clip(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return 1


def test_clip_registration_persists_the_selection_reason():
    candidate = ClipCandidate(
        start=12.0,
        end=42.0,
        score=86,
        hook="The transcript-grounded hook",
        reason="The speaker reveals the surprising result after a short setup.",
        subscores={"text": 88, "audio": 64},
    )
    db = CaptureDB()

    _register_clip(
        db,
        "video-id",
        candidate,
        Path("clip.mp4"),
        SimpleNamespace(title="A clip", description="", hashtags=[]),
        "{}",
    )

    saved = json.loads(db.kwargs["scores"])
    assert saved["selection_reason"] == candidate.reason
    assert saved["text"] == 88
    assert saved["audio"] == 64
