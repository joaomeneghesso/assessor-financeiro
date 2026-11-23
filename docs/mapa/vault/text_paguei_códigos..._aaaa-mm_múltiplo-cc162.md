---
tipo: text_trigger
arquivo: services.py
linha: 8622
---
# paguei <códigos...> [aaaa-mm] (múltiplo)

Marca vários itens como pagos/pendentes.

`text:paguei <códigos...> [aaaa-mm] (múltiplo)`

## Vai para
- (chama) [[fn_services.parsear_comando_marcar_checklist_multiplo-7597a|services.parsear_comando_marcar_checklist_multiplo]] 
- (chama) [[fn_services.marcar_itens_checklist_formatado-3fa94|services.marcar_itens_checklist_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8622
