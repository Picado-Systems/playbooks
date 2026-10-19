# 5. Progresso do Projeto: `cripto-bot-2` (Aura Trader .NET 9)

Registo de evolução técnica, arquitetura implementada e backlog do **`cripto-bot-2`** (Lean MVP).

---

## 1. Contexto e Objetivos

O **`cripto-bot-2`** é um bot de negociação e análise técnica em **.NET 9**, desenhado com Clean Architecture:
- `AuraTrader.Domain`: Entidades (`TradeSignal`, `IndicatorResult`), enums (`SignalAction`) e interfaces de indicadores técnicos.
- `AuraTrader.Application`: Serviços de análise técnica (`PriceAnalysisService`), momentum (`MomentumSignalEvaluator`), paper trading e DTOs.
- `AuraTrader.Infrastructure`: Mensageria em memória (`ChannelMessageBus`), clientes de APIs de exchanges.
- `AuraTrader.UnitTests`: Suite de testes unitários com `xUnit`, `FluentAssertions` e `Moq`.

---

## 2. Entregas Concluídas (Merged na `main`)

| Tarefa | Pull Request | Ficheiros Principais | Testes Unitários | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **`t_aura_01`** | [PR #2](https://github.com/RicardoVarzim/cripto-bot-2/pull/2) | `.github/workflows/ci.yml` | 11/11 Passados | **Merged** |
| **`t_aura_02`** | [PR #3](https://github.com/RicardoVarzim/cripto-bot-2/pull/3) | `src/AuraTrader.Domain/Indicators/MACD.cs`<br>`tests/.../MACDTests.cs` | 16/16 Passados | **Merged** |
| **`t_aura_03`** | [PR #4](https://github.com/RicardoVarzim/cripto-bot-2/pull/4) | `src/.../Services/MomentumSignalEvaluator.cs`<br>`tests/.../MomentumSignalEvaluatorTests.cs` | 20/20 Passados | **Merged** |

### Resumo Técnico do Lean MVP Integrado:
1. **Pipeline de CI (.NET 9)**: Setup automatizado, restore, build e testes unitários em release.
2. **Indicador Técnico MACD**: Cálculo de Linha MACD (EMA 12 - EMA 26), Linha de Sinal (EMA 9) e Histograma com lógica de tendência Bullish / Bearish.
3. **Detector de Sinais de Momentum**: Combinação de condições de sobrecompra/sobrevenda (RSI <= 30 / >= 70) com cruzamento de MACD, gerando e publicando `TradeSignal` de forma assíncrona no `ChannelMessageBus`.

---

## 3. Backlog Imediato (Preparado no Kanban para `wave_01`)

1. **`t_aura_04`**: `PaperTradingService: Simulação de Execução de Ordens e PnL`
   - Consumo dos eventos `TradeSignal` emitidos pelo `ChannelMessageBus`.
   - Carteira simulada com saldo inicial (10.000 USDT).
   - Cálculo de PnL realizado e não realizado.
2. **`t_aura_05`**: `TradeLedger e Registo de Execuções Simuladas`
   - Auditoria e histórico de ordens com slippage e comissões simuladas.
