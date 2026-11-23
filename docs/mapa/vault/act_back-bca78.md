---
tipo: action
arquivo: telegram_experiencia.py
linha: 2894
---
# back

Volta: s.stage=None; s.draft=None; restaura (view,month,page) do trail.

`act:back`

## Vai para
- (le_estado) [[state_Session.trail-b6f1c|Session.trail]] pop
- (grava_estado) [[state_Session.month-7f614|Session.month]] restaura mês do trail (l.2412)
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] descarta
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] descarta
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (grava_estado) [[state_Session.view-a9ea1|Session.view]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (chama) [[btn_Voltar-c2fc6|↩ Voltar]] 
- (navega) [[act_invoice_commit-7ad93|invoice_commit]] botão da resposta
