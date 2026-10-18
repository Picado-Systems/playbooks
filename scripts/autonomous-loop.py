#!/usr/bin/env python3
"""
Athos Autonomous Execution Loop
===============================
Ciclo de autonomia do Athos no runtime Hermes Agent na VPS Debian 12.
Princípios:
- Custo zero / Bootstrapping estrito (modelos gratuitos Nous / OpenRouter free).
- Seleciona tarefas pré-planeadas do Kanban (~/.hermes/kanban.db).
- Despacha o especialista `dev` para implementar em branch dedicada e abrir PR como athoagent-oss.
- Despacha o especialista `reviewer` para auditar diffs e validar CI.
- Reporta resumo executivo no bot do Telegram do Ricardo.
"""

import os
import sys
import sqlite3
import subprocess
import json
import logging
from datetime import datetime
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
    """Envia notificação executiva para o Telegram se configurado."""
    try:
        # Tenta carregar credenciais do Telegram do .env se existirem
        token, chat_id = None, None
        if HERMES_ENV.exists():
            with open(HERMES_ENV) as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.strip().split("=", 1)[1].strip('"\'')
                    elif line.startswith("TELEGRAM_CHAT_ID="):
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
            # Fallback usando tool interna do Hermes
            run_command(f'hermes chat -q "Envia mensagem ao Ricardo no Telegram: {message}"', timeout=60)
    except Exception as e:
        logging.warning(f"Não foi possível enviar mensagem Telegram: {e}")

def get_next_kanban_task():
    """Lê a próxima tarefa priorizada em 'todo' da base de dados kanban.db."""
    if not KANBAN_DB.exists():
        logging.error(f"Kanban DB não encontrada em {KANBAN_DB}")
        return None

    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    
    # Inspeciona tabelas e campos existentes
    try:
        cursor.execute("SELECT id, title, description, priority, project FROM tasks WHERE status = 'todo' ORDER BY priority DESC, id ASC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "description": row[2] or "",
                "priority": row[3],
                "project": row[4] or "portfolio"
            }
    except sqlite3.OperationalError:
        # Fallback para schema alternativo comum no Hermes
        try:
            cursor.execute("SELECT id, title, description FROM cards WHERE column = 'todo' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"id": row[0], "title": row[1], "description": row[2] or "", "priority": "P0", "project": "portfolio"}
        except Exception as e:
            logging.error(f"Falha ao consultar kanban.db: {e}")
            conn.close()
    
    return None

def update_task_status(task_id, new_status):
    """Atualiza o estado de uma tarefa no Kanban do Hermes."""
    logging.info(f"Atualizando tarefa {task_id} para {new_status}...")
    try:
        run_command(f"hermes kanban move {task_id} {new_status}", timeout=30)
    except Exception:
        # Fallback direto em SQLite se CLI não tiver subcomando move
        try:
            conn = sqlite3.connect(KANBAN_DB)
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Erro ao atualizar status direto na BD: {e}")

def main():
    logging.info("=== Iniciando Ciclo Autónomo do Athos ===")
    
    # 1. Obter próxima tarefa do Kanban
    task = get_next_kanban_task()
    if not task:
        logging.info("Nenhuma tarefa pendente ('todo') no Kanban. Ciclo concluído.")
        return

    task_id = task["id"]
    task_title = task["title"]
    task_desc = task["description"]
    project = task["project"]

    logging.info(f"Tarefa selecionada: [{task_id}] {task_title} (Projeto: {project})")

    # 2. Transitar para 'in_progress'
    update_task_status(task_id, "in_progress")

    # 3. Despachar specialist 'dev'
    dev_prompt = (
        f"Tu és o specialist 'dev' do Athos. Trabalha na identidade 'athoagent-oss'.\n"
        f"Tarefa: [{task_id}] {task_title}\n"
        f"Contexto/ACs:\n{task_desc}\n\n"
        f"Instruções:\n"
        f"1. Acede ao repositório '{project}'.\n"
        f"2. Cria uma branch isolada feat/{task_id}.\n"
        f"3. Implementa a solução respeitando os Critérios de Aceitação e corre os testes locais.\n"
        f"4. Faz commit e abre o Pull Request no GitHub como 'athoagent-oss'.\n"
        f"5. Retorna no final o link/número do PR aberto e o resumo de testes."
    )

    try:
        logging.info("Despachando specialist 'dev'...")
        dev_output = run_command(f'hermes chat -p dev -q "{dev_prompt}"', timeout=600)
        logging.info("Dev concluiu o trabalho.")
    except Exception as e:
        error_msg = f"⚠️ *Athos Alerta de Bloqueio:* Falha no specialist dev para a tarefa `{task_id}`: {e}"
        send_telegram_alert(error_msg)
        update_task_status(task_id, "blocked")
        return

    # 4. Transitar para 'in_review'
    update_task_status(task_id, "in_review")

    # 5. Despachar specialist 'reviewer'
    rev_prompt = (
        f"Tu és o specialist 'reviewer' do Athos. Avalia a entrega do dev para a tarefa [{task_id}] {task_title}.\n"
        f"Evidência do Dev:\n{dev_output}\n\n"
        f"Instruções:\n"
        f"1. Inspeciona o Pull Request aberto.\n"
        f"2. Valida o CI e os diffs de código contra regressões e segurança.\n"
        f"3. Comenta no PR com a tua auditoria e recomenda aprovação ao RicardoVarzim.\n"
        f"4. Retorna o veredito final (APROVADO ou PEDE_ALTERACOES)."
    )

    try:
        logging.info("Despachando specialist 'reviewer'...")
        rev_output = run_command(f'hermes chat -p reviewer -q "{rev_prompt}"', timeout=400)
        logging.info("Reviewer concluiu a auditoria.")
    except Exception as e:
        logging.error(f"Erro na fase de review: {e}")
        rev_output = "Review pendente de validação manual."

    # 6. Marcar como 'done' (aguarda arquivo final pelo Ricardo)
    update_task_status(task_id, "done")

    # 7. Notificação Executiva no Telegram
    telegram_summary = (
        f"🤖 *Athos — Tarefa Concluída com Sucesso!*\n\n"
        f"📌 *Tarefa:* `{task_title}` (`{task_id}`)\n"
        f"📁 *Projeto:* `{project}`\n\n"
        f"🛠️ *Resumo Dev:*\n{dev_output[-300:]}\n\n"
        f"🔍 *Revisão (reviewer):*\n{rev_output[-300:]}\n\n"
        f"👉 O PR está pronto no GitHub para o teu review final e merge!"
    )
    send_telegram_alert(telegram_summary)
    logging.info("=== Ciclo Autónomo do Athos Concluído com Sucesso ===")

if __name__ == "__main__":
    main()
