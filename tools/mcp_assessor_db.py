"""Servidor MCP (stdio, só biblioteca padrão) para inspecionar o banco do assessor.

Somente leitura: abre o SQLite com mode=ro + PRAGMA query_only e aceita apenas
SELECT/PRAGMA de leitura. Por padrão usa data/financeiro.db; defina
ASSESSOR_MCP_DB para apontar a uma cópia.
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("ASSESSOR_MCP_DB") or BASE / "data" / "financeiro.db")
MAX_ROWS = 200
PROIBIDO = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|vacuum|reindex|pragma\s+\w+\s*=)\b", re.I)

TOOLS = [
    {"name": "listar_tabelas", "description": "Lista tabelas do banco com contagem de linhas.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "esquema", "description": "Mostra o CREATE de uma tabela (ou de todas).",
     "inputSchema": {"type": "object", "properties": {"tabela": {"type": "string"}}}},
    {"name": "consultar", "description": "Executa um SELECT somente leitura (máx. 200 linhas).",
     "inputSchema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}},
    {"name": "checar_integridade", "description": "PRAGMA integrity_check e foreign_key_check.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def conectar():
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def executar(nome, args):
    con = conectar()
    try:
        if nome == "listar_tabelas":
            tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY 1")]
            return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tabs}
        if nome == "esquema":
            q = "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL"
            p = ()
            if args.get("tabela"):
                q += " AND (name=? OR tbl_name=?)"
                p = (args["tabela"], args["tabela"])
            return [{"nome": n, "sql": s} for n, s in con.execute(q, p)]
        if nome == "consultar":
            sql = args["sql"].strip().rstrip(";")
            if ";" in sql or not re.match(r"^(select|with)\b", sql, re.I) or PROIBIDO.search(sql):
                raise ValueError("Apenas um SELECT de leitura é permitido.")
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description or []]
            rows = cur.fetchmany(MAX_ROWS)
            return {"colunas": cols, "linhas": rows, "truncado": len(rows) == MAX_ROWS}
        if nome == "checar_integridade":
            return {"integrity_check": [r[0] for r in con.execute("PRAGMA integrity_check")],
                    "foreign_key_check": [list(r) for r in con.execute("PRAGMA foreign_key_check")]}
        raise ValueError("Ferramenta desconhecida: " + nome)
    finally:
        con.close()


def responder(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = {"code": -32000, "message": str(error)}
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out, default=str) + "\n")
    sys.stdout.flush()


def main():
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            msg = json.loads(linha)
        except ValueError:
            continue
        metodo, mid = msg.get("method"), msg.get("id")
        if mid is None:
            continue  # notificações (ex.: notifications/initialized)
        if metodo == "initialize":
            responder(mid, {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2024-11-05"),
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "assessor-db", "version": "1.0"}})
        elif metodo == "tools/list":
            responder(mid, {"tools": TOOLS})
        elif metodo == "tools/call":
            p = msg.get("params", {})
            try:
                dados = executar(p.get("name"), p.get("arguments") or {})
                responder(mid, {"content": [{"type": "text", "text": json.dumps(dados, ensure_ascii=False, default=str)}]})
            except Exception as exc:
                responder(mid, {"content": [{"type": "text", "text": f"Erro: {exc}"}], "isError": True})
        elif metodo == "ping":
            responder(mid, {})
        else:
            responder(mid, error=f"Método não suportado: {metodo}")


if __name__ == "__main__":
    main()
