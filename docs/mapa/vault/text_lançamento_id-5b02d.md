---
tipo: text_trigger
arquivo: app.py
linha: 8805
---
# lançamento <id>

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:lançamento <id>`

## Vai para
- (chama) [[fn_services.buscar_transacao_detalhada_formatado-fa62f|services.buscar_transacao_detalhada_formatado]] 

## Vem de
- (navega) [[btn_1..5_id_visual-767ad|1..5 (id visual)]] envia 'lançamento <id>'
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8805
