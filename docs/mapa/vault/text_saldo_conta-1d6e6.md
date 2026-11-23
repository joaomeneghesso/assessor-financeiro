---
tipo: text_trigger
arquivo: services.py
linha: 8736
---
# saldo <conta>

Saldo da conta no mês atual; 'caixa de som 200' (valor e 3+ palavras) não é tratado como conta.

`text:saldo <conta>`

## Vai para
- (chama) [[fn_services.gerar_saldo_mes_ux-6c533|services.gerar_saldo_mes_ux]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8736
