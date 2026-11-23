import unittest

import sugestoes_comando as sc


def _junto(lista):
    return " | ".join(lista).lower()


class SugestoesComandoTests(unittest.TestCase):
    def test_catalogo_itens_validos(self):
        self.assertGreaterEqual(len(sc.CATALOGO_COMANDOS), 50)
        for cmd, kw in sc.CATALOGO_COMANDOS:
            self.assertIsInstance(cmd, str)
            self.assertTrue(cmd.strip())
            self.assertIsInstance(kw, str)

    def test_erro_de_digitacao(self):
        self.assertIn("saldo", sc.sugerir_comandos("sado"))
        self.assertIn("fixos", sc.sugerir_comandos("fixso"))
        self.assertIn("parcela", _junto(sc.sugerir_comandos("parcleas")))

    def test_frases(self):
        s = _junto(sc.sugerir_comandos("relatorio fixos"))
        self.assertTrue("fixos" in s or "relat" in s)
        s = _junto(sc.sugerir_comandos("alterar data do 3 para ontem"))
        self.assertTrue("corrigir" in s or "alterar" in s or "mudar" in s)

    def test_texto_sem_relacao(self):
        self.assertEqual(sc.sugerir_comandos("xyzqwe"), [])
        self.assertEqual(sc.sugerir_comandos(""), [])
        msg = sc.mensagem_comando_nao_reconhecido("xyzqwe")
        self.assertIn("Registrar", msg)
        self.assertIn("Menu", msg)
        self.assertIn("Nada foi registrado.", msg)

    def test_limite_e_duplicatas(self):
        for texto in ("alterar fixo", "saldo", "apagar"):
            self.assertLessEqual(len(sc.sugerir_comandos(texto, 2)), 2)
            r = sc.sugerir_comandos(texto, 10)
            self.assertEqual(len(r), len(set(r)))
        self.assertEqual(sc.sugerir_comandos("saldo", 0), [])

    def test_determinismo(self):
        a = sc.sugerir_comandos("alterar fixo 3")
        for _ in range(5):
            self.assertEqual(a, sc.sugerir_comandos("alterar fixo 3"))

    def test_mensagem_nao_reconhecido(self):
        msg = sc.mensagem_comando_nao_reconhecido("apagar")
        self.assertTrue(msg.startswith("🤔 Não entendi"))
        self.assertIn("pedido para apagar", msg)
        self.assertIn("Nada foi registrado.", msg)
        self.assertLessEqual(len(msg.splitlines()), 8)
        self.assertNotIn("<", msg)

    def test_truncamento(self):
        longo = "a" * 200
        msg = sc.mensagem_comando_nao_reconhecido(longo)
        self.assertNotIn("a" * 61, msg)
        self.assertLessEqual(len(msg.splitlines()), 8)

    def test_mensagem_sem_valor(self):
        msg = sc.mensagem_sem_valor("mercado")
        self.assertTrue(msg.startswith("🤔 Não encontrei um valor"))
        self.assertIn("gastei 35 no mercado", msg)
        self.assertIn("Nada foi registrado", msg)
        self.assertIn("buscar mercado", sc.mensagem_sem_valor("buscar"))
        self.assertIn("extrato itaú", sc.mensagem_sem_valor("extrato"))


if __name__ == "__main__":
    unittest.main()
