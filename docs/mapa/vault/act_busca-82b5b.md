---
tipo: action
arquivo: telegram_experiencia.py
linha: 2969
---
# busca

Resultado da busca em todos os meses (ou no período), paginado; total de saídas/entradas e categorias.

`act:busca`

## Vai para
- (chama) [[fn_busca_lancamentos.dispatch-39750|busca_lancamentos.dispatch]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 
- (navega) [[act_busca_cat-d2a2f|busca_cat]] 🏷 Mudar categoria de todos
- (navega) [[screen_transaction-cd364|transaction]] N. lançamento
- (navega) [[screen_history-d40e7|history]] 📒 Histórico do mês

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
