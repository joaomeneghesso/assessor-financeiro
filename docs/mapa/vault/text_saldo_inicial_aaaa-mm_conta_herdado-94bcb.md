---
tipo: text_trigger
arquivo: services.py
linha: 8672
---
# saldo inicial [aaaa-mm] <conta> herdado

Define/restaura saldo inicial por conta (grava).

`text:saldo inicial [aaaa-mm] <conta> herdado`

## Vai para
- (chama) [[fn_services.parsear_comando_saldo_inicial-729f6|services.parsear_comando_saldo_inicial]] 
- (chama) [[fn_services.definir_saldo_inicial_formatado-cbce1|services.definir_saldo_inicial_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8672
