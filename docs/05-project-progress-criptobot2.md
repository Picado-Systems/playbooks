# 5. Progresso do Projeto: `cripto-bot-2` (Aura Trader .NET 9)

Registo de evolução técnica, arquitetura implementada e backlog do **`cripto-bot-2`** (Lean MVP).

---

## 1. Contexto e Objetivos

O **`cripto-bot-2`** é um bot de negociação e análise técnica em **.NET 9**, desenhado com Clean Architecture e estratégia Lean MVP (100% local, custo 0€ de infraestrutura):
- `AuraTrader.Domain`: Entidades (`TradeSignal`, `IndicatorResult`, `PaperAccount`, `PaperPosition`, `PaperOrder`), enums (`SignalAction`) e indicadores técnicos matemáticos puros (SMA, EMA, RSI, MACD).
- `AuraTrader.Application`: Serviços de análise técnica (`PriceAnalysisService`), momentum (`MomentumSignalEvaluator`), interfaces (`IExchangeDataProvider`, `IMessageBus`, `IPaperTradingService`) e DTOs.
- `AuraTrader.Infrastructure`: Mensageria assíncrona in-process (`ChannelMessageBus`), base de dados local SQLite (`AuraTraderDbContext`), cache em memória (`MemoryMarketDataCache`) e simulação de ordens (`PaperTradingService`).
- `AuraTrader.Worker`: Serviço em background com temporizador periódico (`PeriodicTimer`) para ingestão e execução autónoma.
- `AuraTrader.Api`: API REST documentada com Swagger e Serilog.
- `ui/`: Frontend reativo em **Angular 19** com Angular Signals e Angular Material.
- `AuraTrader.UnitTests`: Suite de testes unitários com `xUnit`, `FluentAssertions` e SQLite in-memory.

---

## 2. Entregas Concluídas (Merged na `main`)

| Tarefa | Pull Request | Ficheiros Principais | Testes Unitários | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **`t_aura_01`** | [PR #2](https://github.com/RicardoVarzim/cripto-bot-2/pull/2) | `.github/workflows/ci.yml` | 11/11 Passados | **Merged** |
| **`t_aura_02`** | [PR #3](https://github.com/RicardoVarzim/cripto-bot-2/pull/3) | `src/AuraTrader.Domain/Indicators/MACD.cs`<br>`tests/.../MACDTests.cs` | 16/16 Passados | **Merged** |
| **`t_aura_03`** | [PR #4](https://github.com/RicardoVarzim/cripto-bot-2/pull/4) | `src/.../Services/MomentumSignalEvaluator.cs`<br>`tests/.../MomentumSignalEvaluatorTests.cs` | 20/20 Passados | **Merged** |
| **`t_aura_04/05`** | [PR #5](https://github.com/RicardoVarzim/cripto-bot-2/pull/5) | `MarketDataIngestionService`, `PricePollingWorker`, `PaperTradingService`, `PaperTradingWorker`, `ui/` (Angular 19) | 28/28 Passados | **Merged** |
| **`t_aura_06`** | [PR #8](https://github.com/RicardoVarzim/cripto-bot-2/pull/8) | `BinancePublicClient.cs`, `DependencyInjection.cs`, `BinancePublicClientTests.cs` | 35/35 Passados | **Merged** |
| **`t_aura_07`** | [PR #9](https://github.com/RicardoVarzim/cripto-bot-2/pull/9) | `ITradingStrategy.cs`, `EmaCrossStrategy.cs`, `RsiMeanReversionStrategy.cs`, `MacdMomentumStrategy.cs`, `IBacktestService.cs`, `BacktestService.cs`, `BacktestController.cs` | 42/42 Passados | **Merged** |
| **`t_aura_08`** | [PR #10](https://github.com/RicardoVarzim/cripto-bot-2/pull/10) | `BotConfiguration.cs`, `IBotConfigurationService.cs`, `BotConfigurationService.cs`, `AdminController.cs`, `PricePollingWorker.cs`, `MarketDataIngestionService.cs` | 51/51 Passados | **Merged** |
| **`t_aura_09`** | [PR #11](https://github.com/RicardoVarzim/cripto-bot-2/pull/11) | `AdminService.ts`, `AdminPanelComponent` (HTML/SCSS/TS), `app.routes.ts`, `sidebar.component.ts` | 51/51 Tests & Angular Build OK | **Merged** |

### Resumo Técnico do Lean MVP Integrado até ao PR #11:
1. **Painel de Administração e Gestão de Risco Angular 19 (`t_aura_09`)**:
   - Desenvolvido `AdminPanelComponent` e `AdminService` reativo em Angular Signals.
   - Barra de controlo operacional com Play/Pause dinâmico, ingestão manual forçada e Kill Switch de emergência.
   - Gestão de pares dinâmicos por chips interativos (`BTC/USD`, `ETH/USD`, `SOL/USD`, etc.).
   - Parametrização em tempo real com sliders para intervalo de polling, sensibilidade de confiança, histórico e gestão de risco (alocação %, stop-loss %, take-profit % e taxas).
   - Visualizador interativo de Backtesting com gráficos de Curva de Património (Equity Curve via Chart.js), cartões de KPI (Win Rate, Profit Factor, Max Drawdown) e tabela de ordens simuladas.
2. **Motor de Parametrização Dinâmica & Controlo Operacional (`t_aura_08`)**:
   - Entidade `BotConfiguration` persistida em SQLite via EF Core.
   - Serviço `IBotConfigurationService` / `BotConfigurationService` com hot-reloading de parâmetros.
   - `PricePollingWorker` e `MarketDataIngestionService` adaptados para pausa/retoma dinâmica e intervalos flexíveis.
   - Endpoints REST em `AdminController`: `/api/admin/status`, `/api/admin/config`, `/api/admin/worker/pause`, `/api/admin/worker/resume`, `/api/admin/worker/poll`.
3. **Estratégias Plurais & Motor de Backtesting Rápido (`t_aura_07`)**:
   - `ITradingStrategy`: Abstração de estratégias no Domínio com 3 algoritmos concorrentes (`EmaCrossStrategy(9/21)`, `RsiMeanReversionStrategy(14, 30/70)` e `MacdMomentumStrategy(12/26/9)`).
   - `IBacktestService`: Simulação sequencial cronológica vela-a-vela com modelo realista de custos (taxa 0.1% e slippage 0.05%), calculando Win Rate %, Total P&L ($ e %), Profit Factor, Max Drawdown % e Equity Curve temporal.
   - Endpoints REST `GET /api/Backtest/strategies` e `POST /api/Backtest/run`.
4. **Provedor de Mercado Gratuito Binance (`t_aura_06`)**:
   - `BinancePublicClient` consumindo endpoints públicos spot e klines sem necessidade de API key, com normalização de pares (`USD` -> `USDT`).
5. **Pipeline de Ingestão e Simulação de Carteira**:
   - Polling periódico, persistência em SQLite, emissão no `ChannelMessageBus` e acompanhamento de carteira paper trading.

---

## 3. Backlog Ativo da Sprint: Dry-Run & Backtesting de Estratégias

> **Atenção Provedor de Mercado:** A API da CryptoCompare passou a requerer API Key obrigatória (HTTP 401). A API pública da Binance (`api.binance.com`) é gratuita e não requer autenticação. A tarefa `t_aura_06` desbloqueia o fluxo 100% gratuito.

### Tarefas Prioritárias para o Athos Agent:

1. **`t_aura_06`**: `BinancePublicDataProvider: Mercado Spot e Velas Históricas sem Chaves`
   - **Objetivo**: Implementar cliente `BinancePublicClient` consumindo `https://api.binance.com/api/v3/ticker/price` e `/api/v3/klines`.
   - **ACs**: Mapeamento para `CoinHistoricalPrice`, suporte a pares `BTCUSDT`, `ETHUSDT`, `SOLUSDT` e testes unitários com mock HTTP.
   - **Regra**: Proibido merge na `main` e sem deploy. Abrir PR como `athoagent-oss`.

2. **`t_aura_07`**: `ITradingStrategy & Estratégias Concorrentes (EMA Cross, RSI Mean Reversion, MACD Momentum)`
   - **Objetivo**: Abstrair a lógica de sinais para permitir que diferentes algoritmos concorram entre si.
   - **ACs**: Interface `ITradingStrategy` em `AuraTrader.Domain/Strategies/`, implementações `EmaCrossStrategy` (9/21), `RsiMeanReversionStrategy` (30/70) e `MacdMomentumStrategy` com testes xUnit dedicados.
   - **Regra**: Proibido merge na `main` e sem deploy. Abrir PR como `athoagent-oss`.

3. **`t_aura_08`**: `IBacktestService: Motor de Simulação Histórica Rápida e Métricas Financeiras`
   - **Objetivo**: Motor de backtesting sequencial vela-a-vela que avalia uma estratégia contra 100 a 500 velas em milissegundos.
   - **ACs**: Cálculo de Win Rate %, Profit Factor, Max Drawdown %, Curva de Capital (Equity Curve) e endpoint `POST /api/Backtest/run`.
   - **Regra**: Proibido merge na `main` e sem deploy. Abrir PR como `athoagent-oss`.

4. **`t_aura_09`**: `UI Angular de Backtesting & Comparador Visual de Estratégias`
   - **Objetivo**: Tela na aplicação Angular (`ui/`) para selecionar estratégia, correr simulação e exibir gráficos e tabela de rentabilidade.
   - **ACs**: Consumo dos endpoints de backtesting, gráfico de Equity Curve (Chart.js) e tabela comparativa de estratégias.
   - **Regra**: Proibido merge na `main` e sem deploy. Abrir PR como `athoagent-oss`.

5. **`t_aura_10`**: `Multi-Strategy Dry-Run no Worker & Auditoria Final`
   - **Objetivo**: Permitir ao `AuraTrader.Worker` correr múltiplas estratégias em modo dry-run ao vivo em simultâneo com sub-carteiras virtuais.
   - **ACs**: Tagging de ordens por estratégia, relatórios de rentabilidade segregados e auditoria com >85% de cobertura de testes.
   - **Regra**: Proibido merge na `main` e sem deploy. Abrir PR como `athoagent-oss`.
