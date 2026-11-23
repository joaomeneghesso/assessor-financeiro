---
tipo: text_trigger
arquivo: services.py
linha: 8446
---
# prévia de alteração digitada (mudar|corrigir|meta|fixos|entradas...)

Edição digitada não grava direto: gera prévia e pendência (PENDENCIAS_ALTERACAO). Pula se a execução já veio confirmada (ContextVar) ou texto começa com '__'.

`text:prévia de alteração digitada (mudar|corrigir|meta|fixos|entradas...)`

## Vai para
- (chama) [[fn_services.previa_alteracao-4f7fc|services.previa_alteracao]] 
- (chama) [[fn_services._preparar_alteracao_sessao-a37a4|services._preparar_alteracao_sessao]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8446
