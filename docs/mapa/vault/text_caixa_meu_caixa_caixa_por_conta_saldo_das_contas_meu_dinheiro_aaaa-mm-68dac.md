---
tipo: text_trigger
arquivo: services.py
linha: 8660
---
# caixa|meu caixa|caixa por conta|saldo das contas|meu dinheiro [aaaa-mm]

Caixa por conta do mês (parsear_comando_caixa_por_conta). Vem antes do 'saldo <conta>' (8736).

`text:caixa|meu caixa|caixa por conta|saldo das contas|meu dinheiro [aaaa-mm]`

## Vai para
- (chama) [[fn_services.parsear_comando_caixa_por_conta-acb12|services.parsear_comando_caixa_por_conta]] 
- (chama) [[fn_services.gerar_caixa_por_conta_mes-45535|services.gerar_caixa_por_conta_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8660
