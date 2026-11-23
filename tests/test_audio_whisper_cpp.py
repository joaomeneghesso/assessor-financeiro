import subprocess
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from unittest.mock import patch

import transcricao_audio as audio


class WhisperCppAudioTests(unittest.TestCase):
    def test_default_provider_does_not_import_pytorch(self):
        with patch.dict("os.environ", {}, clear=True):
            cfg = audio.audio_config()
        self.assertEqual("whisper_cpp", cfg["provider"])
        self.assertEqual("pt", cfg["language"])
        self.assertEqual("whisper-cli.exe" if audio.EH_WINDOWS else "whisper-cli", Path(cfg["cpp_exe"]).name)
        self.assertTrue(str(cfg["cpp_model"]).endswith("ggml-base.bin"))

    def test_diagnostic_only_checks_local_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "whisper-cli.exe"
            model = Path(tmp) / "ggml-base.bin"
            exe.write_bytes(b"exe")
            model.write_bytes(b"model")
            with patch.dict("os.environ", {
                "ASSESSOR_AUDIO_PROVIDER": "whisper_cpp",
                "ASSESSOR_AUDIO_CPP_EXE": str(exe),
                "ASSESSOR_AUDIO_CPP_MODEL": str(model),
            }, clear=False):
                result = audio.diagnosticar_audio()
        self.assertTrue(result["executable_ready"])
        self.assertTrue(result["model_ready"])

    def test_missing_binary_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "voice.ogg"
            source.write_bytes(b"audio")
            with patch.dict("os.environ", {
                "ASSESSOR_AUDIO_PROVIDER": "whisper_cpp",
                "ASSESSOR_AUDIO_CPP_EXE": str(Path(tmp) / "missing.exe"),
                "ASSESSOR_AUDIO_CPP_MODEL": str(Path(tmp) / "missing.bin"),
            }, clear=False):
                with self.assertRaisesRegex(audio.AudioDependencyMissing, "instalar_audio.ps1"):
                    audio.transcrever_audio(source)

    def test_cpp_transcription_uses_temporary_wav_and_returns_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "voice.ogg"
            exe = root / "whisper-cli.exe"
            model = root / "ggml-base.bin"
            for path in (source, exe, model):
                path.write_bytes(b"fixture")

            def decode(_source, target, _timeout):
                with wave.open(str(target), "wb") as stream:
                    stream.setnchannels(1)
                    stream.setsampwidth(2)
                    stream.setframerate(16000)
                    stream.writeframes(array("h", [2000, -2000] * 8000).tobytes())

            def run(command, **_kwargs):
                output = Path(command[command.index("-of") + 1]).with_suffix(".txt")
                output.write_text(
                    "gastei 25,95 no mercado pagando com cartão de crédito do Itaú",
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 0, b"", b"")

            with patch.dict("os.environ", {
                "ASSESSOR_AUDIO_PROVIDER": "whisper_cpp",
                "ASSESSOR_AUDIO_CPP_EXE": str(exe),
                "ASSESSOR_AUDIO_CPP_MODEL": str(model),
            }, clear=False), patch.object(audio, "_decode_to_wav", side_effect=decode), patch.object(audio.subprocess, "run", side_effect=run) as runner:
                text = audio.transcrever_audio(source)

        self.assertEqual(
            "gastei 25,95 no mercado pagando com cartão de crédito do Itaú", text
        )
        command = runner.call_args.args[0]
        self.assertIn("-l", command)
        self.assertEqual("pt", command[command.index("-l") + 1])
        self.assertIn("--prompt", command)

    def test_windows_legacy_encoding_preserves_financial_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcricao.txt"
            path.write_bytes("cartão de crédito do Itaú".encode("cp1252"))
            self.assertEqual("cartão de crédito do Itaú", audio._read_transcript(path))


if __name__ == "__main__":
    unittest.main()
