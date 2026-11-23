---
tipo: text_trigger
arquivo: services.py
linha: 8471
---
# competência AAAA-MM inválida no texto

Valida toda competência AAAA-MM do texto antes de rotear; inválida responde 'Mês inválido'.

`text:competência AAAA-MM inválida no texto`

## Vai para
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8471
