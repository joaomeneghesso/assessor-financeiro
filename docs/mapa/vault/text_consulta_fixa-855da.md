---
tipo: text_trigger
arquivo: telegram_experiencia.py
linha: 
---
# meu mes|fechamento|atencao|resumo|quanto vou pagar|saldo geral|agenda|alertas|a receber|conciliacoes|assinaturas|meu plano|assessor [AAAA-MM]

handle_text l.2954 (fullmatch): grava mês informado ou RESETA ao corrente; depois act(view,<tela>).

`text:consulta_fixa`

## Vai para
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2956-2957 mês do texto ou corrente
- (chama) [[act_view-1d8b8|view]] 
