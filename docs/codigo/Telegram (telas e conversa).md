---
tipo: grupo
tags: [grupo, telegram-telas-e-conversa]
---
# Telegram (telas e conversa)

Tudo que o titular vê e toca: telas, botões, registros revisáveis, alertas, consultas e mídia.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[telegram_experiencia.py]] | 5543 | 8 | Interface Telegram 2.0: apresentação curta, navegação e registros revisáveis. |
| [[telegram_registros.py]] | 494 | 1 | Gravação confirmada, atômica e auditada usando o schema já existente. |
| [[telegram_design.py]] | 415 | 5 | Apresentação Telegram sem I/O, IA ou regras financeiras. |
| [[telegram_midia.py]] | 311 | 3 | Recepção local de mídia: reconhecimento -> revisão -> formulário existente. |
| [[fixos_interface.py]] | 298 | 1 | Telas e formulário de edição de fixos |
| [[busca_lancamentos.py]] | 251 | 1 | Busca de lançamentos em todos os meses e troca de categoria em lote (Telegram). |
| [[sugestoes_comando.py]] | 242 | 1 | Sugestões de comando quando o texto digitado não é reconhecido. |
| [[telegram_visuais.py]] | 237 | 1 | RC3.0.38 — painéis de leitura; não consultam nem alteram dados financeiros. |
| [[consultas_rapidas.py]] | 228 | 2 | Consultas comuns sem rede; apenas intenção, nunca cálculo ou gravação. |
| [[telegram_recursos.py]] | 222 | 4 | Recursos de leitura e aprendizado; nenhum pagamento é confirmado aqui. |
| [[telegram_alertas.py]] | 203 | 2 | Agenda discreta com preferências persistentes e deduplicação por janela de envio. |
| [[consultas_pagar.py]] | 193 | 1 | 'Quanto vou pagar de X': faturas dos cartões ou contas de uma categoria (pedido de 19/11/2026). |
| [[sugestoes_lancamento.py]] | 167 | 1 | Sugestões de lançamento derivadas do histórico (somente leitura). |
| [[dashboard_metricas.py]] | 148 | 1 | Indicadores descritivos do dashboard; leitura, sem alterar o motor financeiro. |
| [[telegram_streaming.py]] | 96 | 2 | Progresso efêmero para tarefas locais demoradas, sem estado financeiro. |
| [[telegram_aprendizado.py]] | 88 | 1 | Conteúdo didático de leitura: sem banco, pagamentos ou progresso persistente. |
| [[efeito_baixa.py]] | 68 | 1 | Efeito de um registro no dinheiro: saldo da conta e sobra prevista, antes → depois. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
