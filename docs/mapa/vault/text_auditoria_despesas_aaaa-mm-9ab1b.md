---
tipo: text_trigger
arquivo: services.py
linha: 8656
---
# auditoria despesas [aaaa-mm]

Auditoria de despesas do mês.

`text:auditoria despesas [aaaa-mm]`

## Vai para
- (chama) [[fn_services.parsear_comando_auditoria_despesas-e7568|services.parsear_comando_auditoria_despesas]] 
- (chama) [[fn_services.gerar_auditoria_despesas_mes-8c3fa|services.gerar_auditoria_despesas_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8656
