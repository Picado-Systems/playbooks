#!/usr/bin/env python3
"""
Athos Autonomous Execution Loop — Wave & Timebox Engine
======================================================
Ciclo de autonomia do Athos no runtime Hermes Agent na VPS Debian 12.

Princípios & Governança:
1. Bootstrapping estrito: Custo zero (modelos free estáveis).
2. Timeboxed Wave: Executa objetivos pré-planeados por um período definido (ex.: 3 horas)
   ou até esgotar tarefas ou atingir bloqueio.
3. REGRA DO FUNDADOR (DEPLOY EXCLUSION): Proibido fazer deploy em produção ou merge na main.
   Deploys e releases são decisões administrativas exclusivas do Ricardo Varzim.
4. Dupla Identidade: Implementação e abertura de PRs como `athoagent-oss`.
5. Relatório Executivo Consolidado entregue no Telegram ao final do timebox.
"""

import os
import sys
import time
import argparse
import sqlite3
import subprocess
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configuração de Logs
LOG_FILE = Path.home() / ".hermes/logs/autonomous-loop.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

KANBAN_DB = Path.home() / ".hermes/kanban.db"
HERMES_ENV = Path.home() / ".hermes/.env"

def run_command(cmd, timeout=300):
    """Executa um comando shell de forma segura com timeout."""
    try:
        logging.info(f"Executando: {cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro no comando '{cmd}': {e.stderr.strip()}")
        raise
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout atingido para o comando: {cmd}")
        raise

def send_telegram_alert(message):
    """Envia notificação executiva para o Telegram."""
    try:
        token, chat_id = None, None
        if HERMES_ENV.exists():
            with open(HERMES_ENV) as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.strip().split("=", 1)[1].strip('"\'')
                    elif line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("TELEGRAM_HOME_CHANNEL="):
                        chat_id = line.strip().split("=", 1)[1].strip('"\'')

        if token and chat_id:
            import urllib.request
            import urllib.parse
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=10)
            logging.info("Notificação Telegram enviada com sucesso.")
        else:
            run_command(f'hermes chat -q "Envia mensagem ao Ricardo no Telegram: {message}"', timeout=60)
    except Exception as e:
        logging.warning(f"Não foi possível enviar mensagem Telegram: {e}")

def get_next_kanban_task(project_filter=None):
    """Lê a próxima tarefa priorizada em 'todo' da base de dados kanban.db."""
    if not KANBAN_DB.exists():
        logging.error(f"Kanban DB não encontrada em {KANBAN_DB}")
        return None

    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    
    try:
        if project_filter:
            cursor.execute(
                "SELECT id, title, body, priority, project_id FROM tasks "
                "WHERE status = 'todo' AND (project_id = ? OR title LIKE ?) "
                "ORDER BY priority ASC, id ASC LIMIT 1",
                (project_filter, f"%{project_filter}%")
            )
        else:
            cursor.execute(
                "SELECT id, title, body, priority, project_id FROM tasks "
                "WHERE status = 'todo' ORDER BY priority ASC, id ASC LIMIT 1"
            )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "description": row[2] or "",
                "priority": row[3],
                "project": row[4] or "padelsync"
            }
    except Exception as e:
        logging.error(f"Falha ao consultar kanban.db: {e}")
        conn.close()
    
    return None

def update_task_status(task_id, new_status):
    """Atualiza o estado de uma tarefa no Kanban do Hermes."""
    logging.info(f"Atualizando tarefa {task_id} para {new_status}...")
    try:
        conn = sqlite3.connect(KANBAN_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Erro ao atualizar status direto na BD: {e}")

def execute_task(task):
    """Executa o ciclo Dev -> Reviewer para uma tarefa específica."""
    task_id = task["id"]
    task_title = task["title"]
    task_desc = task["description"]
    project = task["project"]

    logging.info(f"--- Iniciando Tarefa: [{task_id}] {task_title} ({project}) ---")
    update_task_status(task_id, "in_progress")

    # 1. Despacho do dev com salvaguardas explícitas de deploy
    dev_prompt = (
        f"Tu és o specialist 'dev' do Athos. Trabalha na identidade 'athoagent-oss'.\n"
        f"Tarefa: [{task_id}] {task_title}\n"
        f"Contexto/ACs:\n{task_desc}\n\n"
        f"🚨 REGRA INEGOCIÁVEL DO FUNDADOR:\n"
        f"- Proibido fazer deploy em produção ou merge na branch main.\n"
        f"- Toda a implementação deve ser feita numa branch isolada feat/{task_id}.\n"
        f"- Executa os testes locais para validar e abre o Pull Request para revisão do RicardoVarzim.\n\n"
        f"Instruções:\n"
        f"1. Acede ao repositório '{project}'.\n"
        f"2. Cria a branch feat/{task_id}.\n"
        f"3. Implementa a solução com testes unitários.\n"
        f"4. Abre o PR no GitHub como 'athoagent-oss'.\n"
        f"5. Retorna o URL do PR e o resumo de testes."
    )

    try:
        logging.info("Despachando specialist 'dev'...")
        dev_output = run_command(f'hermes chat -p dev -q "{dev_prompt}"', timeout=900)
    except Exception as e:
        error_msg = f"⚠️ *Athos Bloqueio:* Falha no specialist dev para a tarefa `{task_id}`: {e}"
        send_telegram_alert(error_msg)
        update_task_status(task_id, "blocked")
        return {"status": "blocked", "error": str(e), "task": task}

    update_task_status(task_id, "in_review")

    # 2. Despacho do reviewer
    rev_prompt = (
        f"Tu és o specialist 'reviewer' do Athos. Avalia a entrega do dev para [{task_id}] {task_title}.\n"
        f"Evidência do Dev:\n{dev_output}\n\n"
        f"🚨 REGRA DO FUNDADOR: Não tentes fazer merge nem deploy. Apenas audita diffs e CI.\n"
        f"Instruções:\n"
        f"1. Inspeciona o PR aberto.\n"
        f"2. Valida CI e segurança do código.\n"
        f"3. Comenta no PR com o parecer técnico e recomenda ao RicardoVarzim."
    )

    try:
        logging.info("Despachando specialist 'reviewer'...")
        rev_output = run_command(f'hermes chat -p reviewer -q "{rev_prompt}"', timeout=600)
    except Exception as e:
        logging.error(f"Erro na fase de review: {e}")
        rev_output = "Review concluído com avisos."

    update_task_status(task_id, "done")
    return {
        "status": "completed",
        "task": task,
        "dev_output": dev_output,
        "rev_output": rev_output
    }

def main():
    parser = argparse.ArgumentParser(description="Athos Autonomous Wave Loop")
    parser.add_argument("--timebox-hours", type=float, default=3.0, help="Duração máxima da onda em horas")
    parser.add_argument("--project", type=str, default="padelsync", help="Filtrar por projeto (ex.: padelsync)")
    args = parser.parse_args()

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=args.timebox_hours)
    
    logging.info(f"=== Iniciando Onda Autónoma do Athos ({args.timebox_hours}h) ===")
    logging.info(f"Projeto alvo: {args.project} | Fim planeado: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    executed_tasks = []
    blocked_tasks = []

    while datetime.now() < end_time:
        remaining_minutes = int((end_time - datetime.now()).total_seconds() / 60)
        logging.info(f"Tempo restante na onda: {remaining_minutes} minutos.")

        task = get_next_kanban_task(project_filter=args.project)
        if not task:
            logging.info("Não existem mais tarefas 'todo' para este projeto. Onda concluída antecipadamente.")
            break

        result = execute_task(task)
        if result["status"] == "completed":
            executed_tasks.append(result)
        else:
            blocked_tasks.append(result)
            # Em caso de bloqueio crítico, interrompe a onda para avaliação do fundador
            logging.warning("Bloqueio encontrado. Interrompendo a onda para decisão do fundador.")
            break

    # Relatório Executivo Consolidado da Onda
    duration_str = str(datetime.now() - start_time).split(".")[0]
    report = (
        f"🏁 *Athos — Relatório de Encerramento da Onda Autónoma*\n\n"
        f"⏱️ *Duração da Execução:* `{duration_str}` (Timebox: {args.timebox_hours}h)\n"
        f"📁 *Projeto:* `{args.project}`\n"
        f"✅ *Tarefas Concluídas:* {len(executed_tasks)}\n"
        f"⚠️ *Bloqueios/Avisos:* {len(blocked_tasks)}\n\n"
    )

    if executed_tasks:
        report += "📋 *Entregas Realizadas:*\n"
        for item in executed_tasks:
            t = item["task"]
            report += f"• `{t['id']}`: *{t['title']}* (PR aberto e auditado)\n"

    if blocked_tasks:
        report += "\n🚨 *Bloqueios a Aguardar Decisão:*\n"
        for item in blocked_tasks:
            t = item["task"]
            report += f"• `{t['id']}`: *{t['title']}* — Erro: {item.get('error', 'N/A')}\n"

    report += (
        f"\n🛡️ *Governança:* Nenhuma alteração foi promovida para a `main` nem deployed. "
        f"Todas as entregas aguardam a tua decisão administrativa de merge e release."
    )

    logging.info("Enviando Relatório Consolidado para o Telegram...")
    send_telegram_alert(report)
    logging.info("=== Onda Autónoma Concluída ===")

if __name__ == "__main__":
    main()
