---
tipo: text_trigger
arquivo: services.py
linha: 8460
---
# alterar término fixo <id> para sem término

Remove data_fim do fixo, com auditoria.

`text:alterar término fixo <id> para sem término`

## Vai para
- (chama) [[fn_services.remover_termino_fixo-b7b64|services.remover_termino_fixo]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8460
