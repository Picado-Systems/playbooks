#!/usr/bin/env python3
"""
Briefing Executivo Matinal — Athos (morning-briefing.py)
=======================================================
Gera o relatório diário consolidado para o Ricardo Varzim (Solo Founder)
diretamente da base de dados Kanban e do calendário de ondas.
Executa em milissegundos sem sobrecarga de subprocessos.
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

KANBAN_DB = Path.home() / ".hermes/kanban.db"
WAVES_FILE = Path.home() / ".hermes/waves.json"

SPECIALISTS = ("dev", "reviewer", "pm", "business", "auditor")
FOCUS = ("ready", "in_progress", "in_review", "blocked", "done")

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = int(now.timestamp() - 86400)

    by_status = {}
    blocked_tasks = []
    specialist_activity = {p: [] for p in SPECIALISTS}

    if KANBAN_DB.exists():
        try:
            conn = sqlite3.connect(KANBAN_DB)
            cursor = conn.cursor()

            # 1. Contagem por status
            status_rows = cursor.execute("SELECT status, count(*) FROM tasks GROUP BY status").fetchall()
            by_status = {r[0]: r[1] for r in status_rows}

            # 2. Tarefas bloqueadas
            blocked_rows = cursor.execute(
                "SELECT id, assignee, title, last_failure_error FROM tasks WHERE status = 'blocked'"
            ).fetchall()
            blocked_tasks = blocked_rows

            # 3. Atividade recente dos especialistas (últimas 24h)
            try:
                run_rows = cursor.execute(
                    "SELECT r.profile, r.task_id, r.outcome, r.status, t.title "
                    "FROM task_runs r JOIN tasks t ON r.task_id = t.id "
                    "WHERE r.started_at >= ? ORDER BY r.started_at ASC",
                    (cutoff,)
                ).fetchall()
                for prof, tid, outcome, status, title in run_rows:
                    if prof in specialist_activity:
                        res = outcome or status or "executado"
                        specialist_activity[prof].append(f"`{tid}` ({res}): {title}")
            except Exception:
                pass

            conn.close()
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao ler kanban.db: {e}")

    # Output do Briefing Formatado
    print(f"☀️ *Briefing Executivo Matinal — {now.date().isoformat()}* (Athos → Ricardo)")
    print()
    print("📊 *1. Estado do Kanban*")
    for st in FOCUS:
        count = by_status.get(st, 0)
        icon = "🟢" if st == "done" else ("🔴" if st == "blocked" else ("🟡" if st in ("in_progress", "in_review") else "⚪"))
        print(f"  {icon} *{st.upper()}:* {count}")
    extra = {k: v for k, v in sorted(by_status.items()) if k not in FOCUS and v}
    if extra:
        print("  outros: " + ", ".join(f"{k}={v}" for k, v in extra.items()))

    print()
    print("🚨 *2. Tarefas Bloqueadas (Decisão Necessária)*")
    if not blocked_tasks:
        print("  ✅ Nenhum bloqueio ativo no sistema.")
    else:
        for tid, assignee, title, err in blocked_tasks:
            reason = err or "Aguardando intervenção manual / decisão"
            assignee_str = f"@{assignee}" if assignee else "@founder"
            print(f"  • `{tid}` {assignee_str}: *{title}*")
            print(f"    Motivo: {reason}")

    print()
    print("⚡ *3. Atividade Recente dos Especialistas (24h)*")
    for prof in SPECIALISTS:
        runs = specialist_activity.get(prof, [])
        print(f"  • *{prof.capitalize()}:*")
        if runs:
            for ln in runs[-4:]:
                print(f"    - {ln}")
        else:
            print("    - idle")

    print()
    print("🌊 *4. Calendário de Ondas Autónomas*")
    try:
        if WAVES_FILE.exists():
            waves_data = json.loads(WAVES_FILE.read_text())
            waves = waves_data.get("waves", [])
            def parse_dt(s):
                dt = datetime.datetime.fromisoformat(s)
                return dt.replace(tzinfo=datetime.timezone.utc) if dt.tzinfo is None else dt

            upcoming = [
                w for w in waves
                if w.get("status") == "scheduled" and parse_dt(w["scheduled_at"]) > now
            ]
            if upcoming:
                w = sorted(upcoming, key=lambda x: parse_dt(x["scheduled_at"]))[0]
                dt = parse_dt(w["scheduled_at"])
                delta = dt - now
                h, rem = divmod(int(delta.total_seconds()), 3600)
                m, _ = divmod(rem, 60)
                print(f"  • Próxima onda: `{w['id']}` em {h}h {m}m ({w['scheduled_at']} UTC)")
                print(f"    Projeto: *{w['project']}* ({w['duration_hours']}h) — {w.get('goals')}")
            else:
                print("  • Nenhuma onda futura agendada.")
    except Exception as e:
        print(f"  • Erro ao ler waves.json: {e}")

if __name__ == "__main__":
    main()
