---
tipo: action
arquivo: telegram_experiencia.py
linha: 3285
---
# settle

Baixa de compromisso (begin_settlement).

`act:settle`

## Vai para
- (chama) [[fn_ux.begin_settlement-f6619|begin_settlement]] 
- (chama) [[fn_conciliacao.alvo-7b858|alvo]] 
- (navega) [[fn_ux.preview-35809|preview]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_receivables-eb894|receivables]] Registrar recebimento #id
- (navega) [[screen_obligation-113ca|obligation]] Registrar pagamento (compromisso)
