---
tipo: text_trigger
arquivo: services.py
linha: 9148
---
# alterar categoria <fixo|compromisso|parcela> <id> para <cat>

Troca a categoria do compromisso (passa por prévia de alteração).

`text:alterar categoria <fixo|compromisso|parcela> <id> para <cat>`

## Vai para
- (chama) [[fn_compromissos.alterar_compromisso_categoria-42019|compromissos.alterar_compromisso_categoria]] 

## Vem de
- (alias_de) [[alias_trocar_categoria_fixo_id_por_x-48062|... categoria ... -> alterar categoria <tipo> <id> para <x>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9148
