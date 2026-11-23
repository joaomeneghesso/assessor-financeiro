import sqlite3
import json
import logging
import math
import os
import config
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
import relogio
from pathlib import Path
from categorias import canonicalizar_categoria
from faturas_competencia import sql_competencia, exigir_schema

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = config.DB_PATH  # apelido patchável (testes trocam database.DB_PATH)


def _validar_valor_monetario(valor, campo: str, *, permitir_negativo: bool = False,
                             permitir_zero: bool = False) -> float:
    """Valida valor monetário na camada de banco e devolve float com 2 casas.

    Reaproveita ``money.parse_money`` (Decimal, HALF_UP). Número (int/float/
    Decimal) é arredondado a 2 casas; texto segue o formato estrito de
    ``parse_money``. Recusa bool, None, NaN, infinito, valores acima do teto
    (999.999.999,99), negativos (salvo ``permitir_negativo``) e zero (salvo
    ``permitir_zero``).
    """
    from decimal import Decimal
    from money import parse_money
    if valor is None or isinstance(valor, bool):
        raise ValueError(f"Valor inválido para {campo}: informe um número.")
    if isinstance(valor, float) and not math.isfinite(valor):
        raise ValueError(f"Valor inválido para {campo}: precisa ser um número finito.")
    try:
        d = parse_money(valor, allow_negative=True)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise ValueError(f"Valor inválido para {campo}: precisa ser um número finito.") from exc
    if abs(d) > Decimal("999999999.99"):
        raise ValueError(f"Valor inválido para {campo}: acima do limite de R$ 999.999.999,99.")
    if d < 0 and not permitir_negativo:
        raise ValueError(f"Valor inválido para {campo}: não pode ser negativo.")
    if d == 0 and not (permitir_zero or permitir_negativo):
        raise ValueError(f"Valor inválido para {campo}: precisa ser maior que zero.")
    return float(d)


def _validar_data_iso_db(data, campo: str) -> str:
    from datetime import date
    try:
        return date.fromisoformat(str(data)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data inválida para {campo}: use AAAA-MM-DD com uma data que exista.") from exc


class ClosingConnection(sqlite3.Connection):
    """SQLite connection whose context manager also releases the file handle.

    The standard sqlite3.Connection context manager only commits or rolls back;
    it does not close the connection. This subclass preserves transaction
    semantics and closes deterministically on context exit.
    """

    def __enter__(self):
        if getattr(self, "_shared_read", False):
            self._row_factory_stack.append(self.row_factory)
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if getattr(self, "_shared_read", False):
            try:
                return super().__exit__(exc_type, exc_value, traceback)
            finally:
                self.row_factory = self._row_factory_stack.pop()
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


_READ_ONLY = ContextVar("assessor_db_read_only", default=False)
_READ_CONNECTION = ContextVar("assessor_db_read_connection", default=None)


# journal_mode=WAL é persistente no próprio arquivo: basta ativá-lo uma vez por
# arquivo. Repetir o PRAGMA a cada conexão custava caro (milhares de conexões
# por cálculo de herança de saldo). A identidade inclui dispositivo e inode, então
# um arquivo substituído (restauração de backup, outro DB_PATH) volta a receber o
# PRAGMA na próxima conexão de escrita.
_WAL_CONFIRMADO = set()
_WAL_LOCK = threading.Lock()


def _identidade_arquivo(path):
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (os.fspath(path), info.st_dev, info.st_ino, getattr(info, "st_birthtime_ns", None))


def _garantir_wal(conn):
    identidade = _identidade_arquivo(DB_PATH)
    if identidade is not None and identidade in _WAL_CONFIRMADO:
        return
    modo = conn.execute("PRAGMA journal_mode = WAL").fetchone()
    if modo and str(modo[0]).lower() == "wal":
        identidade = _identidade_arquivo(DB_PATH)
        if identidade is not None:
            with _WAL_LOCK:
                _WAL_CONFIRMADO.add(identidade)


# Pastas de banco já garantidas neste processo: evita um mkdir (syscall) por
# conexão. Se a pasta sumir depois, a abertura falha e o mkdir é refeito.
_PASTAS_GARANTIDAS = set()


def _garantir_pasta(path):
    pasta = os.fspath(path.parent)
    if pasta not in _PASTAS_GARANTIDAS:
        path.parent.mkdir(parents=True, exist_ok=True)
        _PASTAS_GARANTIDAS.add(pasta)


def _open_connection(read_only):
    if read_only:
        target = DB_PATH.resolve().as_uri() + "?mode=ro"
    else:
        _garantir_pasta(DB_PATH)
        target = DB_PATH
    try:
        conn = sqlite3.connect(target, uri=read_only, timeout=15.0, factory=ClosingConnection)
    except sqlite3.OperationalError:
        if read_only or DB_PATH.parent.exists():
            raise
        _PASTAS_GARANTIDAS.discard(os.fspath(DB_PATH.parent))
        _garantir_pasta(DB_PATH)
        conn = sqlite3.connect(target, uri=read_only, timeout=15.0, factory=ClosingConnection)
    conn._shared_read = False
    conn._row_factory_stack = []
    conn._owner_thread = threading.get_ident()
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        if read_only:
            conn.execute("PRAGMA query_only = ON")
        else:
            _garantir_wal(conn)
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn
    except Exception:
        conn.close()
        raise


@contextmanager
def read_only_mode():
    """Restringe e compartilha uma conexão de leitura nesta requisição."""
    token = _READ_ONLY.set(True)
    existente = _READ_CONNECTION.get()
    connection = None
    connection_token = None
    try:
        if existente is None:
            connection = _open_connection(True)
            connection._shared_read = True
            connection_token = _READ_CONNECTION.set(connection)
        yield
    finally:
        if connection_token is not None:
            _READ_CONNECTION.reset(connection_token)
            connection._shared_read = False
            connection.close()
        _READ_ONLY.reset(token)


def verificar_banco_para_iniciar(db_path=None, backups_dir=None, migrations_dir=None):
    """Recusa iniciar o bot em situações que dividiriam ou corromperiam os dados.

    - Banco ausente, mas com backups existentes: o arquivo provavelmente sumiu
      (sincronização, restauração incompleta). Criar um banco vazio separaria os
      dados em dois arquivos.
    - Esquema mais antigo que as migrations do código (ou mais novo que ele).
    Banco ausente sem backups (instalação nova) e versão 0 (legado) seguem como antes.
    Devolve None quando pode iniciar; senão, a mensagem do motivo.
    """
    db_path = Path(db_path or DB_PATH)
    pastas_backup = [Path(backups_dir)] if backups_dir else [BASE_DIR / "backups", Path("backups")]
    migrations_dir = Path(migrations_dir or (BASE_DIR / "migrations"))
    if not db_path.exists():
        for pasta in pastas_backup:
            if pasta.exists() and any(pasta.glob("financeiro_*.db")):
                return (f"Banco não encontrado em {db_path}, mas existem backups em {pasta.resolve()}. "
                        "Restaure o backup mais recente para data/financeiro.db antes de iniciar.")
        return None
    numeros = [int(p.name[:4]) for p in migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py")]
    ultima = max(numeros) if numeros else 0
    try:
        conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            versao = conn.execute("PRAGMA user_version").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        # Sem conseguir ler a versão aqui, mantém o comportamento anterior.
        logging.getLogger("assessor.inicio").warning("Não foi possível ler a versão do banco.", exc_info=True)
        return None
    if 0 < versao < ultima:
        return (f"O banco está na versão {versao} e o código espera a {ultima}. "
                "Pare o bot e execute: python migrations.py migrate")
    if versao > ultima > 0:
        return (f"O banco está na versão {versao}, mais nova que o código ({ultima}). "
                "Atualize os arquivos do assessor antes de iniciar.")
    return None


def get_connection():
    read_only = _READ_ONLY.get()
    if read_only:
        shared = _READ_CONNECTION.get()
        if shared is not None and shared._owner_thread == threading.get_ident():
            return shared
    return _open_connection(read_only)


@contextmanager
def fatura_write_transaction():
    """Serializa alterações de fatura entre processos usando BEGIN IMMEDIATE."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inserir_fatura_movimento_conn(conn, movimento: dict) -> int:
    movimento = _validar_fatura_movimento(movimento)
    agora = relogio.agora().isoformat(timespec="seconds")
    cursor = conn.execute("""
        INSERT INTO fatura_movimentos (
            ano_mes, conta_cartao, tipo_movimento, valor,
            data_movimento, conta_origem, descricao,
            mensagem_original, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        movimento["ano_mes"], movimento["conta_cartao"],
        movimento["tipo_movimento"], float(movimento["valor"]),
        movimento["data_movimento"], movimento.get("conta_origem"),
        movimento.get("descricao"), movimento.get("mensagem_original"),
        agora, agora,
    ))
    return cursor.lastrowid


def obter_primeira_competencia_financeira():
    """Retorna a primeira competência conhecida para limitar recálculo histórico."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT MIN(competencia) FROM (
                SELECT substr(data, 1, 7) AS competencia FROM transacoes WHERE data IS NOT NULL
                UNION ALL
                SELECT substr(data_inicio, 1, 7) FROM compromissos WHERE data_inicio IS NOT NULL
                UNION ALL
                SELECT ano_mes FROM fatura_movimentos WHERE ano_mes IS NOT NULL
            )
        """).fetchone()
        return row[0] if row and row[0] else None


def coluna_existe(conn, tabela: str, coluna: str) -> bool:
    colunas = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(c[1] == coluna for c in colunas)


def adicionar_coluna_se_nao_existir(conn, tabela: str, coluna: str, definicao: str):
    if not coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def _normalizar_categorias_legadas(conn):
    """Consolida aliases conhecidos sem alterar valores financeiros.

    A rotina é idempotente: depois da primeira normalização, novas
    inicializações não reescrevem os registros já canônicos.
    """
    for tabela in ("transacoes", "compromissos"):
        conn.execute(
            f"""UPDATE {tabela}
                SET categoria = 'Assinaturas'
                WHERE lower(trim(categoria)) = 'assinatura'
            """
        )

    # Metas têm UNIQUE(categoria). Se existirem singular e plural ao mesmo
    # tempo, preserva a configuração mais recentemente atualizada.
    rows = conn.execute("""
        SELECT id, categoria, valor, criado_em, atualizado_em
        FROM metas
        WHERE lower(trim(categoria)) IN ('assinatura', 'assinaturas')
        ORDER BY atualizado_em DESC, id DESC
    """).fetchall()
    if not rows:
        return

    if len(rows) == 1:
        unico = rows[0]
        if str(unico[1]).strip() != "Assinaturas":
            conn.execute(
                "UPDATE metas SET categoria = 'Assinaturas' WHERE id = ?",
                (unico[0],),
            )
        return

    escolhido = rows[0]
    ids_remover = [r[0] for r in rows[1:]]
    placeholders = ",".join("?" for _ in ids_remover)
    conn.execute(f"DELETE FROM metas WHERE id IN ({placeholders})", ids_remover)
    conn.execute(
        """UPDATE metas
           SET categoria = 'Assinaturas', valor = ?, criado_em = ?, atualizado_em = ?
           WHERE id = ?""",
        (escolhido[2], escolhido[3], escolhido[4], escolhido[0]),
    )


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                categoria TEXT NOT NULL,
                descricao TEXT,
                conta TEXT,
                forma_pagamento TEXT,
                mensagem_original TEXT,
                criado_em TEXT NOT NULL
            )
        """)

        adicionar_coluna_se_nao_existir(conn, "transacoes", "parcelamento_id", "INTEGER")
        adicionar_coluna_se_nao_existir(conn, "transacoes", "parcela_atual", "INTEGER")
        adicionar_coluna_se_nao_existir(conn, "transacoes", "parcelas_total", "INTEGER")
        adicionar_coluna_se_nao_existir(conn, "transacoes", "valor_total_parcelamento", "REAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL UNIQUE,
                valor REAL NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS compromissos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                conta_pagamento TEXT,
                forma_pagamento TEXT,
                valor REAL NOT NULL,
                dia_vencimento INTEGER,
                data_inicio TEXT NOT NULL,
                data_fim TEXT,
                parcelas_total INTEGER,
                ativo INTEGER NOT NULL DEFAULT 1,
                origem TEXT,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            , conta_origem TEXT NULL, destino_pagamento TEXT NULL)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saldos_mensais (
                ano_mes TEXT PRIMARY KEY,
                saldo_inicial REAL NOT NULL,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saldos_mensais_contas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ano_mes TEXT NOT NULL,
                conta TEXT NOT NULL,
                saldo_inicial REAL NOT NULL,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                UNIQUE(ano_mes, conta)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transferencias_caixa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                valor REAL NOT NULL,
                conta_origem TEXT NOT NULL,
                conta_destino TEXT NOT NULL,
                descricao TEXT,
                mensagem_original TEXT,
                criado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_datas_pagamento_padrao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_chave TEXT NOT NULL UNIQUE,
                dia_pagamento INTEGER NOT NULL,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_datas_pagamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ano_mes TEXT NOT NULL,
                item_chave TEXT NOT NULL,
                data_pagamento TEXT NOT NULL,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                UNIQUE(ano_mes, item_chave)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS fatura_movimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ano_mes TEXT NOT NULL,
                conta_cartao TEXT NOT NULL,
                tipo_movimento TEXT NOT NULL,
                valor REAL NOT NULL,
                data_movimento TEXT NOT NULL,
                conta_origem TEXT,
                descricao TEXT,
                mensagem_original TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_fatura_movimentos_mes_conta
            ON fatura_movimentos (ano_mes, conta_cartao)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entidade TEXT NOT NULL,
                entidade_id TEXT,
                operacao TEXT NOT NULL,
                dados_antes TEXT,
                dados_depois TEXT,
                origem TEXT,
                usuario_sessao TEXT,
                criado_em TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_auditoria_eventos_entidade
            ON auditoria_eventos (entidade, entidade_id, criado_em)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ano_mes TEXT NOT NULL,
                item_chave TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                pago_em TEXT,
                observacao TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                UNIQUE(ano_mes, item_chave)
            )
        """)

        _normalizar_categorias_legadas(conn)
        conn.commit()


def buscar_saldo_mensal(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM saldos_mensais
            WHERE ano_mes = ?
        """, (ano_mes,)).fetchone()


def definir_saldo_inicial_mes(ano_mes: str, saldo_inicial: float, observacao: str | None = None):
    saldo_inicial = _validar_valor_monetario(saldo_inicial, "saldo inicial", permitir_negativo=True)
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM saldos_mensais
            WHERE ano_mes = ?
        """, (ano_mes,)).fetchone()

        if existente:
            conn.execute("""
                UPDATE saldos_mensais
                SET saldo_inicial = ?,
                    observacao = ?,
                    atualizado_em = ?
                WHERE ano_mes = ?
            """, (saldo_inicial, observacao, agora, ano_mes))
        else:
            conn.execute("""
                INSERT INTO saldos_mensais (
                    ano_mes,
                    saldo_inicial,
                    observacao,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?)
            """, (ano_mes, saldo_inicial, observacao, agora, agora))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM saldos_mensais
            WHERE ano_mes = ?
        """, (ano_mes,)).fetchone()


def listar_saldos_mensais():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM saldos_mensais
            ORDER BY ano_mes
        """).fetchall()


def buscar_saldos_contas_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM saldos_mensais_contas
            WHERE ano_mes = ?
            ORDER BY conta
        """, (ano_mes,)).fetchall()


def buscar_saldo_conta_mes(ano_mes: str, conta: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM saldos_mensais_contas
            WHERE ano_mes = ?
              AND lower(conta) = lower(?)
        """, (ano_mes, conta)).fetchone()


def definir_saldo_inicial_conta_mes(ano_mes: str, conta: str, saldo_inicial: float, observacao: str | None = None):
    saldo_inicial = _validar_valor_monetario(saldo_inicial, "saldo inicial", permitir_negativo=True)
    agora = relogio.agora().isoformat(timespec="seconds")
    conta = (conta or "Geral").strip() or "Geral"

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM saldos_mensais_contas
            WHERE ano_mes = ?
              AND lower(conta) = lower(?)
        """, (ano_mes, conta)).fetchone()

        if existente:
            conn.execute("""
                UPDATE saldos_mensais_contas
                SET saldo_inicial = ?,
                    observacao = ?,
                    atualizado_em = ?
                WHERE id = ?
            """, (saldo_inicial, observacao, agora, existente["id"]))
        else:
            conn.execute("""
                INSERT INTO saldos_mensais_contas (
                    ano_mes,
                    conta,
                    saldo_inicial,
                    observacao,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ano_mes, conta, saldo_inicial, observacao, agora, agora))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM saldos_mensais_contas
            WHERE ano_mes = ?
              AND lower(conta) = lower(?)
        """, (ano_mes, conta)).fetchone()



def inserir_transferencia_caixa(transferencia: dict) -> int:
    transferencia = dict(transferencia)
    transferencia["valor"] = _validar_valor_monetario(transferencia.get("valor"), "transferência")
    transferencia["data"] = _validar_data_iso_db(transferencia.get("data"), "transferência")
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO transferencias_caixa (
                data,
                valor,
                conta_origem,
                conta_destino,
                descricao,
                mensagem_original,
                criado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            transferencia["data"],
            transferencia["valor"],
            transferencia["conta_origem"],
            transferencia["conta_destino"],
            transferencia.get("descricao"),
            transferencia.get("mensagem_original"),
            agora,
        ))

        conn.commit()
        return cursor.lastrowid


def buscar_transferencias_caixa_por_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM transferencias_caixa
            WHERE substr(data, 1, 7) = ?
            ORDER BY data, id
        """, (ano_mes,)).fetchall()


def buscar_transferencia_caixa_por_id(transferencia_id: int):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM transferencias_caixa
            WHERE id = ?
        """, (transferencia_id,)).fetchone()


def apagar_transferencia_caixa_por_id(transferencia_id: int):
    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM transferencias_caixa
            WHERE id = ?
        """, (transferencia_id,))
        conn.commit()
        return cursor.rowcount





def definir_checklist_data_pagamento_padrao(item_chave: str, dia_pagamento: int, observacao: str | None = None):
    agora = relogio.agora().isoformat(timespec="seconds")
    item_chave = (item_chave or "").strip()

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento_padrao
            WHERE item_chave = ?
        """, (item_chave,)).fetchone()

        if existente:
            conn.execute("""
                UPDATE checklist_datas_pagamento_padrao
                SET dia_pagamento = ?,
                    observacao = ?,
                    atualizado_em = ?
                WHERE id = ?
            """, (dia_pagamento, observacao, agora, existente["id"]))
        else:
            conn.execute("""
                INSERT INTO checklist_datas_pagamento_padrao (
                    item_chave,
                    dia_pagamento,
                    observacao,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?)
            """, (item_chave, dia_pagamento, observacao, agora, agora))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento_padrao
            WHERE item_chave = ?
        """, (item_chave,)).fetchone()


def buscar_checklist_datas_pagamento_padrao():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento_padrao
        """).fetchall()

    return {row["item_chave"]: row for row in rows}


def apagar_checklist_data_pagamento_padrao(item_chave: str):
    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM checklist_datas_pagamento_padrao
            WHERE item_chave = ?
        """, (item_chave,))
        conn.commit()
        return cursor.rowcount



def definir_checklist_data_pagamento(ano_mes: str, item_chave: str, data_pagamento: str, observacao: str | None = None):
    agora = relogio.agora().isoformat(timespec="seconds")
    item_chave = (item_chave or "").strip()

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento
            WHERE ano_mes = ?
              AND item_chave = ?
        """, (ano_mes, item_chave)).fetchone()

        if existente:
            conn.execute("""
                UPDATE checklist_datas_pagamento
                SET data_pagamento = ?,
                    observacao = ?,
                    atualizado_em = ?
                WHERE id = ?
            """, (data_pagamento, observacao, agora, existente["id"]))
        else:
            conn.execute("""
                INSERT INTO checklist_datas_pagamento (
                    ano_mes,
                    item_chave,
                    data_pagamento,
                    observacao,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ano_mes, item_chave, data_pagamento, observacao, agora, agora))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento
            WHERE ano_mes = ?
              AND item_chave = ?
        """, (ano_mes, item_chave)).fetchone()


def buscar_checklist_datas_pagamento_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT *
            FROM checklist_datas_pagamento
            WHERE ano_mes = ?
        """, (ano_mes,)).fetchall()

    return {row["item_chave"]: row for row in rows}


def apagar_checklist_data_pagamento(ano_mes: str, item_chave: str):
    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM checklist_datas_pagamento
            WHERE ano_mes = ?
              AND item_chave = ?
        """, (ano_mes, item_chave))
        conn.commit()
        return cursor.rowcount



def inserir_transacao(transacao: dict) -> int:
    with get_connection() as conn:
        transacao_id = _inserir_transacao_conn(conn, transacao)
        conn.commit()
        return transacao_id


def inserir_parcelamento_atomico(parcelas: list[dict]) -> list[int]:
    """Grava todas as parcelas e o vínculo do parcelamento numa única transação.

    Equivale a ``inserir_transacao`` para cada parcela seguido de
    ``atualizar_dados_parcelamento`` (parcelamento_id = ID da 1ª parcela), mas sem
    deixar parcelas soltas se algo falhar no meio.
    """
    if not parcelas:
        return []
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ids = [_inserir_transacao_conn(conn, parcela) for parcela in parcelas]
        parcelamento_id = ids[0]
        for transacao_id, parcela in zip(ids, parcelas):
            conn.execute("""
                UPDATE transacoes
                SET parcelamento_id = ?,
                    parcela_atual = ?,
                    parcelas_total = ?,
                    valor_total_parcelamento = ?
                WHERE id = ?
            """, (parcelamento_id, parcela.get("parcela_atual"), parcela.get("parcelas_total"),
                  parcela.get("valor_total_parcelamento"), transacao_id))
        conn.commit()
        return ids


def _inserir_transacao_conn(conn, transacao: dict) -> int:
    """INSERT de uma transação na conexão recebida; o commit fica com quem chama."""
    transacao = dict(transacao)
    transacao["valor"] = _validar_valor_monetario(transacao.get("valor"), "transação")
    if transacao.get('competencia_fatura') or transacao.get('data_compra'):
        exigir_schema(conn)
        from faturas_competencia import eh_credito, validar_mes
        if not eh_credito(transacao):
            raise ValueError('Fatura e exclusiva de despesas no credito.')
        if transacao.get('competencia_fatura'):
            validar_mes(transacao['competencia_fatura'])
    cursor = conn.execute("""
        INSERT INTO transacoes (
            data,
            tipo,
            valor,
            categoria,
            descricao,
            conta,
            forma_pagamento,
            mensagem_original,
            criado_em,
            parcelamento_id,
            parcela_atual,
            parcelas_total,
            valor_total_parcelamento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        transacao["data"],
        transacao["tipo"],
        transacao["valor"],
        canonicalizar_categoria(transacao["categoria"], "Outros"),
        transacao.get("descricao"),
        transacao.get("conta"),
        transacao.get("forma_pagamento"),
        transacao.get("mensagem_original"),
        relogio.agora().isoformat(timespec="seconds"),
        transacao.get("parcelamento_id"),
        transacao.get("parcela_atual"),
        transacao.get("parcelas_total"),
        transacao.get("valor_total_parcelamento")
    ))

    if transacao.get('competencia_fatura') or transacao.get('data_compra'):
        conn.execute('UPDATE transacoes SET data_compra=?, competencia_fatura=? WHERE id=?',
                     (transacao.get('data_compra'), transacao.get('competencia_fatura'), cursor.lastrowid))
    return cursor.lastrowid


def atualizar_dados_parcelamento(transacao_id: int, parcelamento_id: int, parcela_atual: int, parcelas_total: int, valor_total: float):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [transacao_id])
        conn.execute("""
            UPDATE transacoes
            SET parcelamento_id = ?,
                parcela_atual = ?,
                parcelas_total = ?,
                valor_total_parcelamento = ?
            WHERE id = ?
        """, (parcelamento_id, parcela_atual, parcelas_total, valor_total, transacao_id))
        conn.commit()


def buscar_ultimas_transacoes(limite: int = 10):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM transacoes
            ORDER BY id DESC
            LIMIT ?
        """, (limite,)).fetchall()


def buscar_transacoes_por_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM transacoes
            WHERE substr(data, 1, 7) = ?
            ORDER BY data, id
        """, (ano_mes,)).fetchall()


def buscar_transacoes_por_competencia(ano_mes: str):
    """Mes financeiro; credito usa a fatura, demais registros usam sua data."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        expressao = sql_competencia(conn)
        return conn.execute(
            f'SELECT * FROM transacoes WHERE ({expressao}) = ? ORDER BY data, id',
            (ano_mes,),
        ).fetchall()


def buscar_todas_transacoes():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM transacoes
            ORDER BY data, id
        """).fetchall()


class ExclusaoParcialParcelamentoError(ValueError):
    """Exclusão que levaria só parte de um parcelamento (nada é apagado)."""


def parcelamentos_incompletos_conn(conn, transacao_ids):
    """Parcelamentos (parcelamento_id) dos quais o conjunto alvo leva só PARTE.

    Considera apenas o vínculo explícito ``parcelamento_id``; grupos legados
    (sem esse campo) seguem como antes.
    """
    alvo = {int(i) for i in transacao_ids}
    if not alvo or not coluna_existe(conn, "transacoes", "parcelamento_id"):
        return []
    ordenados = sorted(alvo)
    marcadores = ",".join("?" for _ in ordenados)
    grupos = [r[0] for r in conn.execute(
        f"SELECT DISTINCT parcelamento_id FROM transacoes WHERE id IN ({marcadores}) "
        "AND parcelamento_id IS NOT NULL ORDER BY parcelamento_id", ordenados).fetchall()]
    incompletos = []
    for parcelamento_id in grupos:
        membros = [r[0] for r in conn.execute(
            "SELECT id FROM transacoes WHERE parcelamento_id = ? ORDER BY id", (parcelamento_id,)).fetchall()]
        if len(membros) > 1 and not set(membros) <= alvo:
            incompletos.append({
                "parcelamento_id": parcelamento_id,
                "ids": membros,
                "selecionados": [i for i in membros if i in alvo],
            })
    return incompletos


def mensagem_exclusao_parcial_parcelamento(incompletos):
    linhas = [
        "⚠️ Exclusão parcial de parcelamento bloqueada",
        "",
        "Nada foi apagado.",
        "",
    ]
    for grupo in incompletos:
        linhas.append(
            f"Parcelamento P{grupo['parcelamento_id']}: a seleção inclui "
            f"{len(grupo['selecionados'])} de {len(grupo['ids'])} parcelas "
            f"(#{grupo['ids'][0]} a #{grupo['ids'][-1]})."
        )
    linhas += [
        "",
        "Apagar só parte das parcelas deixaria o parcelamento incompleto.",
        "Para apagar a compra inteira, envie:",
    ]
    linhas += [f"apagar parcelamento P{grupo['parcelamento_id']}" for grupo in incompletos]
    linhas += ["", "Para ajustar uma parcela, use: corrigir valor ID para VALOR"]
    return "\n".join(linhas)


def _bloquear_exclusao_parcial_parcelamento(conn, transacao_ids):
    incompletos = parcelamentos_incompletos_conn(conn, transacao_ids)
    if incompletos:
        raise ExclusaoParcialParcelamentoError(mensagem_exclusao_parcial_parcelamento(incompletos))


def apagar_ultima_transacao():
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        ultima = conn.execute("""
            SELECT *
            FROM transacoes
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if not ultima:
            return None

        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [ultima["id"]])
        _bloquear_exclusao_parcial_parcelamento(conn, [ultima["id"]])
        conn.execute("DELETE FROM transacoes WHERE id = ?", (ultima["id"],))
        conn.commit()
        return ultima


def resumo_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        totais = conn.execute(f"""
            SELECT tipo, SUM(valor) AS total
            FROM transacoes
            WHERE ({sql_competencia(conn)}) = ?
            GROUP BY tipo
        """, (ano_mes,)).fetchall()

        categorias = conn.execute(f"""
            SELECT categoria, SUM(valor) AS total
            FROM transacoes
            WHERE ({sql_competencia(conn)}) = ?
              AND tipo = 'despesa'
            GROUP BY categoria
            ORDER BY total DESC
        """, (ano_mes,)).fetchall()

        return totais, categorias


def total_por_tipo_mes(ano_mes: str, tipo: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(f"""
            SELECT SUM(valor) AS total
            FROM transacoes
            WHERE ({sql_competencia(conn)}) = ?
              AND tipo = ?
        """, (ano_mes, tipo)).fetchone()
        return row["total"] or 0


def total_por_categoria_mes(ano_mes: str, categoria: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(f"""
            SELECT SUM(valor) AS total
            FROM transacoes
            WHERE ({sql_competencia(conn)}) = ?
              AND tipo = 'despesa'
              AND lower(categoria) = lower(?)
        """, (ano_mes, categoria)).fetchone()
        return row["total"] or 0


def total_gastos_por_data(data: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT SUM(valor) AS total
            FROM transacoes
            WHERE data = ?
              AND tipo = 'despesa'
        """, (data,)).fetchone()
        return row["total"] or 0


def atualizar_categoria_ultima_transacao(nova_categoria: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        ultima = conn.execute("""
            SELECT *
            FROM transacoes
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if not ultima:
            return None

        conn.execute("UPDATE transacoes SET categoria = ? WHERE id = ?", (canonicalizar_categoria(nova_categoria, "Outros"), ultima["id"]))
        conn.commit()
        return conn.execute("SELECT * FROM transacoes WHERE id = ?", (ultima["id"],)).fetchone()


def buscar_transacao_por_id(transacao_id: int):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()


def _linhas_auditoria(linhas):
    return [dict(linha) for linha in linhas]


def _auditar_comando_conn(conn, entidade, entidade_id, operacao, antes=None, depois=None):
    """Auditoria de comandos de edição/exclusão, na MESMA transação da escrita.

    Usa entidades próprias (``transacao_cmd``, ``compromisso_cmd``,
    ``meta_cmd``) que nenhum leitor de ``auditoria_eventos`` consulta; se o
    INSERT falhar, a exceção sobe e a escrita é desfeita junto.
    """
    registrar_auditoria(entidade, entidade_id, operacao, dados_antes=antes, dados_depois=depois, conn=conn)


def apagar_transacao_por_id(transacao_id: int):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [transacao_id])
        conn.row_factory = sqlite3.Row
        transacao = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()

        if not transacao:
            return None

        _bloquear_exclusao_parcial_parcelamento(conn, [transacao_id])
        conn.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))
        _auditar_comando_conn(conn, "transacao_cmd", transacao_id, "apagada", antes=dict(transacao))
        conn.commit()
        return transacao


def apagar_transacoes_por_ids(transacao_ids):
    """Apaga um conjunto de transações de forma atômica (tudo ou nada).

    Mesmas regras de ``apagar_transacao_por_id``: conciliação é verificada para
    todos os IDs antes de qualquer DELETE. Usado por parcelamentos, que antes
    apagavam parcela a parcela e podiam ficar pela metade.
    """
    ids = sorted({int(i) for i in transacao_ids})
    if not ids:
        return []
    marcadores = ",".join("?" for _ in ids)
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        transacoes = conn.execute(
            f"SELECT * FROM transacoes WHERE id IN ({marcadores}) ORDER BY id", ids
        ).fetchall()
        if not transacoes:
            return []
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [t["id"] for t in transacoes])
        conn.execute(f"DELETE FROM transacoes WHERE id IN ({marcadores})", ids)
        _auditar_comando_conn(conn, "transacao_cmd", ",".join(str(t["id"]) for t in transacoes),
                              "apagadas_lote", antes=_linhas_auditoria(transacoes))
        conn.commit()
        return transacoes


def apagar_transacoes_por_intervalo_ids(id_inicio: int, id_fim: int):
    if id_inicio > id_fim:
        id_inicio, id_fim = id_fim, id_inicio

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        transacoes = conn.execute("""
            SELECT *
            FROM transacoes
            WHERE id BETWEEN ? AND ?
            ORDER BY id
        """, (id_inicio, id_fim)).fetchall()

        if not transacoes:
            return []

        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [t["id"] for t in transacoes])
        _bloquear_exclusao_parcial_parcelamento(conn, [t["id"] for t in transacoes])
        conn.execute("DELETE FROM transacoes WHERE id BETWEEN ? AND ?", (id_inicio, id_fim))
        _auditar_comando_conn(conn, "transacao_cmd", f"{id_inicio}-{id_fim}", "apagadas_faixa",
                              antes=_linhas_auditoria(transacoes))
        conn.commit()
        return transacoes


def atualizar_categoria_por_id(transacao_id: int, nova_categoria: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        transacao = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()

        if not transacao:
            return None

        conn.execute("UPDATE transacoes SET categoria = ? WHERE id = ?", (canonicalizar_categoria(nova_categoria, "Outros"), transacao_id))
        depois = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()
        _auditar_comando_conn(conn, "transacao_cmd", transacao_id, "categoria_alterada",
                              antes=dict(transacao), depois=dict(depois))
        conn.commit()
        return depois


def atualizar_categoria_por_intervalo_ids(id_inicio: int, id_fim: int, nova_categoria: str):
    id_inicio, id_fim = min(id_inicio, id_fim), max(id_inicio, id_fim)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        transacoes = conn.execute("SELECT * FROM transacoes WHERE id BETWEEN ? AND ? ORDER BY id", (id_inicio, id_fim)).fetchall()
        if not transacoes:
            return []
        conn.execute("UPDATE transacoes SET categoria = ? WHERE id BETWEEN ? AND ?",
                     (canonicalizar_categoria(nova_categoria, "Outros"), id_inicio, id_fim))
        depois = conn.execute("SELECT * FROM transacoes WHERE id BETWEEN ? AND ? ORDER BY id", (id_inicio, id_fim)).fetchall()
        _auditar_comando_conn(conn, "transacao_cmd", f"{id_inicio}-{id_fim}", "categoria_alterada_faixa",
                              antes=_linhas_auditoria(transacoes), depois=_linhas_auditoria(depois))
        conn.commit()
        return depois


def atualizar_categoria_em_lote(categorias_antes: dict, nova_categoria: str):
    """{id: categoria vista na prévia} -> nova categoria, numa transação; falha fechado se algo mudou; audita item a item."""
    ids = sorted(int(i) for i in categorias_antes)
    marcas, nova = ",".join("?" * len(ids)), canonicalizar_categoria(nova_categoria, "Outros")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE");conn.row_factory = sqlite3.Row
        antes = conn.execute(f"SELECT * FROM transacoes WHERE id IN ({marcas}) ORDER BY id", ids).fetchall()
        if not ids or len(antes) != len(ids) or any(r["categoria"] != categorias_antes[r["id"]] for r in antes):
            raise ValueError("Os lançamentos mudaram desde a prévia. Faça a busca de novo. Nada foi alterado.")
        conn.execute(f"UPDATE transacoes SET categoria = ? WHERE id IN ({marcas})", [nova, *ids])
        depois = conn.execute(f"SELECT * FROM transacoes WHERE id IN ({marcas}) ORDER BY id", ids).fetchall()
        for a, d in zip(antes, depois):
            _auditar_comando_conn(conn, "transacao_cmd", a["id"], "categoria_alterada_lote", antes=dict(a), depois=dict(d))
        conn.commit()
        return depois


def atualizar_conta_por_id(transacao_id: int, nova_conta: str):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [transacao_id])
        columns = {r[1] for r in conn.execute('PRAGMA table_info(transacoes)')}
        if 'competencia_fatura' in columns:
            row = conn.execute('SELECT competencia_fatura, substr(data,1,7) FROM transacoes WHERE id=?', (transacao_id,)).fetchone()
            if row and row[0] and row[0] != row[1]:
                raise ValueError('Este registro tem fatura escolhida. Para trocar conta ou forma, desfaça/cancele a compra e registre novamente com a fatura correta.')

        conn.row_factory = sqlite3.Row
        transacao = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()

        if not transacao:
            return None

        conn.execute("UPDATE transacoes SET conta = ? WHERE id = ?", (nova_conta, transacao_id))
        depois = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()
        _auditar_comando_conn(conn, "transacao_cmd", transacao_id, "conta_alterada",
                              antes=dict(transacao), depois=dict(depois))
        conn.commit()
        return depois


def atualizar_forma_por_id(transacao_id: int, nova_forma: str):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [transacao_id])
        columns = {r[1] for r in conn.execute('PRAGMA table_info(transacoes)')}
        if 'competencia_fatura' in columns:
            row = conn.execute('SELECT competencia_fatura, substr(data,1,7) FROM transacoes WHERE id=?', (transacao_id,)).fetchone()
            if row and row[0] and row[0] != row[1]:
                raise ValueError('Este registro tem fatura escolhida. Para trocar conta ou forma, desfaça/cancele a compra e registre novamente com a fatura correta.')

        conn.row_factory = sqlite3.Row
        transacao = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()

        if not transacao:
            return None

        conn.execute("UPDATE transacoes SET forma_pagamento = ? WHERE id = ?", (nova_forma, transacao_id))
        if 'competencia_fatura' in columns:
            from faturas_competencia import normalizar
            if normalizar(nova_forma) not in {'credito','cartao','cartao de credito'}:
                conn.execute('UPDATE transacoes SET data_compra=NULL, competencia_fatura=NULL WHERE id=?', (transacao_id,))
        depois = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()
        _auditar_comando_conn(conn, "transacao_cmd", transacao_id, "forma_alterada",
                              antes=dict(transacao), depois=dict(depois))
        conn.commit()
        return depois


def atualizar_valor_por_id(transacao_id: int, novo_valor: float):
    try:
        valor_valido = math.isfinite(float(novo_valor)) and float(novo_valor) > 0
    except (TypeError, ValueError):
        valor_valido = False
    if not valor_valido:
        raise ValueError("valor inválido; use um número finito maior que zero")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [transacao_id])
        conn.row_factory = sqlite3.Row
        transacao = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()

        if not transacao:
            return None

        conn.execute("UPDATE transacoes SET valor = ? WHERE id = ?", (novo_valor, transacao_id))
        # Parcela de um parcelamento: o total gravado acompanha a correção
        # (total + diferença), na mesma transação, para não ficar defasado.
        colunas = transacao.keys()
        parcelamento_id = transacao["parcelamento_id"] if "parcelamento_id" in colunas else None
        total_atual = transacao["valor_total_parcelamento"] if "valor_total_parcelamento" in colunas else None
        totais_antes = []
        if parcelamento_id is not None and total_atual is not None:
            from decimal import Decimal
            diferenca = Decimal(str(novo_valor)) - Decimal(str(transacao["valor"]))
            for linha in conn.execute(
                "SELECT id, valor_total_parcelamento FROM transacoes "
                "WHERE parcelamento_id = ? AND valor_total_parcelamento IS NOT NULL",
                (parcelamento_id,),
            ).fetchall():
                novo_total = (Decimal(str(linha["valor_total_parcelamento"])) + diferenca).quantize(Decimal("0.01"))
                totais_antes.append({"id": linha["id"], "valor_total_parcelamento": linha["valor_total_parcelamento"],
                                     "novo_valor_total_parcelamento": float(novo_total)})
                conn.execute("UPDATE transacoes SET valor_total_parcelamento = ? WHERE id = ?",
                             (float(novo_total), linha["id"]))
        depois = conn.execute("SELECT * FROM transacoes WHERE id = ?", (transacao_id,)).fetchone()
        dados_depois = dict(depois)
        if totais_antes:
            dados_depois["totais_parcelamento_ajustados"] = totais_antes
        _auditar_comando_conn(conn, "transacao_cmd", transacao_id, "valor_alterado",
                              antes=dict(transacao), depois=dados_depois)
        conn.commit()
        return depois


def definir_meta(categoria: str, valor: float):
    valor = _validar_valor_monetario(valor, "meta", permitir_zero=True)
    categoria = canonicalizar_categoria(categoria, "Outros")
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM metas
            WHERE lower(categoria) = lower(?)
        """, (categoria,)).fetchone()

        if existente:
            conn.execute("""
                UPDATE metas
                SET valor = ?, atualizado_em = ?
                WHERE id = ?
            """, (valor, agora, existente["id"]))
        else:
            conn.execute("""
                INSERT INTO metas (categoria, valor, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?)
            """, (categoria, valor, agora, agora))

        depois = conn.execute("""
            SELECT *
            FROM metas
            WHERE lower(categoria) = lower(?)
        """, (categoria,)).fetchone()
        _auditar_comando_conn(conn, "meta_cmd", depois["id"], "meta_definida",
                              antes=dict(existente) if existente else None, depois=dict(depois))
        conn.commit()
        return depois


def listar_metas():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM metas ORDER BY categoria").fetchall()


def buscar_meta_por_categoria(categoria: str):
    categoria = canonicalizar_categoria(categoria, "Outros")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT *
            FROM metas
            WHERE lower(categoria) = lower(?)
        """, (categoria,)).fetchone()


def apagar_meta_por_categoria(categoria: str):
    categoria = canonicalizar_categoria(categoria, "Outros")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        meta = conn.execute("""
            SELECT *
            FROM metas
            WHERE lower(categoria) = lower(?)
        """, (categoria,)).fetchone()

        if not meta:
            return None

        conn.execute("DELETE FROM metas WHERE id = ?", (meta["id"],))
        _auditar_comando_conn(conn, "meta_cmd", meta["id"], "meta_apagada", antes=dict(meta))
        conn.commit()
        return meta


def inserir_compromisso(compromisso: dict) -> int:
    compromisso = dict(compromisso)
    compromisso["valor"] = _validar_valor_monetario(compromisso.get("valor"), "compromisso", permitir_zero=True)
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO compromissos (
                tipo,
                nome,
                categoria,
                conta_pagamento,
                forma_pagamento,
                valor,
                dia_vencimento,
                data_inicio,
                data_fim,
                parcelas_total,
                ativo,
                origem,
                observacao,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            compromisso["tipo"],
            compromisso["nome"],
            canonicalizar_categoria(compromisso["categoria"], "Outros"),
            compromisso.get("conta_pagamento"),
            compromisso.get("forma_pagamento"),
            compromisso["valor"],
            compromisso.get("dia_vencimento"),
            compromisso["data_inicio"],
            compromisso.get("data_fim"),
            compromisso.get("parcelas_total"),
            1 if compromisso.get("ativo", True) else 0,
            compromisso.get("origem"),
            compromisso.get("observacao"),
            agora,
            agora
        ))
        conn.commit()
        return cursor.lastrowid


def listar_compromissos(tipo: str | None = None, somente_ativos: bool = False):
    sql = "SELECT * FROM compromissos WHERE 1=1"
    params = []

    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)

    if somente_ativos:
        sql += " AND ativo = 1"

    sql += " ORDER BY ativo DESC, tipo, conta_pagamento, dia_vencimento, nome, id"

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchall()


def buscar_compromisso_por_id(compromisso_id: int):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()


def atualizar_valor_compromisso(compromisso_id: int, novo_valor: float):
    novo_valor = _validar_valor_monetario(novo_valor, "compromisso", permitir_zero=True)
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_compromisso
        bloquear_alteracao_compromisso(conn, compromisso_id)
        conn.row_factory = sqlite3.Row
        compromisso = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()

        if not compromisso:
            return None

        conn.execute("""
            UPDATE compromissos
            SET valor = ?, atualizado_em = ?
            WHERE id = ?
        """, (novo_valor, agora, compromisso_id))
        conn.commit()
        return conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()


def atualizar_vencimento_compromisso(compromisso_id: int, novo_dia: int):
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        compromisso = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()

        if not compromisso:
            return None

        conn.execute("""
            UPDATE compromissos
            SET dia_vencimento = ?, atualizado_em = ?
            WHERE id = ?
        """, (novo_dia, agora, compromisso_id))
        conn.commit()
        return conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()


def atualizar_campo_compromisso(compromisso_id: int, campo: str, valor):
    campos_permitidos = {
        "conta_pagamento",
        "forma_pagamento",
        "categoria",
    }

    if campo not in campos_permitidos:
        raise ValueError(f"Campo não permitido para atualização: {campo}")

    if campo == "categoria":
        valor = canonicalizar_categoria(valor, "Outros")

    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Categoria e conta de pagamento nao invalidam as conciliacoes: o vinculo guarda o
        # movimento (lancamento) e so confere a assinatura do compromisso na hora de vincular.
        if campo not in {"categoria", "conta_pagamento"}:
            from conciliacao import bloquear_alteracao_compromisso
            bloquear_alteracao_compromisso(conn, compromisso_id)
        conn.row_factory = sqlite3.Row
        compromisso = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()

        if not compromisso:
            return None

        conn.execute(f"""
            UPDATE compromissos
            SET {campo} = ?, atualizado_em = ?
            WHERE id = ?
        """, (valor, agora, compromisso_id))
        # Modelo canônico: a leitura prioriza conta_origem. Se ela já está
        # preenchida, a troca de conta precisa atualizá-la também (sem backfill
        # quando estava vazia).
        if campo == "conta_pagamento" and compromisso["conta_origem"] is not None:
            conn.execute(
                "UPDATE compromissos SET conta_origem = ? WHERE id = ?",
                (valor, compromisso_id),
            )
        conn.commit()

        return conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()


def definir_status_compromisso(compromisso_id: int, ativo: bool):
    agora = relogio.agora().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_compromisso
        bloquear_alteracao_compromisso(conn, compromisso_id)
        conn.row_factory = sqlite3.Row
        compromisso = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()

        if not compromisso:
            return None

        from fixos_vigencia import garantir_sem_sobreposicao
        garantir_sem_sobreposicao(conn,compromisso_id,dict(compromisso,ativo=int(ativo)))

        conn.execute("""
            UPDATE compromissos
            SET ativo = ?, atualizado_em = ?
            WHERE id = ?
        """, (1 if ativo else 0, agora, compromisso_id))
        depois = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()
        _auditar_comando_conn(conn, "compromisso_cmd", compromisso_id, "reativado" if ativo else "pausado",
                              antes=dict(compromisso), depois=dict(depois))
        conn.commit()
        return depois


class ExclusaoCompromissoBloqueadaError(ValueError):
    """Exclusão de compromisso recusada (nada é apagado)."""


PREFIXO_EXCLUSAO_FIXO_SERIE = "⚠️ Exclusão bloqueada: fixo com histórico de versões"


def bloqueio_exclusao_fixo_serie_conn(conn, compromisso, hoje=None):
    """Mensagem de recusa ao apagar uma versão de fixo (série de 'nova condição')
    que já tem meses passados; None quando a exclusão pode seguir.

    Apagar a versão apagaria também as projeções dos meses já vividos. A série
    é identificada pela auditoria (fixos_vigencia.ids_da_serie)."""
    compromisso = dict(compromisso)
    if compromisso.get("tipo") != "fixo":
        return None
    from fixos_vigencia import ids_da_serie
    ident = int(compromisso["id"])
    try:
        serie = ids_da_serie(conn, ident)
    except ValueError as exc:
        return "\n".join([PREFIXO_EXCLUSAO_FIXO_SERIE, "", "Nada foi apagado.", "", str(exc)])
    # Versões já apagadas continuam na auditoria; contam só as existentes.
    serie = {i for i in serie if i == ident or conn.execute(
        "SELECT 1 FROM compromissos WHERE id = ?", (i,)).fetchone()}
    mes_atual = (hoje or relogio.hoje()).strftime("%Y-%m")
    inicio = str(compromisso.get("data_inicio") or "")
    if len(serie) <= 1 or not inicio or inicio[:7] >= mes_atual:
        return None
    versoes = ", ".join(f"#C{i}" for i in sorted(serie))
    linhas = [
        PREFIXO_EXCLUSAO_FIXO_SERIE,
        "",
        "Nada foi apagado.",
        "",
        f"#C{ident} · {compromisso.get('nome')} é uma versão do fixo {versoes} e vale desde {inicio[:7]}.",
        "Apagar removeria os meses já passados das projeções e do checklist.",
        "",
    ]
    fim = compromisso.get("data_fim")
    if fim and str(fim) < (hoje or relogio.hoje()).isoformat():
        linhas.append(f"Esta versão já está encerrada em {fim}; ela só aparece nos meses em que valeu.")
    else:
        linhas += [
            "Para encerrar mantendo o histórico, envie:",
            f"alterar término fixo {ident} para DD/MM/AAAA",
            f"Para apenas suspender (some de todos os meses enquanto pausado): pausar fixo {ident}",
        ]
    return "\n".join(linhas)


def apagar_compromisso_por_id(compromisso_id: int):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        from conciliacao import bloquear_alteracao_compromisso
        bloquear_alteracao_compromisso(conn, compromisso_id)
        conn.row_factory = sqlite3.Row
        compromisso = conn.execute("SELECT * FROM compromissos WHERE id = ?", (compromisso_id,)).fetchone()

        if not compromisso:
            return None

        bloqueio = bloqueio_exclusao_fixo_serie_conn(conn, compromisso)
        if bloqueio:
            raise ExclusaoCompromissoBloqueadaError(bloqueio)

        conn.execute("DELETE FROM compromissos WHERE id = ?", (compromisso_id,))
        # O checklist guarda status/datas por chave (C<id>; P<id> para
        # parcelamentos). Sem o compromisso, essas linhas ficariam órfãs.
        chaves = (f"C{int(compromisso_id)}", f"P{int(compromisso_id)}")
        checklist_removido = {}
        for tabela in ("checklist_pagamentos", "checklist_datas_pagamento", "checklist_datas_pagamento_padrao"):
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone():
                linhas = conn.execute(f"SELECT * FROM {tabela} WHERE item_chave IN (?, ?)", chaves).fetchall()
                if linhas:
                    checklist_removido[tabela] = _linhas_auditoria(linhas)
                conn.execute(f"DELETE FROM {tabela} WHERE item_chave IN (?, ?)", chaves)
        antes = dict(compromisso)
        if checklist_removido:
            antes["checklist_removido"] = checklist_removido
        _auditar_comando_conn(conn, "compromisso_cmd", compromisso_id, "apagado", antes=antes)
        conn.commit()
        return compromisso


def apagar_compromissos_por_origem(origem: str):
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        compromissos = conn.execute("SELECT * FROM compromissos WHERE origem = ?", (origem,)).fetchall()

        if not compromissos:
            return []

        from conciliacao import bloquear_alteracao_compromisso
        for vinculado in compromissos:
            bloquear_alteracao_compromisso(conn, vinculado["id"])
        conn.execute("DELETE FROM compromissos WHERE origem = ?", (origem,))
        conn.commit()
        return compromissos



def substituir_compromissos_por_origem(origem: str, compromissos: list[dict]):
    """Substitui uma importação inteira de forma atômica."""
    agora = relogio.agora().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        anteriores = conn.execute("SELECT * FROM compromissos WHERE origem = ?", (origem,)).fetchall()
        from conciliacao import bloquear_alteracao_compromisso
        for vinculado in anteriores:
            bloquear_alteracao_compromisso(conn, vinculado["id"])
        conn.execute("DELETE FROM compromissos WHERE origem = ?", (origem,))
        ids = []
        for compromisso in compromissos:
            cursor = conn.execute("""
                INSERT INTO compromissos (
                    tipo, nome, categoria, conta_pagamento, forma_pagamento, valor,
                    dia_vencimento, data_inicio, data_fim, parcelas_total, ativo, origem,
                    observacao, criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                compromisso["tipo"], compromisso["nome"], canonicalizar_categoria(compromisso["categoria"], "Outros"),
                compromisso.get("conta_pagamento"), compromisso.get("forma_pagamento"),
                float(compromisso["valor"]), compromisso.get("dia_vencimento"),
                compromisso["data_inicio"], compromisso.get("data_fim"),
                compromisso.get("parcelas_total"), 1 if compromisso.get("ativo", True) else 0,
                compromisso.get("origem") or origem, compromisso.get("observacao"), agora, agora
            ))
            ids.append(cursor.lastrowid)
        return {"apagados": len(anteriores), "ids": ids}


FATURA_TIPOS_VALIDOS = {"pagamento_parcial", "pagamento_total", "estorno", "credito"}

def _validar_ano_mes_db(valor: str) -> str:
    try:
        dt = datetime.strptime(str(valor), "%Y-%m")
    except ValueError as exc:
        raise ValueError("competência inválida; use AAAA-MM") from exc
    return dt.strftime("%Y-%m")

def _validar_fatura_movimento(movimento: dict) -> dict:
    dados = dict(movimento)
    dados["ano_mes"] = _validar_ano_mes_db(dados.get("ano_mes"))
    tipo = str(dados.get("tipo_movimento") or "").strip()
    if tipo not in FATURA_TIPOS_VALIDOS:
        raise ValueError("tipo de movimento de fatura inválido")
    valor = float(dados.get("valor") or 0)
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError("valor do movimento deve ser maior que zero")
    dados["valor"] = round(valor, 2)
    try:
        dados["data_movimento"] = datetime.strptime(str(dados.get("data_movimento")), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("data do movimento inválida") from exc
    if tipo.startswith("pagamento") and not str(dados.get("conta_origem") or "").strip():
        raise ValueError("conta de origem é obrigatória para pagamentos")
    return dados



def inserir_fatura_movimento(movimento: dict) -> int:
    with get_connection() as conn:
        movimento_id = inserir_fatura_movimento_conn(conn, movimento)
        conn.commit()
        return movimento_id


def listar_fatura_movimentos(ano_mes: str | None = None, conta_cartao: str | None = None):
    sql = "SELECT * FROM fatura_movimentos WHERE 1=1"
    params = []
    if ano_mes:
        sql += " AND ano_mes = ?"
        params.append(ano_mes)
    if conta_cartao:
        sql += " AND lower(conta_cartao) = lower(?)"
        params.append(conta_cartao)
    sql += " ORDER BY data_movimento, id"
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchall()


def buscar_fatura_movimento_por_id(movimento_id: int):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM fatura_movimentos WHERE id = ?",
            (movimento_id,)
        ).fetchone()


def atualizar_fatura_movimento(movimento_id: int, usuario_sessao: str | None = None, origem: str | None = None, **campos):
    permitidos = {
        "ano_mes", "conta_cartao", "tipo_movimento", "valor",
        "data_movimento", "conta_origem", "descricao", "mensagem_original"
    }
    dados = {k: v for k, v in campos.items() if k in permitidos}
    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        atual = conn.execute("SELECT * FROM fatura_movimentos WHERE id = ?", (movimento_id,)).fetchone()
        if not atual:
            return None
        if not dados:
            return atual
        combinado = dict(atual)
        combinado.update(dados)
        combinado = _validar_fatura_movimento(combinado)
        agora = relogio.agora().isoformat(timespec="seconds")
        sets = [f"{campo} = ?" for campo in dados]
        valores = [combinado[campo] for campo in dados]
        sets.append("atualizado_em = ?")
        valores.extend([agora, movimento_id])
        conn.execute(f"UPDATE fatura_movimentos SET {', '.join(sets)} WHERE id = ?", valores)
        depois = conn.execute("SELECT * FROM fatura_movimentos WHERE id = ?", (movimento_id,)).fetchone()
        registrar_auditoria("fatura_movimento", movimento_id, "atualizacao", dict(atual), dict(depois), origem, usuario_sessao, conn=conn)
        return depois


def apagar_fatura_movimento(movimento_id: int, usuario_sessao: str | None = None, origem: str | None = None):
    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        movimento = conn.execute("SELECT * FROM fatura_movimentos WHERE id = ?", (movimento_id,)).fetchone()
        if not movimento:
            return None
        conn.execute("DELETE FROM fatura_movimentos WHERE id = ?", (movimento_id,))
        registrar_auditoria("fatura_movimento", movimento_id, "exclusao", dict(movimento), None, origem, usuario_sessao, conn=conn)
        return movimento


def registrar_auditoria(entidade: str, entidade_id, operacao: str, dados_antes=None, dados_depois=None, origem: str | None = None, usuario_sessao: str | None = None, conn=None):
    """Registra alteração financeira sem armazenar objetos não serializáveis."""
    def serializar(valor):
        if valor is None:
            return None
        if hasattr(valor, "keys"):
            valor = dict(valor)
        return json.dumps(valor, ensure_ascii=False, default=str, sort_keys=True)

    params = (
        str(entidade), str(entidade_id) if entidade_id is not None else None,
        str(operacao), serializar(dados_antes), serializar(dados_depois),
        origem, usuario_sessao, relogio.agora().isoformat(timespec="seconds"),
    )
    sql = """
        INSERT INTO auditoria_eventos (
            entidade, entidade_id, operacao, dados_antes, dados_depois,
            origem, usuario_sessao, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    if conn is not None:
        conn.execute(sql, params)
        return
    with get_connection() as local_conn:
        local_conn.execute(sql, params)
        local_conn.commit()


def listar_auditoria(entidade: str | None = None, entidade_id=None, limite: int = 100):
    sql = "SELECT * FROM auditoria_eventos WHERE 1=1"
    params = []
    if entidade:
        sql += " AND entidade = ?"
        params.append(entidade)
    if entidade_id is not None:
        sql += " AND entidade_id = ?"
        params.append(str(entidade_id))
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limite), 1000)))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchall()


def buscar_checklist_status_mes(ano_mes: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT *
            FROM checklist_pagamentos
            WHERE ano_mes = ?
        """, (ano_mes,)).fetchall()

        return {row["item_chave"]: row for row in rows}


def marcar_checklist_pagamento(ano_mes: str, item_chave: str, status: str, observacao: str | None = None):
    agora = relogio.agora().isoformat(timespec="seconds")
    status = status if status in ["pago", "pendente"] else "pendente"
    pago_em = agora if status == "pago" else None

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        existente = conn.execute("""
            SELECT *
            FROM checklist_pagamentos
            WHERE ano_mes = ? AND item_chave = ?
        """, (ano_mes, item_chave)).fetchone()

        if existente:
            conn.execute("""
                UPDATE checklist_pagamentos
                SET status = ?, pago_em = ?, observacao = ?, atualizado_em = ?
                WHERE ano_mes = ? AND item_chave = ?
            """, (status, pago_em, observacao, agora, ano_mes, item_chave))
        else:
            conn.execute("""
                INSERT INTO checklist_pagamentos (
                    ano_mes, item_chave, status, pago_em, observacao, criado_em, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ano_mes, item_chave, status, pago_em, observacao, agora, agora))

        conn.commit()

        return conn.execute("""
            SELECT *
            FROM checklist_pagamentos
            WHERE ano_mes = ? AND item_chave = ?
        """, (ano_mes, item_chave)).fetchone()


def resetar_checklist_pagamentos_mes(ano_mes: str):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM checklist_pagamentos WHERE ano_mes = ?", (ano_mes,))
        conn.commit()
        return cursor.rowcount
