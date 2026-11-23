---
tipo: screen
arquivo: telegram_experiencia.py
linha: 910
---
# closing_details

Fechamento detalhado: entradas, despesas, comparativo mês anterior.

`screen:closing_details`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] título/consulta usa s.month
- (chama) [[fn_orientacao.coletar-ba856|coletar]] 
- (chama) [[fn_ux.transactions-60180|transactions]] 
- (navega) [[screen_categories-bcdb1|categories]] 🏷 Ver categorias
- (navega) [[screen_pay-ee2a3|pay]] 🧾 Ver contas
- (navega) [[screen_history-d40e7|history]] 🔎 Ver lançamentos
- (navega) [[screen_attention-ebc03|attention]] ⚠️ Central de atenção
- (navega) [[fn_ux.nav-29bea|Experience.nav]] 📅 Período/☰ Menu/🏠 Início (nav)
- (chama) [[fn_ux._cresceu_linhas-16d90|ux._cresceu_linhas]] 
- (navega) [[act_view-1d8b8|view]] 
- (navega) [[screen_home-111fe|home]] 

## Vem de
- (navega) [[screen_closing-a1da9|closing]] 🔎 Conferência completa
