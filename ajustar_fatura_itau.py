from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from sqlite_backup import backup_sqlite_consistente

AJUSTE_ID = "itau_fatura_2026_07_postergacao_1_mes"
CONTA = "Itaú"
MES_ORIGEM = "2026-07"


def add_month_iso(value: str) -> str:
    dt = datetime.strptime(value, "%Y-%m-%d")
    year = dt.year + (1 if dt.month == 12 else 0)
    month = 1 if dt.month == 12 else dt.month + 1
    day = min(dt.day, monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def add_month_ym(value: str) -> str:
    dt = datetime.strptime(value + "-01", "%Y-%m-%d")
    year = dt.year + (1 if dt.month == 12 else 0)
    month = 1 if dt.month == 12 else dt.month + 1
    return f"{year:04d}-{month:02d}"


def norm_sql(column: str) -> str:
    return f"lower(replace(replace(trim(coalesce({column}, '')), 'ú', 'u'), 'é', 'e'))"


def selecionar_alvos(conn: sqlite3.Connection) -> dict:
    conn.row_factory = sqlite3.Row
    transacoes = conn.execute(
        f"""
        SELECT * FROM transacoes
        WHERE data >= ? || '-01'
          AND {norm_sql('conta')} = 'itau'
          AND {norm_sql('forma_pagamento')} = 'credito'
        ORDER BY data, id
        """,
        (MES_ORIGEM,),
    ).fetchall()

    parcelamentos_compromissos = conn.execute(
        f"""
        SELECT * FROM compromissos
        WHERE lower(trim(tipo)) = 'parcelamento'
          AND data_fim >= ? || '-01'
          AND {norm_sql('conta_pagamento')} = 'itau'
          AND {norm_sql('forma_pagamento')} = 'credito'
        ORDER BY id
        """,
        (MES_ORIGEM,),
    ).fetchall()

    fixos_origem = conn.execute(
        f"""
        SELECT * FROM compromissos
        WHERE lower(trim(tipo)) = 'fixo'
          AND ativo = 1
          AND data_inicio <= ? || '-31'
          AND (data_fim IS NULL OR data_fim >= ? || '-01')
          AND {norm_sql('conta_pagamento')} = 'itau'
          AND {norm_sql('forma_pagamento')} = 'credito'
        ORDER BY id
        """,
        (MES_ORIGEM, MES_ORIGEM),
    ).fetchall()

    movimentos = conn.execute(
        f"""
        SELECT * FROM fatura_movimentos
        WHERE ano_mes >= ?
          AND {norm_sql('conta_cartao')} = 'itau'
        ORDER BY ano_mes, id
        """,
        (MES_ORIGEM,),
    ).fetchall()

    return {
        "transacoes": [dict(r) for r in transacoes],
        "parcelamentos_compromissos": [dict(r) for r in parcelamentos_compromissos],
        "fixos_origem": [dict(r) for r in fixos_origem],
        "movimentos": [dict(r) for r in movimentos],
    }


def ja_aplicado(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM auditoria_eventos WHERE entidade = 'ajuste_pontual' AND entidade_id = ? LIMIT 1",
        (AJUSTE_ID,),
    ).fetchone()
    return bool(row)


def banco_usa_competencia_fatura(conn: sqlite3.Connection) -> bool:
    """True quando há lançamentos com competência de fatura explícita.

    Este ajuste é legado (anterior à coluna ``competencia_fatura``): ele move a
    ``data`` das compras de crédito Itaú de julho/2026. Em um banco que já usa
    competência explícita, isso deslocaria compras e pagamentos já corretos.
    """
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(transacoes)")}
    if "competencia_fatura" not in colunas:
        return False
    return conn.execute(
        "SELECT 1 FROM transacoes WHERE competencia_fatura IS NOT NULL LIMIT 1"
    ).fetchone() is not None


def montar_resumo(alvos: dict) -> dict:
    valor_transacoes = sum(float(r.get("valor") or 0) for r in alvos["transacoes"])
    valor_fixos = sum(float(r.get("valor") or 0) for r in alvos["fixos_origem"])
    valor_movimentos = sum(float(r.get("valor") or 0) for r in alvos["movimentos"])
    return {
        "ajuste_id": AJUSTE_ID,
        "conta": CONTA,
        "mes_origem": MES_ORIGEM,
        "transacoes_postergadas": len(alvos["transacoes"]),
        "valor_transacoes": round(valor_transacoes, 2),
        "parcelamentos_compromissos_postergados": len(alvos["parcelamentos_compromissos"]),
        "fixos_duplicados_em_agosto": len(alvos["fixos_origem"]),
        "valor_fixos_duplicados": round(valor_fixos, 2),
        "movimentos_fatura_postergados": len(alvos["movimentos"]),
        "valor_movimentos": round(valor_movimentos, 2),
    }


def aplicar(db_path: Path, confirmar: bool, forcar_legado: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if confirmar:
            conn.execute('BEGIN IMMEDIATE')
        if ja_aplicado(conn):
            raise RuntimeError("Este ajuste já foi aplicado neste banco. Nenhuma alteração foi feita.")
        if not forcar_legado and banco_usa_competencia_fatura(conn):
            raise RuntimeError(
                "Este banco já usa competência de fatura explícita (transacoes.competencia_fatura). "
                "O ajuste legado da fatura Itaú deslocaria compras e pagamentos já corretos. "
                "Nenhuma alteração foi feita. Use --forcar-legado somente se tiver certeza."
            )
        alvos = selecionar_alvos(conn)
        resumo = montar_resumo(alvos)
        if not confirmar:
            return resumo

        backup_dir = db_path.parent.parent / "backups" / "ajuste_fatura_itau"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = backup_dir / f"financeiro_pre_{AJUSTE_ID}_{stamp}.db"
        backup_sqlite_consistente(db_path, backup_path)

        agora = datetime.now().isoformat(timespec="seconds")
        with conn:
            for r in alvos["transacoes"]:
                conn.execute("UPDATE transacoes SET data = ? WHERE id = ?", (add_month_iso(r["data"]), r["id"]))

            for r in alvos["parcelamentos_compromissos"]:
                nova_inicio = add_month_iso(r["data_inicio"])
                nova_fim = add_month_iso(r["data_fim"]) if r.get("data_fim") else None
                conn.execute(
                    "UPDATE compromissos SET data_inicio = ?, data_fim = ?, atualizado_em = ? WHERE id = ?",
                    (nova_inicio, nova_fim, agora, r["id"]),
                )

            # Duplica somente a ocorrência de julho dos fixos no crédito Itaú.
            # O compromisso original permanece intacto e continua gerando agosto em diante.
            for r in alvos["fixos_origem"]:
                dia = int(r.get("dia_vencimento") or int(r["data_inicio"][8:10]))
                dia = min(dia, monthrange(2026, 8)[1])
                data_aug = f"2026-08-{dia:02d}"
                obs_base = (r.get("observacao") or "").strip()
                obs = (
                    f"{obs_base}\n" if obs_base else ""
                ) + f"Duplicação pontual da ocorrência de julho/2026 por mudança de fechamento/vencimento da fatura Itaú. Ajuste: {AJUSTE_ID}."
                conn.execute(
                    """
                    INSERT INTO compromissos (
                        tipo, nome, categoria, conta_pagamento, forma_pagamento, valor,
                        dia_vencimento, data_inicio, data_fim, parcelas_total, ativo,
                        origem, observacao, criado_em, atualizado_em, conta_origem, destino_pagamento
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "fixo",
                        f"{r['nome']} (reprogramado de jul/2026)",
                        r["categoria"], r["conta_pagamento"], r["forma_pagamento"], r["valor"],
                        dia, data_aug, data_aug,
                        AJUSTE_ID, obs, agora, agora, r.get("conta_origem"), r.get("destino_pagamento"),
                    ),
                )

            for r in alvos["movimentos"]:
                conn.execute(
                    "UPDATE fatura_movimentos SET ano_mes = ?, atualizado_em = ? WHERE id = ?",
                    (add_month_ym(r["ano_mes"]), agora, r["id"]),
                )

            conn.execute(
                """
                INSERT INTO auditoria_eventos (
                    entidade, entidade_id, operacao, dados_antes, dados_depois,
                    origem, usuario_sessao, criado_em
                ) VALUES ('ajuste_pontual', ?, 'POSTERGAR_FATURA_ITAU', ?, ?, ?, 'script_local', ?)
                """,
                (
                    AJUSTE_ID,
                    json.dumps({"mes_origem": MES_ORIGEM}, ensure_ascii=False),
                    json.dumps(resumo, ensure_ascii=False),
                    str(backup_path),
                    agora,
                ),
            )

        resumo["backup"] = str(backup_path)
        resumo["aplicado"] = True
        return resumo
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajuste pontual da fatura Itaú após mudança de fechamento/vencimento.")
    parser.add_argument("--db", default="data/financeiro.db", help="Caminho do banco SQLite.")
    parser.add_argument("--aplicar", action="store_true", help="Aplica as alterações. Sem esta opção, apenas simula.")
    parser.add_argument("--forcar-legado", action="store_true",
                        help="Executa mesmo em banco que já usa competencia_fatura (não recomendado).")
    args = parser.parse_args()

    resultado = aplicar(Path(args.db).resolve(), confirmar=args.aplicar, forcar_legado=args.forcar_legado)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
