"""Regras pessoais e explícitas de categorização.

Nada é aprendido silenciosamente. O arquivo só é criado quando o titular toca
em "Aprender" após corrigir uma categoria.
"""
from __future__ import annotations

import json
import os
import config
import re
import threading
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR / "data" / "categorias_pessoais.json"
MAX_RULES = 250
_LOCK = threading.RLock()
_EXPRESSOES_INSEGURAS = {
    "pix", "credito", "debito", "cartao", "cartao de credito", "cartao de debito",
    "itau", "nubank", "mercado pago", "infinitepay", "lia", "dinheiro", "transferencia",
}


def _path(path=None) -> Path:
    configured = config.ler("ASSESSOR_CATEGORY_RULES_PATH", "").strip()
    return Path(path or configured or DEFAULT_PATH).resolve()


def normalizar_expressao(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+]+", " ", text)).strip()


def _document(path=None) -> dict:
    target = _path(path)
    if not target.is_file():
        return {"version": 1, "rules": []}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"version": 1, "rules": []}
    rules = value.get("rules", []) if isinstance(value, dict) else []
    return {"version": 1, "rules": rules if isinstance(rules, list) else []}


def listar_regras(path=None) -> list[dict]:
    with _LOCK:
        rules = _document(path)["rules"]
    valid = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        phrase = str(item.get("phrase") or "").strip()
        normalized = normalizar_expressao(item.get("normalized") or phrase)
        category = str(item.get("category") or "").strip()
        if phrase and normalized and category:
            valid.append(dict(item, phrase=phrase, normalized=normalized, category=category))
    return valid


def _write(rules: list[dict], path=None) -> Path:
    target = _path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp_" + uuid.uuid4().hex)
    document = {"version": 1, "rules": rules[-MAX_RULES:]}
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def salvar_regra(expressao: str, categoria: str, path=None, now=None) -> dict:
    phrase = re.sub(r"\s+", " ", str(expressao or "").strip())
    normalized = normalizar_expressao(phrase)
    category = str(categoria or "").strip()
    if len(normalized) < 3 or not re.search(r"[a-z]", normalized):
        raise ValueError("A descrição é curta demais para virar uma regra pessoal.")
    if normalized in _EXPRESSOES_INSEGURAS:
        raise ValueError("Use o nome do estabelecimento ou da despesa, não a conta ou a forma de pagamento.")
    if not category or len(category) > 60:
        raise ValueError("Categoria pessoal inválida.")
    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    rule = {
        "phrase": phrase[:160],
        "normalized": normalized[:160],
        "category": category,
        "updated_at": stamp,
    }
    with _LOCK:
        rules = [r for r in listar_regras(path) if r["normalized"] != rule["normalized"]]
        rules.append(rule)
        _write(rules, path)
    return rule


def remover_regra(expressao: str, path=None) -> bool:
    normalized = normalizar_expressao(expressao)
    with _LOCK:
        rules = listar_regras(path)
        kept = [rule for rule in rules if rule["normalized"] != normalized]
        if len(kept) == len(rules):
            return False
        _write(kept, path)
    return True


def sugerir_categoria_pessoal(texto: str | None, tipo: str = "despesa", path=None) -> str | None:
    if normalizar_expressao(tipo) in {"receita", "entrada"}:
        return None
    source = normalizar_expressao(texto)
    if not source:
        return None
    candidates = []
    for rule in listar_regras(path):
        term = rule["normalized"]
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", source):
            candidates.append((len(term.split()), len(term), rule["category"]))
    return max(candidates)[2] if candidates else None
