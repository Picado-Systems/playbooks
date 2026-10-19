import sqlite3
import pathlib
import datetime

conn = sqlite3.connect(pathlib.Path.home() / ".hermes/kanban.db")
cursor = conn.cursor()
now = datetime.datetime.utcnow().isoformat()

tasks = [
    (
        "t_padel_01",
        "[PadelSync] Engine de Torneio Americano: rotacão de parceiros e ranking individual",
        """## Objetivo
Implementar o algoritmo de torneio no formato Americano em server/src/domain/tournament/americanoEngine.ts.

## Critérios de Aceitação (ACs)
- AC1: Função pura de emparelhamento rotativo para 8 e 12 jogadores (garantindo parceiros únicos por ronda).
- AC2: Cálculo de pontuação e ranking individual acumulado por jogador.
- AC3: Testes unitários Jest cobrindo 7 rondas completas para 8 jogadores.
- AC4: Branch isolada feat/t_padel_01 e PR aberto como athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        0,
        "padelsync",
        now
    ),
    (
        "t_padel_02",
        "[PadelSync] Endpoint público de consulta de torneio sem autenticação",
        """## Objetivo
Permitir visualização pública e partilha de torneios via WhatsApp sem necessidade de login.

## Critérios de Aceitação (ACs)
- AC1: Rota GET /api/tournaments/:slug/public no backend.
- AC2: Sanitização de dados sensíveis (sem emails ou hashes de password).
- AC3: Teste de integração validando resposta HTTP 200 sem JWT.
- AC4: Branch isolada feat/t_padel_02 e PR aberto como athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        1,
        "padelsync",
        now
    ),
    (
        "t_padel_03",
        "[PadelSync] Utilitário de temporizador de ronda e buzzer sonoro",
        """## Objetivo
Utilitário de contagem decrescente com estados para rondas de torneio com tempo fixo.

## Critérios de Aceitação (ACs)
- AC1: Utilitário de countdown com estados running, paused, finished.
- AC2: Testes unitários validando transições e callbacks de fim de tempo.
- AC3: Branch isolada feat/t_padel_03 e PR aberto como athoagent-oss.

REGRA DO FUNDADOR: Proibido merge na main e proibido deploy.""",
        "todo",
        2,
        "padelsync",
        now
    )
]

for t in tasks:
    cursor.execute("INSERT OR REPLACE INTO tasks (id, title, body, status, priority, project_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", t)

conn.commit()
print("3 tarefas do PadelSync inseridas com sucesso no kanban.db")
conn.close()
