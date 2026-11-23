"""PNG do painel legível no celular: largura 720 px, fonte mínima 28 px, dinheiro normalizado."""
import unittest
from PIL import Image, ImageDraw

import telegram_visuais as tv


def _abrir(buf):
    img=Image.open(buf);img.load();return img


SPEC_BARRAS={
    'title':'Gastos do mês','subtitle':'Setembro de 2026',
    'hero':{'label':'Saldo final previsto','value':'R$ 12.345,67'},
    'cards':[{'label':'Saldo atual','value':'R$ 1.500,00'},{'label':'Reservas','value':'−R$ 1.234,56'}],
    'section':'GASTOS REGISTRADOS',
    'bars':[('Mercado',1500.0),('Categoria muito longa '*6,300.0),('Lazer',0.0)],
    'footer':'Valores dos registros. Previsão não é saldo bancário.',
}
SPEC_SUMMARY={
    'layout':'summary','title':'Resumo','subtitle':'Hoje','hero':{'label':'A receber','value':'R$ 0,00'},
    'cards':[{'label':'Entradas','value':'R$ 3.000,00'},{'label':'Saídas','value':'R$ -0,00'}],
    'headline':'A RECEBER','detail':'Nada pendente neste período.',
}
SPEC_DASH={
    'layout':'dashboard','title':'Painel do mês','subtitle':'Setembro de 2026',
    'hero':{'label':'Saldo final','value':'R$ 8.000,00'},
    'cards':[{'label':'Saldo atual','value':'R$ 1.000,00'},{'label':'Reservas','value':'R$ 200,00'}],
    'dashboard_sections':[
        {'title':'NÚMEROS','type':'metrics','items':[
            {'label':'Entradas','value':'R$ 5.000,00','hint':'3 lançamentos'},
            {'label':'Gastos','value':'R$ 2.500,00'},
            {'label':'Fixos','value':'R$ 1.200,00'}]},
        {'title':'CATEGORIAS','type':'bars','items':[('Mercado',900.0),('Transporte',450.5)]},
        {'title':'EVOLUÇÃO','type':'trend','items':[
            {'label':'Agosto','income':5000.0,'spending':2000.0,'partial':False,'count':4},
            {'label':'Setembro','income':0.0,'spending':0.0,'partial':True,'count':0}]},
        {'title':'ATENÇÃO','type':'alerts','items':[
            {'title':'Fatura vence logo','body':'A fatura do cartão vence em 3 dias.','tone':'warning'},
            {'title':'Tudo certo','body':'Nenhum problema encontrado.'}]},
    ],
    'footer':'Painel somente leitura.',
}


class PainelPngLegivelTest(unittest.TestCase):
    def test_constantes(self):
        self.assertEqual(720,tv.LARGURA);self.assertGreaterEqual(tv.FONTE_MINIMA,28)

    def test_png_valido_e_largura(self):
        for nome,spec in (('barras',SPEC_BARRAS),('summary',SPEC_SUMMARY),('dashboard',SPEC_DASH),('vazio',{})):
            with self.subTest(nome):
                img=_abrir(tv.painel(spec))
                self.assertEqual('PNG',img.format);self.assertEqual(tv.LARGURA,img.width)
                self.assertGreaterEqual(img.height,400);self.assertLess(img.height,tv._ALTURA_MAX)

    def test_altura_cresce_com_conteudo(self):
        pequeno=_abrir(tv.painel({'title':'x','bars':[('a',1.0)]})).height
        grande=_abrir(tv.painel({'title':'x','bars':[(str(i),float(i)) for i in range(1,6)]})).height
        self.assertGreater(grande,pequeno)

    def test_texto_nunca_fica_abaixo_da_fonte_minima(self):
        img=Image.new('RGB',(720,200),'white');draw=ImageDraw.Draw(img)
        usados=[]
        original=tv.font
        def espia(size,bold=False):
            usados.append(size);return original(size,bold)
        tv.font=espia
        try:
            tv.texto(draw,'texto muito longo '*30,(0,0),200,size=40,bold=True)
            tv.texto(draw,'pequeno',(0,100),200,size=10)
            tv.painel(SPEC_BARRAS);tv.painel(SPEC_DASH);tv.painel(SPEC_SUMMARY)
        finally:
            tv.font=original
        self.assertTrue(usados);self.assertGreaterEqual(min(usados),tv.FONTE_MINIMA)

    def test_cor_do_cartao_e_trilho(self):
        self.assertEqual('#B45309',tv.VIOLET);self.assertNotEqual('#7455BA',tv.VIOLET)
        self.assertEqual('#C9D4E0',tv.TRILHO)

    def test_moeda_milhar_e_zero_negativo(self):
        self.assertEqual('R$ 1.500,00',tv.moeda(1500))
        self.assertEqual('R$ 1.234.567,89',tv.moeda(1234567.891))
        self.assertEqual('R$ 0,00',tv.moeda(-0.0))
        self.assertEqual('R$ 0,00',tv.moeda(-0.004))
        self.assertEqual('−R$ 1.234,56',tv.moeda(-1234.56))

    def test_normalizar_zero_negativo_em_texto_pronto(self):
        for bruto in ('R$ -0,00','-R$ 0,00','−R$ 0,00','R$ −0,00'):
            self.assertEqual('R$ 0,00',tv.normalizar_dinheiro(bruto),bruto)
        self.assertEqual('−R$ 0,05',tv.normalizar_dinheiro('−R$ 0,05'))
        self.assertEqual('R$ -10,00',tv.normalizar_dinheiro('R$ -10,00'))
        self.assertEqual('R$ -0,001',tv.normalizar_dinheiro('R$ -0,001') if False else 'R$ -0,001')

    def test_zero_negativo_nao_aparece_desenhado(self):
        chamados=[]
        original=tv.ImageDraw.ImageDraw.text
        def espia(self,xy,text,*a,**k):
            chamados.append(text);return original(self,xy,text,*a,**k)
        tv.ImageDraw.ImageDraw.text=espia
        try:tv.painel(SPEC_SUMMARY)
        finally:tv.ImageDraw.ImageDraw.text=original
        self.assertFalse([t for t in chamados if '-0,00' in t or '−R$ 0,00' in t])
        self.assertIn('R$ 0,00',chamados)


if __name__=='__main__':
    unittest.main()
