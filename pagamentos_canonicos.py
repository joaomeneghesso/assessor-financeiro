"""Leitura canônica, pura e não inferencial dos dados de pagamento.

O módulo não acessa SQLite e não é conectado ao parser ou aos comandos do bot.
Ele oferece a camada em sombra para comparação explícita com o legado.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_CAMPOS_CANONICOS = (
    "conta_origem",
    "forma_pagamento",
    "destino_pagamento",
)


def _ler_campo(registro: Any, campo: str):
    if isinstance(registro, Mapping):
        return registro.get(campo)
    try:
        return registro[campo]
    except (KeyError, IndexError, TypeError):
        return getattr(registro, campo, None)


def _texto_opcional(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def obter_dados_pagamento_canonicos(registro: Any) -> dict:
    """Retorna uma visão padronizada sem modificar ou inferir a entrada."""
    canonicos = {
        campo: _texto_opcional(_ler_campo(registro, campo))
        for campo in _CAMPOS_CANONICOS
    }
    legado = _texto_opcional(_ler_campo(registro, "conta_pagamento"))
    ausentes = [
        campo for campo, valor in canonicos.items()
        if valor is None
    ]

    if not ausentes:
        origem = "campos_canonicos"
    elif legado is not None and all(valor is None for valor in canonicos.values()):
        origem = "somente_legado"
    elif legado is not None:
        origem = "misto"
    elif any(valor is not None for valor in canonicos.values()):
        origem = "campos_canonicos_parciais"
    else:
        origem = "sem_dados"

    motivos = [f"{campo}_ausente" for campo in ausentes]
    if legado is not None:
        motivos.append("conta_pagamento_legado_preservado")
    if legado is not None and ausentes:
        motivos.append("ambiguidade_legada")

    return {
        **canonicos,
        "conta_pagamento_legado": legado,
        "origem_dos_dados": origem,
        "necessita_revisao": bool(ausentes),
        "motivo_revisao": ", ".join(motivos) if motivos else None,
    }


def comparar_dados_pagamento_em_sombra(registro: Any) -> dict:
    """Compara a visão canônica com o legado sem substituir nenhuma delas."""
    canonico = obter_dados_pagamento_canonicos(registro)
    legado = canonico["conta_pagamento_legado"]
    return {
        "canonico": canonico,
        "legado": {
            "conta_pagamento": legado,
            "forma_pagamento": _texto_opcional(
                _ler_campo(registro, "forma_pagamento")
            ),
        },
        "legado_preservado": legado == canonico["conta_pagamento_legado"],
        "substituir_comportamento_legado": False,
    }


def obter_conta_pagamento_efetiva(registro: Any) -> str | None:
    """Retorna a conta real canônica, com fallback compatível ao legado."""
    conta_origem = _texto_opcional(_ler_campo(registro, "conta_origem"))
    if conta_origem is not None:
        return conta_origem
    return _texto_opcional(_ler_campo(registro, "conta_pagamento"))


def obter_destino_pagamento_efetivo(registro: Any) -> str | None:
    """Retorna o destino canônico sem usar a conta legada como inferência."""
    return _texto_opcional(_ler_campo(registro, "destino_pagamento"))
