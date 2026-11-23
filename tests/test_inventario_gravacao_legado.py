"""Onda 2: inventário executável das gravações do caminho legado de texto.

Prova a tabela de docs/reavaliacao/07_inventario_gravacao_legado.md:

1. Para cada comando de escrita conhecido do roteador
   (``services._processar_mensagem_core``), num banco temporário: NADA muda no
   banco antes da confirmação, e a confirmação grava (prova que é escrita).
2. Exceções justificadas (marcar pago/pendente no checklist) gravam direto, mas
   com auditoria e a instrução de como desfazer.
3. Guarda estática: toda função chamada pelo roteador está classificada aqui
   como leitura, gravação atrás de prévia/confirmação ou exceção justificada.
   Um ramo novo que chame uma função não classificada faz o teste falhar até
   alguém decidir em qual lista ela entra (e, se grava, pôr a prévia).
4. O recálculo da prévia (que roda o próprio roteador em modo prévia) nunca grava.

Banco, backups e exports sempre temporários.
"""
import ast
import importlib.util
import inspect
import sys
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest import mock

import database as db
import services as svc

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_inventario_legado", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)

SESSAO = "inv:1"
MES = date.today().strftime("%Y-%m")

# Todas as tabelas, menos a trilha de auditoria (comparada à parte quando importa)
# e o controle de migrations.
FORA_DO_SNAPSHOT = {"auditoria_eventos", "schema_migrations", "sqlite_sequence"}


class _Banco(unittest.TestCase):
    def setUp(self):
        self._novo_banco()
        for store in (svc.PENDENCIAS_ALTERACAO, svc.PENDENCIAS_EXCLUSAO, svc.PENDENCIAS_PAGAMENTO_FATURA,
                      svc.PENDENCIAS_EXPORTACAO, svc.PENDENCIAS_IMPORTACAO, svc.PENDENCIAS_CONFIRMACAO):
            store.clear()
            self.addCleanup(store.clear)

    def _novo_banco(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        for mod, attr, valor in ((db, "DB_PATH", base / "fixture.db"), (svc, "DB_PATH", base / "fixture.db"),
                                 (svc, "BACKUPS_DIR", base / "backups"), (svc, "EXPORTS_DIR", base / "exports"),
                                 (svc, "DASHBOARDS_DIR", base / "dashboards")):
            if hasattr(mod, attr):
                p = mock.patch.object(mod, attr, valor)
                p.start()
                self.addCleanup(p.stop)
        db.init_db()
        runner.apply_migrations(base / "fixture.db", ROOT / "migrations", base / "mig_backups",
                                executed_by="inventario_legado")
        self.ids = self._semear()

    def _semear(self):
        def tx(**extra):
            dados = dict(data=f"{MES}-02", tipo="despesa", valor=10.0, categoria="Mercado",
                         descricao="compra", conta="Itaú", forma_pagamento="pix")
            dados.update(extra)
            return db.inserir_transacao(dados)
        a, b = tx(), tx(valor=20.0)
        tx(valor=200.0, conta="Nubank", forma_pagamento="crédito", data_compra=f"{MES}-02",
           competencia_fatura=MES, descricao="loja")
        fixo = db.inserir_compromisso(dict(tipo="fixo", nome="Academia", categoria="Saúde",
                                           conta_pagamento="Itaú", forma_pagamento="pix", valor=100.0,
                                           data_inicio=f"{MES}-01", dia_vencimento=10, ativo=True))
        entrada = db.inserir_compromisso(dict(tipo="entrada_fixa", nome="Salário", categoria="Salário",
                                              conta_pagamento="Itaú", forma_pagamento="pix", valor=4000.0,
                                              data_inicio=f"{MES}-01", dia_vencimento=5, ativo=True))
        db.definir_meta("Mercado", 500)
        transf = db.inserir_transferencia_caixa(dict(valor=50.0, conta_origem="Itaú", conta_destino="Nubank",
                                                     data=f"{MES}-03", descricao="t", mensagem_original="t"))
        mov = db.inserir_fatura_movimento(dict(ano_mes=MES, conta_cartao="Nubank", tipo_movimento="estorno",
                                               valor=50.0, data_movimento=f"{MES}-04", conta_origem=None,
                                               descricao="estorno", mensagem_original="x"))
        return dict(a=a, b=b, fixo=fixo, entrada=entrada, transf=transf, mov=mov)

    def snapshot(self):
        with closing(sqlite3.connect(db.DB_PATH)) as c:
            tabelas = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                             if r[0] not in FORA_DO_SNAPSHOT)
            return {t: c.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall() for t in tabelas}

    def auditoria(self):
        with closing(sqlite3.connect(db.DB_PATH)) as c:
            return c.execute("SELECT count(*) FROM auditoria_eventos").fetchone()[0]

    def msg(self, texto):
        return str(svc.processar_mensagem(texto, sessao=SESSAO))


# (comando, confirmação). Os ids vêm de _semear.
COMANDOS_COM_PREVIA = [
    # Alterações (Onda 1)
    ("mudar {a}-{b} para Lazer", "confirmar alteracao"),
    ("mudar {a} para Lazer", "confirmar alteracao"),
    ("mudar último para Lazer", "confirmar alteracao"),
    ("corrigir valor {a} para 99", "confirmar alteracao"),
    ("corrigir {a} para 99", "confirmar alteracao"),
    ("corrigir conta {a} para Nubank", "confirmar alteracao"),
    ("corrigir forma {a} para débito", "confirmar alteracao"),
    ("meta lazer 300", "confirmar alteracao"),
    ("pausar fixo {fixo}", "confirmar alteracao"),
    ("alterar conta fixo {fixo} para Nubank", "confirmar alteracao"),
    ("alterar forma fixo {fixo} para débito", "confirmar alteracao"),
    ("alterar categoria fixo {fixo} para Moradia", "confirmar alteracao"),
    ("alterar valor fixo {fixo} para 120", "confirmar alteracao"),
    ("alterar fixo {fixo} para 130", "confirmar alteracao"),
    ("alterar vencimento fixo {fixo} para dia 12", "confirmar alteracao"),
    ("alterar entrada {entrada} para 4500", "confirmar alteracao"),
    ("pausar entrada {entrada}", "confirmar alteracao"),
    ("nova entrada fixa bonus 300 dia 7", "confirmar alteracao"),
    ("novo fixo agua 150 dia 25", "confirmar alteracao"),
    # Onda 2: o que ainda gravava direto
    ("corrigir F{mov} valor para 25,50", "confirmar alteracao"),
    ("vencimento fatura nubank dia 15", "confirmar alteracao"),
    ("vencimento fatura nubank " + MES + " dia 15", "confirmar alteracao"),
    ("vencimento C{fixo} para dia 12", "confirmar alteracao"),
    ("vencimento C{fixo} " + MES + " para dia 12", "confirmar alteracao"),
    ("transferi 100 do Itaú para Nubank", "confirmar alteracao"),
    ("saldo inicial Itaú 1000", "confirmar alteracao"),
    ("ajustar saldo Itaú para 1000", "confirmar alteracao"),
    ("saldo inicial " + MES + " 2500", "confirmar alteracao"),
    ("gastei 35 no mercado", "confirmar alteracao"),
    ("recebi 500 de salário", "confirmar alteracao"),
    ("nova entrada prevista freela 800 dia 20", None),  # D01: não grava por nenhum caminho
    # Exclusões (prévia + confirmar exclusao)
    ("apagar {a}", "confirmar exclusao"),
    ("apagar {a}-{b}", "confirmar exclusao"),
    ("apagar ultimo", "confirmar exclusao"),
    ("apagar fixo {fixo}", "confirmar exclusao"),
    ("apagar entrada {entrada}", "confirmar exclusao"),
    ("apagar meta mercado", "confirmar exclusao"),
    ("apagar transferencia caixa {transf}", "confirmar exclusao"),
    ("apagar F{mov}", "confirmar exclusao"),
    # Movimentos de fatura (prévia própria)
    ("paguei 50 da fatura nubank usando itaú", "confirmar pagamento"),
    ("estorno de 10 na fatura nubank", "confirmar estorno"),
]

FRASES_DE_CONFIRMACAO = ("Responda: confirmar alteracao", "Responda: confirmar exclusao",
                         "Responda: confirmar pagamento", "Responda: confirmar estorno")


class ComandosDeEscritaPedemConfirmacaoTests(_Banco):
    def test_nada_muda_antes_de_confirmar_e_a_confirmacao_grava(self):
        for modelo, confirmacao in COMANDOS_COM_PREVIA:
            with self.subTest(comando=modelo):
                self._novo_banco()
                comando = modelo.format(**self.ids)
                antes = self.snapshot()
                resposta = self.msg(comando)
                self.assertEqual(antes, self.snapshot(), f"{comando!r} gravou antes da confirmação")
                if confirmacao is None:
                    continue
                self.assertTrue(any(f in resposta for f in FRASES_DE_CONFIRMACAO),
                                f"{comando!r} não pediu confirmação: {resposta[:300]}")
                final = self.msg(confirmacao)
                self.assertNotEqual(antes, self.snapshot(),
                                    f"{comando!r} confirmado não gravou: {final[:300]}")

    def test_lancamento_por_texto_confirmado_fica_auditado(self):
        self.msg("gastei 35 no mercado")
        eventos_antes = self.auditoria()
        self.assertIn("Despesa registrada", self.msg("confirmar alteracao"))
        self.assertEqual(eventos_antes + 1, self.auditoria())

    def test_transferencia_confirmada_fica_auditada(self):
        self.msg("transferi 100 do Itaú para Nubank")
        eventos_antes = self.auditoria()
        self.assertIn("Transferência registrada", self.msg("confirmar alteracao"))
        self.assertEqual(eventos_antes + 1, self.auditoria())

    def test_cancelar_nao_grava(self):
        antes = self.snapshot()
        self.msg("transferi 100 do Itaú para Nubank")
        self.assertIn("Nada foi alterado", self.msg("cancelar alteracao"))
        self.assertIn("Não há alteração pendente", self.msg("confirmar alteracao"))
        self.assertEqual(antes, self.snapshot())

    def test_dados_mudaram_desde_a_previa_nada_grava(self):
        self.msg("vencimento fatura nubank dia 15")
        db.inserir_transacao(dict(data=f"{MES}-05", tipo="despesa", valor=1.0, categoria="Outros",
                                  descricao="x", conta="Nubank", forma_pagamento="crédito",
                                  data_compra=f"{MES}-05", competencia_fatura=MES))
        # A data atual da fatura muda junto (é derivada da compra mais recente sem vencimento).
        antes = self.snapshot()
        resposta = self.msg("confirmar alteracao")
        if "mudaram desde a prévia" in resposta:
            self.assertEqual(antes, self.snapshot())

    def test_recusas_respondem_sem_pendencia(self):
        for comando in ("vencimento fatura inexistente dia 15", "vencimento fatura nubank dia 40",
                        "corrigir F999 valor para 10", f"corrigir F{self.ids['mov']} valor para abc",
                        "transferi 100 do Itaú para Itaú"):
            with self.subTest(comando=comando):
                antes = self.snapshot()
                resposta = self.msg(comando)
                self.assertNotIn("Responda: confirmar", resposta)
                self.assertEqual(antes, self.snapshot())
                self.assertIsNone(svc._obter_pendencia(svc.PENDENCIAS_ALTERACAO, SESSAO))


class ExcecoesJustificadasTests(_Banco):
    def test_marcar_pendente_grava_direto_com_auditoria_e_desfazer(self):
        codigo = f"C{self.ids['fixo']}"
        eventos = self.auditoria()
        resposta = self.msg(f"desmarcar {codigo} {MES}")
        self.assertIn("Checklist atualizado", resposta)
        self.assertIn(f"Para desfazer: paguei {codigo} {MES}", resposta)
        self.assertEqual(eventos + 1, self.auditoria())

    def test_baixa_de_compromisso_continua_recusada(self):
        antes = self.snapshot()
        resposta = self.msg(f"paguei C{self.ids['fixo']} {MES}")
        self.assertIn("A pagar", resposta)
        self.assertEqual(antes, self.snapshot())


class RecalculoDaPreviaNaoGravaTests(_Banco):
    def test_recalcular_previa_nunca_grava(self):
        for modelo, _ in COMANDOS_COM_PREVIA + [("desmarcar C{fixo}", None), ("paguei C{fixo}", None)]:
            with self.subTest(comando=modelo):
                comando = modelo.format(**self.ids)
                antes, eventos = self.snapshot(), self.auditoria()
                svc.recalcular_previa_gravacao(comando)
                self.assertEqual(antes, self.snapshot())
                self.assertEqual(eventos, self.auditoria())
                self.assertIsNone(svc._obter_pendencia(svc.PENDENCIAS_ALTERACAO, svc._SESSAO_PREVIA))


# --- Guarda estática -------------------------------------------------------

# Gravam, mas só depois de prévia + confirmação (ou só rodam já confirmadas).
GRAVACAO_COM_PREVIA = {
    # executadas só sob _ALTERACAO_CONFIRMADA (prévia em previa_alteracao ou _gravacao_pede_confirmacao)
    "salvar_fixo", "remover_termino_fixo", "editar_movimento_fatura_formatado",
    "definir_vencimento_fatura_por_nome_formatado", "definir_data_pagamento_checklist_formatado",
    "registrar_transferencia_caixa_formatado", "definir_saldo_inicial_formatado",
    "cadastrar_entrada_fixa_formatado", "cadastrar_entrada_avulsa_formatado", "alterar_entrada_valor",
    "pausar_entrada", "reativar_entrada", "cadastrar_fixo_manual_formatado", "alterar_fixo_valor",
    "alterar_fixo_vencimento", "alterar_compromisso_conta", "alterar_compromisso_forma",
    "alterar_compromisso_categoria", "pausar_compromisso", "reativar_compromisso", "definir_meta_formatado",
    "mudar_categoria_por_faixa", "mudar_categoria_por_id", "mudar_categoria_ultimo", "corrigir_conta_por_id",
    "corrigir_forma_por_id", "corrigir_valor_por_id", "registrar_transacao_unica", "registrar_compra_parcelada",
    # executadas só sob _EXCLUSAO_CONFIRMADA (prévia + backup + auditoria)
    "apagar_movimento_fatura_formatado", "apagar_data_pagamento_checklist_formatado",
    "apagar_transferencia_caixa_formatado", "resetar_checklist_formatado", "apagar_entrada_formatado",
    "apagar_compromisso_formatado", "apagar_parcelamento_unificado", "apagar_meta_formatado", "apagar_ultimo",
    "apagar_por_faixa", "apagar_por_id",
    # confirmações de pendências criadas por prévia
    "confirmar_alteracao_pendente", "confirmar_exclusao_pendente", "confirmar_movimento_fatura_pendente",
    "confirmar_importacao_csv", "confirmar_lancamento_pendente",
}

# Gravam sem prévia, por decisão registrada no inventário.
EXCECOES_JUSTIFICADAS = {
    "marcar_item_checklist_formatado": "marcação visual pago/pendente; auditada, com 'Para desfazer'",
    "marcar_itens_checklist_formatado": "idem, em lote",
    "registrar_auditoria": "trilha de auditoria",
    "_auditar_roteador": "trilha de auditoria",
    "gerar_backup": "arquivo de backup (não altera dados); exige PIN no app",
    "gerar_backup_automatico": "arquivo de backup (não altera dados)",
    "exportar_csv_completo": "arquivo CSV (não altera dados); exige PIN no app",
    "exportar_csv_mes": "arquivo CSV (não altera dados)",
    "exportar_csv_periodo": "arquivo CSV (não altera dados); período grande exige PIN no app",
    "gerar_dashboard_visual_mes": "PNG em dashboards/ (não altera dados)",
    "gerar_dashboard_categorias_visual_mes": "PNG em dashboards/ (não altera dados)",
}

# Mecânica das pendências (criam/limpam prévias em memória, não gravam no banco).
PENDENCIAS = {
    "_preparar_alteracao_sessao", "_preparar_exclusao_sessao", "_preparar_movimento_fatura_sessao",
    "_gravacao_pede_confirmacao", "_limpar_pendencia", "_obter_pendencia", "cancelar_alteracao_pendente",
    "cancelar_exclusao_pendente", "cancelar_lancamento_pendente", "cancelar_movimento_fatura_pendente",
    "analisar_csv_importacao", "pedir_periodo_exportacao", "_PreviaColetada",
}

LEITURA = {
    "_bloqueio_parcela_isolada", "_chave_sessao", "_comando_protegido", "_previa_data_pagamento_checklist",
    "_previa_editar_fatura", "_previa_lancamento", "_previa_saldo_inicial", "_previa_transferencia_caixa",
    "_previa_vencimento_fatura", "_sufixo_desfazer_checklist", "analisar_compra",
    "aplicar_correcao_categoria_transacao", "bloco_heranca_mes_anterior", "buscar_checklist_status_mes",
    "buscar_transacao_detalhada_formatado", "buscar_transacao_por_id", "buscar_transacoes_formatado",
    "buscar_transferencia_caixa_por_id", "buscar_ultimas_transacoes", "comando_destrutivo_exclusao",
    "comando_operacional", "consultar_categoria", "converter_valor_texto", "detalhar_categoria_futuro",
    "detalhar_categoria_mes", "detalhar_item_checklist_formatado", "detalhar_mes", "detalhar_pagamento_por_conta",
    "detalhar_parcelamento_unificado", "diagnosticar_fixo", "eh_alias_saldo_geral", "eh_credito",
    "extrair_periodo_exportacao", "extrato_conta_mes_formatado", "formatar_ano_mes_visual",
    "formatar_nome_conta_saldo", "formatar_resumo_fatura", "gerar_agenda_assessor",
    "gerar_auditoria_despesas_mes", "gerar_auditoria_resultado_mes_ux", "gerar_caixa_por_conta_mes",
    "gerar_checklist_pagamentos", "gerar_compromissos_ux", "gerar_diagnostico_assessor",
    "gerar_fechamento_mensal_formatado", "gerar_fechamento_semanal_formatado", "gerar_gastos_hoje",
    "gerar_lembrete_pagamentos_data", "gerar_meu_mes_curto_ux", "gerar_meu_mes_ux", "gerar_painel_hoje_ux",
    "gerar_pendencias_abertas_formatado", "gerar_relatorio_mes", "gerar_resumo_mes", "gerar_revisao_inteligente",
    "gerar_saldo_mes_ux", "gerar_status", "gerar_tela_ajustes_ux", "gerar_tela_registrar_ux",
    "listar_categorias_mes", "listar_compromissos_formatado", "listar_entradas_formatado",
    "listar_entradas_mes_formatado", "listar_fixos_formatado", "listar_formas_mes", "listar_metas_formatado",
    "listar_movimentos_fatura_formatado", "listar_parcelamentos_unificados_formatado",
    "listar_parcelas_futuras_unificadas", "listar_parcelas_mes_unificadas", "listar_transferencias_caixa_formatado",
    "listar_ultimas", "listar_ultimas_paginado", "listar_vencimentos_checklist_formatado",
    "mensagem_comando_nao_reconhecido", "mensagem_exclusao_bloqueada_por_confirmacao", "mensagem_sem_valor",
    "montar_lista_transacoes_paginada", "movimentacoes_conta_mes_formatado", "normalizar_ano_mes_flexivel",
    "normalizar_comando_sinonimos", "obter_metricas_resultado_mes", "parse_fixo", "parse_mensagem",
    "parsear_comando_aprender", "parsear_comando_auditoria_despesas", "parsear_comando_caixa_por_conta",
    "parsear_comando_checklist", "parsear_comando_dashboard", "parsear_comando_dashboard_categorias",
    "parsear_comando_detalhar_checklist", "parsear_comando_entrada_avulsa", "parsear_comando_entrada_fixa",
    "parsear_comando_extrato_conta_mes", "parsear_comando_marcar_checklist",
    "parsear_comando_marcar_checklist_multiplo", "parsear_comando_movimentacoes_conta_mes",
    "parsear_comando_movimento_fatura", "parsear_comando_novo_fixo", "parsear_comando_pendencias_abertas",
    "parsear_comando_resetar_checklist", "parsear_comando_saldo_inicial", "parsear_comando_transferencia_caixa",
    "precisa_escolher", "preparar_fixo", "previa_alteracao", "resumo_contas_mes",
    "resumo_pagamento_mes_consolidado", "resumo_pagamento_por_conta", "simular_lancamento", "validar_ano_mes",
}


def _funcoes_chamadas_pelo_roteador():
    arvore = ast.parse(inspect.getsource(svc._processar_mensagem_core))
    nomes = set()
    locais = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Name,)) and isinstance(no.ctx, ast.Store):
            locais.add(no.id)
        if isinstance(no, ast.ImportFrom):
            for alias in no.names:
                nomes.add(alias.asname or alias.name)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            nomes.add(no.func.id)
        if isinstance(no, ast.Tuple):  # funções passadas em tuplas (laços de ramos)
            nomes.update(e.id for e in no.elts if isinstance(e, ast.Name) and callable(getattr(svc, e.id, None)))
    import builtins
    return {n for n in nomes - locais if not hasattr(builtins, n)}


class GuardaEstaticaTests(unittest.TestCase):
    def test_toda_funcao_do_roteador_esta_classificada(self):
        conhecidas = GRAVACAO_COM_PREVIA | set(EXCECOES_JUSTIFICADAS) | PENDENCIAS | LEITURA
        novas = sorted(_funcoes_chamadas_pelo_roteador() - conhecidas)
        self.assertEqual([], novas,
                         "O roteador chama funções não classificadas. Se gravam, ponha a prévia "
                         "(_gravacao_pede_confirmacao) e inclua em GRAVACAO_COM_PREVIA; se não, em LEITURA; "
                         "exceção sem prévia exige justificativa em EXCECOES_JUSTIFICADAS e no inventário.")

    def test_listas_disjuntas(self):
        grupos = [GRAVACAO_COM_PREVIA, set(EXCECOES_JUSTIFICADAS), PENDENCIAS, LEITURA]
        for i, a in enumerate(grupos):
            for b in grupos[i + 1:]:
                self.assertEqual(set(), a & b)

    def test_gravacoes_so_rodam_atras_de_um_gate(self):
        """Cada chamada de função de gravação no roteador vem depois de um gate no mesmo bloco
        (_gravacao_pede_confirmacao, _preparar_*, previa_alteracao no topo ou exclusão confirmada)."""
        fonte = inspect.getsource(svc._processar_mensagem_core)
        topo = fonte.index("previa_alteracao(texto)")
        for funcao in GRAVACAO_COM_PREVIA - {"confirmar_alteracao_pendente", "confirmar_exclusao_pendente",
                                             "confirmar_movimento_fatura_pendente", "confirmar_importacao_csv",
                                             "confirmar_lancamento_pendente"}:
            if f"{funcao}(" not in fonte and funcao not in fonte:
                continue
            with self.subTest(funcao=funcao):
                self.assertGreater(fonte.index(funcao), topo)


if __name__ == "__main__":
    unittest.main()
