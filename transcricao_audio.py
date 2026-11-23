"""Transcrição local de voz com worker Whisper isolado.

O processo principal do assessor nunca carrega PyTorch/Whisper diretamente. Um worker
separado é iniciado sob demanda, mantém o modelo em memória e é reiniciado se morrer.
Isso protege o bot contra crashes nativos e mantém texto/botões independentes do áudio.
"""
from __future__ import annotations

import json
import math
import os
import config
import re
import subprocess
import sys
import tempfile
import threading
import time
import wave
from array import array
from pathlib import Path
from typing import Any


class AudioTranscriptionError(RuntimeError):
    """Falha recuperável de transcrição."""


class AudioDependencyMissing(AudioTranscriptionError):
    """Dependência local de áudio ainda não instalada."""


_WORKER: subprocess.Popen[str] | None = None
_WORKER_LOCK = threading.Lock()


EH_WINDOWS = os.name == "nt"


def _env(name: str, default: str) -> str:
    return str(config.ler(name, default) or default).strip()


def audio_config() -> dict[str, Any]:
    runtime = Path(__file__).resolve().parent / ".runtime" / "whispercpp"
    model_name = _env("ASSESSOR_AUDIO_MODELO", "base")
    return {
        # whisper.cpp não depende do Python/PyTorch e fica isolado do bot.
        "provider": _env("ASSESSOR_AUDIO_PROVIDER", "whisper_cpp").lower(),
        "model": model_name,
        "language": _env("ASSESSOR_AUDIO_IDIOMA", "pt"),
        "threads": max(1, int(_env("ASSESSOR_AUDIO_THREADS", "4"))),
        "timeout": max(20, int(_env("ASSESSOR_AUDIO_TIMEOUT", "120"))),
        "cpp_exe": Path(_env("ASSESSOR_AUDIO_CPP_EXE", str(runtime / "bin" / ("whisper-cli.exe" if EH_WINDOWS else "whisper-cli")))),
        "cpp_model": Path(_env("ASSESSOR_AUDIO_CPP_MODEL", str(runtime / "models" / f"ggml-{model_name}.bin"))),
    }


def _worker_script() -> Path:
    return Path(__file__).with_name("transcricao_audio_worker.py")


def _start_worker() -> subprocess.Popen[str]:
    global _WORKER
    script = _worker_script()
    if not script.exists():
        raise AudioDependencyMissing("Arquivo transcricao_audio_worker.py não encontrado.")

    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=str(script.parent),
    )
    _WORKER = proc
    return proc


def _ensure_worker() -> subprocess.Popen[str]:
    global _WORKER
    if _WORKER is None or _WORKER.poll() is not None:
        return _start_worker()
    return _WORKER


def _kill_worker() -> None:
    global _WORKER
    proc = _WORKER
    _WORKER = None
    if proc is None:
        return
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=2)
    except Exception:
        pass


def _readline_with_timeout(stream, timeout: float) -> str:
    result: list[str] = []
    error: list[BaseException] = []

    def _reader():
        try:
            result.append(stream.readline())
        except BaseException as exc:  # pragma: no cover - I/O do SO
            error.append(exc)

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError("Tempo limite da transcrição excedido.")
    if error:
        raise error[0]
    return result[0] if result else ""


def _request_worker(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    with _WORKER_LOCK:
        proc = _ensure_worker()
        if proc.stdin is None or proc.stdout is None:
            _kill_worker()
            raise AudioTranscriptionError("Worker de áudio não iniciou corretamente.")
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = _readline_with_timeout(proc.stdout, timeout)
        except TimeoutError as exc:
            _kill_worker()
            raise AudioTranscriptionError(
                f"A transcrição ultrapassou {timeout}s e foi interrompida. Tente um áudio mais curto."
            ) from exc
        except Exception as exc:
            code = proc.poll()
            _kill_worker()
            detalhe = f" (código {code})" if code is not None else ""
            raise AudioTranscriptionError(
                "O motor local de voz foi encerrado inesperadamente" + detalhe + ". O bot permaneceu ativo."
            ) from exc

        if not line:
            code = proc.poll()
            _kill_worker()
            detalhe = f" código {code}" if code is not None else ""
            raise AudioTranscriptionError(
                f"O motor local de voz não retornou resposta ({detalhe.strip() or 'processo encerrado'}). "
                "O bot permaneceu ativo."
            )
        try:
            return json.loads(line)
        except Exception as exc:
            raise AudioTranscriptionError("Resposta inválida do motor local de voz.") from exc


def normalizar_transcricao(texto: str | None) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    if not re.search(r"[A-Za-zÀ-ÿ0-9]", texto):
        return ""
    return texto


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _decode_to_wav(source: Path, target: Path, timeout: int) -> None:
    try:
        import imageio_ffmpeg
    except Exception as exc:
        raise AudioDependencyMissing(
            "O decodificador de áudio não está instalado. Rode instalar_audio.ps1."
        ) from exc
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        run = subprocess.run(
            [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(source), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            timeout=min(timeout, 45), creationflags=_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioTranscriptionError("Não consegui converter o áudio recebido para WAV.") from exc
    if run.returncode != 0 or not target.exists() or target.stat().st_size <= 44:
        detail = run.stderr.decode("utf-8", errors="replace")[-500:].strip()
        raise AudioTranscriptionError("Não consegui decodificar o áudio." + (" " + detail if detail else ""))


def _wav_has_voice_level(path: Path) -> bool:
    """Recusa silêncio/ruído ínfimo antes que o modelo possa alucinar texto."""
    try:
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                return False
            samples = array("h", stream.readframes(stream.getnframes()))
    except (OSError, EOFError, wave.Error):
        return False
    if not samples:
        return False
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max(abs(value) for value in samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    return peak >= 350 and rms >= 70


def _read_transcript(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


def _transcribe_whisper_cpp(caminho: Path, cfg: dict[str, Any], prompt: str) -> str:
    exe = Path(cfg["cpp_exe"])
    model = Path(cfg["cpp_model"])
    if not exe.is_file():
        raise AudioDependencyMissing(
            "O executável local whisper.cpp não foi encontrado. Rode instalar_audio.ps1."
        )
    if not model.is_file():
        raise AudioDependencyMissing(
            f"O modelo local de voz '{model.name}' não foi encontrado. Rode instalar_audio.ps1."
        )
    with tempfile.TemporaryDirectory(prefix="assessor_voz_") as temp:
        root = Path(temp)
        wav = root / "entrada.wav"
        output = root / "transcricao"
        _decode_to_wav(caminho, wav, int(cfg["timeout"]))
        if not _wav_has_voice_level(wav):
            raise AudioTranscriptionError(
                "Não identifiquei volume de voz suficiente. Fale mais perto do microfone e tente novamente."
            )
        command = [
            str(exe), "-m", str(model), "-f", str(wav),
            "-l", str(cfg["language"]), "-t", str(cfg["threads"]),
            "-otxt", "-of", str(output), "-nt",
        ]
        if prompt:
            command += ["--prompt", prompt]
        try:
            run = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                timeout=int(cfg["timeout"]), creationflags=_creation_flags(),
            )
        except subprocess.TimeoutExpired as exc:
            raise AudioTranscriptionError(
                f"A transcrição ultrapassou {cfg['timeout']}s e foi interrompida. Tente um áudio mais curto."
            ) from exc
        except OSError as exc:
            raise AudioTranscriptionError("Não consegui iniciar o motor local whisper.cpp.") from exc
        text_file = output.with_suffix(".txt")
        text = _read_transcript(text_file) if text_file.exists() else ""
        if run.returncode != 0:
            detail = run.stderr.decode("utf-8", errors="replace")[-800:].strip()
            raise AudioTranscriptionError(
                "O motor local whisper.cpp não conseguiu transcrever o áudio."
                + (" " + detail if detail else "")
            )
        return text


def diagnosticar_audio() -> dict[str, Any]:
    """Diagnóstico sem carregar modelo, abrir rede ou revelar credenciais."""
    cfg = audio_config()
    result = {
        "provider": cfg["provider"], "language": cfg["language"],
        "model": cfg["model"], "threads": cfg["threads"], "timeout": cfg["timeout"],
    }
    if cfg["provider"] == "whisper_cpp":
        result.update(
            executable_ready=Path(cfg["cpp_exe"]).is_file(),
            model_ready=Path(cfg["cpp_model"]).is_file(),
        )
    return result


def transcrever_audio(caminho: str | Path) -> str:
    caminho = Path(caminho)
    if not caminho.exists() or caminho.stat().st_size <= 0:
        raise AudioTranscriptionError("O arquivo de áudio recebido está vazio.")

    cfg = audio_config()
    prompt = _env(
        "ASSESSOR_AUDIO_PROMPT",
        "Mensagem financeira em português brasileiro. Termos comuns: reais, Pix, débito, crédito, "
        "parcela, Itaú, Nubank, Caju, Mercado Pago, InfinitePay, salário, VR, vale refeição.",
    )
    if cfg["provider"] == "whisper_cpp":
        raw_text = _transcribe_whisper_cpp(caminho, cfg, prompt)
    elif cfg["provider"] in {"pytorch", "openai_whisper"}:
        payload = {
            "cmd": "transcribe", "path": str(caminho.resolve()),
            "model": cfg["model"], "language": cfg["language"],
            "threads": cfg["threads"], "prompt": prompt,
        }
        out = _request_worker(payload, int(cfg["timeout"]))
        if not out.get("ok"):
            err = str(out.get("error") or "Falha desconhecida no motor de voz.")
            if "não está instalado" in err.lower() or "not installed" in err.lower():
                raise AudioDependencyMissing(
                    "O backend PyTorch de voz não está disponível. Use whisper_cpp e rode instalar_audio.ps1."
                )
            raise AudioTranscriptionError(f"Não consegui transcrever esse áudio. {err}")
        raw_text = out.get("text")
    else:
        raise AudioDependencyMissing(
            f"Backend de voz desconhecido: {cfg['provider']}. Use ASSESSOR_AUDIO_PROVIDER=whisper_cpp."
        )

    texto = normalizar_transcricao(raw_text)
    if not texto:
        raise AudioTranscriptionError(
            "Não consegui identificar fala nesse áudio. Tente novamente falando mais perto do microfone."
        )
    return texto

