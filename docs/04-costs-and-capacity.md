# 4. Estimativa de Custos, Unit Economics & Capacidade Diária

Análise económica e de dimensionamento de capacidade para operações autónomas do Athos na VPS Debian 12.

---

## 1. Unit Economics do Athos

Cada tarefa autónoma no Athos percorre 3 etapas:
1. **Especialista `dev`**: Lê o repositório, implementa ficheiros, executa testes locais e cria o PR estruturado.
2. **Gatekeeper de CI**: Polling e validação do GitHub Actions (0 tokens de LLM — custo zero).
3. **Especialista `reviewer`**: Auditoria interna do diff, segurança, padrões de arquitetura e conformidade com os Critérios de Aceitação (ACs).

| Recurso | Consumo por Tarefa | Custo Unitário (Grok 4.20) | Custo Unitário (OpenRouter Free) |
| :--- | :--- | :--- | :--- |
| **Input Tokens** | ~50.000 a 70.000 | ~\$0.10 a \$0.14 | **\$0.00** |
| **Output Tokens** | ~800 a 1.500 | ~\$0.01 a \$0.02 | **\$0.00** |
| **Tempo de Execução** | 6 a 12 minutos | — | — |
| **Custo Total Estimado** | — | **~\$0.12 a \$0.18 / tarefa** | **\$0.00 / tarefa** |

---

## 2. Estado dos Créditos e Dimensionamento

- **Saldo Inicial xAI**: \$5.00 pré-pagos (Top-up automático **desativado** para segurança de custo zero fixo).
- **Consumo Total nos Trials (18-19 Out)**: **~\$0.18 a \$0.30** para 6 tarefas desenvolvidas e auditadas.
- **Saldo Disponível Restante**: **~\$4.50 a \$4.70**.
- **Autonomia Restante com Saldo Atual**:
  - ~25 a 30 tarefas completas operando com a máxima qualidade do Grok 4.20.
  - Cobre com folga o plano de 5 dias (10 ondas / ~15-20 tarefas).
- **Fallback Automático Sustentável**:
  - Quando os créditos xAI se esgotarem, o Hermes passa automaticamente para o OpenRouter (`nvidia/nemotron-3-super-120b-a12b:free`), que tem **1.000 requests/dia gratuitos desbloqueados**, mantendo o sistema em funcionamento contínuo a **custo zero fixo**.

---

## 3. Recomendações de Carga Diária Sustentável

| Regime | Estrutura Diária | Throughput Esperado | Custo Estimado | Perfil de Gestão |
| :--- | :--- | :--- | :--- | :--- |
| **Sustentável (Recomendado)** | **2 ondas de 1.5h** (3h total/dia) | **8 a 12 tarefas/dia** (8-12 PRs) | ~\$1.20/dia (ou \$0.00 no fallback) | Ritmo perfeito para o Fundador: rever 4-5 PRs por bloco em 10 minutos. |
| **Intensivo (Sprint)** | **3 ondas de 2h** (6h total/dia) | **18 a 25 tarefas/dia** | ~\$3.00/dia | Aceleração de milestones antes de releases ou auditorias de segurança. |
