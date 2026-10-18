# Athos — Playbook do Loop Autónomo e Estabilidade na VPS

Guia operacional para manter o **Athos** autónomo, estável e com custo zero (**bootstrapping estrito**), operando dentro do **Hermes Agent** na VPS Debian 12 do Ricardo Varzim.

---

## 1. Passo Imediato na VPS: Resolver o Drift de Modelo no Cron

O cron job de auto-review de PRs (`f5bc8e03056d`) acumulou falhas porque o modelo original (`stepfun/step-3.7-flash:free`) ficou dessincronizado do modelo ativo na plataforma Nous (`upstage/solar-pro4:free`).

### Comandos de Recuperação (Executar na VPS via SSH):

```bash
# 1. Fazer o pin explícito do cron job com o modelo free ativo do Nous
hermes cron edit f5bc8e03056d --provider nous --model upstage/solar-pro4:free

# 2. Verificar o estado de todos os cron jobs
hermes cron list

# 3. Testar a execução manual do script de PR review para garantir que passa
python3 ~/.hermes/scripts/pr-auto-review.py
```

---

## 2. Instalação do Script do Loop Autónomo

O script [`autonomous-loop.py`](scripts/autonomous-loop.py) permite ao Athos:
1. Ler a próxima tarefa prioritária em `todo` no `~/.hermes/kanban.db`.
2. Mover a tarefa para `in_progress` e despachar o specialist **`dev`** (`athoagent-oss`) para codificar, rodar testes locais e abrir PR.
3. Mover a tarefa para `in_review` e despachar o specialist **`reviewer`** para auditar diffs e validar CI.
4. Mover a tarefa para `done` e enviar relatório executivo com o link do PR para o **Telegram** do Ricardo.

### Instalação na VPS:

```bash
# Copiar o script para a pasta de scripts do Hermes
cp /home/ricardo-varzim/dev/playbooks/scripts/autonomous-loop.py ~/.hermes/scripts/autonomous-loop.py
chmod +x ~/.hermes/scripts/autonomous-loop.py

# Testar uma execução manual de verificação
python3 ~/.hermes/scripts/autonomous-loop.py
```

---

## 3. Agendamento do Loop Autónomo no Hermes

Para permitir que o Athos execute tarefas planeadas de forma programada:

```bash
# Exemplo: Agendar o loop autónomo para correr nos dias de semana às 10:00 e 15:00 UTC
hermes cron add \
  --name "athos-autonomous-execution" \
  --schedule "0 10,15 * * 1-5" \
  --command "python3 ~/.hermes/scripts/autonomous-loop.py"
```

---

## 4. Regras Cardeais de Governança e Segurança

1. **Bootstrapping Estrito**: Zero custos. Usar apenas modelos gratuitos (`upstage/solar-pro4:free` no Nous e endpoints `:free` no OpenRouter se adicionado).
2. **Dupla Identidade GitHub**: O script despacha o `dev` sob `athoagent-oss`. O `RicardoVarzim` é o revisor e aprovador final no GitHub.
3. **Limite de 10 Cartões**: O Athos nunca cria mais de 10 cartões ativos no Kanban.
4. **Arquivo Manual**: *Done fica Done*. O Ricardo é o único que arquiva tarefas terminadas.
