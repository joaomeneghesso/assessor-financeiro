---
tipo: text_trigger
arquivo: services.py
linha: 8504
---
# apagar movimento #f<id>

-> 'apagar': prévia; executa só com _EXCLUSAO_CONFIRMADA.

`text:apagar movimento #f<id>`

## Vai para
- (chama) [[fn_services._preparar_exclusao_sessao-b1879|services._preparar_exclusao_sessao]] 
- (chama) [[fn_services.apagar_movimento_fatura_formatado-e829c|services.apagar_movimento_fatura_formatado]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8504
