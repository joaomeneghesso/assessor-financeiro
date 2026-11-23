---
tipo: text_trigger
arquivo: services.py
linha: 9370
---
# quanto gastei com <categoria>

Mês = hoje.

`text:quanto gastei com <categoria>`

## Vai para
- (chama) [[fn_services.consultar_categoria-40bf2|services.consultar_categoria]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9370
