---
tipo: modulo
grupo: Ferramentas e validação
linhas: 216
tags: [modulo, ferramentas-e-validacao]
aliases: [validacao/relogio_falso.py]
---
# validacao/relogio_falso.py

> Relógio falso por deslocamento, só para testes (nunca importado pela produção).

**Grupo:** [[Ferramentas e validação]] · **Linhas:** 216 · **Funções:** 12 · **Classes:** 6

## Usa

- (nenhum módulo do projeto)

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Tudo que define

- `_delta` (L42, 2 linhas)
- `_agora` (L46, 2 linhas)
- classe `_MetaData` (L50, 6 linhas)
- classe `_MetaDataHora` (L58, 6 linhas)
- classe `DataFalsa` (L66, 6 linhas)
- classe `DataHoraFalsa` (L74, 14 linhas)
- classe `_ChamavelComTempo` (L90, 9 linhas) — Objeto chamável (não função): não vira método ao ser atribuído a atributo
- `_strftime` (L101, 2 linhas)
- `_modulo_do_projeto` (L116, 11 linhas)
- `_trocar` (L129, 3 linhas)
- `_instalar` (L134, 16 linhas)
- `_desinstalar` (L152, 13 linhas)
- `interpretar` (L167, 5 linhas) — 'AAAA-MM-DD' (+ 'HH:MM') -> datetime ingênuo local.
- `ativar` (L174, 8 linhas) — Empilha um relógio que começa em ``data hora`` (hora local do processo).
- `desativar` (L184, 6 linhas)
- `ativo` (L192, 2 linhas)
- classe `fixar` (L196, 13 linhas) — Context manager: ``with fixar('2026-11-09'): ...`` (ou ``date``/``datetime``).
- `ativar_pelo_ambiente` (L211, 6 linhas) — Usado pelo HARNESS do gate: GATE_DATA_FALSA=AAAA-MM-DD, GATE_HORA_FALSA=HH:MM.

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
