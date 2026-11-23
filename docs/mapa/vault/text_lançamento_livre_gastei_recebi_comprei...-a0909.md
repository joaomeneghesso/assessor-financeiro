---
tipo: text_trigger
arquivo: services.py
linha: 9452
---
# lançamento livre (gastei|recebi|comprei...)

Último elo: parse_mensagem -> registra DIRETO (sem confirmação) via registrar_transacao_unica/registrar_compra_parcelada. No Telegram UX2 handle_text intercepta gastei/recebi/comprei antes e monta rascunho com confirmação.

`text:lançamento livre (gastei|recebi|comprei...)`

## Vai para
- (chama) [[fn_parser_financeiro.parse_mensagem-7c39b|parser_financeiro.parse_mensagem]] 
- (chama) [[fn_services.aplicar_correcao_categoria_transacao-436fd|services.aplicar_correcao_categoria_transacao]] 
- (chama) [[fn_services.registrar_compra_parcelada-00023|services.registrar_compra_parcelada]] 
- (chama) [[fn_services.registrar_transacao_unica-f096c|services.registrar_transacao_unica]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9452
