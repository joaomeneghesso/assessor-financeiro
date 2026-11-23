---
tipo: text_trigger
arquivo: telegram_experiencia.py
linha: 2954
---
# quanto vou pagar [aaaa-mm] (UX2)

fullmatch em handle_text: aceita só 'quanto vou pagar|quanto pagar [AAAA-MM]'. Com mês: s.month=mês; sem: s.month=mês atual. Mostra view 'pay'. Em prática dispatch_text o intercepta antes via fast_deterministic_query.

`text:quanto vou pagar (ux2 aaaa-mm)`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] 2956-2957
- (chama) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] ('view','pay')

## Vem de
- (chama) [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]] 2954
- (navega) [[text_quanto_vou_pagar-9e130|quanto vou pagar]] no Telegram UX2 o mesmo texto é tratado antes (dispatch_text); services só roda se UX2 devolver None
