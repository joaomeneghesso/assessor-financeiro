---
tipo: state
arquivo: services.py
linha: 301
---
# PENDENCIAS_EXPORTACAO

Dict global: aguardando período de exportação CSV (sessão).

`state:PENDENCIAS_EXPORTACAO`

## Vem de
- (grava_estado) [[fn_services.pedir_periodo_exportacao-97d0c|services.pedir_periodo_exportacao]] 
- (le_estado) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] 8845
- (grava_estado) [[text_exportação_pendente_cancelar_período_tudo-3ca8c|exportação pendente (cancelar|período|tudo)]] limpa ao cancelar/receber período
- (le_estado) [[text_cancelar_exportação-9b55e|cancelar exportação]] sem pendência responde que nada foi alterado
