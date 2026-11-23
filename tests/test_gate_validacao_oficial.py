import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "validacao" / "validar_versao_oficial.py"


def _carregar_gate():
    spec = importlib.util.spec_from_file_location("gate_oficial_sob_teste", GATE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class GateValidacaoOficialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = GATE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(GATE))
        cls.gate = _carregar_gate()

    def test_gate_aprova_so_com_a_suite_python_completa(self):
        # Painel web removido em 13/11/2026: não há mais contratos JavaScript.
        self.assertIn("result['python_approved']=bool(result.get('approved')) and not timeout", self.source)
        self.assertIn("result['approved']=result['python_approved']", self.source)
        self.assertNotIn("'node'", self.source)

    def test_gate_bloqueia_caminho_do_banco_oficial(self):
        # Sem alternativa comportamental: o HARNESS roda em subprocesso isolado.
        self.assertIn("ASSESSOR_TEST_FORBIDDEN_DB", self.gate.HARNESS)
        self.assertIn("Teste tentou acessar o banco oficial", self.gate.HARNESS)
        self.assertIn("db._open_connection=guarded_open_connection", self.gate.HARNESS)

    def test_harness_e_sintaticamente_valido(self):
        ast.parse(self.gate.HARNESS)

    def test_parser_padroes(self):
        args = self.gate.criar_parser().parse_args(["--saida", "x"])
        self.assertEqual(args.timeout, 1200)
        self.assertEqual(args.workers, 1)

    def test_parser_aceita_timeout_e_workers(self):
        args = self.gate.criar_parser().parse_args(["--saida", "x", "--timeout", "30", "--workers", "4"])
        self.assertEqual((args.timeout, args.workers), (30, 4))

    def test_listar_modulos_a_partir_de_diretorio_falso(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "tests").mkdir()
            (stage / "testes_v39").mkdir()
            for nome in ("tests/test_a.py", "tests/test_b.py", "tests/__init__.py", "tests/auxiliar.py",
                         "testes_v39/test_v.py", "testes_v39/__init__.py"):
                (stage / nome).write_text("", encoding="utf-8")
            self.assertEqual(
                self.gate.listar_modulos(stage),
                ["tests.test_a", "tests.test_b", "testes_v39.test_v", "test_rc307_deduplicacao"],
            )

    def test_particionar_cobre_cada_modulo_uma_vez_e_isola_o_mais_pesado(self):
        pesos = {"pesado": 100, "m1": 15, "m2": 12, "m3": 10, "m4": 1, "m5": 1, "m6": 3}
        lotes = self.gate.particionar(pesos, 4)
        self.assertEqual(len(lotes), 4)
        planos = [m for lote in lotes for m in lote]
        self.assertEqual(sorted(planos), sorted(pesos))
        self.assertEqual(lotes[0][0], "pesado")
        self.assertEqual(lotes[0], ["pesado"])

    def test_particionar_um_worker_mantem_tudo_junto(self):
        lotes = self.gate.particionar({"a": 1, "b": 2}, 1)
        self.assertEqual(len(lotes), 1)
        self.assertEqual(sorted(lotes[0]), ["a", "b"])

    def test_particionar_mais_workers_que_modulos_deixa_lotes_vazios(self):
        lotes = self.gate.particionar({"a": 1}, 3)
        self.assertEqual(len(lotes), 3)
        self.assertEqual(sum(len(l) for l in lotes), 1)

    def test_agregar_soma_e_exige_todos_aprovados(self):
        ok = {"version": "9", "tests": 3, "failures": 0, "errors": 0, "skipped": 0, "approved": True,
              "action_successes": {"x": 2}}
        outro = dict(ok, tests=4, action_successes={"x": 1, "y": 5})
        total = self.gate.agregar([ok, outro], [0, 0])
        self.assertEqual(total["tests"], 7)
        self.assertEqual(total["action_successes"], {"x": 3, "y": 5})
        self.assertTrue(total["approved"])
        self.assertFalse(self.gate.agregar([ok, outro], [0, 1])["approved"])
        self.assertFalse(self.gate.agregar([ok, dict(outro, skipped=1)], [0, 0])["approved"])

    def test_agregar_worker_sem_resultado_conta_como_erro(self):
        total = self.gate.agregar([None], [1])
        self.assertFalse(total["approved"])
        self.assertEqual(total["errors"], 1)

    def test_dividir_pesados_lista_os_mesmos_testes_que_o_loader(self):
        # A divisão por AST não pode perder teste herdado: compara com o unittest.
        for modulo in self.gate.DIVIDIR_POR_TESTE:
            ids = self.gate.testes_do_modulo(ROOT, modulo)
            carregados = unittest.defaultTestLoader.loadTestsFromName(modulo)
            reais = sorted(t.id() for grupo in carregados for t in grupo)
            self.assertEqual(sorted(ids), reais)
        pesos = self.gate.dividir_pesados(ROOT, {"tests.test_saldo_ajuste_para_frente": 100, "outro": 3})
        self.assertEqual(pesos["outro"], 3)
        self.assertNotIn("tests.test_saldo_ajuste_para_frente", pesos)
        self.assertGreater(len(pesos), 10)

    def test_pesos_conhecidos_tem_o_modulo_mais_lento_no_topo(self):
        pesos = self.gate.PESOS_CONHECIDOS
        self.assertEqual(max(pesos, key=pesos.get), "tests.test_saldo_ajuste_para_frente")


if __name__ == "__main__":
    unittest.main()
