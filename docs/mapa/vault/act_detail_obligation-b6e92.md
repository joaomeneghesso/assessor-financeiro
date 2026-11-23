---
tipo: action
arquivo: telegram_experiencia.py
linha: 2892
---
# detail_obligation

Abre detalhe de obrigação (code, mês de origem).

`act:detail_obligation`

## Vai para
- (chama) [[fn_ux.pause_for_guidance-482b6|pause_for_guidance]] 
- (grava_estado) [[state_Session.selected_obligation-4fd8c|Session.selected_obligation]] 
- (grava_estado) [[state_Session.trail-b6f1c|Session.trail]] 
- (navega) [[screen_obligation-113ca|obligation]] 
- (le_estado) [[state_Session.view-a9ea1|Session.view]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (le_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (chama) [[fn_telegram_recursos._resume-ec321|telegram_recursos._resume]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_pay-ee2a3|pay]] N. <obrigação>
- (navega) [[screen_agenda-a82fc|agenda]] N. Ver compromisso
- (navega) [[act_invoice_commit-7ad93|invoice_commit]] botão da resposta
