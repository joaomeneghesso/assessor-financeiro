# Validação do Assessor Financeiro

## Comando oficial

Execute somente o gate isolado a partir da raiz do projeto:

```powershell
$saida = Join-Path $env:TEMP "assessor-validacao"
.\.venv\Scripts\python.exe .\validacao\validar_versao_oficial.py --saida $saida
```

Relógio falso (Onda 2): `--data AAAA-MM-DD [--hora HH:MM]` roda a suíte inteira com "hoje" começando nessa data (o relógio anda). O patch fica em `validacao/relogio_falso.py`, é aplicado só dentro do harness, antes de importar o projeto, e troca `date`/`datetime`/`time.time` de todos os módulos do projeto; a produção nunca o importa. Testes que dependem de "hoje" usam `tests/relogio_fixo.py` (`data_fixa`). Datas críticas sugeridas: dia 1, 24, 25 (corte), 26, último dia do mês, 31/12, 01/01 e 29/02/2028. `st_mtime` de arquivos continua real.

O gate:

- copia o código para uma pasta temporária;
- remove credenciais do ambiente;
- bloqueia rede externa durante a suíte Python;
- usa exclusivamente bancos temporários;
- aborta se algum teste tentar abrir o banco oficial;
- executa a suíte atual, a matriz histórica v3.9 e a deduplicação;
- executa os contratos JavaScript com Node;
- só retorna código zero quando Python e JavaScript são aprovados;
- grava `resultado.json`, `regressao.log`, `web.log` e `dependencias.log` na pasta de saída.

## Coleções históricas

As pastas `validacao/tests` e `validacao/testes_v39` são material histórico. Elas dependem do layout de release reconstruído pelo gate e **não devem ser executadas diretamente** com `unittest discover`.

`validacao/tests` é uma fotografia antiga da suíte principal e não participa do gate. A fonte vigente é `tests`.

`validacao/testes_v39` participa do gate somente depois de ser copiada para a raiz temporária esperada pelos seus imports legados.

## Banco de produção

O arquivo abaixo nunca pode ser usado por testes:

`C:\Projetos\assessor-financeiro\data\financeiro.db`

O gate informa esse caminho ao harness por `ASSESSOR_TEST_FORBIDDEN_DB` e substitui a abertura de conexão por uma versão que falha imediatamente caso o caminho proibido seja selecionado.
