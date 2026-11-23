# Mapa de rotas do assessor

Grafo de tudo que tem ação e para onde vai (comandos, textos, botões, callbacks, telas, ações, serviços, estado). Mostra só estrutura do código, sem dados financeiros.

- `mapa.html`: abra no navegador. Busca, filtro por tipo (legenda), clique no nó para ver "vai para" / "vem de". Arraste para mover, role para zoom.
- `vault/`: uma nota por nó com `[[links]]`. Abra a pasta no Obsidian e use a visão de grafo (é o estilo da imagem de referência).
- `dados/*.json`: fonte (nós e arestas), regenerada a partir do código em 12/11/2026 (Onda 2, depois das Fases 1-2 e da Onda 1): `app_legado.json` (app.py), `ux.json` (telegram_experiencia.py), `servicos.json` (services.py, mídia). Em 13/11/2026 saíram os 20 nós do painel web removido. 1.434 nós e 3.298 ligações (antes: 1.284 / 2.593), 0 pontas soltas.
- Regenerar HTML e vault: `.\.venv\Scripts\python.exe tools\gerar_mapa.py`
- Conferir defasagem: `.\.venv\Scripts\python.exe tools\verificar_mapa.py` (ou `--json`). Compara, por análise estática, o mapa com o código: ações `kind=='...'` de `Experience.act`, telas `screen_*`, `CommandHandler` de app.py e funções chamadas pelo roteador `_processar_mensagem_core`; e, ao contrário, nós `act:`, `screen:`, `cmd:` e `fn:services|app|ux.*` que não existem mais. Defasagem em 12/11/2026: 0 (antes da regeneração: 56).
- Teste: `tests/test_mapa_rotas_atualizado.py` falha quando a defasagem passa de 10 itens (o gate copia `docs/mapa/dados` e `tools/verificar_mapa.py` para rodá-lo).

## Convenção de ids
`cmd:/menu`, `text:<gatilho>`, `alias:<sinonimo>`, `btn:<rotulo>`, `cb:<prefixo>`, `screen:<nome>`, `act:<acao>`, `fn:services.<f>` / `fn:ux.<m>`, `state:<nome>`, `route:GET /api/...`, `job:`, `gate:`.

## Como manter
Os JSON não se atualizam sozinhos. Ao criar tela, botão, comando ou estado novo, peça ao Claude para atualizar o JSON do arquivo correspondente, rodar `tools/verificar_mapa.py` e o gerador. O verificador só enxerga ações, telas, comandos e destinos do roteador; botões, callbacks, gatilhos de texto e estados continuam sendo mantidos à mão. Pontos de atenção para novas telas: `state:Session.month` (113 ligações) e filtros persistentes da sessão.

## Achados do mapa (28/10/2026)
- Bug do mês: `/menu` e botão Início não voltavam ao mês vigente após "quanto vou pagar em novembro". Corrigido (`tests/test_menu_mes_nao_gruda.py`).
- Outras telas gravam `Session.month` como efeito colateral (registro com data antiga, pagamento de fatura, detalhe de conta) e filtros do A pagar/histórico só limpam em botões próprios.
- Rota diferente para o mesmo comando digitado vs. clicado: `ux.dispatch_text` roda antes das pendências legadas.
- 10 gatilhos de `services.py` nunca são alcançados porque uma regra anterior captura o texto (caixa, compromissos, revisar, resumo do mês, saldo do mês, últimas...).
- Rotinas `rotina_lembrete_pagamentos_diario`, `rotina_alerta_diario`, `rotina_resumo_domingo` definidas e nunca agendadas.
- Teclado inferior novo (Início, Registrar, A pagar...) fora de `ATALHOS_MENU`.
- PIN não reexecuta a ação bloqueada depois do desbloqueio.

## Regeneração de 12/11/2026
- Removidos 7 gatilhos mortos do roteador e 9 telas que não existiam como tela (viraram arestas para o método real, ex. `fn:ux.prompt`).
- Novos: 21 ações (contas, compra, categoria, data, conflito, duplicata, ajuste de saldo), telas `accounts_manage` e `can_buy`, pendência de alteração (`state:PENDENCIAS_ALTERACAO`, confirmar/cancelar alteração), ação pendente de PIN reexecutada após o desbloqueio, tratador de erro, limitador persistente.
- Limitações: muitas descrições novas são genéricas; arestas de `act:view`/`act:month` para telas de nome dinâmico seguem as antigas; os rótulos de alguns botões legados mudaram no código e mantêm o id antigo.
- `rotina_lembrete_pagamentos_diario`, `rotina_alerta_diario` e `rotina_resumo_domingo` continuam no app.py sem agendamento: são código morto, os alertas agendados hoje vêm de `telegram_alertas.rotina` (mais o backup diário).
