"""O mapa de rotas (docs/mapa/dados/*.json) não pode ficar muito defasado do código.

Roda tools/verificar_mapa.py (análise estática: ações de Experience.act, telas
screen_*, CommandHandlers de app.py e destinos do roteador legado) e falha
quando a soma "no código e faltando no mapa" + "no mapa e inexistente no
código" passa de LIMITE. Em 12/11/2026, depois de regenerar o mapa, a
defasagem era 0 (antes: 56). Ao criar rota nova, atualize o JSON do arquivo
correspondente e rode tools/gerar_mapa.py (ver docs/mapa/LEIA-ME.md).
"""
import importlib.util
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LIMITE = 10


def _verificador():
    spec = importlib.util.spec_from_file_location("verificar_mapa_sob_teste", RAIZ / "tools" / "verificar_mapa.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class MapaRotasAtualizadoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # O gate copia docs/mapa/dados e tools/verificar_mapa.py para a pasta temporária.
        cls.resultado = _verificador().verificar()

    def test_defasagem_dentro_do_limite(self):
        r = self.resultado
        detalhe = {k: v for g in ("faltam_no_mapa", "sobram_no_mapa") for k, v in
                   ((f"{g}.{c}", ids) for c, ids in r[g].items()) if v}
        self.assertLessEqual(r["defasagem"], LIMITE,
                             f"Mapa de rotas defasado ({r['defasagem']} itens > {LIMITE}): {detalhe}. "
                             "Atualize docs/mapa/dados/*.json e rode tools/gerar_mapa.py.")

    def test_verificador_enxerga_o_codigo(self):
        # Guarda contra o verificador "passar" por não achar nada (ex.: arquivo renomeado).
        c = self.resultado["contagem_codigo"]
        self.assertGreater(c["acoes"], 50)
        self.assertGreater(c["telas"], 20)
        self.assertGreater(c["comandos"], 10)
        self.assertGreater(c["roteador"], 50)


if __name__ == "__main__":
    unittest.main()
