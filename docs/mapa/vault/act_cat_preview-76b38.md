---
tipo: action
arquivo: telegram_experiencia.py
linha: 3430
---
# cat_preview

Prévia da troca de categoria (pede confirmação).

`act:cat_preview`

## Vai para
- (chama) [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]] 
- (chama) [[fn_telegram_registros.validar_campo_textual-c5180|telegram_registros.validar_campo_textual]] 
- (chama) [[fn_ux._categoria_menu-09adc|ux._categoria_menu]] 
- (chama) [[fn_conciliacao.listar_vinculos-ca122|listar_vinculos]] 
- (navega) [[act_cat_confirm-ff9ed|cat_confirm]] botão da resposta
- (navega) [[act_transaction-fab7d|transaction]] botão da resposta
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux._categoria_menu-09adc|ux._categoria_menu]] 
