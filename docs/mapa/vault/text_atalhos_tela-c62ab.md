---
tipo: text_trigger
arquivo: telegram_experiencia.py
linha: 
---
# registrar/a pagar/historico/analises/mais/ajuda

handle_text.shortcuts l.2926-2931: route in {home,pay,history,analytics,...} reseta mês; register/more/help não resetam.

`text:atalhos_tela`

## Vai para
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] reseta só p/ home,pay,history,analytics,balance,agenda,receivables,reconciliations,recurring,plan
- (chama) [[act_view-1d8b8|view]] 

## Vem de
- (chama) [[btn_Histórico_teclado-15934|Teclado fixo: 🏠 Início ➕ Registrar 🧾 A pagar 🔎 Histórico 📊 Análises ⚙️ Mais]] 
