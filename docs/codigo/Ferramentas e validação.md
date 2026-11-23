---
tipo: grupo
tags: [grupo, ferramentas-e-validacao]
---
# Ferramentas e validação

Scripts de apoio: gate oficial, mapa de rotas, medições, MCP somente leitura e este gerador.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[tools__gerar_vault_codigo.py|tools/gerar_vault_codigo.py]] | 358 | 0 | Gera as notas de código do vault Obsidian (docs/codigo/) e a página inicial (docs/00 Início.md). |
| [[validacao__validar_versao_oficial.py|validacao/validar_versao_oficial.py]] | 221 | 0 | Gate de release: código copiado, banco temporário e rede externa bloqueada. |
| [[validacao__relogio_falso.py|validacao/relogio_falso.py]] | 216 | 0 | Relógio falso por deslocamento, só para testes (nunca importado pela produção). |
| [[tools__verificar_mapa.py|tools/verificar_mapa.py]] | 191 | 0 | Compara o mapa de rotas (docs/mapa/dados/*.json) com o código, por análise estática simples. |
| [[tools__gerar_mapa.py|tools/gerar_mapa.py]] | 170 | 0 | Gera o mapa de rotas do assessor a partir de docs/mapa/dados/*.json. |
| [[tools__medir_desempenho.py|tools/medir_desempenho.py]] | 147 | 0 | Mede o tempo das operações do dia a dia num banco de TESTE do tamanho do real. |
| [[tools__medir_rotina.py|tools/medir_rotina.py]] | 114 | 0 | Rotina do dia a dia, cronometrada, no motor real do bot (banco de TESTE do tamanho do real). |
| [[tools__mcp_assessor_db.py|tools/mcp_assessor_db.py]] | 108 | 0 | Servidor MCP (stdio, só biblioteca padrão) para inspecionar o banco do assessor. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
