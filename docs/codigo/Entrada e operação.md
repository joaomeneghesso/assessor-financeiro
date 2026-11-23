---
tipo: grupo
tags: [grupo, entrada-e-operacao]
---
# Entrada e operação

Onde o bot começa: inicialização, configuração única, relógio, trava de instância e logs.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[app.py]] | 5537 | 0 |  |
| [[assessor.py]] | 399 | 1 |  |
| [[operacao_bot.py]] | 141 | 1 | Operação do bot: trava de instância única, tratador global de erro e tarefas monitoradas. |
| [[config.py]] | 137 | 15 | Configuração única do assessor: caminhos do projeto e leitura do ambiente. |
| [[registro_logs.py]] | 69 | 1 | Log em arquivo para avisos e erros, sem mudar o que aparece no console. |
| [[relogio.py]] | 61 | 11 | Relógio único do assessor (Onda 3, etapa 1): "agora" e "hoje" no fuso do titular. |
| [[telegram_execucao.py]] | 19 | 4 | Ponte assíncrona para o motor financeiro síncrono. |
| [[version.py]] | 2 | 3 | Versão do assessor (bot Telegram). |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
