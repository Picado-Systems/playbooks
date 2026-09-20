# Athos — Onboarding para Agentes Externos

> Documento objetivo: dá a outro agente de IA (Cursor, Codex, Antigravity, Claude Code, etc.) tudo o que precisa para interagir comigo — quem sou, o que posso, como me invocares, e o que esperar.

**Versão:** 2026-09-20  
**Revisão:** Ricardo Varzim aprova alterações.

---

## 1. Quem sou

| Campo | Valor |
|-------|-------|
| Nome | **Athos** |
| Função | Maestro de agentes — orquestro, planeio, valido entregas |
| Hospede | VPS Debian 12 do Ricardo Varzim |
| Runtimes | **Hermes Agent** (perfil `default`) + cursos Python/Node/terminal |
| Canal principal | **Telegram** (bot Athos) + CLI Hermes TUI |
| Idiomas | Pt-pt (preferido) e inglês |

**Não sou** um executor anónimo. Sou o mestre que cria profiles especialistas, lhes atribui trabalho, lê a evidência nas entregas e decide se aceito, peço alterações ou autorizo o próximo passo. Os specialists fazem o trabalho concreto; eu faço a orquestração e a qualidade.

---

## 2. O runtime: Hermes Agent

Eu corro dentro do [Hermes Agent](https://github.com/NousResearch/hermes-agent) — um framework de agentes open-source que roda em terminal, desktop, messaging platforms e IDEs, com acesso a ferramentas reais (arquivo, terminal, browser, cron, Telegram, etc.).

**Para interactuar comigo de fora, o Hermes expõe:**

### 2.1 Por CLI (local, na VPS)
```bash
# Chat interativo (TUI Ink)
hermes

# Query única (fire-and-forget)
hermes chat -q "Quem és?"

# Com um agente externo à VPS: ssh + hermes chat -q
ssh ricardovarzim@vps "hermes chat -q '...'"
```

### 2.2 Por API / proxy (para agentes remotos)

O Hermes corre um **proxy OpenAI-compatible** local:
```bash
hermes proxy   # liga um endpoint localhost compatível com a API do OpenAI
```
Qualquer cliente que fale com a API do OpenAI (Cursor, Codex, Aider, scripts Python, etc.) pode apontar para esse proxy e usar-me como modelo — **sem chave API externa**.

Endpoints relevantes:
- Chat completions (o principal — é aqui que um agente externo me dá instruções)
- ACP server para IDEs (VS Code / Zed / JetBrains)

### 2.3 Por Telegram
O canal principal é o bot do Telegram. Envia mensagens como farias a um colega. Posso executar tarefas, ler ficheiros, discutir planos, criar issues no kanban. É o canal preferido para interação assíncrona e para supervisão.

### 2.4 Models e provider
- **Modelo:** `upstage/solar-pro4:free`
- **Provider:** Nous Research (`nous` platform)
- Configurado em `~/.hermes/config.yaml` (campo `model.default`) + cache em `~/.hermes/provider_models_cache.json` e `~/.hermes/models_dev_cache.json`

### 2.5 Profiles Hermes (specialists)
O Athos corre no profile `default`. Esse profile orquestra 6 profiles especialistas, cada um com SOUL.md próprio e papel definido:

| Profile | Função | SOUL.md | Identidade escrita |
|---------|--------|---------|--------------------|
| `default` (Athos) | Maestro / orquestrador — cria, atribui e valida entregas | `~/.hermes/SOUL.md` | `athoagent-oss` |
| `auditor` | Auditoria: lacunas, dívida técnica, ownership, segurança operacional | `~/.hermes/profiles/auditor/SOUL.md` | `athoagent-oss` |
| `business` | Business Strategist: validação de mercado, Lean Canvas, monetização | `~/.hermes/profiles/business/SOUL.md` | `athoagent-oss` |
| `dev` | Programador/executor técnico: implementa código, abre PRs | `~/.hermes/profiles/dev/SOUL.md` | `athoagent-oss` |
| `pm` | Product Manager: roadmap, issues, critérios de aceitação | `~/.hermes/profiles/pm/SOUL.md` | `athoagent-oss` |
| `researcher` | Tech & Market Researcher: investigação, PoC, viabilidade | `~/.hermes/profiles/researcher/SOUL.md` | `athoagent-oss` |
| `reviewer` | Arquiteto/ gatekeeper: rever código e PRs do dev | `~/.hermes/profiles/reviewer/SOUL.md` | `athoagent-oss` |

Todos os profiles seguem a **Política de Dupla Identidade GitHub (2026-09-10)**: leitura com `GH_TOKEN` (RicardoVarzim), escrita com `AGENT_GH_TOKEN` (athoagent-oss), ativada apenas quando o cartão kanban autoriza explicitamente.

### 2.6 Kanban
- **DB:** `~/.hermes/kanban.db` (SQLite)
- **Comando:** `hermes kanban list` (e `hermes kanban add`, `hermes kanban done`, etc.)
- **Orchestrator profile:** `default` (é o Athos quem cria, atribui e valida cartões)
- **Cadência:** triage noturno (06:00 UTC) + triage da tarde (13:30 UTC) + briefing executivo matinal (07:00 UTC, weekdays)
- Máx 10 cartões ativos por vez; Done fica Done — arquivo é responsabilidade do Ricardo.

### 2.7 Cron jobs ativos
Quatro jobs agendados, todos com estado `active`:

| Job | ID | Schedule | Último run | Estado |
|-----|----|----------|------------|--------|
| briefing-executivo-matinal | `17162c077aba` | weekdays 07:00 UTC | 2026-09-18 ok | ✅ active |
| PR Auto-Review — portfolio | `f5bc8e03056d` | every 120m | 2026-09-20 **error** | ⚠️ active (drift) |
| Triage noturno — proposta de tarefas úteis antes do briefing | `c0f4ca14bece` | daily 06:00 UTC | 2026-09-20 ok | ✅ active |
| Triage da tarde — checkpoint pós-almoço (13:30 UTC) | `d415ef0c5d5f` | daily 13:30 UTC | 2026-09-20 ok | ✅ active |

O **PR Auto-Review (`f5bc8e03056d`)** está com **drift de modelo**: foi criado com `stepfun/step-3.7-flash:free` mas o config global mudou para `upstage/solar-pro4:free`. O job está unpinned e desiste de executar — 6 falhas consecutivas. Para restaurar: `hermes cron edit f5bc8e03056d --provider <provider> --model <model>` (ou re-pin o modelo original). Ver #44585.

### 2.8 Scripts de automação
- `~/.hermes/scripts/morning-briefing.py` — briefing executivo matinal
- `~/.hermes/scripts/pr-auto-review.py` — auto-review de PRs (ligado ao cron job `f5bc8e03056d`)

---

## 3. O que posso fazer

### 3.1 Ferramentas nativas do Hermes (built-in tools)
Estas são tool functions nativas do runtime Hermes — disponíveis sempre, sem precisar de carregar skill:

| Ferramenta | O que faz | Quando usar |
|------------|-----------|-------------|
| **terminal** | Executa comandos shell na VPS | Builds, instalação, clonagem, validação de configurações |
| **read_file** | Lê ficheiros com paginação | Análise de código, logs, configs, documentos |
| **write_file** / **patch** | Cria e edita ficheiros | Criar ou corrigir código, docs, configs |
| **search_files** | Procura em conteúdo e nomes de ficheiros | Encontrar código, doc, configs existentes |
| **web_search** / **web_extract** | Pesquisa na web e extrai conteúdo de páginas | Pesquisar documentação, artigos, benchmarks |
| **browser_exec** | Navegação web real via browser | Páginas que bloqueiam scrapers ou precisam de interação |
| **image_generate** / **vision_analyze** | Geração e análise de imagens | Tarefas visuais |
| **text_to_speech** | Síntese de voz | Respostas de áudio |
| **skill_view** / **skill_manage** | Carrega, inspeciona e gerencia skills | Ver catálogo, carregar skill específico antes de uma tarefa |
| **execute_code** | Executa Python com acesso às ferramentas do Hermes | Tarefas que precisam de lógica, loops, múltiplas chamadas sequenciais |
| **session_search** | Busca sessões passadas do Hermes | Contexto histórico, referência a conversas anteriores |
| **memory** (via state.db) | Persistência de factos entre sessões | Preferências, decisões, contexto do projeto |

Ferramentas como **kanban**, **cron**, **github**, **telegram**, **proxy** são acessadas através de skills ou comandos hermes — não são tool functions standalone.

### 3.2 Skills (procedimentos especializados via `hermes skills list`)
Skills são pacotes de conhecimento procedural carregados on-demand. Em 2026-09-20 existem **88 skills enabled** (53 builtin, 22 local, 13 hub-installed). Os mais relevantes para trabalhar comigo:

#### Skills locais (customizados para este ambiente)
- **athos-orchestration** — orquestração de agentes, profiles, kanban, governança
- **kanban-governanca** — governança de triagem, buffer e ciclo de vida do kanban
- **github-auth** — autenticação GitHub (tokens, SSH, gh CLI)
- **github-pr-workflow** — ciclo de vida de PR: branch, commit, open, CI, merge
- **github-code-review** — review de PRs: diffs, comentários inline via gh ou REST
- **github-deploy-workflow** — GitHub Actions, GHCR, nginx, certbot
- **github-issue-to-pr** — levar issue a PR verificado com estado honesto de CI
- **github-issues** — criar, triagear, labelar, assignar issues via gh ou REST
- **github-repo-management** — clonar/criar/fork repos; manage remotes, releases
- **bot-pr-review** — workflows automatizados de review de PR com conta bot
- **merge-reconciler** — resolutão neutra de conflitos de merge entre agents
- **parallel-specialist-dispatch** — despacho de specialists em paralelo
- **supervised-ai-development** — desenvolvimento supervisionado com PR review
- **codebase-audit** — auditoria multi-camadas: backend, frontend, BD, infra, docs
- **codebase-inspection** — inspeção de codebases com pygount: LOC, linguagens, ratios
- **systematic-debugging** — debug root-cause em 4 fases
- **test-driven-development** — TDD com red-green-refactor
- **product-strategy** — clasificação de repos por valor/rentabilidade/reutilização
- **repo-portfolio-strategy** — clasificación de repos por valor, rentabilidade e reutilização
- **vps-operations** — triage VPS e inventário de repos com ou sem gh
- **cli-auth-token-extraction** — extração de tokens quando comandos CLI truncam output
- **nano-pdf** — edição de texto em PDFs existentes via linguagem natural
- **ocr-and-documents** — extração de texto de PDFs/escaneamentos (pymupdf, marker-pdf)
- **session-librarian** — organização de sessões por prompt: find, rename, archive, prune
- **blogwatcher** — monitorização de blogs e feeds RSS/Atom via blogwatcher-cli
- **competitor-news-monitor** — monitorização de notícias materiais de empresas nomeadas
- **grounded-citations** — respostas e documentos apoiados em fontes citáveis e verificáveis
- **llm-wiki** — Karpathy's LLM Wiki: construir/consultar KB markdown interligada
- **blocked-page-recovery** — recuperação quando fetch falha: 403/429, paywall, WAF

#### Skills builtin (nativos do Hermes Agent, sempre disponíveis)
Incluem: `github`, `github-*` (issue-to-pr, repo-management, etc.), `claude-code`, `codex`, `opencode`, `computer-use`, `hermes-agent`, `productivity/*` (docx, xlsx, notion, airtable, etc.), `research/*` (arxiv, llm-wiki, etc.), `mlops/*`, `creative/*`, `devops/*`, `email/*`, `social-media/*`, `smart-home/*`, `note-taking/*`, `media/*`, e `software-development/*` (dogfood, spike, simplify-code, requesting-code-review, etc.).

#### Skills hub-installed (13, instalados do registry)
marcados como `official` ou `builtin` no catálogo — ver `hermes skills list` para o nome exato de cada um.

#### O que NÃO é skill (são capabilities ou procedimentos)
- **Ferramentas nativas** (terminal, read_file, web_search, etc.) — veja 3.1
- **Comandos hermes CLI** (`hermes chat`, `hermes proxy`, `hermes cron`, `hermes kanban`, `hermes doctor`) — são subcomandos do runtime
- **Conhecimento procedural ad-hoc** — e.g. "como fazer PR review" é um procedimento que o Athos aplica, não necessariamente um skill carregado

Podes me pedir para carregar qualquer skill antes de uma tarefa — `skill_view('<nome>')` ou `hermes skills list` para o catálogo completo.

### 3.3 O que copri regularmente (em nome do Ricardo)

|| Área | Exemplos de tarefas ||
||------|---------------------|
|| **Engenharia** | Co-piloto dos repos `padelsync`, `raiz`, `athos-core`, `jpa`, `Picado-Systems` |
|| **Planeamento** | Semanas, prioridades, roadmaps, continuidade operacional |
|| **Orquestração** | Criação e gestão de profiles Hermes, validação de entregas entre specialists, kanban |
|| **PR review automático** | Script `~/.hermes/scripts/pr-auto-review.py` + cron job `f5bc8e03056d` — analiso diffs, verifico CI, comento em PRs abertos nos repos configurados (atualmente com drift de modelo — ver 2.7) |
|| **Inventário e clasificação** | Repo portfolio analysis por valor/rentabilidade/reutilização |
|| **Automação** | Cron jobs para tarefas recorrentes, webhooks, monitorização |

**Roadmap relevante:** as tarefas do portfolio estão em `~/ai-assistant/roadmap.md` — onde o work é priorizado e rastreado. O kanban reflete o estado atual do roadmap. Ao iniciar trabalho, verifica o roadmap e o kanban para não atropelar P0s pendentes.

---

## 4. Identidade e política de acesso

Isto é importante se fores abrir PRs, issues, ou commits em nome de "Athos":

| Entidade | Valor |
|----------|-------|
| **Username GitHub do agente** | `athoagent-oss` |
| **Token de escrita do agente** | `AGENT_GH_TOKEN` (no `.env` do profile) — token `athoagent-oss` |
| **Token de leitura** | `GH_TOKEN` / `GITHUB_TOKEN` (default) — token RicardoVarzim, permite leitura irrestrita |
| **Usuario git (commits)** | Nunca `RicardoVarzim` para acções de agente — sempre `athoagent-oss` |
| **Reviewer de PRs** | `RicardoVarzim` é o reviewer — eu (Athos) nunca faço dev XOR reviewer por iniciativa própria |

**Regra de ouro:** Os commits, pushes, issues e PRs emitidos por mim usam a identidade `athoagent-oss`. Nunca assumo a identidade do Ricardo para acções de agente. PRs que eu abra precisam de `RicardoVarzim` como reviewer.

---

## 5. Contexto de projeto

Estes são os meus principais projetos. Se fores trabalhar connosco, começa por aqui:

| Repo | Prioridade | Estado | Notas |
|------|-----------|--------|-------|
| **padelsync** | P0 | Live em `live.wildpadel.pt` | 3 usuários, 12 matches, 0 receita ainda |
| **raiz** | P0 | Em desenvolvimento | Treasury / caixa imediato; checkout/pagamentos ainda não live; piloto loja artesanal Aguçadoura em discussão |
| **portfolio-dashboard** | P1 | Backlog | Backoffice do estado dos repos |
| **athos-core** | P1 | Baixa atividade | Framework core |
| **jpa** | P1 | Não ainda no GitHub Packages | |

**VPS:** Debian 12, 3.7GB RAM + 4GB swap, 59GB livres, Docker 28.3.3.  
**Stack:** git 2.39.5, python3 3.11.2, node v26.8.1.  
**Domínio dos repos:** `RicardoVarzim` (pessoal) e `Picado-Systems` (organização).

---

## 6. Como interagir comigo — padrões práticos

### 6.1 Envia-me tarefas concretas

Funciona melhor quando me pedes algo específico com contexto:

```
"Roda um audit do codebase do padelsync e dá-me um resumo de dívida técnica"
"Clona o repo raiz em ~/dev e análise a estrutura de payment integration"
"Cria um plano de semana para os repos P0 com os 3 tasks mais urgentes"
```

### 6.2 Para trabalho persistente / multi-sessão

- O **kanban** é o sistema de gestão de trabalho entre profiles e sessões.
- O **memory** guarda factos entre sessões (preferências, decisões, ambiente).
- Os **profiles Hermes** são specialists com SOUL.md próprio — eu crio, atribuo e valido.

### 6.3 Para interação via código (agentes externas)

Se um agente externo (como Cursor, Codex) precisa de falar comigo:

**Opção A — CLI via SSH (mais simples):**
```bash
ssh ricardovarzim@vps "hermes chat -q '<instrução>'"
```

**Opção B — Proxy OpenAI-compatible (mais fluído para agentes que usam tool calling):**
1. No VPS: `hermes proxy` (lança em background)
2. No agente externo: configura o endpoint do proxy como o "modelo OpenAI"
3. Fala comigo como farias com qualquer API de LLM — só que sou o Hermes executando na VPS

**Opção C — Telegram (assíncrono):**
Basta enviar mensagem ao bot. Posso executar tarefas, consultar contexto, devolver resultados.

### 6.4 Como validar que estou operacional

```
# Verificar que o Hermes está vivo na VPS
ssh ricardovarzim@vps "hermes doctor"

# Testar resposta
ssh ricardovarzim@vps "hermes chat -q 'who are you?'"

# Ver estado do kanban
ssh ricardovarzim@vps "hermes kanban list"
```

---

## 7.limitaciones e regras que deves conhecer

1. **Bootstrapping estrito:** zero custos fixos de pessoal. Tarefas que implicam custos precisam de justificação e aprovação do Ricardo.
2. **Um papel por PR:** dev XOR reviewer — nunca os dois por iniciativa própria.
3. **Identidade do agente:** `athoagent-oss` para escrita GitHub; nunca `RicardoVarzim`.
4. **Nenhum comando destrutivo** (rm -rf, drop table, etc.) sem confirmação explícita do Ricardo.
5. **Sem arquivar cartões kanban** — Done fica Done; o Ricardo arquiva.
6. **Max 10 cartões no kanban** de cada vez — consolidar e remover duplicados agressivamente.
7. **PR auto-review (`f5bc8e03056d`):** com **drift de modelo** e 6 falhas consecutivas — o job está skipado até ser pinned. Não estou a fazer auto-reviews neste momento; quando for restaurado, após 3 tentativas falhadas de auto-fix, comento WIP e paras — não mergio/aprovo PRs próprios.

---

## 8. Onde encontro documentação atualizada

| Recurso | Onde |
|---------|------|
| Documentação Hermes oficial | [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/) |
| Index de todas as features | `https://hermes-agent.nousresearch.com/docs/llms.txt` |
| Configuração principal | `~/.hermes/config.yaml` (definições) + `~/.hermes/.env` (secrets apenas) |
|| SOUL.md (identidade) | `~/.hermes/SOUL.md` (profile `default`) |
| Roadmap do portfolio | `~/ai-assistant/roadmap.md` |
| Governança PR review | `~/.hermes/GOVERNANCE.md` |
| Scripts de automação | `~/.hermes/scripts/` |
| Cron jobs ativos | `hermes cron list` |
| Catálogo de skills | `hermes skills list` |

---

## 9. Perguntas que um agente novo deve fazer antes de começar

Se fores um agente a entrar em contexto comigo, estas são boas perguntas iniciais:

1. **Qual é o projeto/foco atual?** — o roadmap muda; não assumas que o que fizemos há 3 meses é ainda relevante.
2. **Que nível de autonomia tenho?** — posso executar sozinho ou preciso de confirmação passo a passo?
3. **Há trabalho em curso no kanban?** — verifica antes de começar algo novo.
4. **Qual a política de acesso GitHub para esta tarefa?** — leitura (GH_TOKEN RicardoVarzim) ou escrita (AGENT_GH_TOKEN athoagent-oss)? Preciso de autorização explícita para escrever.
5. **O que é P0 vs P1 vs P2?** — não atropeles tarefas de menor prioridade se houver P0 pendente.

---

> **Documento mantido por Athos.** Revisa com o Ricardo quando as capacidades, o ambiente ou as políticas mudarem significativamente.
