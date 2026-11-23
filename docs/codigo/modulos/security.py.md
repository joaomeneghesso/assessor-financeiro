---
tipo: modulo
grupo: Dados, backup e segurança
linhas: 182
tags: [modulo, dados-backup-e-seguranca]
---
# security.py

**Grupo:** [[Dados, backup e segurança]] · **Linhas:** 182 · **Funções:** 7 · **Classes:** 2

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `AuthAttemptLimiter`, `chat_is_allowed`, `hash_secret`, `is_hashed_secret`, `verify_pin_pairs`, `verify_secret`
- [[limitador_persistente.py]] — `AttemptState`, `AuthAttemptLimiter`
- [[preparar_seguranca_v40.py]] — `hash_secret`, `is_hashed_secret`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `AuthAttemptLimiter` | 92 | 2 | 6 | Thread-safe in-memory limiter for PIN and recovery attempts. |
| `hash_secret` | 17 | 2 | 5 | Return a versioned PBKDF2-HMAC-SHA256 representation of a secret. |
| `is_hashed_secret` | 34 | 2 | 0 |  |
| `chat_is_allowed` | 166 | 1 | 1 | Fail closed: when an allowed chat is supplied it must match exactly. |
| `AttemptState` | 84 | 1 | 0 |  |
| `verify_pin_pairs` | 69 | 1 | 0 | Validate the randomized pair keyboard without storing the PIN in plaintext. |
| `verify_secret` | 43 | 1 | 0 | Verify PBKDF2 secrets and keep a narrow compatibility path for legacy plaintext. |

## Tudo que define

- `hash_secret` (L17, 15 linhas) — Return a versioned PBKDF2-HMAC-SHA256 representation of a secret.
- `is_hashed_secret` (L34, 2 linhas)
- `_b64decode` (L38, 3 linhas)
- `verify_secret` (L43, 24 linhas) — Verify PBKDF2 secrets and keep a narrow compatibility path for legacy plaintext.
- `verify_pin_pairs` (L69, 12 linhas) — Validate the randomized pair keyboard without storing the PIN in plaintext.
- classe `AttemptState` (L84, 6 linhas)
- classe `AuthAttemptLimiter` (L92, 65 linhas) — Thread-safe in-memory limiter for PIN and recovery attempts.
- `chat_is_private` (L159, 5 linhas)
- `chat_is_allowed` (L166, 17 linhas) — Fail closed: when an allowed chat is supplied it must match exactly.

## Testes que usam (7)

- `tests/test_app_pin_pendencias_bloco_p1.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_gravacao_confirmacao_legado.py`
- `tests/test_inovacoes_410.py`
- `tests/test_phase2_security.py`
- `tests/test_pin_gate_normalizacao.py`
- `tests/test_pin_teclado_assincrono.py`

## No mapa de rotas

- **Funções no mapa (1):** [[fn_security.verify_secret-a43a1|security.verify_secret]]

## Documentos que citam

- [[reavaliacao/03_seguranca_privacidade]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
