---
tipo: state
arquivo: services.py
linha: 8057
---
# _EXCLUSAO_CONFIRMADA

ContextVar bool: marca execução de exclusão já confirmada; nunca vem do texto digitado.

`state:_EXCLUSAO_CONFIRMADA`

## Vem de
- (grava_estado) [[fn_services.executar_exclusao_confirmada-c9366|services.executar_exclusao_confirmada]] set(True)/reset
- (le_estado) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] 8475
