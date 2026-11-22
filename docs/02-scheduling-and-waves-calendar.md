# 2. Agendamento Temporal & Ferramenta `athos-wave`

Documento de referência para o agendamento de ondas temporais e utilização do comando CLI `athos-wave` na VPS Debian 12.

---

## 1. Ferramenta CLI: `athos-wave`

A ferramenta está instalada globalmente em `~/.local/bin/athos-wave` (código fonte em `~/.hermes/scripts/waves.py`) e consulta o ficheiro de configuração `~/.hermes/waves.json`.

### Comandos Disponíveis

```bash
# 1. Consultar calendário completo das ondas dos 5 dias
athos-wave list

# 2. Verificar estado atual da onda em curso e próxima agendada
athos-wave status

# 3. Editar o horário de uma onda existente
athos-wave edit wave_01 --time 10:00

# 4. Alterar projeto alvo ou objetivos de uma onda
athos-wave edit wave_02 --project cripto-bot-2 --goals "Novos indicadores e filtros de volatilidade"

# 5. Adicionar uma nova onda ao calendário
athos-wave add --date 2026-10-24 --time 09:30 --project padelsync --hours 1.5 --goals "Auditoria de segurança e CI"

# 6. Cancelar uma onda
athos-wave cancel wave_03

# 7. Forçar a execução imediata de uma onda (fora do horário marcado)
athos-wave run wave_01
```

---

## 2. Integração com o Agendador Hermes (`hermes cron`)

O disparo das ondas agendadas é gerido pelo scheduler nativo do Hermes:
- **Job ID**: `efdcd345fccc` (`athos-wave-scheduler`)
- **Frequência**: A cada 10 minutos (`every 10m`)
- **Modo**: `no-agent` (executa `wave-runner.py --check` diretamente)
- **Comportamento do `wave-runner.py`**:
  1. A cada 10 minutos, verifica se existe alguma onda em `waves.json` em estado `scheduled` cuja hora de início já tenha chegado (janela de até 30 min).
  2. Se encontrada, atualiza o estado para `running`.
  3. Envia mensagem ao Telegram a notificar o arranque da onda e objetivos.
  4. Dispara o `autonomous-loop.py --timebox-hours <h> --project <proj>`.
  5. Ao terminar, atualiza o estado para `completed` e envia o relatório executivo consolidado ao Telegram.

---

## 3. Calendário Consolidado dos 5 Dias (10 Ondas)

| ID | Data / Hora (UTC) | Hora Portugal | Projeto | Timebox | Objetivos Principais |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`wave_01`** | **19 Out — 09:30** | 10:30 | **`cripto-bot-2`** | 1.5h | `PaperTradingService`: Simulação de ordens baseadas em `TradeSignal` (RSI+MACD) e PnL tracking |
| **`wave_02`** | **19 Out — 15:30** | 16:30 | **`padelsync`** | 1.5h | Segurança & CI: Migração de credenciais de teste para GitHub Secrets (PR #7) e integridade de migrações |
| **`wave_03`** | **20 Out — 09:30** | 10:30 | **`padelsync`** | 1.5h | Non-Stop Tournaments: Modelação de dados e endpoints de inscrições |
| **`wave_04`** | **20 Out — 15:30** | 16:30 | **`cripto-bot-2`** | 1.5h | Candles Crawler: Histórico de preços e conector de mercado resiliente |
| **`wave_05`** | **21 Out — 09:30** | 10:30 | **`raiz`** (P0) | 1.5h | Tesouraria / Caixa Imediato: Estrutura de transações e reconciliação diária |
| **`wave_06`** | **21 Out — 15:30** | 16:30 | **`raiz`** (P0) | 1.5h | Pagamentos & Vouchers: Validação de gateway e emissão de vouchers de campanha |
| **`wave_07`** | **22 Out — 09:30** | 10:30 | **`padelsync`** | 1.5h | Matchmaking de comunidades e notificações Telegram de novos jogos |
| **`wave_08`** | **22 Out — 15:30** | 16:30 | **`portfolio-dashboard`** | 1.5h | Infra & Observabilidade: Resolução definitiva do healthcheck Nginx/Wget no portfolio |
| **`wave_09`** | **23 Out — 09:30** | 10:30 | **`padelsync`** / Infra | 1.5h | Backup Automatizado: Script diário de backup das bases Postgres (`padelsync` + `raiz`) |
| **`wave_10`** | **23 Out — 15:30** | 16:30 | **`cripto-bot-2`** | 1.5h | Sprint Review & Hardening: Auditoria cruzada de CI e relatório executivo consolidado |
