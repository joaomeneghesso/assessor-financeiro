---
tipo: service
arquivo: assessor_orientacao.py
linha: 182
---
# assessor_orientacao.reconhecer_pergunta

Regex determinísticos (texto sem acentos) -> view ('pay','balance','agenda',...). Só devolve view se UMA categoria casa.

`fn:assessor_orientacao.reconhecer_pergunta`

## Vai para
- (navega) [[fn_telegram_experiencia.screen_receivables-7fe08|telegram_experiencia.screen_receivables]] /quanto.*receber|o que.*receber|entradas previstas|salario.*cai/
- (navega) [[fn_telegram_experiencia.screen_pay-c88c4|telegram_experiencia.screen_pay]] /quanto.*pagar|o que.*pagar|contas.*venc|contas a pagar|dividas|pendencias/
- (navega) [[fn_telegram_experiencia.screen_agenda-da330|telegram_experiencia.screen_agenda]] /proximos.*dias|agenda|vence.*semana/
- (navega) [[fn_telegram_experiencia.screen_balance-df783|telegram_experiencia.screen_balance]] /quanto.*tenho|saldo|quanto.*sobr|dinheiro.*disponivel/
- (navega) [[fn_telegram_experiencia.screen_analytics-3aa02|telegram_experiencia.screen_analytics]] /onde.*gast|quanto.*gast|meus gastos|.../
- (navega) [[fn_telegram_experiencia.screen_recurring-4c0ce|telegram_experiencia.screen_recurring]] /assinaturas|recorrentes|se repet/
- (navega) [[fn_telegram_experiencia.screen_budgets-740e9|telegram_experiencia.screen_budgets]] /limites|orcamento|economizar/
- (navega) [[fn_telegram_experiencia.screen_review-6556a|telegram_experiencia.screen_review]] /duplicad|concili|erro.*valor/
- (navega) [[fn_telegram_experiencia.screen_alerts-edeeb|telegram_experiencia.screen_alerts]] /alerta|notific|lembret/
- (navega) [[fn_telegram_experiencia.screen_attention-cfc78|telegram_experiencia.screen_attention]] /atencao|central.*atenc.../
- (navega) [[fn_telegram_experiencia.screen_closing-785b7|telegram_experiencia.screen_closing]] /fechamento.*mes|fechar.*mes|como.*fechou|resultado.*mes/
- (navega) [[fn_telegram_experiencia.screen_home-2d196|telegram_experiencia.screen_home]] /meu mes|como.*mes|resumo|dashboard/
- (navega) [[fn_telegram_experiencia.screen_help-94df3|telegram_experiencia.screen_help]] /ajuda|como.*funciona/

## Vem de
- (chama) [[mod_assessor_orientacao.py-e9925|assessor_orientacao.py]] 
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] 4144
- (chama) [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]] 2971
