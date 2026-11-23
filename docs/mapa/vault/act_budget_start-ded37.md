---
tipo: action
arquivo: telegram_experiencia.py
linha: 3160
---
# budget_start

Criar limite (stage=budget_category).

`act:budget_start`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] budget_category
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (chama) [[fn_ux._categorias_limite-7ed40|ux._categorias_limite]] 
- (navega) [[act_budget_cat-77d03|budget_cat]] botão da resposta
- (navega) [[act_cancel-c6497|cancel]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_budgets-b41b9|budgets]] Criar / ajustar limite
