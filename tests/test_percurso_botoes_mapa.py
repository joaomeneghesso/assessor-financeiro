"""Percurso de botoes: BFS a partir de 'home' clicando cada botao ate o fim.

Cada clique e executado numa sessao nova (chave nova) repetindo o caminho
desde 'home'. Banco temporario; nada toca data/financeiro.db.
"""
import re, tempfile, unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
import database as db, services as svc, telegram_experiencia as ux

MAX_DEPTH = 4
MAX_NODES = 400
# Orçamento determinístico (antes: 50 s de relógio, ~143 telas, variando com a carga).
MAX_EXPANSOES = 450
TELAS_MEDIDAS = 149  # telas distintas visitadas com MAX_EXPANSOES=450 (medido em 09/11/2026)
HOJE = date(2026, 9, 30)
# Acoes que gravam/excluem/enviam: nao percorridas sem o fluxo correto.
ACOES_GRAVACAO = {
    'save_budget', 'save_hours', 'save_balance', 'commit_link', 'unlink', 'new_fixed_commit',
    'commit', 'save', 'confirm', 'delete', 'delete_confirm', 'pay_confirm', 'media_transfer_commit',
    'fixed_commit', 'fixed_save', 'fixed_delete', 'fixed_confirm', 'undo', 'confirm_delete',
    'save_settings', 'save_category', 'backup', 'restore', 'cat_confirm', 'cat_learn',
    'acct_off_ok', 'acct_on',
}
# Botoes tratados fora de Experience.act (callback handler do app.py / services):
# engine.act levanta ValueError('Ação desconhecida') por desenho. Nao percorridos aqui.
DELEGADAS_AO_APP = {'legacy', 'legacy_raw', 'guided', 'lock'}
# Excecoes esperadas por desenho (token/estado ausente ao reexecutar do zero).
EXCECOES_ESPERADAS = (ValueError,)
# Mensagens de ValueError aceitas (estado/token ausente ao reexecutar): padroes dos
# raise de telegram_experiencia.py. O percurso atual nao dispara nenhuma delas.
MENSAGENS_ESPERADAS = (
    r'expirou|expirada',
    r'Abra .*novamente',
    r'n[aã]o existe mais',
    r'n[aã]o est[aá] mais (ativ[ao]|dispon[ií]vel)',
    r'Tela desconhecida',
)


# Botoes que levam a outra tela de navegacao (saida possivel da tela).
NAVEGACAO = {'back', 'cancel', 'render_current', 'new_fixed_cancel', 'view', 'home_income', 'innovations',
             'detail_obligation', 'current_month', 'month', 'cash_setup_skip', 'clear_filters'}


def _acoes(screen):
    return [(lab, a) for row in screen.rows for lab, a in row]


class PercursoBotoes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patches = []
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(cls.tmp.name) / 'fixture.db'); p.start(); cls.patches.append(p)
        db.init_db()
        cls._seed()
        cls.resultado = cls._percorrer()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches: p.stop()
        cls.tmp.cleanup()

    @classmethod
    def _seed(cls):
        for d, v, cat, desc in (('2026-09-03', 120.5, 'Mercado', 'Mercado'), ('2026-09-10', 45, 'Transporte', 'Uber')):
            db.inserir_transacao(dict(data=d, tipo='despesa', valor=v, categoria=cat, descricao=desc, conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        db.inserir_transacao(dict(data='2026-09-05', tipo='receita', valor=5000, categoria='Salário', descricao='Salário', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        db.inserir_transacao(dict(data='2026-09-12', tipo='despesa', valor=300, categoria='Lazer', descricao='Cinema', conta='Nubank', forma_pagamento='crédito', parcelas_total=1))
        db.inserir_compromisso(dict(tipo='fixo', nome='Internet', categoria='Casa', valor=80, data_inicio='2026-09-01', dia_vencimento=25, conta_pagamento='Itaú', forma_pagamento='pix', ativo=1))

    @classmethod
    def _engine_em(cls, caminho, n):
        engine = ux.Experience(date_provider=lambda: HOJE)
        key = f'percurso-{n}'
        screen = engine.act(key, ('view', 'home'))
        for acao in caminho:
            screen = engine.act(key, acao)
        return engine, key, screen

    @classmethod
    def _percorrer(cls):
        r = dict(telas=set(), botoes=0, excecoes=[], vazias=[], malformados=[],
                 sem_volta=[], puladas=set(), kinds=set(), esperadas=[], delegadas=set())
        vistos = set()
        fila = [()]
        n = 0
        # Orcamento deterministico (nº de caminhos expandidos), sem relogio: o mesmo
        # resultado em qualquer maquina.
        while fila and len(r['telas']) < MAX_NODES and n < MAX_EXPANSOES:
            caminho = fila.pop(0)
            n += 1
            try:
                engine, key, screen = cls._engine_em(caminho, n)
            except EXCECOES_ESPERADAS as e:
                r['esperadas'].append((caminho, repr(e))); continue
            except Exception as e:
                r['excecoes'].append((caminho, repr(e))); continue
            botoes = _acoes(screen)
            assinatura = (screen.text, tuple(repr(a) for _, a in botoes))
            if assinatura in vistos:
                continue
            vistos.add(assinatura)
            r['telas'].add(assinatura[0][:60])
            cls._checar_tela(r, caminho, screen, engine, key)
            if len(caminho) >= MAX_DEPTH:
                continue
            for lab, a in botoes:
                r['botoes'] += 1
                if not isinstance(a, (tuple, list)) or not a:
                    continue
                r['kinds'].add(a[0])
                if a[0] in ACOES_GRAVACAO:
                    r['puladas'].add(a[0]); continue
                if a[0] in DELEGADAS_AO_APP:
                    r['delegadas'].add(a[0]); continue
                if a[0] == 'copy_text':
                    continue
                if a[0] in ('month', 'current_month', 'privacy') and any(c[0] in ('month', 'current_month', 'privacy') for c in caminho):
                    continue  # navegacao de mes/privacidade: uma vez por caminho basta
                fila.append(caminho + (tuple(a),))
        return r

    @classmethod
    def _checar_tela(cls, r, caminho, screen, engine, key):
        if not isinstance(screen, ux.Screen) or not screen.text.strip():
            r['vazias'].append((caminho, getattr(screen, 'text', None))); return
        tem_volta = False
        for lab, a in _acoes(screen):
            if not isinstance(lab, str) or not lab.strip() or not isinstance(a, (tuple, list)) or not a or not isinstance(a[0], str):
                r['malformados'].append((caminho, lab, a)); continue
            if a[0] in NAVEGACAO:
                tem_volta = True
        for row in engine.tokens_for(key, screen):
            for lab, tok in row:
                if tok is not None and len(tok.encode()) > 64:
                    r['malformados'].append((caminho, lab, 'callback_data>64'))
        if not tem_volta and caminho:
            r['sem_volta'].append((caminho, screen.text[:50]))

    def test_percurso_visitou_telas(self):
        # Percurso deterministico (orcamento de expansoes, date_provider fixo): medido
        # em TELAS_MEDIDAS telas distintas; exige >= 90% disso.
        self.assertGreaterEqual(len(self.resultado['telas']), int(TELAS_MEDIDAS * 0.9))

    def test_valueerror_apenas_do_tipo_esperado(self):
        # ValueError por desenho (estado/token ausente): so mensagens conhecidas.
        # Hoje o percurso nao produz nenhuma; uma mensagem nova reprova.
        for caminho, exc in self.resultado['esperadas']:
            self.assertRegex(exc, r'^ValueError\(', msg=str(caminho))
            self.assertTrue(any(re.search(p, exc) for p in MENSAGENS_ESPERADAS),
                            msg=f'mensagem nao prevista: {exc} em {caminho}')

    def test_lista_de_mensagens_esperadas_casa_com_as_reais(self):
        for msg in ('Essa prévia expirou. Abra Registrar novamente.', 'Abra o registro novamente.',
                    'Esse lançamento não existe mais.', 'Essa confirmação expirou.'):
            self.assertTrue(any(re.search(p, repr(ValueError(msg))) for p in MENSAGENS_ESPERADAS), msg)
        self.assertFalse(any(re.search(p, repr(ValueError('Erro qualquer inesperado'))) for p in MENSAGENS_ESPERADAS))

    def test_sem_excecoes_inesperadas(self):
        self.assertEqual(self.resultado['excecoes'], [])

    def test_telas_nao_vazias(self):
        self.assertEqual(self.resultado['vazias'], [])

    def test_botoes_bem_formados_e_callback_64(self):
        self.assertEqual(self.resultado['malformados'], [])

    def test_toda_tela_tem_volta(self):
        self.assertEqual(self.resultado['sem_volta'], [])


if __name__ == '__main__':
    unittest.main()
