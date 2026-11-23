"""O gate de PIN enxerga o mesmo texto que o núcleo executa (espaços, sinônimos) e vale no fluxo guiado."""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock

import app
import security
import services as svc

PIN = "123456"


def _hash():
    return security.hash_secret(PIN, iterations=1000, salt=b"0123456789abcdef")


def _msg_update(texto, user_id=1, chat_id=1):
    msg = SimpleNamespace(text=texto, message_id=7, reply_text=AsyncMock())
    return SimpleNamespace(message=msg, callback_query=None,
                           effective_user=SimpleNamespace(id=user_id),
                           effective_chat=SimpleNamespace(id=chat_id))


class GateNormalizacaoTests(unittest.TestCase):
    def test_variantes_de_espaco_exigem_pin(self):
        for texto in ("backup", "gerar backup", "gerar  backup", "gerar\tbackup", "gerar backup",
                      "  GERAR   BACKUP  ", "exportar  tudo", "exportar csv  tudo", "exportar  csv  tudo",
                      "exportar\tcsv\ttudo", "apagar  1-50", "apagar 1 - 50", "confirmar  importacao",
                      "status", "saude  do  assessor"):
            with self.subTest(texto=repr(texto)):
                self.assertTrue(app.acao_exige_pin(texto))

    def test_uso_diario_continua_sem_pin(self):
        for texto in ("saldo", "gastei 45 no mercado", "quanto vou pagar", "exportar csv 2026-07",
                      "apagar 12", "menu", "", None, "backup do celular custou 50"):
            with self.subTest(texto=repr(texto)):
                self.assertFalse(app.acao_exige_pin(texto))

    def test_o_que_o_nucleo_trata_como_sinonimo_tambem_exige_pin(self):
        # Para cada texto que o núcleo converte num comando protegido, o gate tem de concordar.
        protegidos = ("backup", "gerar backup", "exportar csv tudo", "exportar tudo", "status")
        candidatos = ("fazer backup", "criar backup", "gerar  backup", "exportar  tudo", "backup agora",
                      "exporta tudo", "exportar todos", "exportar base inteira", "baixar backup")
        for texto in candidatos:
            canonico = svc.normalizar_comando_sinonimos(" ".join(texto.lower().split()))
            if canonico in protegidos:
                with self.subTest(texto=texto, canonico=canonico):
                    self.assertTrue(app.acao_exige_pin(texto))

    def test_exportacao_grande_com_espacos_extras_exige_pin(self):
        for texto in ("exportar  csv  2000-01-01 2099-12-31", "exportar csv   2000-01-01   2099-12-31",
                      "exportar\tcsv tudo", "exportar  csv  tudo"):
            with self.subTest(texto=repr(texto)):
                self.assertTrue(svc.exportacao_exige_pin(texto, "s-gate"))
        self.assertFalse(svc.exportacao_exige_pin("exportar  csv  2026-07", "s-gate"))


class GateNoFluxoGuiadoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patches = [
            mock.patch.object(app, "ASSESSOR_PIN_HASH", _hash()),
            mock.patch.object(app, "ASSESSOR_PIN", ""),
            mock.patch.object(app, "ASSESSOR_PIN_LENGTH", "6"),
            mock.patch.object(app, "AUTH_LIMITER", security.AuthAttemptLimiter(3, 15)),
            mock.patch.object(app, "registrar_auditoria", mock.Mock()),
            mock.patch.dict(app.PIN_TECLADO, {}, clear=True),
            mock.patch.dict(app.ACAO_PENDENTE_PIN, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_RESET_PIN, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_EXCLUSAO, {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: app.limpar_pendencia_guiada(1))
        app.bloquear_assessor(1)

    async def _enviar(self, texto, comando_montado):
        update = _msg_update(texto)
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app.ux, "dispatch_text", AsyncMock(return_value=False)), \
                mock.patch.object(app, "montar_comando_de_pendencia", mock.Mock(return_value=comando_montado)), \
                mock.patch.object(app, "enviar_teclado_pin", AsyncMock()) as teclado, \
                mock.patch.object(app, "enviar_acao_digitando", AsyncMock()), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()), \
                mock.patch.object(app, "executar_core", AsyncMock(return_value="ok")) as core:
            await app.receber_mensagem(update, SimpleNamespace())
        return teclado, core

    async def test_comando_protegido_montado_pelo_fluxo_guiado_pede_pin(self):
        app.definir_pendencia_guiada(1, "qualquer", {})
        teclado, core = await self._enviar("backup", "backup")
        teclado.assert_awaited()
        core.assert_not_awaited()
        self.assertIsNotNone(app.obter_pendencia_guiada(1))  # preservada para refazer após o PIN

    async def test_comando_comum_do_fluxo_guiado_segue_sem_pin(self):
        app.definir_pendencia_guiada(1, "qualquer", {})
        teclado, core = await self._enviar("7 Mercado", "corrigir categoria 7 para Mercado")
        teclado.assert_not_awaited()
        core.assert_awaited_once()
        self.assertIsNone(app.obter_pendencia_guiada(1))

    async def test_pendencia_guiada_expira(self):
        app.definir_pendencia_guiada(1, "qualquer", {})
        app.PENDENCIAS_GUIADAS[1]["criado_em"] = datetime.now() - timedelta(minutes=11)
        self.assertIsNone(app.obter_pendencia_guiada(1))
        self.assertNotIn(1, app.PENDENCIAS_GUIADAS)


if __name__ == "__main__":
    unittest.main()
