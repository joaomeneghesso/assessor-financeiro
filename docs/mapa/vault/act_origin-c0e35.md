---
tipo: action
arquivo: telegram_experiencia.py
linha: 2822
---
# origin

Memória de cálculo (saldo/reserva/previsão) via telegram_recursos.dispatch.

`act:origin`

## Vai para
- (chama) [[fn_telegram_recursos.dispatch-a2ef9|telegram_recursos.dispatch]] 
- (le_estado) [[state_Session.month-7f614|Session.month]] 
- (chama) [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_balance-64c54|balance]] 🔎 Origem do saldo
- (navega) [[screen_dashboard-6ba51|dashboard]] 🧮 Entender valores / Composição
- (navega) [[act_chart-efa97|chart]] botão da resposta
