"""Bloco C: auditoria dos comandos de edição (C5), baixa de fatura pelo
checklist (C6) e trava do ajuste legado da fatura Itaú (G1)."""
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import database
import services

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_bloco_c_auditoria", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)



class _ConexaoQueFecha(sqlite3.Connection):
    """Como `with conn`, mas também fecha: no Windows uma conexão aberta
    impede apagar o banco temporário no fim do teste."""
    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            self.close()

def _criar_banco(path):
    old = database.DB_PATH
    database.DB_PATH = path
    try:
        database.init_db()
    finally:
        database.DB_PATH = old
    runner.apply_migrations(path, ROOT / "migrations", path.parent / "mig_backups", executed_by="bloco_c_auditoria")


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (database.DB_PATH, services.DB_PATH, services.BACKUPS_DIR)
        database.DB_PATH = services.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        services.BACKUPS_DIR = Path(self.tmp.name) / "backups"
        _criar_banco(database.DB_PATH)
        services.PENDENCIAS_EXCLUSAO.clear()
        self.sessao = "user1:chat1"

    def tearDown(self):
        database.DB_PATH, services.DB_PATH, services.BACKUPS_DIR = self.old
        self.tmp.cleanup()

    def tx(self, **extra):
        dados = dict(data="2026-07-10", tipo="despesa", valor=10.0, categoria="Mercado",
                     descricao="compra", conta="Nubank", forma_pagamento="pix")
        dados.update(extra)
        return database.inserir_transacao(dados)

    def alterar(self, comando):
        self.assertIn("Responda: confirmar alteracao", services.processar_mensagem(comando, self.sessao))
        return services.processar_mensagem("confirmar alteracao", self.sessao)

    def eventos(self, entidade):
        with sqlite3.connect(database.DB_PATH, factory=_ConexaoQueFecha) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(
                "SELECT * FROM auditoria_eventos WHERE entidade=? ORDER BY id", (entidade,))]

    def total_eventos(self):
        with sqlite3.connect(database.DB_PATH, factory=_ConexaoQueFecha) as conn:
            return conn.execute("SELECT count(*) FROM auditoria_eventos").fetchone()[0]

    def falhar_auditoria(self, entidade):
        with sqlite3.connect(database.DB_PATH, factory=_ConexaoQueFecha) as conn:
            conn.execute(f"CREATE TRIGGER falhar_{entidade} BEFORE INSERT ON auditoria_eventos WHEN NEW.entidade='{entidade}' "
                         "BEGIN SELECT RAISE(ABORT,'falha induzida'); END")


class AuditoriaComandosTests(_Base):
    def test_edicoes_de_transacao_auditam_antes_e_depois(self):
        ident = self.tx()
        # Edições por texto mostram prévia e só gravam com "confirmar alteracao" (Onda 1).
        self.alterar(f"corrigir valor {ident} para 12,34")
        self.alterar(f"mudar {ident} para Lazer")
        self.alterar(f"corrigir conta {ident} para Itaú")
        self.alterar(f"corrigir forma {ident} para débito")
        eventos = self.eventos("transacao_cmd")
        self.assertEqual(["valor_alterado", "categoria_alterada", "conta_alterada", "forma_alterada"],
                         [e["operacao"] for e in eventos])
        self.assertTrue(all(e["entidade_id"] == str(ident) for e in eventos))
        valor = eventos[0]
        self.assertEqual(10.0, json.loads(valor["dados_antes"])["valor"])
        self.assertEqual(12.34, json.loads(valor["dados_depois"])["valor"])
        self.assertEqual("Mercado", json.loads(eventos[1]["dados_antes"])["categoria"])
        self.assertEqual("Lazer", json.loads(eventos[1]["dados_depois"])["categoria"])

    def test_exclusoes_e_faixas_auditam_linhas_removidas(self):
        a, b, c = self.tx(), self.tx(valor=20.0), self.tx(valor=30.0)
        self.alterar(f"mudar {a}-{b} para Lazer")
        services.processar_mensagem(f"apagar {c}", self.sessao)
        services.processar_mensagem("confirmar exclusao", self.sessao)
        services.processar_mensagem(f"apagar {a}-{b}", self.sessao)
        services.processar_mensagem("confirmar exclusao", self.sessao)
        ops = {e["operacao"]: e for e in self.eventos("transacao_cmd")}
        self.assertEqual({"categoria_alterada_faixa", "apagada", "apagadas_faixa"}, set(ops))
        self.assertEqual(30.0, json.loads(ops["apagada"]["dados_antes"])["valor"])
        self.assertEqual([a, b], [r["id"] for r in json.loads(ops["apagadas_faixa"]["dados_antes"])])
        self.assertIsNone(ops["apagadas_faixa"]["dados_depois"])

    def test_metas_e_compromissos_auditam(self):
        self.alterar("meta lazer 300")
        services.processar_mensagem("apagar meta lazer", self.sessao)
        services.processar_mensagem("confirmar exclusao", self.sessao)
        self.assertEqual(["meta_definida", "meta_apagada"], [e["operacao"] for e in self.eventos("meta_cmd")])
        ident = database.inserir_compromisso(dict(tipo="fixo", nome="Academia", categoria="Saúde",
            conta_pagamento="Nubank", forma_pagamento="pix", valor=100.0,
            data_inicio="2026-07-01", dia_vencimento=10, ativo=True))
        self.alterar(f"pausar fixo {ident}")
        self.alterar(f"reativar fixo {ident}")
        services.processar_mensagem(f"apagar fixo {ident}", self.sessao)
        services.processar_mensagem("confirmar exclusao", self.sessao)
        ops = [e["operacao"] for e in self.eventos("compromisso_cmd")]
        self.assertEqual(["pausado", "reativado", "apagado"], ops)
        # Leitores existentes por entidade 'compromissos' não enxergam estes eventos.
        self.assertEqual([], database.listar_auditoria("compromissos", ident))

    def test_falha_na_auditoria_desfaz_a_escrita(self):
        ident = self.tx()
        self.falhar_auditoria("transacao_cmd")
        with self.assertRaises(sqlite3.IntegrityError):
            database.atualizar_valor_por_id(ident, 99.0)
        with self.assertRaises(sqlite3.IntegrityError):
            database.atualizar_categoria_por_id(ident, "Lazer")
        with self.assertRaises(sqlite3.IntegrityError):
            database.apagar_transacao_por_id(ident)
        linha = database.buscar_transacao_por_id(ident)
        self.assertEqual((10.0, "Mercado"), (linha["valor"], linha["categoria"]))
        self.falhar_auditoria("meta_cmd")
        with self.assertRaises(sqlite3.IntegrityError):
            database.definir_meta("Lazer", 300)
        self.assertIsNone(database.buscar_meta_por_categoria("Lazer"))

    def test_mensagens_ao_usuario_inalteradas(self):
        ident = self.tx()
        resposta = self.alterar(f"corrigir valor {ident} para 12,34")
        self.assertTrue(resposta.startswith("💵 Valor atualizado"))
        self.assertNotIn("auditoria", resposta.lower())


class FaturaChecklistTests(_Base):
    def _fatura(self, mes="2026-07"):
        self.tx(data=f"{mes}-05", conta="Itaú", forma_pagamento="crédito", valor=200.0,
                data_compra=f"{mes}-05", competencia_fatura=mes)
        itens = services.aplicar_status_checklist(mes, services.montar_itens_checklist_mes(mes, modo="geral"))
        return next(i for i in itens if i.get("grupo") == "bancos")

    def test_paguei_fatura_com_saldo_nao_marca_e_orienta(self):
        item = self._fatura()
        codigo = item.get("codigo") or item["chave"]
        resposta = services.processar_mensagem(f"paguei {codigo} 2026-07", self.sessao)
        self.assertIn("Nada foi gravado", resposta)
        self.assertIn("paguei o restante da fatura", resposta)
        self.assertEqual({}, dict(database.buscar_checklist_status_mes("2026-07")))
        resposta = services.processar_mensagem(f"paguei {codigo} C99 2026-07", self.sessao)
        self.assertIn("Nenhuma marcação deste lote foi alterada", resposta)
        self.assertEqual({}, dict(database.buscar_checklist_status_mes("2026-07")))

    def test_marcar_pendente_continua_permitido(self):
        item = self._fatura()
        database.marcar_checklist_pagamento("2026-07", item["chave"], "pago")  # marcação legada
        codigo = item.get("codigo") or item["chave"]
        services.processar_mensagem(f"marcar pendente {codigo} 2026-07", self.sessao)
        self.assertEqual("pendente", database.buscar_checklist_status_mes("2026-07")[item["chave"]]["status"])


class AjusteItauLegadoTests(unittest.TestCase):
    def test_recusa_banco_com_competencia_fatura(self):
        from ajustar_fatura_itau import aplicar
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data" / "financeiro.db"
            db.parent.mkdir()
            _criar_banco(db)
            old = database.DB_PATH
            database.DB_PATH = db
            try:
                database.inserir_transacao(dict(data="2026-07-05", tipo="despesa", valor=10.0, categoria="Lazer",
                    descricao="x", conta="Itaú", forma_pagamento="crédito", data_compra="2026-07-05",
                    competencia_fatura="2026-07"))
            finally:
                database.DB_PATH = old
            def estado():
                with sqlite3.connect(db, factory=_ConexaoQueFecha) as conn:
                    return (conn.execute("SELECT * FROM transacoes ORDER BY id").fetchall(),
                            conn.execute("SELECT count(*) FROM auditoria_eventos").fetchone())
            antes = estado()
            for confirmar in (False, True):
                with self.assertRaisesRegex(RuntimeError, "competência de fatura explícita"):
                    aplicar(db, confirmar=confirmar)
            self.assertEqual(antes, estado())
            self.assertFalse((Path(tmp) / "backups").exists())
            resumo = aplicar(db, confirmar=False, forcar_legado=True)
            self.assertEqual(1, resumo["transacoes_postergadas"])


if __name__ == "__main__":
    unittest.main()
