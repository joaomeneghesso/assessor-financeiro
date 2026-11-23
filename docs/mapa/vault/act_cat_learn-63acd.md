---
tipo: action
arquivo: telegram_experiencia.py
linha: 3444
---
# cat_learn

Guarda a troca de categoria como regra aprendida.

`act:cat_learn`

## Vai para
- (chama) [[fn_db.buscar_transacao_por_id-d0e04|buscar_transacao_por_id]] 
- (chama) [[fn_categorias_pessoais.salvar_regra-8272c|categorias_pessoais.salvar_regra]] 
- (navega) [[act_transaction-fab7d|transaction]] botão da resposta
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (navega) [[act_cat_confirm-ff9ed|cat_confirm]] botão da resposta
