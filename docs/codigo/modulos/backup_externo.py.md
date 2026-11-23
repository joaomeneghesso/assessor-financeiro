---
tipo: modulo
grupo: Dados, backup e segurança
linhas: 304
tags: [modulo, dados-backup-e-seguranca]
---
# backup_externo.py

> Cópia diária criptografada do assessor FORA do computador (OneDrive por padrão).

**Grupo:** [[Dados, backup e segurança]] · **Linhas:** 304 · **Funções:** 20 · **Classes:** 1

## Usa

- [[config.py]]
- [[estado_runtime.py]]
- [[relogio.py]]
- [[version.py]] *(importação tardia, dentro de função)*

## Usado por

- [[backup_externo_cli.py]] — `BackupExternoErro`, `_senha_salva`, `conferir_pacote`, `configurado`, `destino`, `gerar`, `linha_status`, `restaurar` +1
- [[services.py]] — `gerar_se_configurado`, `linha_status`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `linha_status` | 274 | 2 | 1 | Uma linha para a resposta do comando backup (sem dados sensíveis). |
| `BackupExternoErro` | 80 | 1 | 2 |  |
| `conferir_pacote` | 173 | 1 | 1 | Decifra, confere os SHA-256 do manifesto e roda quick_check no banco (sem gravar nada fora do temp). |
| `configurado` | 93 | 1 | 1 |  |
| `gerar` | 220 | 1 | 1 | Grava o pacote cifrado no destino, relê e confere; devolve o caminho. |
| `gerar_se_configurado` | 261 | 1 | 1 | Gancho do backup diário: nunca levanta erro; devolve uma linha de status (ou '' se não configurado). |
| `restaurar` | 286 | 1 | 1 | Extrai o pacote numa pasta NOVA (nunca sobrescreve) e escreve RESTAURAR.txt. |
| `salvar_senha` | 97 | 1 | 1 |  |
| `_senha_salva` | 105 | 1 | 0 |  |
| `destino` | 84 | 1 | 0 |  |
| `_enviar_rclone` | 204 | 0 | 1 | Envia os arquivos (já cifrados) ao remoto rclone e apaga lá os pacotes com mais de 45 dias. |
| `_git_bundle` | 137 | 0 | 1 | Repositório inteiro num arquivo; None se o git não estiver disponível (o resto segue). |

## Tudo que define

- classe `BackupExternoErro` (L80, 2 linhas)
- `destino` (L84, 3 linhas)
- `_store` (L89, 2 linhas)
- `configurado` (L93, 2 linhas)
- `salvar_senha` (L97, 6 linhas)
- `_senha_salva` (L105, 5 linhas)
- `_chave` (L113, 2 linhas)
- `cifrar` (L117, 4 linhas)
- `decifrar` (L123, 11 linhas)
- `_git_bundle` (L137, 12 linhas) — Repositório inteiro num arquivo; None se o git não estiver disponível (o resto segue).
- `montar_pacote` (L151, 20 linhas) — Zip em memória com banco, código, .env, manifesto e leia-me.
- `conferir_pacote` (L173, 15 linhas) — Decifra, confere os SHA-256 do manifesto e roda quick_check no banco (sem gravar nada fora do temp).
- `_rotacionar` (L190, 7 linhas)
- `remoto_rclone` (L199, 3 linhas) — Servidor sem OneDrive instalado: destino rclone (ex.: 'onedrive:Backups/Assessor'); '' = não enviar.
- `_enviar_rclone` (L204, 14 linhas) — Envia os arquivos (já cifrados) ao remoto rclone e apaga lá os pacotes com mais de 45 dias.
- `gerar` (L220, 22 linhas) — Grava o pacote cifrado no destino, relê e confere; devolve o caminho.
- `_gravar_status` (L244, 8 linhas)
- `status` (L254, 5 linhas)
- `gerar_se_configurado` (L261, 11 linhas) — Gancho do backup diário: nunca levanta erro; devolve uma linha de status (ou '' se não configurado).
- `linha_status` (L274, 10 linhas) — Uma linha para a resposta do comando backup (sem dados sensíveis).
- `restaurar` (L286, 19 linhas) — Extrai o pacote numa pasta NOVA (nunca sobrescreve) e escreve RESTAURAR.txt.

## Testes que usam (2)

- `tests/test_backup_externo.py`
- `tests/test_portabilidade_linux.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
