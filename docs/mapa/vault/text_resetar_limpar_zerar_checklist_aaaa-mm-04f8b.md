---
tipo: text_trigger
arquivo: services.py
linha: 8612
---
# resetar|limpar|zerar checklist [aaaa-mm]

Zera marcações do checklist do mês.

`text:resetar|limpar|zerar checklist [aaaa-mm]`

## Vai para
- (chama) [[fn_services.parsear_comando_resetar_checklist-7e054|services.parsear_comando_resetar_checklist]] 
- (chama) [[fn_services.resetar_checklist_formatado-ae936|services.resetar_checklist_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8612
