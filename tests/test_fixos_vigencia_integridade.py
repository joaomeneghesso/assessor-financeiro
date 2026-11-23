"""Regressão com banco temporário: listagem, histórico e edição sem despesas."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import fixos_edicao as fx
import fixos_interface as ui
import services as svc
import telegram_experiencia as ux


class Setembro(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 30)


class FixosVigenciaIntegridade(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / 'financeiro.db'
        for target, field, value in ((db, 'DB_PATH', path), (svc, 'DB_PATH', path),
                                     (comp, 'date', Setembro), (svc, 'date', Setembro)):
            p = patch.object(target, field, value)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.exp = ux.Experience(date_provider=lambda: date(2026, 9, 30))

    def insert(self, **changes):
        row = dict(tipo='fixo', nome='Plano de celular', categoria='Telefonia',
                   conta_pagamento='Itaú', forma_pagamento='pix', valor=49.99,
                   dia_vencimento=10, data_inicio='2026-01-01', data_fim=None,
                   ativo=True, origem='teste_isolado')
        row.update(changes)
        return db.inserir_compromisso(row)

    def financial_rows(self):
        with db.get_connection() as conn:
            return {name: conn.execute('SELECT * FROM '+name+' ORDER BY id').fetchall()
                    for name in ('transacoes', 'fatura_movimentos')}

    def test_exemplo_total_e_itens_preserva_historico(self):
        old = self.insert(data_fim='2026-08-31')
        new = self.insert(data_inicio='2026-09-01')
        for i in range(9):
            self.insert(nome=f'Outro {i}', valor=50 if i < 8 else 141.45)
        before = self.financial_rows()
        text = svc.processar_mensagem('fixos')
        self.assertIn('R$ 591,44', text)
        self.assertRegex(text, r'Itens\s+10')
        self.assertNotIn(f'┌ #C{old} ·', text)
        self.assertIn(f'┌ #C{new} ·', text)
        self.assertEqual(before, self.financial_rows())
        self.assertEqual(11, len(db.listar_compromissos(tipo='fixo')))
        self.assertEqual(1, db.buscar_compromisso_por_id(old)['ativo'])

    def test_filtro_exclui_antigo_futuro_e_pausado(self):
        self.insert(data_fim='2026-08-31')
        self.insert(data_inicio='2026-10-01')
        self.insert(ativo=False)
        current = self.insert(valor=60)
        text = svc.processar_mensagem('fixos celular')
        self.assertIn('R$ 60,00', text)
        self.assertRegex(text, r'Itens\s+1')
        self.assertIn(f'#C{current}', text)

    def test_sem_fixos_vigentes(self):
        self.insert(data_fim='2026-08-31')
        self.assertIn('Não encontrei fixos ativos', comp.listar_fixos_formatado())

    def test_limites_de_vigencia_reutilizam_regra_financeira(self):
        included = self.insert(data_fim='2026-09-10')
        excluded = self.insert(data_fim='2026-09-09')
        text = comp.listar_fixos_formatado()
        self.assertIn(f'┌ #C{included} ·', text)
        self.assertNotIn(f'┌ #C{excluded} ·', text)

    def test_fevereiro_bissexto_e_dia_31(self):
        self.insert(dia_vencimento=31, data_inicio='2024-01-01', data_fim='2024-02-29')
        class Fevereiro(date):
            @classmethod
            def today(cls): return cls(2024, 2, 29)
        with patch.object(comp, 'date', Fevereiro):
            self.assertRegex(comp.listar_fixos_formatado(), r'Itens\s+1')

    def test_virada_do_ano(self):
        old = self.insert(data_fim='2026-12-31')
        new = self.insert(data_inicio='2027-01-01')
        class Janeiro(date):
            @classmethod
            def today(cls): return cls(2027, 1, 1)
        with patch.object(comp, 'date', Janeiro):
            text = comp.listar_fixos_formatado()
        self.assertNotIn(f'┌ #C{old} ·', text)
        self.assertIn(f'┌ #C{new} ·', text)

    def test_edicao_versionada_pix_e_credito_nao_cria_movimentos(self):
        for method in ('pix', 'crédito'):
            with self.subTest(method=method):
                ident = self.insert(nome='Plano '+method, forma_pagamento=method)
                before = self.financial_rows()
                fx.salvar(fx.preparar(ident, 'valor', '60', '2026-09'), 'teste')
                self.assertEqual(before, self.financial_rows())
                old = dict(db.buscar_compromisso_por_id(ident))
                self.assertEqual('2026-08-31', old['data_fim'])
                related = [dict(c) for c in db.listar_compromissos(tipo='fixo') if c['nome']==old['nome']]
                new = next(c for c in related if c['id']!=ident)
                self.assertEqual('2026-09-01', new['data_inicio'])
                self.assertEqual(60, new['valor'])
                self.assertEqual(method, new['forma_pagamento'])
                aug = [c for c in comp.projetar_compromissos_mes('2026-08') if c['nome']==old['nome']]
                sep = [c for c in comp.projetar_compromissos_mes('2026-09') if c['nome']==old['nome']]
                self.assertEqual([49.99], [c['valor'] for c in aug])
                self.assertEqual([60], [c['valor'] for c in sep])
                self.assertEqual(1, len(db.listar_auditoria('compromissos', ident)))
                self.assertEqual(1, len(db.listar_auditoria('compromissos', new['id'])))

    def test_correcao_de_cada_campo_sem_movimentos(self):
        for field, value in [('nome','Plano atualizado'), ('categoria','Assinaturas'),
                             ('valor','60'), ('conta','Nubank'), ('forma','crédito'),
                             ('vencimento','31'), ('inicio','2026-02-01'),
                             ('termino','2026-12-31'), ('status','pausado')]:
            with self.subTest(field=field):
                ident = self.insert()
                before = self.financial_rows()
                fx.salvar(fx.preparar(ident, field, value), 'teste')
                self.assertEqual(before, self.financial_rows())
                self.assertEqual(1, len(db.listar_auditoria('compromissos', ident)))

    def test_previa_obsoleta_e_repeticao_nao_duplicam(self):
        ident = self.insert()
        preview = fx.preparar(ident, 'valor', '60', '2026-09')
        fx.salvar(preview, 'teste')
        with self.assertRaisesRegex(ValueError, 'mudou desde a prévia'):
            fx.salvar(preview, 'teste')
        self.assertEqual(2, len(db.listar_compromissos()))

    def test_falha_na_auditoria_reverte_versionamento(self):
        ident = self.insert()
        before = dict(db.buscar_compromisso_por_id(ident))
        with patch.object(db, 'registrar_auditoria', side_effect=RuntimeError('falha sintética')):
            with self.assertRaises(RuntimeError):
                fx.salvar(fx.preparar(ident, 'valor', '60', '2026-09'), 'teste')
        self.assertEqual(before, dict(db.buscar_compromisso_por_id(ident)))
        self.assertEqual(1, len(db.listar_compromissos()))

    def test_editar_fixos_preserva_acesso_ao_historico(self):
        old = self.insert(data_fim='2026-08-31')
        paused = self.insert(ativo=False)
        text = ui.listar(self.exp, 'teste').text
        self.assertIn('incluindo pausados e encerrados', text)
        rows = ui.listar(self.exp, 'teste').rows
        self.assertIn(str(old), str(rows))
        self.assertIn(str(paused), str(rows))

    def test_previa_interface_so_grava_apos_salvar(self):
        ident = self.insert()
        before = self.financial_rows()
        ui.acao(self.exp, 'teste', ('fixed_field', ident, 'valor'))
        ui.texto(self.exp, 'teste', '60')
        ui.acao(self.exp, 'teste', ('fixed_scope', 'month'))
        ui.texto(self.exp, 'teste', '2026-09')
        self.assertEqual(1, len(db.listar_compromissos()))
        ui.acao(self.exp, 'teste', ('fixed_save',))
        self.assertEqual(2, len(db.listar_compromissos()))
        self.assertEqual(before, self.financial_rows())

    def test_cadastro_guiado_so_cria_compromisso(self):
        before = self.financial_rows()
        result = svc.cadastrar_fixo_guiado(dict(nome='Conta nova', valor='60', categoria='Telefonia',
            conta_pagamento='Itaú', forma_pagamento='pix', dia_vencimento=10,
            data_inicio='2026-09', data_fim=None), 'teste')
        self.assertEqual(before, self.financial_rows())
        self.assertEqual(1, len(db.listar_compromissos()))
        self.assertTrue(result['compromisso']['id'])

    def test_quanto_vou_pagar_inalterado_apos_consulta(self):
        self.insert(data_fim='2026-08-31')
        self.insert(data_inicio='2026-09-01', valor=60)
        before = comp.calcular_resumo_pagamento_conta('2026-09', 'Itaú')
        comp.listar_fixos_formatado()
        self.assertEqual(before, comp.calcular_resumo_pagamento_conta('2026-09', 'Itaú'))
        self.assertEqual(60, before['fixos'])


if __name__ == '__main__':
    unittest.main()
