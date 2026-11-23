from __future__ import annotations

import argparse
import getpass
import shutil
from datetime import datetime
from pathlib import Path

from security import hash_secret, is_hashed_secret

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def ler_env(path: Path) -> tuple[list[str], dict[str, str]]:
    linhas = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    valores: dict[str, str] = {}
    for raw in linhas:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        valores[key.strip()] = value
    return linhas, valores


def escrever_env(path: Path, linhas: list[str], updates: dict[str, str], removals: set[str]) -> None:
    saida: list[str] = []
    aplicados: set[str] = set()
    for raw in linhas:
        stripped = raw.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in removals:
                continue
            if key in updates:
                if key not in aplicados:
                    saida.append(f"{key}={updates[key]}")
                    aplicados.add(key)
                continue
        saida.append(raw)
    if saida and saida[-1].strip():
        saida.append("")
    for key, value in updates.items():
        if key not in aplicados:
            saida.append(f"{key}={value}")
    path.write_text("\n".join(saida).rstrip() + "\n", encoding="utf-8")


def pedir_pin() -> str:
    while True:
        pin = getpass.getpass("Novo PIN V40 (6 a 8 dígitos): ").strip()
        if not pin.isdigit() or not 6 <= len(pin) <= 8:
            print("Use somente números, com 6 a 8 dígitos.")
            continue
        confirm = getpass.getpass("Repita o novo PIN: ").strip()
        if pin != confirm:
            print("Os PINs não conferem.")
            continue
        return pin


def pedir_recovery() -> str:
    while True:
        value = getpass.getpass("Nova chave mestre de recuperação (mínimo 16 caracteres): ").strip()
        if len(value) < 16:
            print("A chave precisa ter pelo menos 16 caracteres.")
            continue
        confirm = getpass.getpass("Repita a chave mestre: ").strip()
        if value != confirm:
            print("As chaves não conferem.")
            continue
        return value


def validar_config(valores: dict[str, str]) -> list[str]:
    problemas: list[str] = []
    uid = valores.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if not uid or not uid.lstrip("-").isdigit():
        problemas.append("TELEGRAM_ALLOWED_USER_ID ausente ou inválido")
    pin_hash = valores.get("ASSESSOR_PIN_HASH", "")
    try:
        pin_len = int(valores.get("ASSESSOR_PIN_LENGTH", "0"))
    except ValueError:
        pin_len = 0
    if not is_hashed_secret(pin_hash) or not 6 <= pin_len <= 8:
        problemas.append("PIN ainda não está protegido no padrão V40")
    if not is_hashed_secret(valores.get("ASSESSOR_PIN_RESET_KEY_HASH", "")):
        problemas.append("chave de recuperação ainda não está protegida no padrão V40")
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description="Protege os segredos e valida a configuração da v40.")
    parser.add_argument("--check", action="store_true", help="Somente valida; não altera o .env.")
    args = parser.parse_args()

    linhas, valores = ler_env(ENV_PATH)
    if args.check:
        problemas = validar_config(valores)
        if problemas:
            print("CONFIGURAÇÃO V40: PENDENTE")
            for item in problemas:
                print(f"- {item}")
            return 1
        print("CONFIGURAÇÃO V40: OK")
        print("- allowlist Telegram presente")
        print("- PIN protegido por PBKDF2")
        print("- recovery key protegida por PBKDF2")
        return 0

    uid = valores.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if not uid or not uid.lstrip("-").isdigit():
        print("Defina TELEGRAM_ALLOWED_USER_ID no .env antes de continuar.")
        return 2

    pin = pedir_pin()
    recovery = pedir_recovery()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if ENV_PATH.exists():
        backup = ENV_PATH.with_name(f".env.pre_v40_{stamp}.bak")
        shutil.copy2(ENV_PATH, backup)
        print(f"Backup do .env criado: {backup.name}")

    updates = {
        "ASSESSOR_PIN_HASH": hash_secret(pin, iterations=100_000),
        "ASSESSOR_PIN_LENGTH": str(len(pin)),
        "ASSESSOR_PIN_RESET_KEY_HASH": hash_secret(recovery),
    }
    removals = {"ASSESSOR_PIN", "ASSESSOR_PIN_RESET_KEY"}
    escrever_env(ENV_PATH, linhas, updates, removals)
    print("Segredos protegidos. Os valores em texto puro foram removidos do .env.")
    print("Execute: python preparar_seguranca_v40.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
