---
tipo: modulo
grupo: Entrada e operação
linhas: 61
tags: [modulo, entrada-e-operacao]
---
# relogio.py

> Relógio único do assessor (Onda 3, etapa 1): "agora" e "hoje" no fuso do titular.

**Grupo:** [[Entrada e operação]] · **Linhas:** 61 · **Funções:** 5 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `agora`, `agora_com_fuso`, `hoje`
- [[backup_externo.py]] — `agora`
- [[compromissos.py]] — `hoje`
- [[conciliacao.py]] — `hoje`
- [[database.py]] — `agora`, `hoje`
- [[fatura_conferencia.py]] — `agora`
- [[fixos_edicao.py]] — `agora`
- [[saldos_edicao.py]] — `agora`
- [[services.py]] — `agora`, `hoje`
- [[telegram_experiencia.py]] — `hoje`
- [[telegram_registros.py]] — `agora`, `hoje`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `agora` | 34 | 8 | 1 | Data e hora atuais em UTC-3, ingênuas (sem ``tzinfo``), como o ``datetime.now()`` de antes. |
| `hoje` | 39 | 7 | 1 | Data de hoje em UTC-3. |
| `agora_com_fuso` | 29 | 1 | 1 | Instante atual com ``tzinfo`` UTC-3. |
| `mes_atual` | 59 | 0 | 1 | Mês corrente ``AAAA-MM`` em UTC-3. |

## Tudo que define

- `agora_com_fuso` (L29, 3 linhas) — Instante atual com ``tzinfo`` UTC-3.
- `agora` (L34, 3 linhas) — Data e hora atuais em UTC-3, ingênuas (sem ``tzinfo``), como o ``datetime.now()`` de antes.
- `hoje` (L39, 13 linhas) — Data de hoje em UTC-3.
- `_classe_real` (L54, 3 linhas)
- `mes_atual` (L59, 3 linhas) — Mês corrente ``AAAA-MM`` em UTC-3.

## Testes que usam (1)

- `tests/test_relogio_unico.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
