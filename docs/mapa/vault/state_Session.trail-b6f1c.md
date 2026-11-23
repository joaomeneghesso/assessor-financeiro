---
tipo: state
arquivo: telegram_experiencia.py
linha: 384
---
# Session.trail

Pilha de (view,month,page) para o botão Voltar; empilhada em act(view/topic/transaction/detail_obligation/accounts_for/home_income) e restaurada em act(back)/cancel.

`state:Session.trail`

## Vem de
- (grava_estado) [[act_view-1d8b8|view]] empilha (view,month,page) se muda de tela
- (le_estado) [[act_back-bca78|back]] pop
- (grava_estado) [[act_home_income-c95f5|home_income]] 
- (grava_estado) [[act_accounts_for-fd5a1|accounts_for]] 
- (grava_estado) [[act_account_filter-0f866|account_filter]] pop
- (grava_estado) [[act_transaction-fab7d|transaction]] 
- (grava_estado) [[act_detail_obligation-b6e92|detail_obligation]] 
- (grava_estado) [[act_topic-518da|topic]] 
- (le_estado) [[fn_ux.render-b3471|Experience.render]] mostra ↩ Voltar
- (grava_estado) [[act_ask-dbbdf|ask]] 
- (le_estado) [[act_invoice_commit-7ad93|invoice_commit]] 
- (le_estado) [[act_cancel-c6497|cancel]] 
