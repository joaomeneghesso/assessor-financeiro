---
tipo: service
arquivo: compromissos.py
linha: 2212
---
# compromissos.apagar_compromisso_formatado

Função de negócio (destino de roteamento).

`fn:compromissos.apagar_compromisso_formatado`

## Vai para
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] compromissos + auditoria

## Vem de
- (chama) [[text_apagar_fixo_compromisso_id-16849|apagar fixo|compromisso <id>]] 
