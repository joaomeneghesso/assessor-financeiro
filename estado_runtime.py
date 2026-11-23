"""Estado efêmero protegido para retomada do Telegram.

O arquivo não substitui o banco financeiro. Ele guarda somente sessões curtas e
callbacks necessários para atravessar um reinício do processo. No Windows, o
conteúdo é protegido pelo DPAPI do usuário. Em ambientes de serviço sem perfil
DPAPI disponível, há fallback para a proteção da máquina, mantendo o arquivo
dentro da pasta privada do projeto.

Fora do Windows (servidor Linux, desde 14/11/2026), o DPAPI é substituído por
AES-256-GCM com uma chave local aleatória em ``.runtime/chave_local.key``,
criada com permissão só do dono (0600). Protege o arquivo copiado sozinho; a
segurança do servidor fica com o acesso SSH só por chave.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import threading
import uuid
from pathlib import Path

try:
    from ctypes import wintypes
except (ImportError, ValueError):  # pragma: no cover - fora do Windows
    wintypes = None


MAGIC = b"AFS1"
MAX_STATE_BYTES = 2 * 1024 * 1024
CHAVE_LOCAL = Path(__file__).resolve().parent / ".runtime" / "chave_local.key"
_PREFIXO_LOCAL = b"L1"
EH_WINDOWS = os.name == "nt"  # constante do módulo: testes simulam Linux sem mexer no os global


def _chave_local() -> bytes:
    """Chave de 32 bytes do servidor; criada uma vez, legível só pelo dono."""
    if not CHAVE_LOCAL.exists():
        CHAVE_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(CHAVE_LOCAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass  # outro processo criou ao mesmo tempo
        else:
            with os.fdopen(fd, "wb") as f:
                f.write(os.urandom(32))
    chave = CHAVE_LOCAL.read_bytes()
    if len(chave) != 32:
        raise OSError("Chave local inválida em .runtime/chave_local.key.")
    return chave


def _local_protect(data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    return _PREFIXO_LOCAL + nonce + AESGCM(_chave_local()).encrypt(nonce, data, MAGIC)


def _local_unprotect(data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not data.startswith(_PREFIXO_LOCAL):
        raise ValueError("Estado protegido em outro formato (gerado no Windows?).")
    corpo = data[len(_PREFIXO_LOCAL):]
    return AESGCM(_chave_local()).decrypt(corpo[:12], corpo[12:], MAGIC)


if wintypes is not None:
    class _DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _dpapi_protect(data: bytes) -> bytes:
    if not EH_WINDOWS:
        return _local_protect(data)
    source, source_buffer = _blob(data)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
        wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL
    # Prefira CurrentUser. Alguns supervisores Windows executam sem perfil
    # carregado; nesse caso use LocalMachine para não perder a retomada.
    protected = crypt32.CryptProtectData(
        ctypes.byref(source), "Assessor Financeiro", None, None, None, 0x1,
        ctypes.byref(output),
    )
    if not protected:
        output = _DataBlob()
        protected = crypt32.CryptProtectData(
            ctypes.byref(source), "Assessor Financeiro", None, None, None, 0x5,
            ctypes.byref(output),
        )
    if not protected:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)
        del source_buffer


def _dpapi_unprotect(data: bytes) -> bytes:
    if not EH_WINDOWS:
        return _local_unprotect(data)
    source, source_buffer = _blob(data)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(_DataBlob),
        wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)
        del source_buffer


class ProtectedJsonStore:
    """Leitura/escrita atômica de um pequeno documento JSON protegido."""

    def __init__(self, path: str | Path, *, enabled: bool = True, protect: bool = True):
        self.path = Path(path)
        self.enabled = bool(enabled)  # Windows: DPAPI; Linux: chave local (ver _local_protect)
        self.protect = bool(protect)
        self._lock = threading.RLock()

    def load(self, default=None):
        default = {} if default is None else default
        if not self.enabled or not self.path.is_file():
            return default
        try:
            with self._lock:
                raw = self.path.read_bytes()
            if len(raw) > MAX_STATE_BYTES or not raw.startswith(MAGIC):
                raise ValueError("Formato de estado inválido.")
            payload = raw[len(MAGIC):]
            if self.protect:
                payload = _dpapi_unprotect(payload)
            value = json.loads(payload.decode("utf-8"))
            return value if isinstance(value, dict) else default
        except Exception:
            logging.warning("Estado efêmero do assessor não pôde ser restaurado.", exc_info=True)
            return default

    def save(self, value: dict) -> bool:
        if not self.enabled:
            return False
        payload = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        if len(payload) > MAX_STATE_BYTES:
            raise ValueError("Estado efêmero excedeu o limite de segurança.")
        if self.protect:
            payload = _dpapi_protect(payload)
        raw = MAGIC + payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp_" + uuid.uuid4().hex)
        try:
            with self._lock:
                temporary.write_bytes(raw)
                temporary.replace(self.path)
            return True
        finally:
            temporary.unlink(missing_ok=True)

    def clear(self) -> None:
        if self.enabled:
            with self._lock:
                self.path.unlink(missing_ok=True)
