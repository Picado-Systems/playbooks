#!/usr/bin/env python3
"""
Athos Wave Scheduler & Manager (athos-wave)
===========================================
Gestão e agendamento temporal de ondas de trabalho autónomo do Athos.

Comandos:
  athos-wave list                  Lista todas as ondas agendadas dos 5 dias
  athos-wave status                Exibe estado da onda corrente e próxima onda
  athos-wave add                   Agenda uma nova onda
  athos-wave edit <id>             Edita horário, projeto ou objetivos de uma onda
  athos-wave cancel <id>           Cancela uma onda agendada
  athos-wave run <id>              Executa uma onda imediatamente
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WAVES_FILE = Path.home() / ".hermes/waves.json"
SCRIPTS_DIR = Path.home() / ".hermes/scripts"
HERMES_BIN = Path.home() / ".local/bin/hermes"
PYTHON_BIN = sys.executable

def load_waves():
    if not WAVES_FILE.exists():
        return {"waves": []}
    try:
        with open(WAVES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"waves": []}

def save_waves(data):
    WAVES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WAVES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def list_waves():
    data = load_waves()
    waves = data.get("waves", [])
    if not waves:
        print("\n📭 Nenhuma onda agendada.")
        return

    print("\n" + "=" * 90)
    print(f"🌊 ATHOS — CALENDÁRIO DE ONDAS AUTÓNOMAS (Próximos 5 Dias)")
    print("=" * 90)
    print(f"{'ID':<10} {'Data / Hora (UTC)':<20} {'Projeto':<16} {'Duração':<10} {'Estado':<12} {'Objetivo Principal'}")
    print("-" * 90)

    now = datetime.utcnow()
    for w in sorted(waves, key=lambda x: x.get("scheduled_at", "")):
        wid = w.get("id", "N/A")
        sched = w.get("scheduled_at", "N/A")
        proj = w.get("project", "N/A")
        dur = f"{w.get('duration_hours', 1.5)}h"
        st = w.get("status", "scheduled")
        goals = w.get("goals", "")
        if isinstance(goals, list):
            goals = "; ".join(goals)
        if len(goals) > 28:
            goals = goals[:25] + "..."

        st_icon = "⏳"
        if st == "completed":
            st_icon = "✅"
        elif st == "running":
            st_icon = "🚀"
        elif st == "blocked" or st == "failed":
            st_icon = "❌"
        elif st == "cancelled":
            st_icon = "🚫"

        print(f"{wid:<10} {sched:<20} {proj:<16} {dur:<10} {st_icon} {st:<9} {goals}")

    print("=" * 90)
    print("Dica: Executa 'athos-wave edit <id> --time HH:MM' para alterar horários.")
    print("Dica: Executa 'athos-wave run <id>' para disparar uma onda fora de hora.\n")

def show_status():
    data = load_waves()
    waves = data.get("waves", [])
    now = datetime.utcnow()

    running = [w for w in waves if w.get("status") == "running"]
    upcoming = [w for w in waves if w.get("status") == "scheduled" and datetime.fromisoformat(w["scheduled_at"]) > now]
    upcoming = sorted(upcoming, key=lambda x: x["scheduled_at"])

    print("\n=== Estado Atual das Ondas do Athos ===")
    if running:
        w = running[0]
        print(f"🚀 ONDA ATIVA: [{w['id']}] Projeto: {w['project']} | Duração: {w['duration_hours']}h")
        print(f"   Objetivos: {w.get('goals')}")
    else:
        print("💤 Nenhuma onda a correr no momento.")

    if upcoming:
        w = upcoming[0]
        dt = datetime.fromisoformat(w["scheduled_at"])
        delta = dt - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"⏳ PRÓXIMA ONDA: [{w['id']}] em {hours}h {minutes}m ({w['scheduled_at']} UTC)")
        print(f"   Projeto: {w['project']} | Duração: {w['duration_hours']}h")
        print(f"   Objetivo: {w.get('goals')}")
    else:
        print("📭 Nenhuma próxima onda agendada.")
    print()

def add_wave(args):
    data = load_waves()
    waves = data.get("waves", [])
    
    # Gerar ID
    next_num = len(waves) + 1
    wid = f"wave_{next_num:02d}"

    dt_str = f"{args.date} {args.time}:00"
    try:
        dt = datetime.fromisoformat(dt_str)
    except Exception as e:
        print(f"❌ Formato de data/hora inválido: {e}. Usa YYYY-MM-DD e HH:MM.")
        return

    wave = {
        "id": wid,
        "scheduled_at": dt_str,
        "project": args.project,
        "duration_hours": args.hours,
        "goals": args.goals or "",
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat()
    }

    waves.append(wave)
    data["waves"] = waves
    save_waves(data)
    print(f"✅ Onda [{wid}] agendada com sucesso para {dt_str} UTC (Projeto: {args.project}, {args.hours}h).")

def edit_wave(args):
    data = load_waves()
    waves = data.get("waves", [])
    
    target = None
    for w in waves:
        if w["id"] == args.wave_id:
            target = w
            break

    if not target:
        print(f"❌ Onda '{args.wave_id}' não encontrada.")
        return

    if args.time or args.date:
        old_dt = datetime.fromisoformat(target["scheduled_at"])
        date_part = args.date or old_dt.strftime("%Y-%m-%d")
        time_part = args.time or old_dt.strftime("%H:%M")
        target["scheduled_at"] = f"{date_part} {time_part}:00"

    if args.project:
        target["project"] = args.project

    if args.hours:
        target["duration_hours"] = args.hours

    if args.goals:
        target["goals"] = args.goals

    if args.status:
        target["status"] = args.status

    target["updated_at"] = datetime.utcnow().isoformat()
    save_waves(data)
    print(f"✅ Onda [{args.wave_id}] atualizada com sucesso:")
    print(f"   Data/Hora: {target['scheduled_at']} UTC | Projeto: {target['project']} | Duração: {target['duration_hours']}h")

def cancel_wave(args):
    data = load_waves()
    waves = data.get("waves", [])
    
    for w in waves:
        if w["id"] == args.wave_id:
            w["status"] = "cancelled"
            w["cancelled_at"] = datetime.utcnow().isoformat()
            save_waves(data)
            print(f"🚫 Onda [{args.wave_id}] cancelada.")
            return

    print(f"❌ Onda '{args.wave_id}' não encontrada.")

def run_wave(args):
    data = load_waves()
    waves = data.get("waves", [])
    
    target = None
    for w in waves:
        if w["id"] == args.wave_id:
            target = w
            break

    if not target:
        print(f"❌ Onda '{args.wave_id}' não encontrada.")
        return

    runner_script = SCRIPTS_DIR / "wave-runner.py"
    cmd = [PYTHON_BIN, str(runner_script), "--wave-id", args.wave_id]
    print(f"🚀 Disparando execução imediata da onda [{args.wave_id}] ({target['project']})...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Onda iniciada em segundo plano. Podes acompanhar via 'athos-wave status' e Telegram.")

def main():
    parser = argparse.ArgumentParser(description="Athos Wave Scheduler & Manager")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="Listar calendário de ondas")
    # status
    subparsers.add_parser("status", help="Exibir estado atual e próxima onda")

    # add
    p_add = subparsers.add_parser("add", help="Adicionar nova onda")
    p_add.add_argument("--date", required=True, help="Data da onda (YYYY-MM-DD)")
    p_add.add_argument("--time", required=True, help="Hora UTC (HH:MM)")
    p_add.add_argument("--project", required=True, help="Projeto alvo (cripto-bot-2, padelsync, raiz, etc.)")
    p_add.add_argument("--hours", type=float, default=1.5, help="Duração em horas (default: 1.5)")
    p_add.add_argument("--goals", type=str, default="", help="Descrição dos objetivos da onda")

    # edit
    p_edit = subparsers.add_parser("edit", help="Editar onda existente")
    p_edit.add_argument("wave_id", help="ID da onda (ex: wave_01)")
    p_edit.add_argument("--date", help="Nova data (YYYY-MM-DD)")
    p_edit.add_argument("--time", help="Nova hora UTC (HH:MM)")
    p_edit.add_argument("--project", help="Novo projeto alvo")
    p_edit.add_argument("--hours", type=float, help="Nova duração em horas")
    p_edit.add_argument("--goals", help="Novos objetivos")
    p_edit.add_argument("--status", choices=["scheduled", "running", "completed", "cancelled", "blocked"], help="Alterar estado")

    # cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancelar onda agendada")
    p_cancel.add_argument("wave_id", help="ID da onda (ex: wave_01)")

    # run
    p_run = subparsers.add_parser("run", help="Executar onda imediatamente")
    p_run.add_argument("wave_id", help="ID da onda (ex: wave_01)")

    args = parser.parse_args()

    if not args.command or args.command == "list":
        list_waves()
    elif args.command == "status":
        show_status()
    elif args.command == "add":
        add_wave(args)
    elif args.command == "edit":
        edit_wave(args)
    elif args.command == "cancel":
        cancel_wave(args)
    elif args.command == "run":
        run_wave(args)

if __name__ == "__main__":
    main()
