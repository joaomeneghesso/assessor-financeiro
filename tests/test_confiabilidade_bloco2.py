"""Bloco 2: término de compromissos importados, erros registrados em log,
log em arquivo e aviso de fuso. Cada teste verifica também o que NÃO muda.
"""
import logging
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import compromissos as c
import database as db
import registro_logs
import services as svc
import telegram_experiencia as ux


CSV = """Date,Category,Amount,Note
25/06/2026,Internet,-100,Internet casa
25/07/2026,Internet,-100,Internet casa
20/08/2026,Internet,-100,Internet casa
10/06/2026,Notebook,-300,Notebook loja
10/07/2026,Notebook,-300,Notebook loja
05/08/2026,Notebook,-300,Notebook loja
15/07/2026,Presente,-80,Presente aniversario
31/08/2026,Loja,-250,Geladeira
30/09/2026,Loja,-250,Geladeira
02/11/2026,Loja,-250,Geladeira
"""


class ImportacaoTerminoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv = Path(self.tmp.name) / "t.csv"
        self.csv.write_text(CSV, encoding="utf-8")
        self.preview = c.classificar_csv(self.csv)

    def por_nome(self, trecho):
        itens = self.preview["compromissos"] + self.preview["avulsos"]
        return next(i for i in itens if trecho in i["nome"].lower())

    def ocorre(self, item, mes):
        return c.compromisso_ocorre_no_mes(item, mes)

    def test_fixo_mantem_ultimo_mes_mesmo_pago_antes_do_vencimento(self):
        fixo = self.por_nome("internet")
        self.assertEqual("fixo", fixo["tipo"])
        self.assertEqual(25, fixo["dia_vencimento"])
        self.assertEqual("2026-08-31", fixo["data_fim"])
        self.assertEqual([True, True, True, False],
                         [self.ocorre(fixo, m) for m in ("2026-06", "2026-07", "2026-08", "2026-09")])
        self.assertFalse(self.ocorre(fixo, "2026-05"))

    def test_parcelamento_projeta_todas_as_parcelas(self):
        parc = self.por_nome("notebook")
        self.assertEqual(("parcelamento", 3), (parc["tipo"], parc["parcelas_total"]))
        meses = [m for m in ("2026-05", "2026-06", "2026-07", "2026-08", "2026-09") if self.ocorre(parc, m)]
        self.assertEqual(["2026-06", "2026-07", "2026-08"], meses)

    def test_pagamento_atrasado_que_cruza_o_mes_nao_cria_mes_extra(self):
        # Vencimento dia 31; a 3ª parcela foi paga em 02/11. A regra antiga
        # (data exata) projeta 3 meses; o fim do mês criaria uma 4ª parcela.
        parc = self.por_nome("geladeira")
        self.assertEqual(("parcelamento", 3, "2026-11-02"), (parc["tipo"], parc["parcelas_total"], parc["data_fim"]))
        meses = [m for m in ("2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12") if self.ocorre(parc, m)]
        self.assertEqual(["2026-08", "2026-09", "2026-10"], meses)

    def test_csv_misto_ignora_entradas_positivas(self):
        misto = Path(self.tmp.name) / "m.csv"
        misto.write_text(CSV + "05/06/2026,Salario,5000,Empresa\n05/07/2026,Salario,5000,Empresa\n"
                               "26/06/2026,Internet,100,Internet casa\n", encoding="utf-8")
        preview = c.classificar_csv(misto)
        self.assertEqual(3, preview["ignorados_positivos"])
        self.assertEqual(13, preview["linhas"])
        nomes = [x["nome"].lower() for x in preview["compromissos"] + preview["avulsos"]]
        self.assertFalse(any("empresa" in n or "salario" in n for n in nomes))
        internet = next(x for x in preview["compromissos"] if "internet" in x["nome"].lower())
        self.assertIn("Ocorrências: 3", internet["observacao"])
        self.assertIn("Entradas/estornos ignorados (valores positivos): 3", c.resumir_previa_importacao(preview))
        self.assertNotIn("ignorados", c.resumir_previa_importacao(self.preview))

    def test_avulso_continua_com_a_data_exata(self):
        avulso = self.por_nome("presente")
        self.assertEqual(("avulso", "2026-07-15", "2026-07-15"),
                         (avulso["tipo"], avulso["data_inicio"], avulso["data_fim"]))
        self.assertEqual([False, True, False], [self.ocorre(avulso, m) for m in ("2026-06", "2026-07", "2026-08")])

    def test_extrato_com_valores_negativos_e_positivos(self):
        # Extratos exportam despesas negativas; o valor do compromisso é absoluto.
        self.assertEqual(100.0, self.por_nome("internet")["valor"])
        positivo = Path(self.tmp.name) / "p.csv"
        positivo.write_text(CSV.replace(",-", ","), encoding="utf-8")
        self.assertEqual(
            [(x["nome"], x["valor"], x["data_fim"]) for x in self.preview["compromissos"]],
            [(x["nome"], x["valor"], x["data_fim"]) for x in c.classificar_csv(positivo)["compromissos"]],
        )
        zerado = Path(self.tmp.name) / "z.csv"
        zerado.write_text("Date,Category,Amount,Note\n01/06/2026,X,0,Nada\n", encoding="utf-8")
        self.assertEqual(0, c.classificar_csv(zerado)["linhas"])

    def test_previa_e_observacao_inalteradas(self):
        parc = self.por_nome("notebook")
        self.assertIn("até 2026-08-05", parc["observacao"])
        texto = c.resumir_previa_importacao(self.preview)
        self.assertIn("2026-06 até 2026-08", texto)

    def test_termino_preciso_definido_pelo_usuario_continua_valendo(self):
        # Término escolhido no dia 10 com vencimento dia 15: o mês do término não ocorre.
        manual = dict(tipo="fixo", data_inicio="2026-01-15", data_fim="2026-12-10", dia_vencimento=15)
        self.assertTrue(self.ocorre(manual, "2026-11"))
        self.assertFalse(self.ocorre(manual, "2026-12"))


class ErrosRegistradosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()

    def test_saldo_por_conta_registra_erro_e_mantem_resultado(self):
        normal = svc._calcular_saldo_mensal_etapa("2026-10", "Nubank", True)
        with patch.object(svc, "calcular_caixa_por_conta_mes", side_effect=RuntimeError("falha simulada")):
            with self.assertLogs("assessor.calculos", level="WARNING") as logs:
                com_erro = svc._calcular_saldo_mensal_etapa("2026-10", "Nubank", True)
        self.assertIn("Saldo herdado por conta (2026-10, Nubank)", logs.output[0])
        self.assertEqual(normal["saldo_projetado"], com_erro["saldo_projetado"])

    def test_calculo_normal_nao_gera_log(self):
        with patch.object(svc._LOG_CALCULOS, "warning") as aviso:
            svc._calcular_saldo_mensal_etapa("2026-10", "Nubank", True)
            svc.calcular_caixa_por_conta_mes("2026-10")
        aviso.assert_not_called()

    def test_backup_que_nao_pode_ser_removido_fica_registrado(self):
        pasta = Path(self.tmp.name) / "backups"
        pasta.mkdir()
        import os
        for i in range(3):
            arquivo = pasta / f"financeiro_backup_2026010{i}.db"
            arquivo.write_bytes(b"x")
            os.utime(arquivo, (1_000_000 + i, 1_000_000 + i))  # 0 é o mais antigo
        original_unlink = Path.unlink

        def unlink(self, *a, **k):
            if self.name.endswith("0.db"):
                raise PermissionError("em uso")
            return original_unlink(self, *a, **k)

        with patch.object(svc, "BACKUPS_DIR", pasta), patch.object(Path, "unlink", unlink):
            with self.assertLogs("assessor.calculos", level="WARNING") as logs:
                removidos = svc.remover_backups_antigos(manter=1)
        self.assertEqual(["financeiro_backup_20260101.db"], removidos)
        self.assertIn("financeiro_backup_20260100.db", logs.output[0])
        self.assertTrue((pasta / "financeiro_backup_20260100.db").exists())

    def _resumo_revisao(self, erro):
        metricas = {"revisoes_conciliacao": [dict(tipo="baixa_antiga", compromisso_id=7, mes="2026-10")]}
        engine = ux.Experience()
        with patch.object(svc, "obter_metricas_resultado_mes", return_value=metricas), \
             patch.object(ux.conc, "alvo", side_effect=erro):
            return engine._reconciliation_review_summary("2026-10")

    def test_revisao_conciliacao_erro_esperado_sem_log(self):
        with patch.object(logging, "warning") as aviso:
            _, detalhes, _ = self._resumo_revisao(ux.conc.ConciliacaoError("pausado"))
        aviso.assert_not_called()
        self.assertEqual(0.0, detalhes[0]["valor"])

    def test_revisao_conciliacao_erro_inesperado_registrado(self):
        with self.assertLogs(level="WARNING") as logs:
            _, detalhes, _ = self._resumo_revisao(RuntimeError("bug"))
        self.assertIn("#C7", logs.output[0])
        self.assertEqual(0.0, detalhes[0]["valor"])


class RegistroLogsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        raiz = logging.getLogger()
        self.handlers = list(raiz.handlers)
        self.level = raiz.level
        self.niveis = {n: logging.getLogger(n).level for n in ("httpx", "httpcore")}

    def tearDown(self):
        raiz = logging.getLogger()
        for h in list(raiz.handlers):
            if h not in self.handlers:
                raiz.removeHandler(h)
                h.close()
        for h in self.handlers:
            if h not in raiz.handlers:
                raiz.addHandler(h)
        raiz.setLevel(self.level)
        for n, nivel in self.niveis.items():
            logging.getLogger(n).setLevel(nivel)

    def test_grava_avisos_em_arquivo_sem_duplicar(self):
        raiz = logging.getLogger()
        for h in list(raiz.handlers):
            raiz.removeHandler(h)
        destino = registro_logs.configurar_logs("teste.log", pasta=Path(self.tmp.name))
        self.assertIsNone(registro_logs.configurar_logs("teste.log", pasta=Path(self.tmp.name)))
        marcados = [h for h in raiz.handlers if getattr(h, registro_logs._MARCA, False)]
        self.assertEqual(2, len(marcados))  # console + arquivo
        logging.getLogger("assessor.calculos").info("info não vai para o arquivo")
        logging.getLogger("assessor.calculos").warning("aviso de teste")
        for h in marcados:
            h.flush()
        conteudo = destino.read_text(encoding="utf-8")
        self.assertIn("WARNING assessor.calculos: aviso de teste", conteudo)
        self.assertNotIn("info não vai", conteudo)
        self.assertEqual(logging.WARNING, logging.getLogger("httpx").level)
        self.assertEqual(logging.WARNING, logging.getLogger("httpcore").level)

    def test_pasta_invalida_nao_impede_inicio(self):
        arquivo = Path(self.tmp.name) / "nao_e_pasta"
        arquivo.write_text("x")
        logging.getLogger().handlers[:] = []
        self.assertIsNone(registro_logs.configurar_logs("x.log", pasta=arquivo))

    def test_aviso_de_fuso(self):
        brt = datetime(2026, 10, 13, 23, 30, tzinfo=timezone(timedelta(hours=-3)))
        utc = datetime(2026, 10, 14, 2, 30, tzinfo=timezone.utc)
        self.assertFalse(registro_logs.avisar_se_fuso_divergente(brt))
        with self.assertLogs("assessor.relogio", level="WARNING") as logs:
            self.assertTrue(registro_logs.avisar_se_fuso_divergente(utc))
        self.assertIn("UTC+0000", logs.output[0])


if __name__ == "__main__":
    unittest.main()
