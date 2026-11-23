---
tipo: handler
arquivo: app.py
linha: 2683
---
# app.montar_teclado_inline_para_resposta

Escolhe o teclado inline conforme comando executado e/ou prefixo do texto da resposta

`fn:app.montar_teclado_inline_para_resposta`

## Vai para
- (chama) [[fn_app.montar_teclado_confirmacoes_texto-4561c|app.montar_teclado_confirmacoes_texto]] prioridade 1
- (chama) [[fn_app.montar_teclado_acao_produtiva-85b6e|app.montar_teclado_acao_produtiva]] prioridade 2 (por prefixo do TEXTO da resposta)
- (le_estado) [[state_mes_base-b9f3b|mes_base]] obter_mes_base(comando, resposta)

## Vem de
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] 
