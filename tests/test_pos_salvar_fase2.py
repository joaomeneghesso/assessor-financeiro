"""Fase 2 (P5/P6): barra pós-salvar, categoria com confirmação e duplicata útil. Banco temporário."""
import json, os, tempfile, unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import database as db, services as svc, telegram_experiencia as ux, telegram_registros as reg


class PosSalvar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db'); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, {'ASSESSOR_CATEGORY_RULES_PATH': str(Path(self.tmp.name) / 'regras.json')}); p.start(); self.addCleanup(p.stop)
        db.init_db()
        import importlib.util
        spec = importlib.util.spec_from_file_location('fix_0004', Path(__file__).resolve().parents[1] / 'migrations/0004_competencia_faturas.py')
        mig = importlib.util.module_from_spec(spec); spec.loader.exec_module(mig)
        with db.get_connection() as conn: mig.upgrade(conn)
        self.engine = ux.Experience(date_provider=lambda: date(2026, 9, 30)); self.key = 'pos-salvar'

    # ---- utilitários
    def rascunho(self, **kw):
        d = dict(tipo='despesa', valor=45.0, descricao='Mercado Extra', categoria='Mercado', conta='Itaú',
                 forma_pagamento='pix', data='2026-09-30', parcelas_total=1, key='k-' + os.urandom(4).hex(), parsed=True)
        d.update(kw)
        s = self.engine.session(self.key); s.draft = d; s.stage = 'confirm'
        return self.engine.preview(self.key)

    def acoes(self, screen):
        return [(lab, a) for row in screen.rows for lab, a in row]

    def botao(self, screen, kind):
        achados = [a for _, a in self.acoes(screen) if a[0] == kind]
        self.assertTrue(achados, f'Botão {kind} ausente: {screen.text}')
        return tuple(achados[0])

    def salvar(self, **kw):
        prev = self.rascunho(**kw)
        return self.engine.act(self.key, self.botao(prev, 'commit'))

    def n(self):
        with db.get_connection() as c:
            return c.execute('SELECT count(*) FROM transacoes').fetchone()[0]

    def eventos(self, entidade, operacao):
        with db.get_connection() as c:
            return c.execute('SELECT count(*) FROM auditoria_eventos WHERE entidade=? AND operacao=?', (entidade, operacao)).fetchone()[0]

    def inserir(self, **kw):
        t = dict(data='2026-09-29', tipo='despesa', valor=45, categoria='Mercado', descricao='Mercado Extra', conta='Itaú', forma_pagamento='pix', parcelas_total=1)
        t.update(kw); return db.inserir_transacao(t)

    # ---- barra pós-salvar
    def test_sucesso_mostra_barra_e_desfazer_reutiliza_fluxo_existente(self):
        ok = self.salvar()
        kinds = [a[0] for _, a in self.acoes(ok)]
        self.assertEqual(kinds[:3], ['undo_preview', 'cat_menu', 'repeat'])
        self.assertEqual(self.n(), 1)
        prev = self.engine.act(self.key, self.botao(ok, 'undo_preview'))
        self.assertEqual(self.n(), 1)  # prévia não apaga
        self.engine.act(self.key, self.botao(prev, 'undo'))
        self.assertEqual(self.n(), 0)
        self.assertEqual(self.eventos('telegram_registro', 'desfeito'), 1)
        with db.get_connection() as c:
            antes = c.execute("SELECT dados_antes FROM auditoria_eventos WHERE operacao='desfeito'").fetchone()[0]
        self.assertIn('linhas', json.loads(antes))

    def test_parcelado_so_oferece_desfazer(self):
        ok = self.salvar(forma_pagamento='crédito', conta='Nubank', parcelas_total=3, data='2026-09-10')
        kinds = [a[0] for _, a in self.acoes(ok)]
        self.assertIn('undo_preview', kinds); self.assertNotIn('cat_menu', kinds); self.assertNotIn('repeat', kinds)

    def test_detalhe_mostra_desfazer_enquanto_recente_e_inalterado(self):
        ok = self.salvar()
        tid = self.botao(ok, 'cat_menu')[1]
        det = self.engine.act(self.key, ('transaction', tid))
        self.assertIn('undo_preview', [a[0] for _, a in self.acoes(det)])
        self.assertIn('cat_menu', [a[0] for _, a in self.acoes(det)])
        # outra sessão não vê o desfazer
        outra = self.engine.act('outra-sessao', ('transaction', tid))
        self.assertNotIn('undo_preview', [a[0] for _, a in self.acoes(outra)])
        # depois da janela some
        with patch.object(reg, 'JANELA_DESFAZER_MIN', 0):
            self.assertIsNone(reg.evento_registro_recente(tid, self.key, agora=datetime.now() + timedelta(minutes=1)))
        # linha alterada some
        with db.get_connection() as c:
            c.execute('UPDATE transacoes SET valor=99 WHERE id=?', (tid,)); c.commit()
        self.assertIsNone(reg.evento_registro_recente(tid, self.key))

    def test_desfazer_pelo_detalhe_apos_navegar(self):
        ok = self.salvar(); tid = self.botao(ok, 'cat_menu')[1]
        self.engine.act(self.key, ('view', 'history'))
        det = self.engine.act(self.key, ('transaction', tid))
        prev = self.engine.act(self.key, self.botao(det, 'undo_preview'))
        self.engine.act(self.key, self.botao(prev, 'undo'))
        self.assertEqual(self.n(), 0)

    def test_repetir_abre_rascunho_sem_gravar(self):
        ok = self.salvar(); tid = self.botao(ok, 'repeat')[1]
        antes = self.n()
        prev = self.engine.act(self.key, ('repeat', tid))
        self.assertEqual(self.n(), antes)
        self.assertIn('commit', [a[0] for _, a in self.acoes(prev)])

    # ---- categoria
    def test_categoria_menu_ate_cinco_opcoes_e_outra(self):
        tid = self.inserir()
        tela = self.engine.act(self.key, ('cat_menu', tid))
        previews = [a for _, a in self.acoes(tela) if a[0] == 'cat_preview']
        self.assertLessEqual(len(previews) + 1, 5)
        self.assertIn('cat_all', [a[0] for _, a in self.acoes(tela)])
        self.assertTrue(any(lab.startswith('✓') for lab, _ in self.acoes(tela)))
        todas = self.engine.act(self.key, ('cat_all', tid))
        self.assertGreater(len([1 for _, a in self.acoes(todas) if a[0] == 'cat_preview']), 5)

    def test_categoria_previa_nao_grava_e_confirmacao_e_idempotente_e_auditada(self):
        tid = self.inserir()
        prev = self.engine.act(self.key, ('cat_preview', tid, 'Casa'))
        self.assertEqual(db.buscar_transacao_por_id(tid)['categoria'], 'Mercado')
        conf = self.botao(prev, 'cat_confirm')
        tela = self.engine.act(self.key, conf)
        self.assertEqual(db.buscar_transacao_por_id(tid)['categoria'], 'Casa')
        self.assertIn('cat_learn', [a[0] for _, a in self.acoes(tela)])
        again = self.engine.act(self.key, conf)  # clique repetido
        self.assertIn('já havia', again.text)
        self.assertEqual(self.eventos('telegram_categoria', 'categoria_alterada'), 1)
        with db.get_connection() as c:
            ev = c.execute("SELECT dados_antes,dados_depois FROM auditoria_eventos WHERE entidade='telegram_categoria'").fetchone()
        self.assertEqual(json.loads(ev[0])['categoria'], 'Mercado'); self.assertEqual(json.loads(ev[1])['categoria'], 'Casa')

    def test_categoria_nao_altera_valor_conta_data(self):
        tid = self.inserir(); antes = dict(db.buscar_transacao_por_id(tid))
        prev = self.engine.act(self.key, ('cat_preview', tid, 'Casa')); self.engine.act(self.key, self.botao(prev, 'cat_confirm'))
        depois = dict(db.buscar_transacao_por_id(tid))
        antes.pop('categoria'); depois.pop('categoria'); self.assertEqual(antes, depois)

    def test_categoria_recusa_mudanca_concorrente(self):
        tid = self.inserir()
        prev = self.engine.act(self.key, ('cat_preview', tid, 'Casa'))
        with db.get_connection() as c:
            c.execute("UPDATE transacoes SET categoria='Lazer' WHERE id=?", (tid,)); c.commit()
        with self.assertRaises(ValueError):
            self.engine.act(self.key, self.botao(prev, 'cat_confirm'))
        self.assertEqual(db.buscar_transacao_por_id(tid)['categoria'], 'Lazer')

    def test_categoria_conciliada_e_recusada(self):
        db.inserir_compromisso(dict(tipo='fixo', nome='Internet', categoria='Casa', valor=80, data_inicio='2026-09-01', dia_vencimento=25, conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))
        tid = self.inserir(data='2026-09-25', valor=80, descricao='Internet', categoria='Casa')
        screen = self.engine.act(self.key, ('link_existing', tid))
        if not any(a[0] == 'choose_target' for _, a in self.acoes(screen)):
            screen = self.engine.act(self.key, self.botao(screen, 'pick_target'))
        screen = self.engine.act(self.key, self.botao(screen, 'choose_target'))
        self.engine.act(self.key, self.botao(screen, 'commit_link'))
        det = self.engine.act(self.key, ('transaction', tid))
        self.assertNotIn('cat_menu', [a[0] for _, a in self.acoes(det)])
        tela = self.engine.act(self.key, ('cat_preview', tid, 'Lazer'))
        self.assertNotIn('cat_confirm', [a[0] for _, a in self.acoes(tela)])
        with self.assertRaises(ValueError):
            reg.corrigir_categoria_registro(tid, 'Lazer', 'chave-x', self.key, 'Casa')
        self.assertEqual(db.buscar_transacao_por_id(tid)['categoria'], 'Casa')

    def test_aprender_so_com_toque(self):
        tid = self.inserir()
        prev = self.engine.act(self.key, ('cat_preview', tid, 'Casa'))
        tela = self.engine.act(self.key, self.botao(prev, 'cat_confirm'))
        import categorias_pessoais as cp
        self.assertEqual(cp.listar_regras(), [])
        self.engine.act(self.key, self.botao(tela, 'cat_learn'))
        self.assertEqual(cp.sugerir_categoria_pessoal('Mercado Extra'), 'Casa')

    def test_callbacks_ate_64_bytes(self):
        ok = self.salvar()
        for _, token in [b for row in self.engine.tokens_for(self.key, ok) for b in row if b[1]]:
            pass
        for _, token in [b for row in self.engine.tokens_for(self.key, ok) for b in row if b[1]]:
            self.assertLessEqual(len(token.encode()), 64)
        tid = self.botao(ok, 'cat_menu')[1]
        tela = self.engine.act(self.key, ('cat_menu', tid))
        for row in self.engine.tokens_for(self.key, tela):
            for _, token in row:
                if token: self.assertLessEqual(len(token.encode()), 64)

    def test_modo_ocultar_mascara_valores(self):
        self.engine.session(self.key).privacy = True
        ok = self.salvar()
        self.assertNotIn('45,00', ok.text)
        det = self.engine.act(self.key, ('transaction', self.botao(ok, 'cat_menu')[1]))
        self.assertNotIn('45,00', det.text)

    # ---- duplicata
    def test_duplicata_mesmo_dia_mostra_id_e_botoes(self):
        did = self.inserir(data='2026-09-30')
        prev = self.rascunho()
        # Onda 2C: id interno não aparece no texto; a data e a descrição identificam o parecido.
        self.assertNotIn(f'#{did}', prev.text); self.assertIn('Parece duplicado', prev.text)
        labels = [lab for lab, _ in self.acoes(prev)]
        self.assertIn('✅ Salvar mesmo assim', labels); self.assertIn('🔎 Ver o parecido', labels); self.assertIn('Cancelar', labels)
        # nunca bloqueia
        self.engine.act(self.key, self.botao(prev, 'commit')); self.assertEqual(self.n(), 2)

    def test_duplicata_dia_anterior_e_posterior(self):
        did = self.inserir(data='2026-09-29')
        self.assertIn('Parece duplicado', self.rascunho(data='2026-09-30').text)
        self.assertIn('29/09', self.rascunho(data='2026-09-30').text)
        self.assertIn('Parece duplicado', self.rascunho(data='2026-09-28').text)

    def test_nao_avisa_fora_da_janela_valor_ou_conta_diferentes(self):
        self.inserir(data='2026-09-27')
        self.assertNotIn('Parece duplicado', self.rascunho(data='2026-09-30').text)
        self.inserir(data='2026-09-30', valor=46)
        self.assertNotIn('Parece duplicado', self.rascunho().text)
        self.inserir(data='2026-09-30', conta='Nubank')
        self.assertNotIn('Parece duplicado', self.rascunho().text)
        self.inserir(data='2026-09-30', forma_pagamento='débito')
        self.assertNotIn('Parece duplicado', self.rascunho().text)

    def test_descricao_normalizada_acentos_e_caixa(self):
        self.inserir(data='2026-09-30', descricao='MERCADO  extra')
        self.assertIn('Parece duplicado', self.rascunho(descricao='mercado extra').text)

    def test_parcela_posterior_nao_conta_como_duplicata(self):
        db.inserir_transacao(dict(data='2026-09-30', tipo='despesa', valor=15, categoria='Mercado', descricao='Mercado Extra', conta='Nubank', forma_pagamento='crédito', parcelas_total=3, parcela_atual=2, valor_total_parcelamento=45))
        t = dict(tipo='despesa', valor=15, descricao='Mercado Extra', conta='Nubank', forma_pagamento='crédito', data='2026-09-30')
        self.assertIsNone(reg.buscar_duplicata(t))

    def test_duplicata_e_somente_leitura(self):
        self.inserir(data='2026-09-30')
        antes = self.n(); ev = self.eventos('telegram_registro', 'confirmado')
        self.rascunho()
        self.assertEqual((antes, ev), (self.n(), self.eventos('telegram_registro', 'confirmado')))

    def test_ver_duplicata_preserva_rascunho(self):
        did = self.inserir(data='2026-09-30')
        prev = self.rascunho()
        ver = self.engine.act(self.key, self.botao(prev, 'dup_view'))
        self.assertIn('Lançamento parecido', ver.text); self.assertNotIn(f'#{did}', ver.text); self.assertEqual(self.n(), 1)
        volta = self.engine.act(self.key, self.botao(ver, 'dup_back'))
        self.assertIn('commit', [a[0] for _, a in self.acoes(volta)])

    def test_legado_texto_livre_tambem_avisa(self):
        did = self.inserir(data='2026-09-30', descricao='Mercado', valor=45)
        tela = self.engine.handle_text(self.key, 'gastei 45 no mercado no pix itau')
        self.assertIn('commit', [a[0] for _, a in self.acoes(tela)])
        self.assertIn('Parece duplicado de um lançamento existente', tela.text)


if __name__ == '__main__':
    unittest.main()
