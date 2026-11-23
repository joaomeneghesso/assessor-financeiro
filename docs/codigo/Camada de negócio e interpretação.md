---
tipo: grupo
tags: [grupo, camada-de-negocio-e-interpretacao]
---
# Camada de negócio e interpretação

Roteador de comandos por texto, interpretação de registros e orientação local (sem gravar sozinho).

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[services.py]] | 11767 | 15 |  |
| [[parser_financeiro.py]] | 745 | 3 |  |
| [[registro_conversa.py]] | 348 | 2 | Extrai apenas os dados informados em um registro, sem banco, rede ou IA. |
| [[assessor_orientacao.py]] | 328 | 3 | Orientação local explicável |
| [[assessor_ia_local.py]] | 205 | 1 | Interpretação financeira local via Ollama. |
| [[consulta_cache.py]] | 144 | 7 | Cache efêmero compartilhado por uma única consulta/renderização. |
| [[roteamento_seguro.py]] | 11 | 2 | Comandos operacionais nunca são interpretados como novos gastos. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
