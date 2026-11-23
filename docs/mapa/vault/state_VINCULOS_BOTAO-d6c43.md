---
tipo: state
arquivo: app.py
linha: 1500
---
# VINCULOS_BOTAO

dict callback_data -> token da pendencia; botao de mensagem antiga nao confirma pendencia mais recente (max 1000)

`state:VINCULOS_BOTAO`

## Vem de
- (grava_estado) [[fn_app.botao_comando_vinculado-beb3a|botao_comando_vinculado]] 
- (le_estado) [[cb___confirmar_exclusao-3fc51|__confirmar_exclusao__]] botao de pendencia antiga nunca confirma
- (le_estado) [[cb___cancelar_exclusao-623cb|__cancelar_exclusao__]] 
