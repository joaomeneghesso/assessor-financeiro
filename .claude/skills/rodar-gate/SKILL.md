---
name: rodar-gate
description: Executa o gate oficial de validação do Assessor (suíte Python em banco temporário) e resume o resultado. Use após qualquer alteração de código.
---
# Rodar o gate oficial

1. Na raiz do projeto (a pasta nuvem não tem `.venv` próprio: usa o do projeto do PC apontando `--projeto`):
```powershell
$saida = Join-Path $env:TEMP "assessor-validacao"
C:\Projetos\assessor-financeiro\.venv\Scripts\python.exe .\validacao\validar_versao_oficial.py --projeto C:\Projetos\assessor-financeiro-nuvem --workers 4 --timeout 1500 --saida $saida
```
2. Código de saída 0 = aprovado. Detalhes em `$saida\resultado.json`, `regressao.log`.
3. Para um teste isolado (unittest, pois pytest não está instalado):
```powershell
C:\Projetos\assessor-financeiro\.venv\Scripts\python.exe -m unittest tests.test_<modulo> -v
```
4. Nunca rode testes contra `data\financeiro.db`; o harness aborta se isso acontecer.
5. Reporte: nº de testes Python, falhas com trecho do log. Não declare "ok" sem ter rodado.
