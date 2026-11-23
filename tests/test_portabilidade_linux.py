"""Portabilidade para o servidor Linux (Oracle Cloud), sem mudar o comportamento no Windows.

Roda no Windows simulando ``os.name == 'posix'`` nos pontos que escolhem o caminho
do sistema; no servidor, o gate roda tudo de verdade em Linux.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import estado_runtime as er
import telegram_midia as midia
import transcricao_audio

RAIZ = Path(__file__).resolve().parents[1]


class EstadoProtegidoForaDoWindowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='port_'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = patch.object(er, 'CHAVE_LOCAL', self.tmp / '.runtime' / 'chave_local.key')
        p.start()
        self.addCleanup(p.stop)

    def test_local_protege_e_recupera(self):
        dado = b'{"senha":"x"}'
        cifrado = er._local_protect(dado)
        self.assertNotIn(b'senha', cifrado)
        self.assertEqual(dado, er._local_unprotect(cifrado))
        self.assertEqual(32, len(er.CHAVE_LOCAL.read_bytes()))
        if os.name != 'nt':
            self.assertEqual(0o600, er.CHAVE_LOCAL.stat().st_mode & 0o777)

    def test_store_funciona_com_os_posix(self):
        with patch.object(er, 'EH_WINDOWS', False):
            store = er.ProtectedJsonStore(self.tmp / 'estado.bin')
            self.assertTrue(store.enabled)
            self.assertTrue(store.save({'senha': 'abc'}))
            self.assertNotIn(b'abc', (self.tmp / 'estado.bin').read_bytes())
            self.assertEqual({'senha': 'abc'}, store.load())

    def test_chave_trocada_nao_abre(self):
        cifrado = er._local_protect(b'segredo')
        er.CHAVE_LOCAL.write_bytes(os.urandom(32))
        with self.assertRaises(Exception):
            er._local_unprotect(cifrado)


class OcrForaDoWindowsTests(unittest.TestCase):
    def foto(self):
        from PIL import Image
        tmp = Path(tempfile.mkdtemp(prefix='ocr_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        caminho = tmp / 'c.png'
        Image.new('RGB', (40, 20), 'white').save(caminho)
        return caminho

    def test_usa_tesseract_em_portugues(self):
        chamadas = []

        def run(cmd, **kw):
            chamadas.append(cmd)
            return SimpleNamespace(returncode=0, stdout='PIX R$ 52,90 13/11/2026\n')
        with patch.object(midia, 'EH_WINDOWS', False), patch.object(midia.subprocess, 'run', run):
            texto = midia.reconhecer_foto(self.foto())
        self.assertIn('R$ 52,90', texto)
        self.assertEqual(['tesseract'], chamadas[0][:1])
        self.assertEqual(['-l', 'por'], chamadas[0][-2:])
        self.assertEqual({'valor': 52.9, 'data': '2026-11-13'}, midia.receipt_fields(texto))

    def test_sem_tesseract_explica_e_nao_quebra(self):
        def run(cmd, **kw):
            raise FileNotFoundError('tesseract')
        with patch.object(midia, 'EH_WINDOWS', False), patch.object(midia.subprocess, 'run', run):
            with self.assertRaisesRegex(midia.MediaError, 'Registrar por etapas'):
                midia.reconhecer_foto(self.foto())


class RcloneTests(unittest.TestCase):
    def test_sem_remoto_nao_chama_rclone(self):
        import backup_externo as bx
        with patch.dict(os.environ, {'ASSESSOR_BACKUP_EXTERNO_RCLONE': ''}), patch.object(bx.subprocess, 'run') as run:
            bx._enviar_rclone(Path('x.assessor-bkp'))
        run.assert_not_called()

    def test_envia_e_limpa_antigos_so_do_assessor(self):
        import backup_externo as bx
        chamadas = []
        with patch.dict(os.environ, {'ASSESSOR_BACKUP_EXTERNO_RCLONE': 'onedrive:Backups/Assessor'}), \
                patch.object(bx.subprocess, 'run', lambda cmd, **kw: chamadas.append(cmd) or SimpleNamespace(returncode=0, stderr='')):
            bx._enviar_rclone(Path('a.assessor-bkp'), Path('LEIA-ME.txt'))
        self.assertEqual(['rclone', 'copy', 'a.assessor-bkp', 'onedrive:Backups/Assessor'], chamadas[0])
        self.assertEqual('copy', chamadas[1][1])
        self.assertEqual(['rclone', 'delete', 'onedrive:Backups/Assessor', '--min-age', '45d',
                          '--include', 'assessor_*.assessor-bkp'], chamadas[2])

    def test_falha_do_rclone_vira_erro_do_backup_externo(self):
        import backup_externo as bx
        with patch.dict(os.environ, {'ASSESSOR_BACKUP_EXTERNO_RCLONE': 'onedrive:x'}), \
                patch.object(bx.subprocess, 'run', lambda cmd, **kw: SimpleNamespace(returncode=1, stderr='token expirado')):
            with self.assertRaisesRegex(bx.BackupExternoErro, 'token expirado'):
                bx._enviar_rclone(Path('a.assessor-bkp'))


class AudioEServicoTests(unittest.TestCase):
    def test_whisper_sem_exe_no_linux_e_com_exe_no_windows(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ASSESSOR_AUDIO_CPP_EXE', None)
            with patch.object(transcricao_audio, 'EH_WINDOWS', False):
                self.assertEqual('whisper-cli', transcricao_audio.audio_config()['cpp_exe'].name)
            with patch.object(transcricao_audio, 'EH_WINDOWS', True):
                self.assertEqual('whisper-cli.exe', transcricao_audio.audio_config()['cpp_exe'].name)

    def test_unidade_systemd_reinicia_sempre_e_sobe_com_o_servidor(self):
        unidade = (RAIZ / 'deploy' / 'assessor.service').read_text(encoding='utf-8')
        for trecho in ('Restart=always', 'StartLimitIntervalSec=0', 'WantedBy=multi-user.target',
                       'After=network-online.target', 'UMask=0077'):
            self.assertIn(trecho, unidade)

    def test_scripts_do_servidor_com_lf(self):
        for nome in ('deploy/instalar_servidor.sh', 'deploy/assessor.service'):
            self.assertNotIn(b'\r\n', (RAIZ / nome).read_bytes(), nome)


if __name__ == '__main__':
    unittest.main()
