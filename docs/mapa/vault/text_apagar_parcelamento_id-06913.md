---
tipo: text_trigger
arquivo: services.py
linha: 9213
---
# apagar parcelamento <id>

Apaga o parcelamento inteiro (prévia + confirmar).

`text:apagar parcelamento <id>`

## Vai para
- (chama) [[fn_services.apagar_parcelamento_unificado-84a14|services.apagar_parcelamento_unificado]] 

## Vem de
- (alias_de) [[alias_deletar_parcelamento_parcela_id-ec4e9|deletar/cancelar parcelamento|parcela <id> -> apagar parcelamento <id>]] 
- (alias_de) [[alias_cancelar_parcelamento_parcela_id-8b140|cancelar parcelamento|parcela <id>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9213
