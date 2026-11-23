---
tipo: text_trigger
arquivo: services.py
linha: 9090
---
# <categoria> <aaaa-mm>

Regex solta de letras + mês, exceto termos bloqueados (agenda, parcelas, contas...).

`text:<categoria> <aaaa-mm>`

## Vai para
- (chama) [[fn_services.detalhar_categoria_mes-a5bb0|services.detalhar_categoria_mes]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9090
