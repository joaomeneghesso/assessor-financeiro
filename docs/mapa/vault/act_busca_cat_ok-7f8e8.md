---
tipo: action
arquivo: telegram_experiencia.py
linha: 2969
---
# busca_cat_ok

Grava a troca em lote (db.atualizar_categoria_em_lote) só se nada mudou desde a prévia; audita item a item.

`act:busca_cat_ok`

## Vai para
- (chama) [[fn_busca_lancamentos.dispatch-39750|busca_lancamentos.dispatch]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 
- (chama) [[fn_db.atualizar_categoria_em_lote-efa49|db.atualizar_categoria_em_lote]] 
- (navega) [[act_busca_regra-c2b09|busca_regra]] 🧠 Sim, aprender

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_busca_cat_ver-2ee97|busca_cat_ver]] ✅ Confirmar alteração
