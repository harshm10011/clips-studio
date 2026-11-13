"""Portable checks for the M4 capability and memory-profile helpers."""

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.macos.acceleration import mps_usable, run_with_device_fallback
from core.macos.memory import ai_inference_slot, estimate_memory_pressure, profile_for_memory
from core.macos.models import model_recommendation, release_model_for_memory_profile
from transcription import transcriber


class _MPS:
    def __init__(self, built=True, available=True):
        self._built = built
        self._available = available

    def is_built(self):
        return self._built

    def is_available(self):
        return self._available


class MacOSEngineTests(unittest.TestCase):
    def test_mps_is_selected_only_when_built_and_available(self):
        torch = SimpleNamespace(backends=SimpleNamespace(mps=_MPS()))
        self.assertEqual(mps_usable(torch), (True, "Apple Metal Performance Shaders (MPS)"))

        unavailable = SimpleNamespace(backends=SimpleNamespace(mps=_MPS(available=False)))
        usable, reason = mps_usable(unavailable)
        self.assertFalse(usable)
        self.assertIn("unavailable", reason)

    def test_sixteen_gigabyte_machine_uses_conservative_profile(self):
        profile = profile_for_memory(16_000_000_000, 9_000_000_000)
        self.assertEqual(profile.tier, "normal")
        self.assertEqual(profile.recommendation, "gemma3:4b")
        self.assertEqual(profile.max_concurrent_ai_jobs, 1)
        self.assertLessEqual(profile.max_model_memory_bytes, 7_680_000_000)

    def test_low_and_high_memory_profiles_are_adaptive(self):
        self.assertEqual(profile_for_memory(8_000_000_000).tier, "low")
        self.assertEqual(profile_for_memory(32_000_000_000).recommendation, "gemma3:12b")

    def test_memory_pressure_estimate_tracks_available_headroom(self):
        self.assertEqual(estimate_memory_pressure(16_000_000_000, 8_000_000_000), "normal")
        self.assertEqual(estimate_memory_pressure(16_000_000_000, 2_500_000_000), "tight")
        self.assertEqual(estimate_memory_pressure(16_000_000_000, 900_000_000), "critical")
        self.assertEqual(estimate_memory_pressure(None, None), "unknown")

    def test_memory_model_advice_does_not_write_settings(self):
        report = model_recommendation({
            "total_bytes": 16_000_000_000,
            "available_bytes": 10_000_000_000,
        })
        self.assertEqual(report["recommendation"], "gemma3:4b")

    def test_ai_inference_slot_is_a_context_manager(self):
        with ai_inference_slot("test model"):
            self.assertTrue(True)

    def test_mps_detection_handles_missing_backend(self):
        torch = SimpleNamespace(backends=SimpleNamespace())
        usable, reason = mps_usable(torch)
        self.assertFalse(usable)
        self.assertIn("could not check MPS", reason)

    def test_memory_profile_releases_only_local_small_machine_model(self):
        with patch("core.macos.models.unload_ollama_model", return_value=True) as unload:
            self.assertTrue(release_model_for_memory_profile(
                "gemma3:4b", "http://localhost:11434", 16 * 1024**3
            ))
            unload.assert_called_once_with("gemma3:4b", "http://localhost:11434")

        with patch("core.macos.models.unload_ollama_model") as unload:
            self.assertFalse(release_model_for_memory_profile(
                "gemma3:4b", "https://remote.example:11434", 16 * 1024**3
            ))
            self.assertFalse(release_model_for_memory_profile(
                "gemma3:4b", "http://localhost:11434", 32 * 1024**3
            ))
            unload.assert_not_called()

    def test_memory_profile_keeps_local_model_warm_when_headroom_is_healthy(self):
        with patch("core.macos.models.unload_ollama_model") as unload:
            self.assertFalse(release_model_for_memory_profile(
                "gemma3:4b", "http://localhost:11434", 16 * 1024**3, 8 * 1024**3
            ))
            unload.assert_not_called()

        with patch("core.macos.models.unload_ollama_model", return_value=True) as unload:
            self.assertTrue(release_model_for_memory_profile(
                "gemma3:4b", "http://localhost:11434", 16 * 1024**3, 2 * 1024**3
            ))
            unload.assert_called_once_with("gemma3:4b", "http://localhost:11434")

    def test_accelerator_inference_failure_retries_on_cpu(self):
        class Model:
            device = "mps"

            def to(self, device):
                self.device = device

        model = Model()

        def operation(device):
            if device == "mps":
                raise RuntimeError("unsupported MPS operation")
            return device

        with patch("core.gpu.force_torch_cpu") as force_cpu:
            result = run_with_device_fallback(model, "mps", operation, "test inference")

        self.assertEqual(result, "cpu")
        self.assertEqual(model.device, "cpu")
        force_cpu.assert_called_once()

    def test_auto_whisper_uses_cpu_when_only_mps_is_available(self):
        created = []

        class WhisperModel:
            def __init__(self, _name, device="cpu", compute_type="auto"):
                created.append(device)
                self.model = SimpleNamespace(device=device)

        fake_backend = SimpleNamespace(WhisperModel=WhisperModel)
        with patch.dict(sys.modules, {"faster_whisper": fake_backend}):
            with patch("core.gpu.torch_device", return_value="mps"):
                model = transcriber._load_model("small", "auto")

        self.assertEqual(created, ["cpu"])
        self.assertFalse(transcriber._on_gpu(model))


if __name__ == "__main__":
    unittest.main()
