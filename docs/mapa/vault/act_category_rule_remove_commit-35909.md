---
tipo: action
arquivo: telegram_experiencia.py
linha: 2962
---
# category_rule_remove_commit

REMOVE regra (categorias_pessoais.remover_regra + auditoria).

`act:category_rule_remove_commit`

## Vai para
- (chama) [[fn_categorias_pessoais.remover_regra-1eb50|remover_regra]] 
- (chama) [[fn_db.registrar_auditoria-1ae3c|registrar_auditoria]] 
- (grava_estado) [[state_Session.settings_draft-703dd|Session.settings_draft]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[act_category_rule_remove-7bab7|category_rule_remove]] botão da resposta
