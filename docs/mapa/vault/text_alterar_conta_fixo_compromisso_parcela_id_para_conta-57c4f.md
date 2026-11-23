---
tipo: text_trigger
arquivo: services.py
linha: 9130
---
# alterar conta <fixo|compromisso|parcela> <id> para <conta>

Troca a conta do compromisso (passa por prévia de alteração).

`text:alterar conta <fixo|compromisso|parcela> <id> para <conta>`

## Vai para
- (chama) [[fn_compromissos.alterar_compromisso_conta-64748|compromissos.alterar_compromisso_conta]] 

## Vem de
- (alias_de) [[alias_trocar_conta_fixo_id_por_x-6c7a9|alterar|mudar|trocar|editar|ajustar|atualizar conta ... -> alterar conta <tipo> <id> para <x>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9130
