---
tipo: action
arquivo: telegram_experiencia.py
linha: 3421
---
# dup_view

Mostra o lançamento já existente apontado como possível duplicata.

`act:dup_view`

## Vai para
- (chama) [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 
- (navega) [[act_dup_back-8d8c0|dup_back]] botão da resposta
- (navega) [[act_cancel-c6497|cancel]] botão da resposta

## Vem de
- (chama) [[fn_ux.preview-35809|preview]] 
