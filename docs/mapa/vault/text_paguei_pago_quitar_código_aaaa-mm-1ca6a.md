---
tipo: text_trigger
arquivo: services.py
linha: 8630
---
# paguei|pago|quitar <código> [aaaa-mm]

Marca item do checklist (também desmarcar/pendente).

`text:paguei|pago|quitar <código> [aaaa-mm]`

## Vai para
- (chama) [[fn_services.parsear_comando_marcar_checklist-260c9|services.parsear_comando_marcar_checklist]] 
- (chama) [[fn_services.marcar_item_checklist_formatado-4e259|services.marcar_item_checklist_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8630
