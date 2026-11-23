"""Contratos da taxonomia única usada por texto, áudio, formulário e fixos."""
from datetime import date
import unittest

import compromissos
import services
from categorias import (
    CATEGORIAS_CANONICAS,
    canonicalizar_categoria,
    inferir_categoria,
    sugerir_categoria,
)
from parser_financeiro import detectar_categoria, parse_mensagem
from registro_conversa import extrair_campos, normalizar
from telegram_experiencia import Experience


MATRIZ = {
    'Pet Shop': 'Pet',
    'consulta no veterinário': 'Pet',
    'ração do cachorro': 'Pet',
    'remédio ifood': 'Saúde',
    'café da manhã médico': 'Alimentação',
    'óculos de grau': 'Saúde',
    'corte de cabelo': 'Beleza',
    'curso de Python': 'Educação',
    'papelaria': 'Educação',
    'empréstimo pessoal': 'Dívidas',
    'passagem aérea': 'Viagem',
    'hotel na praia': 'Viagem',
    'passagem de trem': 'Transporte',
    'Uber': 'Transporte',
    'conta de luz': 'Moradia',
    'YouTube Premium': 'Assinaturas',
    'monitor Mercado Livre': 'Eletrônicos',
    'camiseta da Shein': 'Vestuário',
    'compras no supermercado': 'Mercado',
    'almoço no iFood': 'Alimentação',
    'ingresso do cinema': 'Lazer',
}


class CategorizacaoUnificadaTests(unittest.TestCase):
    def test_matriz_estrategica(self):
        for texto,esperada in MATRIZ.items():
            with self.subTest(texto=texto):
                self.assertEqual(esperada,inferir_categoria(texto))

    def test_motores_de_texto_formulario_e_fixos_usam_mesma_fonte(self):
        experience=Experience(date_provider=lambda:date(2026,10,8))
        for texto,esperada in MATRIZ.items():
            with self.subTest(texto=texto):
                self.assertEqual(esperada,detectar_categoria(normalizar(texto),'despesa'))
                self.assertEqual(esperada,services.texto_para_categoria(texto))
                self.assertEqual(esperada,compromissos.inferir_categoria(texto,texto))
                self.assertEqual(esperada,experience._registration_category(texto,'despesa'))

    def test_texto_e_audio_equivalentes(self):
        frase='gastei 60 reais no petshop pagando com cartão de crédito do Itaú'
        audio=extrair_campos(frase,hoje=date(2026,10,8),tipo='despesa')
        escrito=parse_mensagem(frase,data_referencia=date(2026,10,8))
        self.assertEqual('Pet',audio['categoria'])
        self.assertEqual(audio['categoria'],escrito['categoria'])

    def test_receita_e_categoria_explicita_prevalecem(self):
        self.assertEqual('Receita',inferir_categoria('salário mensal','receita'))
        parsed=parse_mensagem('gastei 20 no petshop categoria Família',data_referencia=date(2026,10,8))
        self.assertEqual('Família',parsed['categoria'])

    def test_marketplace_sem_produto_nao_inventa_categoria(self):
        for texto in ('Mercado Pago','Mercado Livre','Shopee','Amazon'):
            with self.subTest(texto=texto):self.assertIsNone(sugerir_categoria(texto))

    def test_canonicalizacao_preserva_taxonomia_e_categoria_personalizada(self):
        for categoria in CATEGORIAS_CANONICAS:
            self.assertEqual(categoria,canonicalizar_categoria(categoria.lower()))
        self.assertEqual('Família',canonicalizar_categoria('Família'))


if __name__=='__main__':
    unittest.main()
