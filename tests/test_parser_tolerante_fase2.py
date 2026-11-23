"""Fase 2 (P2): parser tolerante do texto de lançamento (guiado e legado).

O parser só pré-preenche campos; nenhuma confirmação é relaxada. Sem banco e
com data fixa (quinta-feira, 29/10/2026).
"""
from datetime import date
import unittest

from parser_financeiro import parse_mensagem
from registro_conversa import data_informada, extrair_campos

HOJE = date(2026, 10, 29)


def guiado(texto, **kw):
    return extrair_campos(texto, hoje=HOJE, **kw)


def legado(texto):
    return parse_mensagem(texto, data_referencia=HOJE)


class ValorEmQualquerPosicaoTests(unittest.TestCase):
    def test_valor_no_fim_ou_no_inicio(self):
        casos = {
            'recebi salário 5000': (5000.0, 'salário', 'receita'),
            'gastei mercado 45': (45.0, 'mercado', 'despesa'),
            'mercado 45': (45.0, 'mercado', 'despesa'),
            '45 mercado': (45.0, 'mercado', 'despesa'),
            'recebi salario 5.000,50': (5000.5, 'salario', 'receita'),
            'uber 23,50 ontem': (23.5, 'uber', 'despesa'),
        }
        for texto, (valor, descricao, tipo) in casos.items():
            with self.subTest(texto=texto):
                c = guiado(texto)
                self.assertEqual(valor, c['valor'])
                self.assertEqual(descricao, c['descricao'])
                self.assertEqual(tipo, c['tipo'])

    def test_total_parcelado_no_meio_da_frase(self):
        c = guiado('comprei tv 3000 em 10x no itaú')
        self.assertEqual((3000.0, 10, 'crédito', 'Itaú', 'tv'),
                         (c['valor'], c['parcelas_total'], c['forma_pagamento'], c['conta'], c['descricao']))
        self.assertEqual(3000.0, guiado('tv 3000 em 10x')['valor'])

    def test_descricao_nao_carrega_o_numero(self):
        for texto in ('mercado 45', 'tv 3000 em 10x', 'recebi salário 5000'):
            self.assertFalse(any(ch.isdigit() for ch in guiado(texto)['descricao']), texto)

    def test_nomes_de_produto_e_99_nao_viram_valor(self):
        self.assertNotIn('valor', guiado('comprei iphone 15'))
        self.assertNotIn('valor', guiado('uber 99'))
        self.assertEqual(99.0, guiado('gastei 99 no uber')['valor'])
        c = guiado('comprei iphone 15 por 5000 em 10x')
        self.assertEqual((5000.0, 'iphone 15'), (c['valor'], c['descricao']))
        self.assertEqual(45.0, guiado('mercado 3 itens 45')['valor'])

    def test_dois_numeros_livres_sao_recusados_com_erro_claro(self):
        for texto, esperado in (
            ('gastei mercado 45 e 30', 'Encontrei dois valores: 45 e 30. Qual é o valor?'),
            ('mercado 45, padaria 30', 'Encontrei dois valores: 45 e 30. Qual é o valor?'),
            ('mercado 45 padaria 30 café 12', 'Encontrei 3 valores: 45, 30 e 12. Qual é o valor?'),
        ):
            with self.subTest(texto=texto):
                with self.assertRaises(ValueError) as erro:
                    guiado(texto)
                self.assertEqual(esperado, str(erro.exception))

    def test_dois_valores_com_marca_continuam_recusados(self):
        for texto in ('gastei 10,00 e 20,00', 'gastei R$ 10 e R$ 20'):
            with self.assertRaises(ValueError):
                guiado(texto)

    def test_valor_passa_por_parse_money(self):
        self.assertEqual(33.3, guiado('padaria 33,30')['valor'])
        self.assertEqual(1234.56, guiado('padaria 1.234,56')['valor'])
        with self.assertRaises(ValueError):  # 3 casas decimais: recusa, não arredonda em silêncio
            guiado('padaria 33,333')


class MilharesTests(unittest.TestCase):
    def test_k_e_mil(self):
        casos = {
            'gastei 1,5k no mercado': 1500.0,
            'gastei 2k no mercado': 2000.0,
            'gastei 1,5 mil no mercado': 1500.0,
            'gastei 1 mil e 500 no mercado': 1500.0,
            'tv 3 mil': 3000.0,
            'recebi 2k de salário': 2000.0,
        }
        for texto, valor in casos.items():
            with self.subTest(texto=texto):
                c = guiado(texto)
                self.assertEqual(valor, c['valor'])
                self.assertFalse(any(ch.isdigit() for ch in c['descricao']))
                self.assertEqual(valor, legado(texto)['valor'])

    def test_kg_nao_vira_mil(self):
        self.assertNotIn('valor', guiado('mercado 2kg'))


class DatasTests(unittest.TestCase):
    def test_datas_curtas_e_relativas(self):
        casos = {
            'gastei 45 no mercado 15/10': '2026-10-15',
            'gastei 45 no mercado dia 15/10': '2026-10-15',
            'gastei 45 no mercado dia 15': '2026-10-15',
            'gastei 45 no mercado dia 30': '2026-09-30',  # ainda não chegou: mês anterior
            'gastei 45 no mercado dia 29': '2026-10-29',
            'gastei 45 no mercado dia 15 de outubro': '2026-10-15',
            'gastei 45 no mercado ontem': '2026-10-28',
            'gastei 45 no mercado anteontem': '2026-10-27',
            'gastei 45 no mercado ontem à noite': '2026-10-28',
            'gastei 45 no mercado segunda': '2026-10-26',
            'gastei 45 no mercado na quinta': '2026-10-22',  # hoje é quinta: semana anterior
            'gastei 45 no mercado no sábado': '2026-10-24',
            'gastei 45 no mercado 15/10/2025': '2025-10-15',
        }
        for texto, data in casos.items():
            with self.subTest(texto=texto):
                c = guiado(texto)
                self.assertEqual(data, c['data'])
                self.assertEqual(45.0, c['valor'])
                self.assertEqual('mercado', c['descricao'])
                r = legado(texto)
                self.assertEqual(data, r['data'])
                self.assertEqual('Mercado', r['descricao'])

    def test_data_futura_e_recusada(self):
        with self.assertRaises(ValueError) as erro:
            guiado('gastei 45 no mercado 15/12')
        self.assertIn('ainda não chegou', str(erro.exception))
        r = legado('gastei 45 no mercado 15/12')
        self.assertEqual(('mensagem_bloqueada', 'data_futura'), (r['erro'], r['motivo']))
        with self.assertRaises(ValueError):
            guiado('gastei 45 no mercado 15 de dezembro')
        for texto in ('gastei 45 no mercado amanhã', 'gastei 45 no mercado 15 de dezembro'):
            self.assertEqual('data_futura', legado(texto)['motivo'])

    def test_data_inexistente_e_vaga_dao_erro_especifico(self):
        with self.assertRaises(ValueError) as erro:
            guiado('gastei 45 no mercado 31/02')
        self.assertIn('não existe', str(erro.exception))
        with self.assertRaises(ValueError) as erro:
            guiado('gastei 45 no mercado semana passada')
        self.assertIn('dia exato', str(erro.exception))
        self.assertEqual('valor_ou_data_invalida', legado('gastei 45 no mercado semana passada')['motivo'])
        with self.assertRaises(ValueError):
            guiado('gastei 45 no mercado 15/10 e 16/10')

    def test_parcela_entre_parenteses_nao_e_data(self):
        r = legado('Notebook (3/10) 200')
        self.assertEqual((200.0, '2026-10-29'), (r['valor'], r['data']))

    def test_palavras_parecidas_com_dia_da_semana_ficam_na_descricao(self):
        c = guiado('gastei 45 segunda via do cartorio')
        self.assertNotIn('data', c)
        self.assertIn('segunda via', c['descricao'])

    def test_resposta_de_data_na_etapa_guiada(self):
        self.assertEqual('2026-10-15', data_informada('15/10', HOJE))
        self.assertEqual('2026-10-15', data_informada('dia 15', HOJE))
        self.assertEqual('2026-10-26', data_informada('Segunda', HOJE))
        self.assertEqual('2026-10-28', data_informada('ontem', HOJE))
        self.assertEqual('2026-01-01', data_informada('2026-01-01', HOJE))
        for ruim in ('15/12', '31/02/2026', 'xpto', '2026-02-31'):
            with self.assertRaises(ValueError):
                data_informada(ruim, HOJE)

    def test_virada_de_mes_e_ano_no_dia_do_mes(self):
        self.assertEqual('2025-12-31', data_informada('dia 31', date(2026, 1, 5)))
        with self.assertRaises(ValueError):
            data_informada('dia 31', date(2026, 3, 1))  # fevereiro não tem dia 31


class ApelidosDeContaTests(unittest.TestCase):
    def test_apelidos_das_contas_conhecidas(self):
        casos = {'nu': 'Nubank', 'it': 'Itaú', 'mp': 'Mercado Pago', 'bb': 'Banco do Brasil'}
        for apelido, conta in casos.items():
            with self.subTest(apelido=apelido):
                c = guiado(f'gastei 45 no ifood no {apelido}')
                self.assertEqual((conta, 'ifood', 45.0), (c['conta'], c['descricao'], c['valor']))
                self.assertEqual(conta, legado(f'gastei 45 no ifood no {apelido}')['conta'])

    def test_nao_inventa_bancos(self):
        c = guiado('gastei 45 no ifood no zzbank')
        self.assertNotIn('conta', c)

    def test_conta_cadastrada_pelo_titular_continua_valendo(self):
        c = guiado('gastei 45 no ifood no sicredi', contas=['Sicredi'])
        self.assertEqual('Sicredi', c['conta'])


class VariosLancamentosTests(unittest.TestCase):
    TRES = 'gastei 45 no mercado\ngastei 20 na padaria\ngastei 12 no café'

    def test_guiado_recusa_sem_fundir_linhas(self):
        with self.assertRaises(ValueError) as erro:
            guiado(self.TRES)
        self.assertIn('Encontrei 3 lançamentos', str(erro.exception))
        self.assertIn('um por vez', str(erro.exception))

    def test_legado_recusa_com_mensagem_e_motivo_conhecido(self):
        r = legado(self.TRES)
        self.assertEqual(('mensagem_bloqueada', 'mais_de_um_valor'), (r['erro'], r['motivo']))
        self.assertIn('Encontrei 3 lançamentos', r['mensagem'])
        r = legado('mercado 45\nrecebi 100 de salário')
        self.assertEqual('mais_de_um_valor', r['motivo'])

    def test_dois_verbos_na_mesma_linha(self):
        with self.assertRaises(ValueError):
            guiado('gastei 45 no mercado e gastei 20 na padaria')
        self.assertEqual('mais_de_um_valor', legado('gastei 45 no mercado e gastei 20 na padaria')['motivo'])

    def test_uma_frase_quebrada_em_linhas_continua_valendo(self):
        c = guiado('gastei\n45 no mercado')
        self.assertEqual((45.0, 'mercado'), (c['valor'], c['descricao']))

    def test_codigo_continua_bloqueado_como_codigo(self):
        with self.assertRaises(ValueError) as erro:
            guiado('def f():\n    return 1\n    x = 2\n    y = 3\n    z = 4')
        self.assertIn('frase curta', str(erro.exception))
        self.assertEqual('codigo_ou_texto_longo', legado('def f():\n    return 1\nx = 2\ny = 3\nz = 4')['motivo'])


if __name__ == '__main__':
    unittest.main()
