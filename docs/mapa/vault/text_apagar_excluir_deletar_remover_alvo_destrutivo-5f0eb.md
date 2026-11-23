---
tipo: text_trigger
arquivo: services.py
linha: 8535
---
# apagar|excluir|deletar|remover <alvo> (destrutivo)

Qualquer exclusão gera prévia e pendência; o delete real só roda com a ContextVar de confirmação.

`text:apagar|excluir|deletar|remover <alvo> (destrutivo)`

## Vai para
- (chama) [[fn_services.comando_destrutivo_exclusao-4cbe5|services.comando_destrutivo_exclusao]] 
- (chama) [[fn_services._preparar_exclusao_sessao-b1879|services._preparar_exclusao_sessao]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8535
