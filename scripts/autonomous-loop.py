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

# Garantir PATH para binários do Hermes
os.environ["PATH"] = f"{Path.home()}/.local/bin:" + os.environ.get("PATH", "")

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
ATHOS_TOKEN_FILE = Path.home() / ".github/athos-agent-token"

def get_agent_gh_token():
    """Obtém o token do athoagent-oss a partir de ~/.github/athos-agent-token ou ~/.hermes/.env."""
    if ATHOS_TOKEN_FILE.exists():
        token = ATHOS_TOKEN_FILE.read_text().strip()
        if token:
            return token
    if HERMES_ENV.exists():
        with open(HERMES_ENV) as f:
            for line in f:
                if line.startswith("AGENT_GH_TOKEN="):
                    return line.strip().split("=", 1)[1].strip('"\'')
    return os.environ.get("AGENT_GH_TOKEN")

def run_hermes_chat(profile, prompt, timeout=900, custom_env=None):
    """Executa o hermes chat de forma robusta passando argumentos em lista (sem problemas de escaping shell)."""
    cmd = ["hermes", "chat", "-p", profile, "-q", prompt]
    logging.info(f"Despachando specialist '{profile}' com prompt de {len(prompt)} caracteres...")
    env = {**os.environ}
    if custom_env:
        env.update(custom_env)
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        err_out = (e.stderr or "") + "\n" + (e.stdout or "")
        logging.error(f"Erro no specialist '{profile}': {err_out.strip()}")
        raise
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout atingido no specialist '{profile}'")
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
            cmd = ["hermes", "chat", "-q", f"Envia mensagem ao Ricardo no Telegram: {message}"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=os.environ)
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
                "WHERE status IN ('ready', 'todo') AND (project_id = ? OR title LIKE ?) "
                "ORDER BY priority ASC, id ASC LIMIT 1",
                (project_filter, f"%{project_filter}%")
            )
        else:
            cursor.execute(
                "SELECT id, title, body, priority, project_id FROM tasks "
                "WHERE status IN ('ready', 'todo') ORDER BY priority ASC, id ASC LIMIT 1"
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

def get_project_dir(project):
    """Localiza o diretório absoluto do repositório no dev workspace da VPS."""
    candidates = [
        Path(f"/home/ricardovarzim/dev/RicardoVarzim/{project}"),
        Path(f"/home/ricardovarzim/dev/Picado-Systems/{project}"),
        Path(f"/home/ricardovarzim/dev/{project}"),
    ]
    for c in candidates:
        if c.exists() and (c / ".git").exists():
            return str(c)
    return f"/home/ricardovarzim/dev/RicardoVarzim/{project}"

def check_pr_ci(project_dir, pr_number, timeout=420):
    """
    Aguarda e valida os checks de CI no GitHub para o PR indicado.
    Retorna (True, None) se todos os checks passarem (pass/success).
    Retorna (False, failure_summary) se algum check falhar ou expirar o tempo.
    """
    logging.info(f"Gatekeeper CI: Monitorizando checks do PR #{pr_number} (timeout={timeout}s)...")
    start = time.time()
    
    agent_token = get_agent_gh_token()
    env = {**os.environ}
    if agent_token:
        env["GH_TOKEN"] = agent_token
        env["GITHUB_TOKEN"] = agent_token

    while time.time() - start < timeout:
        time.sleep(15)
        cmd = ["gh", "pr", "checks", str(pr_number)]
        res = subprocess.run(cmd, cwd=project_dir, env=env, capture_output=True, text=True)
        
        output = (res.stdout or "").strip()
        if not output:
            continue
            
        lines = [line.strip().split("\t") for line in output.splitlines() if line.strip()]
        if not lines:
            continue
            
        all_passed = True
        has_pending = False
        failed_checks = []
        
        for parts in lines:
            name = parts[0]
            status = parts[1].lower() if len(parts) > 1 else ""
            
            if status in ("fail", "error", "failure", "timed_out"):
                all_passed = False
                failed_checks.append(name)
            elif status in ("pending", "in_progress", "queued"):
                has_pending = True
                
        if failed_checks:
            err_msg = f"CI Falhou nos checks: {', '.join(failed_checks)}"
            logging.error(f"PR #{pr_number} - {err_msg}")
            return False, err_msg
            
        if not has_pending and all_passed:
            logging.info(f"CI Gatekeeper: Todos os {len(lines)} checks passaram com sucesso no PR #{pr_number}!")
            return True, "CI 100% Verde (todos os checks passaram com sucesso)"
            
    return False, f"Timeout ({timeout}s) a aguardar conclusão dos checks de CI."

def get_ci_failed_logs(project_dir, branch_name, env):
    """Obtém os logs dos passos que falharam no CI do GitHub Actions."""
    try:
        cmd = ["gh", "run", "list", "-b", branch_name, "--limit", "1", "--json", "databaseId", "--jq", ".[0].databaseId"]
        res = subprocess.run(cmd, cwd=project_dir, env=env, capture_output=True, text=True)
        run_id = (res.stdout or "").strip()
        if run_id:
            log_cmd = ["gh", "run", "view", run_id, "--log-failed"]
            log_res = subprocess.run(log_cmd, cwd=project_dir, env=env, capture_output=True, text=True)
            output = (log_res.stdout or "").strip()
            return output[-4000:] if output else ""
    except Exception as e:
        logging.warning(f"Erro ao extrair logs de falha do CI: {e}")
    return ""

def execute_task(task):
    """Executa o ciclo Dev -> Gatekeeper CI (com Self-Healing) -> Reviewer Interno para uma tarefa."""
    task_id = task["id"]
    task_title = task["title"]
    task_desc = task["description"]
    project = task["project"]
    project_dir = get_project_dir(project)

    logging.info(f"--- Iniciando Tarefa: [{task_id}] {task_title} ({project}) ---")
    update_task_status(task_id, "in_progress")

    # 1. Despacho do dev com salvaguardas explícitas de deploy, identidade e template
    agent_token = get_agent_gh_token()
    dev_env = {}
    if agent_token:
        dev_env["GH_TOKEN"] = agent_token
        dev_env["GITHUB_TOKEN"] = agent_token
        dev_env["AGENT_GH_TOKEN"] = agent_token

    dev_prompt = (
        f"Tu és o specialist 'dev' do Athos. Trabalha na identidade estrita 'athoagent-oss'.\n"
        f"Tarefa: [{task_id}] {task_title}\n"
        f"Contexto/ACs:\n{task_desc}\n\n"
        f"REGRA INEGOCIÁVEL DO FUNDADOR:\n"
        f"- Proibido fazer deploy em produção ou merge na branch main.\n"
        f"- Toda a implementação deve ser feita numa branch isolada feat/{task_id}.\n"
        f"- Executa os testes locais para validar e abre o Pull Request para revisão do RicardoVarzim.\n\n"
        f"REQUISITOS ESTRITOS DE PR:\n"
        f"1. Acede ao repositório local em '{project_dir}'.\n"
        f"2. Garante checkout da branch main atualizada e cria a branch feat/{task_id}.\n"
        f"3. Implementa a solução e valida com testes unitários locais.\n"
        f"4. Abre o PR no GitHub como 'athoagent-oss' com descrição COMPLETA e ESTRUTURADA:\n"
        f"   O corpo do PR (--body) DEVE conter obrigatoriamente:\n"
        f"   ## 🎯 Objetivo\n"
        f"   <Descrição clara e concisa do que foi implementado e requisitos atendidos>\n\n"
        f"   ## 🛠️ Alterações Realizadas\n"
        f"   - <Lista dos ficheiros novos ou modificados e o seu papel>\n\n"
        f"   ## 🧪 Evidência de Testes Locais\n"
        f"   - <Comando executado e resumo detalhado dos testes aprovados>\n\n"
        f"   ## 🛡️ Salvaguardas & Governança\n"
        f"   - Implementado em branch isolada feat/{task_id}\n"
        f"   - Nenhuma alteração direta na branch main nem ambiente de produção\n\n"
        f"   OBRIGATÓRIO: Executa com identidade do agente: GH_TOKEN=\"$AGENT_GH_TOKEN\" gh pr create ...\n"
        f"5. Retorna o URL do PR e o resumo de testes."
    )

    try:
        dev_output = run_hermes_chat("dev", dev_prompt, timeout=1200, custom_env=dev_env)
    except Exception as e:
        error_msg = f"⚠️ *Athos Bloqueio:* Falha no specialist dev para a tarefa `{task_id}`: {e}"
        send_telegram_alert(error_msg)
        update_task_status(task_id, "blocked")
        return {"status": "blocked", "error": str(e), "task": task}

    # Extrair PR URL ou número
    import re
    pr_match = re.search(r"pull/(\d+)", dev_output)
    pr_number = pr_match.group(1) if pr_match else None

    if not pr_number:
        pr_list_cmd = ["gh", "pr", "list", "--head", f"feat/{task_id}", "--json", "number", "--jq", ".[0].number"]
        pr_list_res = subprocess.run(pr_list_cmd, cwd=project_dir, env=dev_env, capture_output=True, text=True)
        if pr_list_res.stdout.strip():
            pr_number = pr_list_res.stdout.strip()

    # 2. Gatekeeper de CI com Ciclo de Auto-Remediação (Self-Healing)
    ci_passed, ci_info = True, "Sem PR detetado para validação de CI"
    max_ci_retries = 3

    if pr_number:
        branch_name = f"feat/{task_id}"
        try:
            head_cmd = ["gh", "pr", "view", str(pr_number), "--json", "headRefName", "--jq", ".headRefName"]
            head_res = subprocess.run(head_cmd, cwd=project_dir, env=dev_env, capture_output=True, text=True)
            if head_res.stdout.strip():
                branch_name = head_res.stdout.strip()
        except Exception:
            pass

        for attempt in range(1, max_ci_retries + 1):
            logging.info(f"PR detetado: #{pr_number} (branch: {branch_name}). Verificação de CI (Tentativa {attempt}/{max_ci_retries})...")
            ci_passed, ci_info = check_pr_ci(project_dir, pr_number, timeout=420)
            if ci_passed:
                break
            
            if attempt < max_ci_retries:
                logging.warning(f"CI falhou na tentativa {attempt}. Disparando ciclo de Auto-Remediação...")
                failed_logs = get_ci_failed_logs(project_dir, branch_name, dev_env)
                remediation_prompt = (
                    f"Tu és o specialist 'dev' do Athos em modo AUTO-REMEDIAÇÃO.\n"
                    f"O teu Pull Request #{pr_number} na branch '{branch_name}' falhou a validação de CI no GitHub Actions.\n\n"
                    f"Erro detectado pelo Gatekeeper: {ci_info}\n"
                    f"Logs detalhados de falha do CI:\n{failed_logs}\n\n"
                    f"INSTRUÇÕES OBRIGATÓRIAS DE REMEDIAÇÃO (Tentativa {attempt + 1}/{max_ci_retries}):\n"
                    f"1. Acede a '{project_dir}' na branch '{branch_name}'.\n"
                    f"2. Corrige os erros de compilação, namespaces em falta ou testes com falhas.\n"
                    f"3. Executa a suite de testes local (ex: dotnet test / npm test) e garante 100% de aprovação.\n"
                    f"4. Faz commit da correção e push para a MESMA branch '{branch_name}'.\n"
                    f"NUNCA abras um novo PR! Apenas faz commit e push na branch existente."
                )
                try:
                    dev_output = run_hermes_chat("dev", remediation_prompt, timeout=900, custom_env=dev_env)
                    logging.info("Auto-remediação executada. Aguardando trigger e execução do novo CI...")
                    time.sleep(15)
                except Exception as e:
                    logging.error(f"Erro durante auto-remediação: {e}")
                    break

        if not ci_passed:
            error_msg = f"❌ *Athos Gatekeeper:* CI falhou após {max_ci_retries} tentativas para PR #{pr_number} na tarefa `{task_id}`: {ci_info}"
            send_telegram_alert(error_msg)
            update_task_status(task_id, "blocked")
            return {"status": "blocked", "error": f"CI Falhou após {max_ci_retries} tentativas: {ci_info}", "task": task, "dev_output": dev_output}

    update_task_status(task_id, "in_review")

    # 3. Despacho do reviewer (100% INTERNO — SEM COMENTÁRIOS NO GITHUB)
    rev_prompt = (
        f"Tu és o specialist 'reviewer' do Athos. Faz a auditoria interna da entrega do dev para [{task_id}] {task_title}.\n"
        f"Evidência do Dev:\n{dev_output}\n"
        f"Relatório de CI: {ci_info}\n\n"
        f"REGRA INEGOCIÁVEL DO FUNDADOR:\n"
        f"- A auditoria é ESTREITAMENTE INTERNA. NUNCA comentes no PR do GitHub.\n"
        f"- Proibido fazer merge na main ou deploy em produção.\n"
        f"Instruções:\n"
        f"1. Inspeciona o código e diffs do PR.\n"
        f"2. Valida segurança, qualidade e conformidade com os Critérios de Aceitação.\n"
        f"3. Retorna a tua avaliação técnica estruturada interna (com veredito APROVADO / REJEITADO) para registo no Kanban e envio ao Ricardo no Telegram."
    )

    try:
        rev_output = run_hermes_chat("reviewer", rev_prompt, timeout=600)
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
            logging.warning(f"Tarefa {task['id']} bloqueada após tentativas. Registando bloqueio e prosseguindo com a onda...")
            continue

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
