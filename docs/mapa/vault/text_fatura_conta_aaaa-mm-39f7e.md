---
tipo: text_trigger
arquivo: services.py
linha: 8500
---
# fatura <conta> [aaaa-mm]

parsear_comando_movimento_fatura -> 'consultar'. Mês padrão = hoje.

`text:fatura <conta> [aaaa-mm]`

## Vai para
- (chama) [[fn_services.formatar_resumo_fatura-bf1a8|services.formatar_resumo_fatura]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8500
