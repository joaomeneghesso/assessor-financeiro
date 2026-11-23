# Onda 3, etapa 1: higiene, configuração única e relógio único (12/11/2026)

Base: commit `6fb2990`. Plano: `01_arquitetura.md`, seção D, etapas 0 e 1. Nenhuma regra de negócio, texto de tela ou teste antigo foi alterado. Os testes `test_equivalencia_calculos_onda2` e `test_jornadas_ponta_a_ponta` passaram a cada sub-etapa.

## O que foi feito

| Sub-etapa | Resultado |
|---|---|
| A. Linha de base | `tests/test_arquitetura_linha_de_base.py` mede por AST e trava (só pode diminuir) tamanho dos 5 maiores módulos, funções com mais de 100 linhas (36), ciclos de import (14 módulos, 33 arestas), `database` importando regra (5 módulos), SQL fora de `database.py`, relógio fora de `relogio.py` e ambiente fora de `config.py`. |
| B. Código morto | 33 símbolos sem nenhuma referência no repositório removidos (cerca de 340 linhas), entre eles as 3 rotinas legadas nunca agendadas de `app.py` e o que só elas usavam, `MENU_PRINCIPAL`, `formato_nao_suportado`, `_serie_historica`, 4 listas de keywords de `compromissos.py` e 3 funções de `assessor.py` importadas e nunca chamadas. |
| C. `config.py` | Toda leitura de ambiente passa por `config` (de 53 leituras em 13 módulos para 0). Leitura no mesmo momento e com o mesmo padrão de antes. Pastas `backups/exports/dashboards/imports` ancoradas no projeto. `.env.example` cobre as 54 variáveis lidas. `tests/test_config_unica.py` confere código × registro × exemplo. |
| D. `relogio.py` | UTC-3 fixo. Usos diretos de `date.today()`/`datetime.now()` caíram de 181 para 21. Convertidos: `conciliacao`, `compromissos`, `database`, `fatura_conferencia`, `fixos_edicao`, `saldos_edicao`, `telegram_registros`, `telegram_experiencia.today`, `services` (114) e `app` (14 de 15). |

## Decisões e compatibilidade
- **Nomes antigos preservados como apelidos patcháveis:** `app.ASSESSOR_*`, `services.BACKUPS_DIR/EXPORTS_DIR/DASHBOARDS_DIR`, `compromissos.IMPORTS_DIR` e `database.DB_PATH`.
- **Carga do `.env`:** importar `config` não carrega o `.env`. Só `app.py` e `telegram_experiencia` carregam, como antes. `web_app` continua lendo `ASSESSOR_WEB_*` só do ambiente do processo.
- **`ASSESSOR_TIMEZONE`:** continua lida e ignorada. No `.env.example` ela aparece comentada, com o aviso de que é ignorada.
- **Patches de testes antigos:** `relogio.hoje(date)`/`hoje(fonte_datahora=datetime)` respeitam o `patch.object(modulo, 'date'|'datetime', ...)` desses testes e o relógio falso do gate. Código novo deve chamar `relogio.hoje()` sem argumentos.
- **Gate:** passou a copiar o `.env.example` para a pasta da validação.

## Mudança de comportamento possível
Numa máquina em UTC-3, que é a do titular, não há mudança.

Numa máquina fora de UTC-3:
- os pontos convertidos passam a usar a data e a hora de Brasília em vez da hora local do PC;
- os módulos ainda não convertidos (abaixo) continuam no relógio local. A comparação entre carimbos dos dois lados pode divergir pelo tamanho da diferença de fuso.

Se o `.env` não estiver na pasta do projeto, `app.py` deixa de procurá-lo nas pastas acima: agora o caminho é fixo, `<projeto>/.env`.

## O que faltou (próximos passos)
1. **Relógio:** faltam 21 usos diretos. A tabela mostra os módulos e o motivo de não terem sido convertidos.

   | Módulos | Motivo |
   |---|---|
   | `migrations` (4), `security` (2), `limitador_persistente`, `operacao_bot` | carimbos e travas |
   | `telegram_alertas` (2), `app` (1) | `now(tz)` dos alertas, que já está em UTC-3 |
   | `web_app` (2), `telegram_recursos`, `assessor_orientacao`, `categorias_pessoais` | periféricos |
   | `parser_financeiro` | os testes fazem patch de `pf.date`; converter com `relogio.hoje(date)` |
   | `registro_logs` | é intencional: avisa quando o PC não está em UTC-3 |
   | `preparar_seguranca_v40`, `ajustar_fatura_itau` | utilitários |

   Depois disso, eliminar os wrappers `fonte_data` migrando os testes antigos para `data_fixa`.
2. **Mantidos com referência em testes (não são código morto):**
   - `app.comando_publico`, `COMANDOS_PUBLICOS` e `PREFIXOS_PUBLICOS`, usados por `testes_v39/test_security_v40`;
   - `services.PENDENCIAS_CONFIRMACAO`, que nenhum ramo preenche, mas que 3 testes e `telegram_experiencia` limpam ou leem;
   - `ajustar_fatura_itau.py` e `sqlite_backup.py`, importados por testes;
   - `services.TRANSAÇÕES_POR_PAGINA`, que está em uso.
3. **Da etapa 0 do plano, ficou de fora:**
   - `requirements.in`/`.lock` e remoção de `openai`/`pydantic`;
   - `ruff`;
   - versão do `.bat`.
4. **Próxima etapa:** etapa 2 do plano, com as primitivas únicas (texto, datas, R$, backup).
