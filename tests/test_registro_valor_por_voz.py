"""Regressões de valores monetários em linguagem natural vindos da voz."""
from datetime import date
import unittest

from registro_conversa import extrair_campos


class RegistroValorPorVozTests(unittest.TestCase):
    hoje = date(2026, 10, 8)

    def extrair(self, texto):
        return extrair_campos(texto, hoje=self.hoje)

    def test_frase_real_transcrita_com_reais_e_centavos(self):
        campos = self.extrair(
            'Gastei 197 reais e 99 centavos no mercado no cartão de crédito do Itaú.'
        )
        self.assertEqual(197.99, campos['valor'])
        self.assertEqual('mercado', campos['descricao'].lower())
        self.assertEqual('Mercado', campos['categoria'])
        self.assertEqual('crédito', campos['forma_pagamento'])
        self.assertEqual('Itaú', campos['conta'])

    def test_reais_e_centavos_totalmente_por_extenso(self):
        campos = self.extrair(
            'gastei cento e noventa e sete reais e noventa e nove centavos no mercado'
        )
        self.assertEqual(197.99, campos['valor'])
        self.assertEqual('mercado', campos['descricao'].lower())

    def test_um_real_e_centavos_por_extenso(self):
        self.assertEqual(
            1.50,
            self.extrair('gastei um real e cinquenta centavos no mercado')['valor'],
        )

    def test_valor_somente_em_centavos(self):
        campos = self.extrair('gastei 99 centavos no mercado')
        self.assertEqual(0.99, campos['valor'])
        self.assertEqual('mercado', campos['descricao'].lower())

    def test_valor_somente_em_centavos_por_extenso(self):
        campos = self.extrair('gastei noventa e nove centavos no mercado')
        self.assertEqual(0.99, campos['valor'])
        self.assertEqual('mercado', campos['descricao'].lower())

    def test_reais_sem_centavos_continua_aceito(self):
        self.assertEqual(197.0, self.extrair('gastei 197 reais no mercado')['valor'])

    def test_centavos_fora_do_intervalo_sao_rejeitados(self):
        with self.assertRaisesRegex(ValueError, '0 a 99 centavos'):
            self.extrair('gastei 197 reais e 120 centavos no mercado')

    def test_duas_movimentacoes_continuam_rejeitadas(self):
        with self.assertRaisesRegex(ValueError, 'mais de um'):
            self.extrair('gastei 197 reais e mais 20 reais no mercado')


if __name__ == '__main__':
    unittest.main()
