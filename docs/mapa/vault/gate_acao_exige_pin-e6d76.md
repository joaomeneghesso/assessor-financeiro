---
tipo: security_gate
arquivo: app.py
linha: 911
---
# acao_exige_pin

True para reset/troca de PIN, backup e exportar tudo, status/saude, confirmar importacao e apagar por faixa; normaliza espacos e sinonimos (services.normalizar_comando_sinonimos) antes de checar

`gate:acao_exige_pin`

## Vem de
- (chama) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 
- (exige_pin) [[job_rotina_backup_diario-a6f56|rotina_backup_diario]] NAO passa por PIN (executa processar_mensagem direto)
