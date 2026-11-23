---
tipo: text_trigger
arquivo: services.py
linha: 8748
---
# despesas|gastos|saídas <conta> <mês> [pagina n]

parsear_comando_movimentacoes_conta_mes; mês pode ser AAAA-MM, M/AAAA ou 'nome ano' (normalizar_ano_mes_flexivel).

`text:despesas|gastos|saídas <conta> <mês> [pagina n]`

## Vai para
- (chama) [[fn_services.parsear_comando_movimentacoes_conta_mes-306d0|services.parsear_comando_movimentacoes_conta_mes]] 
- (chama) [[fn_services.movimentacoes_conta_mes_formatado-1b67f|services.movimentacoes_conta_mes_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8748
