---
tipo: state
arquivo: services.py
linha: 304
---
# PENDENCIAS_ALTERACAO

Dict global {sessão: {comando, prévia}}: edição digitada aguardando 'confirmar alteracao'. Efêmero em memória (TTL 600 s).

`state:PENDENCIAS_ALTERACAO`

## Vem de
- (grava_estado) [[fn_services._preparar_alteracao_sessao-a37a4|services._preparar_alteracao_sessao]] define pendência (prévia antes → depois)
- (le_estado) [[fn_services.confirmar_alteracao_pendente-f320b|services.confirmar_alteracao_pendente]] 
- (grava_estado) [[fn_services.confirmar_alteracao_pendente-f320b|services.confirmar_alteracao_pendente]] consome antes de executar
- (grava_estado) [[fn_services.cancelar_alteracao_pendente-4e9a5|services.cancelar_alteracao_pendente]] limpa
