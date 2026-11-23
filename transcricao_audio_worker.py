"""Worker isolado para transcrição local com OpenAI Whisper/PyTorch.

Protocolo: recebe um JSON por linha no stdin e devolve um JSON por linha no stdout.
O modelo é carregado sob demanda e permanece residente enquanto o worker viver.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_MODEL: Any | None = None
_MODEL_NAME: str | None = None


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _decode_audio(path: str):
    try:
        import imageio_ffmpeg
        import numpy as np
    except Exception as exc:
        raise RuntimeError("Dependências de áudio incompletas (imageio-ffmpeg/numpy).") from exc

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-nostdin",
        "-threads", "0",
        "-i", str(path),
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0 or not proc.stdout:
        detalhe = proc.stderr.decode("utf-8", errors="ignore")[-800:]
        raise RuntimeError(f"Não consegui decodificar o áudio. {detalhe}".strip())
    return np.frombuffer(proc.stdout, np.int16).astype("float32") / 32768.0


def _get_model(model_name: str, threads: int):
    global _MODEL, _MODEL_NAME
    if _MODEL is not None and _MODEL_NAME == model_name:
        return _MODEL

    try:
        import torch
        import whisper
    except Exception as exc:
        raise RuntimeError("OpenAI Whisper/PyTorch não está instalado.") from exc

    try:
        torch.set_num_threads(max(1, int(threads)))
        if hasattr(torch, "set_num_interop_threads"):
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                pass
    except Exception:
        pass

    _log(f"[audio-worker] carregando modelo Whisper '{model_name}' em CPU...")
    _MODEL = whisper.load_model(model_name, device="cpu")
    _MODEL_NAME = model_name
    _log(f"[audio-worker] modelo '{model_name}' carregado.")
    return _MODEL


def _transcribe(req: dict[str, Any]) -> dict[str, Any]:
    path = str(req.get("path") or "")
    model_name = str(req.get("model") or "base").strip() or "base"
    language = str(req.get("language") or "pt").strip() or "pt"
    threads = int(req.get("threads") or 4)
    prompt = str(req.get("prompt") or "").strip()

    if not path or not Path(path).exists():
        raise RuntimeError("Arquivo de áudio não encontrado.")

    model = _get_model(model_name, threads)
    audio = _decode_audio(path)
    result = model.transcribe(
        audio,
        language=language,
        task="transcribe",
        fp16=False,
        temperature=0.0,
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        initial_prompt=prompt or None,
        verbose=False,
    )
    text = str((result or {}).get("text") or "").strip()
    return {"ok": True, "text": text, "model": model_name}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if req.get("cmd") == "ping":
                out = {"ok": True, "pong": True}
            elif req.get("cmd") == "shutdown":
                print(json.dumps({"ok": True, "shutdown": True}, ensure_ascii=False), flush=True)
                return 0
            else:
                out = _transcribe(req)
        except Exception as exc:
            out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(out, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
