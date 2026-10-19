# 📚 Athos Knowledge Base & Playbooks Docs

Base de conhecimento consolidada para operação, manutenção e expansão do ecossistema de agentes autónomos do Athos.

---

## 📑 Índice da Documentação

1. **[01. Motor de Execução de Ondas Autónomas](01-autonomous-wave-engine.md)**
   - Arquitetura do loop autónomo (`autonomous-loop.py`).
   - Ciclo de auto-remediação de CI (Self-Healing) com extração de logs de falha do GitHub Actions.
   - Resiliência contra paragens prematuras de timebox.
   - Políticas de identidade (`athoagent-oss` vs. `RicardoVarzim`) e regra do fundador.

2. **[02. Agendamento Temporal & Ferramenta `athos-wave`](02-scheduling-and-waves-calendar.md)**
   - Utilização do comando CLI `athos-wave` (`list`, `status`, `edit`, `add`, `run`, `cancel`).
   - Integração com o agendador nativo do Hermes (`efdcd345fccc` / `wave-runner.py`).
   - Calendário consolidado de 5 dias (10 ondas de 1.5h, 15h de trabalho autónomo).

3. **[03. Hermes Cron, Agendamentos & Manutenção](03-hermes-cron-and-maintenance.md)**
   - Resolução e reescrita de alto desempenho do Briefing Matinal (`morning-briefing.py`).
   - Correção de integridade de dados no `kanban.db` (migração de strings ISO para inteiros UNIX).
   - Resolução de erros HTTP 429 de quota nos cronjobs de triage e migração para o Grok/OpenRouter.

4. **[04. Custos, Unit Economics & Capacidade Diária](04-costs-and-capacity.md)**
   - Unit economics por tarefa (~$0.12 a $0.18 no Grok 4.20).
   - Balanço dos trials e saldo disponível restante na xAI (~$4.50+).
   - Dimensionamento de capacidade: 8 a 12 tarefas/dia em regime sustentável.

5. **[05. Progresso do Projeto: `cripto-bot-2`](05-project-progress-criptobot2.md)**
   - Arquitetura Clean Architecture .NET 9.
   - Entregas concluídas e fundidas na `main` (CI, MACD, MomentumSignalEvaluator).
   - Backlog imediato configurado para a próxima onda (`PaperTradingService` e `TradeLedger`).

---

## 🔗 Referências Rápidas & Ficheiros de Configuração

- **Playbook de Onboarding Central**: [`playbooks/athos-onboarding.md`](../athos-onboarding.md)
- **Diretrizes Globais de Agentes**: [`AGENTS.md`](../../AGENTS.md)
- **Script da Onda Autónoma**: [`playbooks/scripts/autonomous-loop.py`](../scripts/autonomous-loop.py) (VPS: `~/.hermes/scripts/autonomous-loop.py`)
- **Gestor de Ondas**: [`playbooks/scripts/waves.py`](../scripts/waves.py) (VPS: `~/.local/bin/athos-wave`)
- **Ficheiro de Ondas Agendadas**: [`playbooks/waves.json`](../waves.json) (VPS: `~/.hermes/waves.json`)
