---
tipo: modulo
grupo: Ferramentas e validação
linhas: 147
tags: [modulo, ferramentas-e-validacao]
aliases: [tools/medir_desempenho.py]
---
# tools/medir_desempenho.py

> Mede o tempo das operações do dia a dia num banco de TESTE do tamanho do real.

**Grupo:** [[Ferramentas e validação]] · **Linhas:** 147 · **Funções:** 5 · **Classes:** 0

## Usa

- [[database.py]]
- [[services.py]]
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*
- [[telegram_midia.py]] *(importação tardia, dentro de função)*
- [[transcricao_audio.py]] *(importação tardia, dentro de função)*

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Tudo que define

- `montar_banco` (L35, 32 linhas)
- `cronometrar` (L69, 17 linhas)
- `audio_teste` (L88, 9 linhas) — 5 s de tom com variação (passa no filtro de silêncio; custo de transcrição ~ de uma fala curta).
- `foto_teste` (L99, 9 linhas)
- `main` (L110, 34 linhas)

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
