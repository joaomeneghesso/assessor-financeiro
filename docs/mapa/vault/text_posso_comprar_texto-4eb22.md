---
tipo: text_trigger
arquivo: services.py
linha: 9202
---
# posso comprar <texto>

Análise de compra, sem gravar.

`text:posso comprar <texto>`

## Vai para
- (chama) [[fn_services.analisar_compra-ef5f7|services.analisar_compra]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9202
