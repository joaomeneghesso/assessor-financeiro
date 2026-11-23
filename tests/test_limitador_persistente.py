import copy
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from limitador_persistente import LimitadorPersistente


class StoreFalso:
    def __init__(self, dados=None):
        self.dados = dados

    def load(self, default=None):
        return copy.deepcopy(self.dados) if self.dados is not None else (default if default is not None else {})

    def save(self, valor):
        self.dados = copy.deepcopy(valor)
        return True


class StoreQuebrado:
    def load(self, default=None):
        raise OSError("falha")

    def save(self, valor):
        raise OSError("falha")


def _bloquear(lim):
    for _ in range(5):
        lim.register_failure(1, 1)


class LimitadorPersistenteTests(unittest.TestCase):
    def test_bloqueio_sobrevive_a_novo_objeto(self):
        store = StoreFalso()
        lim = LimitadorPersistente(5, 15, store)
        _bloquear(lim)
        self.assertTrue(lim.status(1, 1)[0])
        novo = LimitadorPersistente(5, 15, store)
        self.assertTrue(novo.status(1, 1)[0])

    def test_sucesso_limpa(self):
        store = StoreFalso()
        lim = LimitadorPersistente(5, 15, store)
        _bloquear(lim)
        lim.register_success(1, 1)
        self.assertFalse(LimitadorPersistente(5, 15, store).status(1, 1)[0])

    def test_falhas_parciais_persistem(self):
        store = StoreFalso()
        lim = LimitadorPersistente(5, 15, store)
        for _ in range(4):
            lim.register_failure(1, 1)
        novo = LimitadorPersistente(5, 15, store)
        bloqueado, _, falhas = novo.register_failure(1, 1)
        self.assertTrue(bloqueado)
        self.assertEqual(falhas, 5)

    def test_bloqueio_vencido_nao_restaura(self):
        passado = (datetime.now() - timedelta(minutes=1)).isoformat()
        chave = "pin:1:1"
        store = StoreFalso({"version": 1, "states": {chave: {"failures": 5, "locked_until": passado}}})
        lim = LimitadorPersistente(5, 15, store)
        self.assertFalse(lim.status(1, 1)[0])

    def test_bloqueio_futuro_restaura(self):
        futuro = (datetime.now() + timedelta(minutes=10)).isoformat()
        store = StoreFalso({"version": 1, "states": {"pin:1:1": {"failures": 5, "locked_until": futuro}}})
        self.assertTrue(LimitadorPersistente(5, 15, store).status(1, 1)[0])

    def test_store_corrompido_nao_levanta(self):
        for lixo in ({"states": "lixo"}, {"states": {"a": "x", "b": {"failures": "z"}}}, {"states": {"pin:1:1": {"failures": 5, "locked_until": "nao-data"}}}):
            lim = LimitadorPersistente(5, 15, StoreFalso(lixo))
            self.assertFalse(lim.status(1, 1)[0])

    def test_store_quebrado_nao_impede_funcionamento(self):
        with self.assertLogs("assessor.limitador", level="WARNING"):
            lim = LimitadorPersistente(5, 15, StoreQuebrado())
            _bloquear(lim)
        self.assertTrue(lim.status(1, 1)[0])

    def test_com_protected_json_store(self):
        from estado_runtime import ProtectedJsonStore

        with tempfile.TemporaryDirectory() as tmp:
            store = ProtectedJsonStore(Path(tmp) / "limitador.bin")
            if not store.enabled:
                self.skipTest("ProtectedJsonStore indisponível neste ambiente")
            lim = LimitadorPersistente(5, 15, store)
            try:
                _bloquear(lim)
            except Exception as exc:  # pragma: no cover
                self.skipTest(f"DPAPI indisponível: {exc}")
            if not (Path(tmp) / "limitador.bin").is_file():
                self.skipTest("DPAPI não gravou o estado")
            self.assertTrue(LimitadorPersistente(5, 15, store).status(1, 1)[0])
            lim.register_success(1, 1)
            self.assertFalse(LimitadorPersistente(5, 15, store).status(1, 1)[0])


if __name__ == "__main__":
    unittest.main()
