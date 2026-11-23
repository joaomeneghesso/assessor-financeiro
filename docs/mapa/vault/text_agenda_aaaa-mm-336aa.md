---
tipo: text_trigger
arquivo: services.py
linha: 9178
---
# agenda <aaaa-mm>

Agenda de uma competência AAAA-MM (resumo de contas do mês).

`text:agenda <aaaa-mm>`

## Vai para
- (chama) [[fn_compromissos.resumo_contas_mes-7e95c|compromissos.resumo_contas_mes]] 
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9178
