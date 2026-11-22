# 3. Hermes Cron, Agendamentos & Manutenção de Infraestrutura

Guia de resolução de problemas, manutenção do agendador nativo do Hermes e otimização dos scripts de sistema.

---

## 1. Diagnóstico e Resolução do Briefing Matinal

### Problemas Encontrados & Resoluções

1. **`invalid literal for int() with base 10` no Kanban**:
   - **Causa**: O Hermes espera que as colunas `created_at`, `started_at` e `completed_at` na tabela `tasks` de `~/.hermes/kanban.db` sejam **inteiros UNIX (epoch em segundos)**. Tarefas inseridas manualmente via scripts com strings ISO (ex.: `'2026-10-18T19:51:21.571553'`) faziam rebentar a função interna `int(row['created_at'])` da CLI do Kanban.
   - **Correção**: Todas as tarefas com strings ISO foram migradas para UNIX timestamps inteiros. Novos scripts devem sempre gerar `int(datetime.utcnow().timestamp())`.
2. **Desempenho e Sobrecarga de Subprocessos**:
   - **Causa**: O script original `morning-briefing.py` executava `hermes kanban runs <task_id>` em loop para cada uma das ~50 tarefas da base de dados, gerando 50 subprocessos do Hermes CLI e demorando mais de 1 minuto a correr (com risco de timeout).
   - **Correção**: O script foi reescrito para consultar diretamente o SQLite (`kanban.db`) e o ficheiro de ondas (`waves.json`). A execução passou de ~60 segundos para **0.05 segundos** (50 milissegundos).
3. **Compatibilidade de Fuso Horário**:
   - Tratamento de datetimes naive vs. aware (`parse_dt` com fallback para `datetime.timezone.utc`) para evitar erros de comparação no cálculo do tempo restante para a próxima onda.

---

## 2. Resolução de Falhas de Quota HTTP 429 nos Cronjobs

### Causa Raiz
Três cronjobs estavam a falhar repetidamente há dezenas de execuções com o erro:
`RuntimeError: Gemini HTTP 429 (RESOURCE_EXHAUSTED): Resource has been exhausted ... model=gemini-3.8-flash`
Estes jobs estavam fixados no modelo `gemini-3.8-flash` através da Google AI Studio no plano gratuito (cujo limite diário de requests se esgotou).

### Correção Aplicada
No ficheiro `~/.hermes/cron/jobs.json`:
- Os jobs de triage (`c0f4ca14bece` e `d415ef0c5d5f`) e PR auto-review foram reconfigurados para utilizar o modelo primário ativo:
  - **`model`**: `grok-4.20-0309-non-reasoning`
  - **`provider`**: `xai`
  - **`fallback`**: `nvidia/nemotron-3-super-120b-a12b:free` (OpenRouter)

---

## 3. Comandos Úteis do Hermes Cron

```bash
# Listar todos os jobs agendados e estado do último run
hermes cron list

# Executar diagnóstico de saúde dos jobs agendados
hermes cron doctor

# Forçar execução de um cronjob específico
hermes cron run <job_id>

# Pausar ou retomar um job
hermes cron pause <job_id>
hermes cron resume <job_id>
```
