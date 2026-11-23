"""Linha de comando do backup externo criptografado (rodar no terminal do titular).

    .\\.venv\\Scripts\\python.exe backup_externo_cli.py configurar   # escolhe a senha e faz a 1ª cópia
    .\\.venv\\Scripts\\python.exe backup_externo_cli.py agora        # cópia agora
    .\\.venv\\Scripts\\python.exe backup_externo_cli.py status
    .\\.venv\\Scripts\\python.exe backup_externo_cli.py verificar [arquivo]   # testa a restauração sem gravar nada
    .\\.venv\\Scripts\\python.exe backup_externo_cli.py restaurar <arquivo> <pasta-nova>

A senha é digitada aqui (getpass, não aparece na tela nem no histórico) e nunca
vai para o .env, o git ou o OneDrive.
"""
import getpass
import sys
from pathlib import Path

import config

config.carregar_dotenv()  # mesmo destino que o bot usa (ASSESSOR_BACKUP_EXTERNO_DIR)

import backup_externo as bx  # noqa: E402


def _pedir_senha_nova():
    senha = getpass.getpass(f'Nova senha do backup externo (mínimo {bx.SENHA_MINIMA} caracteres): ')
    if senha != getpass.getpass('Repita a senha: '):
        raise bx.BackupExternoErro('As senhas não conferem. Nada foi configurado.')
    return senha


def _ultimo_arquivo():
    arquivos = sorted(bx.destino().glob('assessor_*' + bx.EXTENSAO), key=lambda p: p.name)
    if not arquivos:
        raise bx.BackupExternoErro(f'Nenhum backup em {bx.destino()}.')
    return arquivos[-1]


def agora():
    from services import criar_backup_db
    banco, _ = criar_backup_db()
    if not banco:
        raise bx.BackupExternoErro('Banco de dados não encontrado.')
    caminho = bx.gerar(banco)
    print(f'Cópia criptografada gravada e conferida: {caminho}')


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    comando = argv[0]
    if comando == 'configurar':
        bx.salvar_senha(_pedir_senha_nova())
        print('Senha protegida neste computador (DPAPI no Windows; chave local 0600 no Linux).')
        print('IMPORTANTE: guarde esta senha no seu gerenciador de senhas. Sem ela,')
        print('nenhum backup externo pode ser aberto em outro computador.')
        print(f'Destino: {bx.destino()}')
        agora()
        return 0
    if comando == 'agora':
        agora()
        return 0
    if comando == 'status':
        print(bx.linha_status())
        print(f'Destino: {bx.destino()}')
        return 0
    if comando == 'verificar':
        arquivo = Path(argv[1]) if len(argv) > 1 else _ultimo_arquivo()
        senha = bx._senha_salva() if bx.configurado() else getpass.getpass('Senha do backup: ')
        m = bx.conferir_pacote(arquivo.read_bytes(), senha)
        print(f'OK: {arquivo.name} abre, confere com o manifesto e o banco passa no quick_check.')
        print(f'Versão {m["versao"]}, criado em {m["criado_em"]}; contém: {", ".join(sorted(m["arquivos"]))}.')
        return 0
    if comando == 'restaurar' and len(argv) == 3:
        m = bx.restaurar(argv[1], argv[2], getpass.getpass('Senha do backup: '))
        print(f'Pacote de {m["criado_em"]} extraído em {argv[2]}. Siga o RESTAURAR.txt.')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except bx.BackupExternoErro as exc:
        print(f'Erro: {exc}')
        sys.exit(1)
