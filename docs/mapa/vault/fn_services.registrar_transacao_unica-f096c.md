---
tipo: service
arquivo: services.py
linha: 10626
---
# services.registrar_transacao_unica

Função de negócio (destino de roteamento).

`fn:services.registrar_transacao_unica`

## Vai para
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] database.inserir_transacao (sem confirmação extra)

## Vem de
- (chama) [[text_lançamento_livre_gastei_recebi_comprei...-a0909|lançamento livre (gastei|recebi|comprei...)]] 
