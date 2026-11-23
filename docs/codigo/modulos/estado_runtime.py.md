---
tipo: modulo
grupo: Dados, backup e segurança
linhas: 189
tags: [modulo, dados-backup-e-seguranca]
---
# estado_runtime.py

> Estado efêmero protegido para retomada do Telegram.

**Grupo:** [[Dados, backup e segurança]] · **Linhas:** 189 · **Funções:** 6 · **Classes:** 1

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `ProtectedJsonStore`
- [[backup_externo.py]] — `ProtectedJsonStore`
- [[telegram_experiencia.py]] — `ProtectedJsonStore`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `ProtectedJsonStore` | 138 | 3 | 6 | Leitura/escrita atômica de um pequeno documento JSON protegido. |
| `_local_protect` | 54 | 0 | 1 |  |
| `_local_unprotect` | 60 | 0 | 1 |  |

## Tudo que define

- `_chave_local` (L37, 15 linhas) — Chave de 32 bytes do servidor; criada uma vez, legível só pelo dono.
- `_local_protect` (L54, 4 linhas)
- `_local_unprotect` (L60, 6 linhas)
- `_blob` (L73, 3 linhas)
- `_dpapi_protect` (L78, 33 linhas)
- `_dpapi_unprotect` (L113, 23 linhas)
- classe `ProtectedJsonStore` (L138, 52 linhas) — Leitura/escrita atômica de um pequeno documento JSON protegido.

## Testes que usam (6)

- `tests/__init__.py`
- `tests/test_bloco_a_protecao_dados.py`
- `tests/test_confiabilidade_413.py`
- `tests/test_limitador_persistente.py`
- `tests/test_mutantes_rede_seguranca.py`
- `tests/test_portabilidade_linux.py`

## Documentos que citam

- [[reavaliacao/03_seguranca_privacidade]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
