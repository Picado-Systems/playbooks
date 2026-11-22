#!/usr/bin/env python3
"""
Athos Wave Runner
=================
Executa uma onda agendada e atualiza o estado em waves.json e Telegram.
Pode ser executado com:
  python3 wave-runner.py --wave-id wave_01
Ou sem argumentos (modo daemon / scheduler check para disparar ondas devidas).
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

WAVES_FILE = Path.home() / ".hermes/waves.json"
SCRIPTS_DIR = Path.home() / ".hermes/scripts"
LOOP_SCRIPT = SCRIPTS_DIR / "autonomous-loop.py"
LOG_DIR = Path.home() / ".hermes/logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WAVE-RUNNER] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "waves.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def send_telegram(message):
    try:
        env_file = Path.home() / ".hermes/.env"
        token, chat_id = None, None
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip("\"'")
                elif line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("TELEGRAM_HOME_CHANNEL="):
                    chat_id = line.split("=", 1)[1].strip("\"'")
        if token and chat_id:
            import urllib.request, urllib.parse
            data = urllib.parse.urlencode({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
            urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=10)
    except Exception as e:
        logging.warning(f"Erro ao enviar Telegram: {e}")

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

def run_specific_wave(wave_id):
    data = load_waves()
    waves = data.get("waves", [])
    target = None
    for w in waves:
        if w["id"] == wave_id:
            target = w
            break

    if not target:
        logging.error(f"Onda '{wave_id}' não encontrada.")
        return False

    project = target.get("project", "padelsync")
    hours = float(target.get("duration_hours", 1.5))
    goals = target.get("goals", "")

    logging.info(f"Iniciando execução da onda [{wave_id}] para o projeto '{project}' ({hours}h)...")
    target["status"] = "running"
    target["started_at"] = datetime.utcnow().isoformat()
    save_waves(data)

    start_msg = (
        f"🌊 *[Athos Wave] Iniciando Onda Agendada: `{wave_id}`*\n\n"
        f"📁 *Projeto:* `{project}`\n"
        f"⏱️ *Timebox:* `{hours}h`\n"
        f"🎯 *Objetivos:* {goals}\n\n"
        f"O loop autónomo e os especialistas entraram em ação."
    )
    send_telegram(start_msg)

    # Executa o autonomous-loop
    cmd = [sys.executable, str(LOOP_SCRIPT), "--timebox-hours", str(hours), "--project", project]
    log_file = LOG_DIR / f"wave-{wave_id}.log"

    try:
        with open(log_file, "w") as out_f:
            res = subprocess.run(cmd, stdout=out_f, stderr=subprocess.STDOUT)
        
        # Recarrega waves após término
        data = load_waves()
        for w in data.get("waves", []):
            if w["id"] == wave_id:
                w["status"] = "completed" if res.returncode == 0 else "failed"
                w["completed_at"] = datetime.utcnow().isoformat()
                break
        save_waves(data)
        logging.info(f"Onda [{wave_id}] finalizada com código {res.returncode}.")
        return True
    except Exception as e:
        logging.error(f"Erro fatal na execução da onda [{wave_id}]: {e}")
        data = load_waves()
        for w in data.get("waves", []):
            if w["id"] == wave_id:
                w["status"] = "failed"
                w["error"] = str(e)
                break
        save_waves(data)
        return False

def check_and_run_due_waves():
    """Modo daemon/cron: verifica se há alguma onda agendada cuja hora já passou e dispara."""
    data = load_waves()
    waves = data.get("waves", [])
    now = datetime.utcnow()

    # Não dispara se já houver uma onda a correr
    running = [w for w in waves if w.get("status") == "running"]
    if running:
        logging.info(f"Já existe uma onda a correr ({running[0]['id']}). Aguardando término.")
        return

    for w in sorted(waves, key=lambda x: x.get("scheduled_at", "")):
        if w.get("status") == "scheduled":
            sched_dt = datetime.fromisoformat(w["scheduled_at"])
            # Se a hora agendada estiver no passado até 30 minutos atrás
            diff_seconds = (now - sched_dt).total_seconds()
            if 0 <= diff_seconds <= 1800:
                logging.info(f"Onda devida encontrada: [{w['id']}] agendada para {w['scheduled_at']}. Disparando...")
                run_specific_wave(w["id"])
                break

def main():
    parser = argparse.ArgumentParser(description="Athos Wave Runner")
    parser.add_argument("--wave-id", help="Executar uma onda específica por ID")
    parser.add_argument("--check", action="store_true", help="Verificar e executar ondas devidas (cron tick)")
    args = parser.parse_args()

    if args.wave_id:
        run_specific_wave(args.wave_id)
    else:
        check_and_run_due_waves()

if __name__ == "__main__":
    main()
