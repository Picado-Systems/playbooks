#!/usr/bin/env python3
"""
Seed CriptoBot2 (Aura Trader) Backtesting & Dry-Run Tasks into Athos Kanban
===========================================================================
Popula a base de dados ~/.hermes/kanban.db com as tarefas t_aura_06 a t_aura_10.
"""

import sqlite3
import pathlib
import datetime

db_path = pathlib.Path.home() / ".hermes/kanban.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Garantir existência da tabela tasks caso ainda não esteja criada
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    status TEXT DEFAULT 'todo',
    priority INTEGER DEFAULT 0,
    project_id TEXT,
    created_at TEXT
)
""")

now = datetime.datetime.utcnow().isoformat()

tasks = [
    (
        "t_aura_06",
        "[AuraTrader] BinancePublicDataProvider: Mercado Spot e Velas Históricas Gratuitas",
        """## Objetivo
Implementar um cliente HTTP para a API pública da Binance (api.binance.com) como provedor de dados de mercado sem necessidade de API key, resolvendo a limitação de autenticação 401 da CryptoCompare.

## Critérios de Aceitação (ACs)
- AC1: Implementar BinancePublicClient implementando IExchangeDataProvider em Infrastructure/ExternalApis/Binance/.
- AC2: Obtenção de preço spot via GET /api/v3/ticker/price?symbol=BTCUSDT (com fallback inteligente de pares ex: BTC/USD -> BTCUSDT).
- AC3: Obtenção de velas históricas via GET /api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30 mapeando para CoinHistoricalPrice.
- AC4: Registo e injeção transparente de dependências no DependencyInjection.cs.
- AC5: Testes unitários com mock HTTP validando parsing e resiliência a falhas de rede.
- AC6: Branch isolada feat/t_aura_06 e PR aberto com identidade athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        0,
        "cripto-bot-2",
        now
    ),
    (
        "t_aura_07",
        "[AuraTrader] ITradingStrategy: Abstração de Estratégias e Modelos Concorrentes",
        """## Objetivo
Desacoplar a geração de sinais algorítmicos em interfaces puras de estratégia (Domain), permitindo comparar múltiplos algoritmos concorrentes.

## Critérios de Aceitação (ACs)
- AC1: Criar ITradingStrategy em Domain/Strategies/ com método StrategyEvaluationResult Evaluate(IReadOnlyList<CoinHistoricalPrice> history).
- AC2: Implementar EmaCrossStrategy (cruzamento rápido/lento de médias móveis EMA 9 com EMA 21).
- AC3: Implementar RsiMeanReversionStrategy (sinais de compra em RSI <= 30 e venda em RSI >= 70).
- AC4: Implementar MacdMomentumStrategy (cruzamento da linha MACD com linha de sinal).
- AC5: Testes unitários cobrindo cenários sintetizados de subida, descida e lateralização.
- AC6: Branch isolada feat/t_aura_07 e PR aberto com identidade athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        1,
        "cripto-bot-2",
        now
    ),
    (
        "t_aura_08",
        "[AuraTrader] IBacktestService: Motor de Simulação Histórica Rápida e KPIs Financeiros",
        """## Objetivo
Criar o motor de backtesting que recebe uma estratégia e histórico de velas e calcula o resultado financeiro simulado com taxas e métricas de desempenho.

## Critérios de Aceitação (ACs)
- AC1: DTOs BacktestRequestDto e BacktestResultDto contendo métricas completas e lista de trades simulados.
- AC2: Simulação vela-a-vela chronológica com desconto de taxa de exchange (0.1%) e slippage (0.05%).
- AC3: Cálculo exato de KPIs: Win Rate %, Total P&L (% e $), Profit Factor, Max Drawdown % e Equity Curve.
- AC4: Endpoints REST POST /api/Backtest/run e GET /api/Backtest/strategies no AuraTrader.Api.
- AC5: Testes unitários cobrindo o cálculo de métricas e drawdown com dados determinísticos.
- AC6: Branch isolada feat/t_aura_08 e PR aberto com identidade athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        2,
        "cripto-bot-2",
        now
    ),
    (
        "t_aura_09",
        "[AuraTrader] UI Angular de Backtesting: Dashboard de Comparação Visual de Estratégias",
        """## Objetivo
Criar interface na aplicação Angular (ui/) para selecionar estratégias, executar simulações históricas e comparar a rentabilidade em gráficos e tabelas.

## Critérios de Aceitação (ACs)
- AC1: Serviço Angular BacktestService consumindo a API .NET 9 de backtesting.
- AC2: Formulário com seleção de par (BTC, ETH), estratégia e período histórico.
- AC3: Cartões visuais de KPIs com indicação verde/vermelho para P&L e Drawdown.
- AC4: Gráfico de Curva de Capital (Equity Curve) usando Chart.js e tabela detalhada de trades.
- AC5: Botão "Comparar Estratégias" exibindo ranking de rentabilidade comparativa.
- AC6: Branch isolada feat/t_aura_09 e PR aberto com identidade athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        3,
        "cripto-bot-2",
        now
    ),
    (
        "t_aura_10",
        "[AuraTrader] Multi-Strategy Dry-Run no Worker & Auditoria Consolidada",
        """## Objetivo
Habilitar o AuraTrader.Worker a executar múltiplas estratégias em modo Paper Trading ao vivo em simultâneo com sub-carteiras virtuais segregadas.

## Critérios de Aceitação (ACs)
- AC1: Tagging de ordens e posições de paper trading com o identificador da estratégia geradora.
- AC2: Filtro de resumo de carteira por estratégia em /api/PaperTrading/summary.
- AC3: Suite de testes completa com cobertura > 85% nos componentes de análise e simulação.
- AC4: Relatório final de sprint consolidado com evidências de execução.
- AC5: Branch isolada feat/t_aura_10 e PR aberto com identidade athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        4,
        "cripto-bot-2",
        now
    )
]

for t in tasks:
    cursor.execute("""
    INSERT OR REPLACE INTO tasks (id, title, body, status, priority, project_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, t)

conn.commit()
print(f"5 tarefas do CriptoBot2 / Aura Trader inseridas com sucesso no kanban em: {db_path}")
conn.close()
