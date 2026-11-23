"""RC1.5.6: normaliza os oito compromissos históricos validados pelo usuário."""

VERSION = 3
NAME = "normalizacao_pagamentos_historicos"
SUPPORTS_ROLLBACK = False
EXPECTED_SCHEMA_HASH = "6A80F75A7CD79B5B30A890B1E8F2F31C6ED2FAB0614C85CF7F7DA9FA32DE3A9A"
RESULTING_SCHEMA_HASH = EXPECTED_SCHEMA_HASH
ALLOWS_PREAPPLIED_SCHEMA = False
ESTIMATED_TIME_MS = 50
AFFECTED_OBJECTS = ("compromissos",)

SQL = (
    "UPDATE compromissos SET conta_origem='Itaú' WHERE id IN (4,5,6,7,8,30,43)",
    "UPDATE compromissos SET conta_origem='Itaú', destino_pagamento='Lia' WHERE id=10",
)

_EXPECTED = {
    4: ("CNPJ (baixa)", "Pix", "pix", 51.53, 1),
    5: ("Condominio", "Pix", "pix", 231.45, 1),
    6: ("IPTU", "Pix", "pix", 53.60, 1),
    7: ("IPTV", "Pix", "pix", 8.00, 1),
    8: ("Internet", "Pix", "pix", 48.30, 1),
    10: ("iCloud", "Lia", "crédito", 33.45, 1),
    30: ("Empréstimos", "Pix", "pix", 400.00, 1),
    43: ("Tag condomínio", "Pix", "pix", 30.00, 1),
}


def _normalize(value):
    return str(value or "").strip().casefold()


def upgrade(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(compromissos)")}
    required = {"id", "nome", "conta_pagamento", "forma_pagamento", "conta_origem", "destino_pagamento", "valor", "ativo"}
    missing = sorted(required - columns)
    if missing:
        raise RuntimeError("Schema incompatível; colunas ausentes: " + ", ".join(missing))

    ids = tuple(_EXPECTED)
    placeholders = ",".join("?" for _ in ids)
    rows = connection.execute(
        f"SELECT id,nome,conta_pagamento,forma_pagamento,conta_origem,destino_pagamento,valor,ativo FROM compromissos WHERE id IN ({placeholders}) ORDER BY id",
        ids,
    ).fetchall()
    if not rows:
        # Bancos novos/limpos não possuem o legado específico desta instalação.
        # A migration é registrada sem inventar ou inserir compromissos.
        return
    if len(rows) != len(_EXPECTED):
        found = {int(row[0]) for row in rows}
        raise RuntimeError(f"Conjunto histórico incompleto; ausentes={sorted(set(ids)-found)}")

    for row in rows:
        ident = int(row[0])
        expected = _EXPECTED[ident]
        actual = (str(row[1]), str(row[2]), str(row[3]), float(row[6]), int(row[7]))
        if actual[0] != expected[0] or _normalize(actual[1]) != _normalize(expected[1]) or _normalize(actual[2]) != _normalize(expected[2]) or abs(actual[3]-expected[3]) > 0.005 or actual[4] != expected[4]:
            raise RuntimeError(f"Registro #{ident} divergiu do levantamento validado: atual={actual!r}")
        if row[4] is not None or row[5] is not None:
            raise RuntimeError(f"Registro #{ident} já possui campos canônicos preenchidos")

    pix_ids = (4, 5, 6, 7, 8, 30, 43)
    placeholders = ",".join("?" for _ in pix_ids)
    cursor = connection.execute(
        f"UPDATE compromissos SET conta_origem='Itaú' WHERE id IN ({placeholders}) AND conta_origem IS NULL AND destino_pagamento IS NULL",
        pix_ids,
    )
    if cursor.rowcount != 7:
        raise RuntimeError(f"Esperados 7 registros Pix; atualizados={cursor.rowcount}")

    cursor = connection.execute(
        "UPDATE compromissos SET conta_origem='Itaú', destino_pagamento='Lia' WHERE id=10 AND conta_origem IS NULL AND destino_pagamento IS NULL"
    )
    if cursor.rowcount != 1:
        raise RuntimeError(f"Esperado 1 registro Lia; atualizados={cursor.rowcount}")

    remaining = connection.execute(
        f"SELECT COUNT(*) FROM compromissos WHERE id IN ({','.join('?' for _ in ids)}) AND conta_origem IS NULL",
        ids,
    ).fetchone()[0]
    if remaining:
        raise RuntimeError(f"Normalização incompleta; conta_origem nula em {remaining} registro(s)")


def downgrade(connection):
    raise RuntimeError("A migration 0003 requer rollback por restauração de backup")
