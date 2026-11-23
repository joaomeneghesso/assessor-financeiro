"""Backup externo criptografado (OneDrive): pacote banco + código + .env, AES-256-GCM.

Tudo em pastas temporárias: destino, senha (DPAPI), status, .env e repositório git
de teste. Nunca toca o OneDrive, o .env nem o .runtime reais.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import backup_externo as bx
import database as db
import services as svc

SENHA = 'senha-de-teste-123'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bx_teste_'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.destino = self.tmp / 'OneDrive' / 'Backups' / 'Assessor'
        env = self.tmp / '.env'
        env.write_text('TELEGRAM_BOT_TOKEN=token-falso-de-teste\n', encoding='utf-8')
        self.banco = self.tmp / 'financeiro.db'
        self._patches = [
            patch.object(bx, 'ARQUIVO_SENHA', self.tmp / 'rt' / 'bx.bin'),
            patch.object(bx, 'ARQUIVO_STATUS', self.tmp / 'rt' / 'st.json'),
            patch.object(bx.config, 'ENV_PATH', env),
            patch.object(svc, 'DB_PATH', self.banco), patch.object(db, 'DB_PATH', self.banco),
            patch.object(svc, 'BACKUPS_DIR', self.tmp / 'backups'),
            patch.object(bx, '_git_bundle', self.bundle_falso),
            patch.dict(os.environ, {'ASSESSOR_BACKUP_EXTERNO_DIR': str(self.destino)}),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        db.inserir_transacao(dict(data='2026-11-01', tipo='despesa', valor=12.5, categoria='Lazer', descricao='Bar Bruno C',
                                  conta='Itaú', forma_pagamento='pix', parcelas_total=1))

    def bundle_falso(self, pasta):
        alvo = Path(pasta) / 'assessor.bundle'
        alvo.write_bytes(b'# git bundle de teste\n')
        return alvo

    def backup_local(self):
        caminho, _ = svc.criar_backup_db()
        return caminho


class NaoConfiguradoTests(Base):
    def test_sem_senha_nao_faz_nada_e_avisa(self):
        self.assertEqual('', bx.gerar_se_configurado(self.backup_local()))
        self.assertFalse(self.destino.exists())
        self.assertIn('não configurada', bx.linha_status())

    def test_senha_curta_recusada(self):
        with self.assertRaises(bx.BackupExternoErro):
            bx.salvar_senha('curta')
        self.assertFalse(bx.configurado())


class PacoteTests(Base):
    def setUp(self):
        super().setUp()
        bx.salvar_senha(SENHA)

    def gerar(self):
        return bx.gerar(self.backup_local())

    def test_arquivo_cifrado_nao_expoe_banco_nem_env(self):
        arquivo = self.gerar()
        self.assertTrue(arquivo.name.startswith('assessor_') and arquivo.name.endswith(bx.EXTENSAO))
        bruto = arquivo.read_bytes()
        self.assertTrue(bruto.startswith(bx.MAGIC))
        for segredo in (b'SQLite format 3', b'token-falso-de-teste', b'Bruno', b'MANIFESTO'):
            self.assertNotIn(segredo, bruto)
        self.assertTrue((self.destino / 'LEIA-ME.txt').exists())
        self.assertNotIn(SENHA, (self.destino / 'LEIA-ME.txt').read_text(encoding='utf-8'))
        self.assertEqual([], list(self.destino.glob('*.tmp')))

    def test_senha_certa_abre_tudo_e_errada_nao(self):
        arquivo = self.gerar()
        m = bx.conferir_pacote(arquivo.read_bytes(), SENHA)
        self.assertEqual({'financeiro.db', 'assessor.bundle', 'env.txt'}, set(m['arquivos']))
        with self.assertRaisesRegex(bx.BackupExternoErro, 'Senha errada'):
            bx.conferir_pacote(arquivo.read_bytes(), 'outra-senha-qualquer')

    def test_arquivo_adulterado_e_recusado(self):
        bruto = bytearray(self.gerar().read_bytes())
        bruto[-5] ^= 0xFF
        with self.assertRaises(bx.BackupExternoErro):
            bx.conferir_pacote(bytes(bruto), SENHA)

    def test_receita_do_leia_me_abre_o_arquivo_sem_o_projeto(self):
        """O script de 6 linhas do LEIA-ME (para um computador novo) decifra de verdade."""
        arquivo = self.gerar()
        texto = (self.destino / 'LEIA-ME.txt').read_text(encoding='utf-8')
        script = texto.split('--- abrir_backup.py ---\n', 1)[1].split('--- fim ---', 1)[0]
        pasta = self.tmp / 'computador_novo'
        pasta.mkdir()
        (pasta / 'abrir_backup.py').write_text(script, encoding='utf-8')
        # Só a senha é simulada (getpass lê do console); o script roda como o titular rodaria.
        (pasta / 'rodar.py').write_text("import getpass, runpy, sys\nsenha = sys.argv.pop()\n"
                                        "getpass.getpass = lambda p='': senha\n"
                                        "runpy.run_path('abrir_backup.py', run_name='__main__')\n", encoding='utf-8')
        r = subprocess.run([sys.executable, 'rodar.py', str(arquivo), SENHA], cwd=pasta,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, r.stderr)
        with zipfile.ZipFile(pasta / 'pacote.zip') as z:
            self.assertIn('financeiro.db', z.namelist())
            self.assertEqual(b'TELEGRAM_BOT_TOKEN=token-falso-de-teste', z.read('env.txt').strip())

    def test_rotacao_mantem_os_mais_recentes(self):
        momento = [datetime(2026, 11, 13, 3, 0)]
        with patch.object(bx, 'MANTER', 2), patch.object(bx.relogio, 'agora', lambda: momento[0]):
            for dia in range(3):
                momento[0] = datetime(2026, 11, 13, 3, 0) + timedelta(days=dia)
                self.gerar()
        nomes = sorted(p.name for p in self.destino.glob('*' + bx.EXTENSAO))
        self.assertEqual(['assessor_20261114_030000' + bx.EXTENSAO, 'assessor_20261115_030000' + bx.EXTENSAO], nomes)

    def test_restaurar_em_pasta_nova_e_nunca_por_cima(self):
        arquivo = self.gerar()
        nova = self.tmp / 'restaurado'
        bx.restaurar(arquivo, nova, SENHA)
        for nome in ('financeiro.db', 'env.txt', 'assessor.bundle', 'RESTAURAR.txt', 'MANIFESTO.json'):
            self.assertTrue((nova / nome).exists(), nome)
        with self.assertRaisesRegex(bx.BackupExternoErro, 'nova ou vazia'):
            bx.restaurar(arquivo, nova, SENHA)

    def test_falha_no_destino_nao_derruba_o_backup_diario_e_fica_visivel(self):
        bloqueio = self.tmp / 'arquivo_no_lugar_da_pasta'
        bloqueio.write_text('x')
        with patch.dict(os.environ, {'ASSESSOR_BACKUP_EXTERNO_DIR': str(bloqueio)}):
            linha = bx.gerar_se_configurado(self.backup_local())
        self.assertIn('⚠️ Cópia externa falhou', linha)
        self.assertIn('falhou', bx.linha_status())
        self.gerar()  # a próxima que der certo volta ao normal
        self.assertIn('OneDrive', bx.linha_status())

    def test_backup_automatico_do_bot_inclui_a_copia_externa(self):
        resposta = svc.gerar_backup_automatico()
        self.assertIn('💾 Backup automático gerado', resposta)
        self.assertIn('☁️ Cópia criptografada no OneDrive', resposta)
        self.assertEqual(1, len(list(self.destino.glob('*' + bx.EXTENSAO))))


class GitBundleRealTests(unittest.TestCase):
    def test_bundle_do_repositorio_inteiro(self):
        git = shutil.which('git')
        self.assertIsNotNone(git, 'git precisa estar no PATH (o backup diário usa git bundle)')
        tmp = Path(tempfile.mkdtemp(prefix='bx_git_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / 'repo'
        repo.mkdir()
        for args in (['init', '-q'], ['-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '--allow-empty', '-m', 'x']):
            subprocess.run([git, *args], cwd=repo, check=True, capture_output=True)
        with patch.object(bx, 'RAIZ', repo):
            bundle = bx._git_bundle(tmp)
        self.assertIsNotNone(bundle)
        r = subprocess.run([git, 'bundle', 'verify', str(bundle)], cwd=repo, capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr)

    def test_sem_repositorio_segue_sem_codigo(self):
        tmp = Path(tempfile.mkdtemp(prefix='bx_git_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        with patch.object(bx, 'RAIZ', tmp):
            self.assertIsNone(bx._git_bundle(tmp))


if __name__ == '__main__':
    unittest.main()
