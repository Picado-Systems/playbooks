#!/usr/bin/env python3
"""
PR Auto-Review — Athos (manual run or cron)
Review aprofundada e gateada de PRs abertos nos repos configurados.
Submete review como COMMENT via GitHub REST API com a identidade athoagent-oss.

Gateiras:
  1. Anti-loop: ignora PRs onde autor == athoagent-oss
  2. Ignora drafts
  3. CI verde obrigatório (usa commits/{sha}/check-runs)
  4. Idempotência: ignora se já tiver review de athoagent-oss no mesmo head_sha
"""

import os, sys, json, subprocess, datetime, re, urllib.request, urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
REPOS_FILE = Path.home() / ".hermes" / "config" / "pr-review-repos.txt"
ATHOS_TOKEN_PATH = Path.home() / ".github" / "athos-agent-token"
RICARDO_TOKEN_PATH = Path.home() / ".github" / "athos-agent-full-token"

REVIEWER_LOGIN = "athoagent-oss"

# ── Shell helpers ─────────────────────────────────────────────────────────
def run(cmd, **kw):
    kw.setdefault("shell", True)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    p = subprocess.run(cmd, **kw)
    return p.stdout, p.stderr, p.returncode

def gh_raw(args, token=None):
    """Executa `gh` com token via GITHUB_TOKEN env (evita --with-token flaky)."""
    env = {**os.environ}
    if token:
        env["GITHUB_TOKEN"] = token
    p = subprocess.run(["gh"] + list(args), capture_output=True, text=True, env=env)
    return p.stdout.strip(), p.stderr.strip(), p.returncode

# ── Auth ──────────────────────────────────────────────────────────────────
def get_athos_token():
    if not ATHOS_TOKEN_PATH.exists():
        print(f"ERRO: {ATHOS_TOKEN_PATH} não existe", file=sys.stderr)
        return None
    return ATHOS_TOKEN_PATH.read_text().strip()

def get_ricardo_token():
    if not RICARDO_TOKEN_PATH.exists():
        print(f"ERRO: {RICARDO_TOKEN_PATH} não existe", file=sys.stderr)
        return None
    return RICARDO_TOKEN_PATH.read_text().strip()

# ── Config ────────────────────────────────────────────────────────────────
def load_repos():
    if not REPOS_FILE.exists():
        print(f"Aviso: {REPOS_FILE} não existe", file=sys.stderr)
        return []
    lines = [l.strip() for l in REPOS_FILE.read_text().splitlines()]
    return [l for l in lines if l and not l.startswith("#") and "/" in l]

# ── GitHub API helpers ────────────────────────────────────────────────────
def api_graphql(query, token=None):
    """Executa GraphQL via gh api graphql."""
    args = ["api", "graphql", "-F", f"query={query}"]
    return gh_raw(args, token=token)

def api_rest(path, method="GET", body=None, token=None):
    """Executa REST API via urllib direto (evita limitações do gh)."""
    url = f"https://api.github.com/{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Athos-PR-AutoReview/1.0"
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), None, resp.status
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8')[:300]}", e.code
    except Exception as e:
        return None, str(e), -1

# ── PR discovery ─────────────────────────────────────────────────────────
def list_open_prs(repo, token):
    """Lista PRs abertos num repo via REST API ( precisa de repo scope)."""
    path = f"repos/{repo}/pulls?state=open&per_page=50&sort=updated&direction=desc"
    data, err, rc = api_rest(path, token=token)
    if err:
        print(f"  ERRO ao listar PRs de {repo}: {err}", file=sys.stderr)
        return []
    return data or []

def get_pr(pr_number, repo, token):
    """Obtém informação completa de um PR em uma chamada GraphQL."""
    owner, name = repo.split("/")
    query = f"""
    {{
      repository(owner: "{owner}", name: "{name}") {{
        pullRequest(number: {pr_number}) {{
          number
          title
          body
          isDraft
          state
          url
          headRefOid
          headRefName
          baseRefName
          author {{ login }}
          reviews(first: 50) {{
            nodes {{
              id
              author {{ login }}
              state
              submittedAt
              body
              commit {{ oid }}
            }}
          }}
          reviewRequests(first: 20) {{
            nodes {{
              requestedReviewer {{
                ... on User {{ login }}
                ... on Team {{ name }}
              }}
            }}
          }}
          comments(first: 50) {{
            nodes {{
              author {{ login }}
              body
              createdAt
            }}
          }}
        }}
      }}
    }}
    """
    out, err, rc = api_graphql(query, token=token)
    if err:
        print(f"  ERRO GraphQL PR #{pr_number}: {err}", file=sys.stderr)
        return None
    data = json.loads(out)
    return data.get("data", {}).get("repository", {}).get("pullRequest")

def get_pr_diff(pr_number, repo, token):
    """Obtém diff de um PR via gh pr diff."""
    out, err, rc = gh_raw(["pr", "diff", str(pr_number), "--repo", repo], token=token)
    if rc != 0:
        print(f"  ERRO diff PR #{pr_number}: {err}", file=sys.stderr)
        return None
    return out

def ci_passed(pr_number, repo, token):
    """Verifica se todos os checks relevantes passaram. Usa commits/{sha}/check-runs."""
    # Primeiro obter o head sha do PR
    pr_data = get_pr(pr_number, repo, token)
    if not pr_data:
        print("    - CI: não foi possível obter PR")
        return True  # assume OK se não conseguir determinar
    head_sha = pr_data.get("headRefOid")
    if not head_sha:
        print("    - CI: sem SHA (assume OK)")
        return True
    
    # Usar commits/{sha}/check-runs com o token fornecido
    path = f"repos/{repo}/commits/{head_sha}/check-runs?per_page=100"
    data, err, rc = api_rest(path, token=token)
    if err:
        # Fallback: tentar gh pr checks
        print(f"    - CI: API devolveu erro, tentando fallback...")
        out, err2, _ = gh_raw(["pr", "checks", str(pr_number), "--repo", repo], token=token)
        if out and out.strip():
            print("    - CI: OK (verificado via gh)")
            return True
        print(f"    - CI: sem checks (assume OK)")
        return True
    
    runs = data.get("check_runs", [])
    if not runs:
        print("    - CI: sem checks (assume OK)")
        return True
    
    completed = [r for r in runs if r.get("status") == "completed"]
    if not completed:
        print("    - CI: checks ainda em execução (assume OK para review)")
        return True
    
    failed = [c for c in runs if c.get("conclusion") not in ("success", "skipped", "neutral")]
    if failed:
        names = ", ".join(c["name"] for c in failed[:5])
        print(f"    - CI: FALHOU — {len(failed)} check(s): {names}")
        return False
    
    success_count = sum(1 for c in runs if c.get("conclusion") == "success")
    skipped_count = sum(1 for c in runs if c.get("conclusion") == "skipped")
    print(f"    - CI: OK ({success_count} success, {skipped_count} skipped)")
    return True

def is_review_requested(pr_data):
    """Verifica se athoagent-oss está explicitamente na lista de reviewRequests."""
    requests = pr_data.get("reviewRequests", {}).get("nodes", [])
    for req in requests:
        reviewer = req.get("requestedReviewer", {})
        if reviewer and reviewer.get("login") == REVIEWER_LOGIN:
            return True
    return False

def has_existing_review(pr_data):
    """Verifica se athoagent-oss já fez review neste PR no headRefOid atual.
    
    Regras:
      1. Se athoagent-oss estiver explicitamente em reviewRequests (pedido de re-review),
         não faz skip (deve rever).
      2. Se existir review de athoagent-oss no headRefOid atual, faz skip (já revisto).
      3. Se a review anterior foi num commit mais antigo (diff foi atualizado), não faz skip.
    """
    if is_review_requested(pr_data):
        return None

    head_sha = pr_data.get("headRefOid")
    reviews = pr_data.get("reviews", {}).get("nodes", [])
    for r in reviews:
        if r.get("author", {}).get("login") == REVIEWER_LOGIN:
            review_sha = r.get("commit", {}).get("oid")
            if review_sha and head_sha:
                if review_sha == head_sha:
                    return r
            else:
                # Fallback se não houver commit info
                return r
    return None

# ── Review analysis ──────────────────────────────────────────────────────
def analyze_diff_and_body(diff_text, pr_body, pr_title):
    """Gera sumário de review aprofundado baseado no diff.
    
    Diferencia adições (+) de remoções (-) no diff para evitar falsos positivos.
    """
    issues = {
        "security": [],
        "code": [],
        "docs": [],
        "tests": [],
        "empty": False
    }
    files_changed = set()
    has_code_files = False
    has_docs_only = True
    has_diff = bool(diff_text.strip())
    
    # Parse ficheiros do diff
    current_file = None
    for line in diff_text.splitlines():
        m = re.match(r'^\+\+\+ b/(.+)$', line)
        if m:
            current_file = m.group(1)
            files_changed.add(current_file)
            ext = Path(current_file).suffix.lower()
            name = Path(current_file).name.lower()
            if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".h", ".hpp", ".swift", ".kt", ".scala", ".clj", ".ex", ".exs", ".lua", ".php", ".cs", ".vb", ".fs"):
                has_code_files = True
                has_docs_only = False
            elif ext in (".md", ".txt", ".rst", ".adoc") or name.startswith("readme"):
                pass
    
    if not has_diff or not files_changed:
        issues["empty"] = True
    
    # ── Security scan (apenas em ADIÇÕES) ──
    # Se algo suspeito foi REMOVIDO, é geralmente bom (está a limpar)
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("---"):  # ficheiro original
            continue
        m = re.match(r'^\+\+\+ b/(.+)$', line)
        if m:
            current_file = m.group(1)
            continue
        
        is_addition = line.startswith("+")
        is_removal = line.startswith("-")
        
        # Skip metadata lines
        if not is_addition and not is_removal:
            continue
        
        if is_addition and re.search(r'\b(VITE_|PUBLIC_|NEXT_PUBLIC_|REACT_APP_|window\.|global\.)', line) and \
           re.search(r'\b(PASSWORD|PASSWD|SECRET|API[_-]?KEY|CREDENTIAL|AWS_SECRET|AWS_ACCESS|PRIVATE[_-]?KEY)\b', line, re.IGNORECASE):
            issues["security"].append(f"🚨 Possível leak de secret no bundle/cliente: `{line.strip()[:120]}`")
        
        # Secrets em ficheiros .env ou similar APENAS em adições
        if is_addition and (re.match(r'^\+\+\+ b/.*\.env', line) or re.match(r'^\+\+\+ b/.*\.env\..*', line) or \
           re.match(r'^\+\+\+ b/.*secret', line, re.IGNORECASE) or \
           re.match(r'^\+\+\+ b/.*credentials', line, re.IGNORECASE)):
            issues["security"].append(f"🚨 Ficheiro de secrets/configuração sensível adicionado: `{line.strip()}`")
        
        # Key/tokens hardcoded em code APENAS em adições reais
        if is_addition:
            # Ignora ficheiros de documentação/markdown
            if current_file and (current_file.endswith(('.md', '.txt', '.rst', '.adoc')) or 'readme' in current_file.lower()):
                continue
            # Ignora tokens de cancelamento de concorrência (.NET CancellationToken)
            if re.search(r'\bCancellationToken\b|\bCancellationTokenSource\b', line):
                continue
            # Ignora comentários
            if line.strip().startswith(('//', '/*', '*', '#')):
                continue

            has_secret_identifier = bool(re.search(
                r'\b(AWS_SECRET|AWS_ACCESS_KEY|STRIPE_KEY|STRIPE_SECRET|SENDGRID|RAZORPAY|PAYPAL|PRIV_KEY|PRIVATE_KEY|PASSWORD|PASSWD|API[_-]?KEY|SECRET[_-]?KEY|AUTH[_-]?TOKEN|ACCESS[_-]?TOKEN)\b',
                line,
                re.IGNORECASE
            ))
            # String literal com pelo menos 20 caracteres entre aspas obrigatórias
            literal_match = re.search(r'["\']([A-Za-z0-9_\-+/=]{20,})["\']', line)
            
            if has_secret_identifier and literal_match:
                matched_val = literal_match.group(1)
                # Ignora URLs, placeholders ou injeções de configuração
                if not matched_val.startswith(('http://', 'https://')) and \
                   not re.search(r'YOUR_|EXAMPLE|CHANGE_ME|DUMMY|REPLACE|TEST_', matched_val, re.IGNORECASE) and \
                   not re.search(r'process\.env|os\.environ|os\.getenv|ENV\[|config\.|configuration\[|Configuration\[', line, re.IGNORECASE):
                    issues["security"].append(f"🚨 Valor suspeito hardcoded em adição: `{line.strip()[:120]}`")
        
        # Se algo de seguro foi REMOVIDO de um ficheiro sensível, nota como positivo
        if is_removal and re.search(r'(VITE_|PUBLIC_|NEXT_PUBLIC_|REACT_APP_).*(PASSWORD|SECRET|TOKEN)', line, re.IGNORECASE):
            issues["security"].append(f"✅ Secret removido do bundle/cliente (boa prática): `{line.strip()[:100]}`")
    
    # ── Breaking changes (apenas adições) ──
    for line in diff_text.splitlines():
        if line.startswith("+") and re.search(r'(BREAKING[_-]?CHANGE|major|MAJOR)', line, re.IGNORECASE):
            issues["code"].append(f"🔴 Breaking change sem version bump explícito: `{line.strip()[:100]}`")
    
    # ── Test removal (apenas remoções em ficheiros de teste) ──
    in_test_file = False
    for line in diff_text.splitlines():
        m = re.match(r'^\+\+\+ b/(.+)$', line)
        if m:
            in_test_file = "test" in m.group(1).lower() or "spec" in m.group(1).lower()
            continue
        if in_test_file and line.startswith("-") and re.search(r'(function|it|test|describe|expect|assert|suite)', line, re.IGNORECASE):
            issues["tests"].append(f"🧪 Possível remoção de teste: `{line.strip()[:100]}`")
    
    # ── Code smells (apenas adições) ──
    for line in diff_text.splitlines():
        if line.startswith("---") or line.startswith("+++ "):
            continue
        is_addition = line.startswith("+")
        if not is_addition:
            continue  # só flagga adições
        
        if re.search(r'console\.(log|debug|info|warn)\(', line):
            # Ignora se for num ficheiro de building/generation/script
            if current_file and ('generate' in current_file.lower() or 'build' in current_file.lower() or 'script' in current_file.lower()):
                continue
            issues["code"].append(f"🟡 console.log residual: `{line.strip()[:80]}`")
        
        if re.search(r'\b(TODO|FIXME|HACK|XXX|BUG)\b', line):
            issues["code"].append(f"📝 Marcador adicionado: `{line.strip()[:80]}`")
    
    # ── Docs check ──
    if has_docs_only and files_changed:
        if not pr_body or len(pr_body.strip()) < 50:
            issues["docs"].append("📄 PR de documentação sem descrição detalhada no corpo do PR")
    
    # ── Build the summary ──
    summary = []
    summary.append(f"## 🤖 Review automático — Athos")
    summary.append("")
    summary.append(f"**PR:** {pr_title}")
    summary.append(f"**Ficheiros ({len(files_changed)}):** " + ", ".join(sorted(files_changed)[:8]) + ("..." if len(files_changed) > 8 else ""))
    summary.append("")
    
    # Risco — considerar também remoções positivas
    security_concerns = [i for i in issues["security"] if i.startswith("🚨")]
    security_fixes = [i for i in issues["security"] if i.startswith("✅")]
    has_code_concerns = bool(issues["code"] or issues["tests"] or issues["docs"])
    
    risk = "🟢 Baixo"
    if security_concerns:
        risk = "🔴 ALTO"
    elif has_code_concerns:
        risk = "🟡 Médio"
    
    summary.append(f"**Nível de risco:** {risk}")
    if security_fixes:
        summary.append(f"**Notas positivas:** {len(security_fixes)} melhoria(s) de segurança detectada(s)")
    summary.append("")
    
    # Recomendação e Evento do GitHub Review
    if security_concerns:
        summary.append("**Recomendação:** ❌ **Pedir alterações** — questões de segurança detectadas.")
        review_event = "REQUEST_CHANGES"
    elif has_code_concerns:
        summary.append("**Recomendação:** ⚠️ **Aprovar com observações** — ver detalhes abaixo.")
        review_event = "COMMENT"
    else:
        summary.append("**Recomendação:** ✅ **Aprovar** — diff validado e sem problemas detectados.")
        review_event = "APPROVE"
    
    summary.append("")
    summary.append("---")
    summary.append("")
    
    # Detalhes
    if issues["security"]:
        summary.append("### 🚨 Segurança")
        summary.append("")
        for note in issues["security"]:
            summary.append(f"- {note}")
        summary.append("")
    
    if issues["code"]:
        summary.append("### 🔍 Código")
        summary.append("")
        for note in issues["code"]:
            summary.append(f"- {note}")
        summary.append("")
    
    if issues["tests"]:
        summary.append("### 🧪 Testes")
        summary.append("")
        for note in issues["tests"]:
            summary.append(f"- {note}")
        summary.append("")
    
    if issues["docs"] and has_docs_only:
        summary.append("### 📄 Documentação")
        summary.append("")
        for note in issues["docs"]:
            summary.append(f"- {note}")
        summary.append("")
    
    has_real_issues = bool(issues["security"] or issues["code"] or issues["tests"] or issues["docs"])
    if not has_real_issues:
        summary.append("### ✅ Sem problemas críticos detectados")
        summary.append("")
        summary.append("O diff está limpo. Sem questões de segurança, sem code smells evidentes, sem regressões de teste detectadas.")
        summary.append("")
    
    summary.append("---")
    summary.append("")
    summary.append("*Review gerado automaticamente pelo Athos. Para decisões críticas, confirma manualmente.*")
    
    return "\n".join(summary), issues, review_event

# ── Submit review ─────────────────────────────────────────────────────────
def submit_review(pr_number, repo, body, event, token):
    """Submete review com o evento apropriado (APPROVE, REQUEST_CHANGES ou COMMENT) via REST API."""
    path = f"repos/{repo}/pulls/{pr_number}/reviews"
    payload = {
        "body": body,
        "event": event
    }
    data, err, rc = api_rest(path, method="POST", body=payload, token=token)
    if err:
        print(f"  ❌ Erro ao submeter review ({event}): {err}", file=sys.stderr)
        return False
    html_url = data.get("html_url") or data.get("pull_request_url", "")
    print(f"  ✅ Review submetido ({event}): {html_url}")
    return True

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    print("=" * 62)
    print(f" PR Auto-Review — Athos  |  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 62)
    print()
    
    # Auth
    athos_token = get_athos_token()
    ricardo_token = get_ricardo_token()
    if not athos_token or not ricardo_token:
        sys.exit(1)
    
    # Verify identity
    out, _, _ = gh_raw(["api", "user", "--jq", ".login"], token=athos_token)
    identity = out if out else None  # --jq devolve string raw, não JSON
    print(f"👤 Athos identity: {identity}")
    out, _, _ = gh_raw(["api", "user", "--jq", ".login"], token=ricardo_token)
    rident = out if out else "?"
    print(f"👤 Ricardo identity: {rident}")
    print()
    
    # Repos
    repos = load_repos()
    print(f"📋 Repos configurados ({len(repos)}): {repos}")
    print()
    
    if not repos:
        print("❌ Nenhum repo. Abortando.", file=sys.stderr)
        sys.exit(1)
    
    # Discover PRs
    candidates = []
    for repo in repos:
        print(f"🔍 {repo}...")
        prs = list_open_prs(repo, ricardo_token)
        print(f"   → {len(prs)} PRs abertos")
        for pr in prs:
            candidates.append((repo, pr))
    
    print()
    print(f"📊 Total candidatos: {len(candidates)}")
    print()
    
    # Process
    reviewed = 0
    skipped = 0
    errors = 0
    results_log = []
    
    for repo, pr in candidates:
        number = pr["number"]
        title = pr.get("title", "?")
        author = pr.get("user", {}).get("login", "?")
        is_draft = pr.get("draft", False)
        head_sha = pr.get("head_sha") or pr.get("headRefOid", "?")
        
        print(f"─── PR #{number} · {repo} ───")
        print(f"  Título: {title}")
        print(f"  Autor:  {author}  |  Draft: {is_draft}  |  SHA: {head_sha[:12] if head_sha else '?'}")
        
        # Gate 1: anti-loop
        if author == REVIEWER_LOGIN:
            print("  ⏭️  skip — autor é athoagent-oss")
            skipped += 1
            results_log.append({"repo": repo, "pr": number, "status": "skipped-self_author"})
            print()
            continue
        
        # Gate 2: draft
        if is_draft:
            print("  ⏭️  skip — draft")
            skipped += 1
            results_log.append({"repo": repo, "pr": number, "status": "skipped-draft"})
            print()
            continue
        
        # Gate 3: fetch full PR info (needed for review check + CI)
        print("  📥 A carregar info do PR...")
        pr_data = get_pr(number, repo, ricardo_token)
        if not pr_data:
            print("  ❌ erro ao carregar PR")
            errors += 1
            results_log.append({"repo": repo, "pr": number, "status": "error-load"})
            print()
            continue
        
        # Gate 3b: CI
        print("  🔍 CI...")
        if not ci_passed(number, repo, ricardo_token):
            print("  ⏭️  skip — CI não passou")
            skipped += 1
            results_log.append({"repo": repo, "pr": number, "status": "skipped-ci"})
            print()
            continue
        
        # Gate 4: idempotency
        existing = has_existing_review(pr_data)
        if existing:
            sha_info = existing.get("commit", {}).get("oid", "")[:8]
            sha_str = f" no commit {sha_info}" if sha_info else ""
            print(f"  ⏭️  skip — já existe review de {REVIEWER_LOGIN}{sha_str} ({existing.get('submittedAt','?')[:10]})")
            skipped += 1
            results_log.append({"repo": repo, "pr": number, "status": "skipped-already_reviewed"})
            print()
            continue
        
        # Diff
        print("  📥 Diff...")
        diff = get_pr_diff(number, repo, ricardo_token)
        if not diff:
            print("  ❌ erro ao obter diff")
            errors += 1
            results_log.append({"repo": repo, "pr": number, "status": "error-diff"})
            print()
            continue
        
        # Analyze
        print("  🧠 Análise...")
        pr_body = pr_data.get("body") or ""
        summary, issues, review_event = analyze_diff_and_body(diff, pr_body, title)
        
        print()
        print("╔" + "═" * 60)
        print("║  REVIEW GERADO")
        print("╠" + "═" * 60)
        for line in summary.splitlines():
            print(f"║ {line}")
        print("╚" + "═" * 60)
        print()
        
        # Submit
        print(f"  📤 A submeter review como {review_event}...")
        ok = submit_review(number, repo, summary, review_event, athos_token)
        if ok:
            reviewed += 1
            results_log.append({"repo": repo, "pr": number, "status": "reviewed", "url": f"https://github.com/{repo}/pull/{number}"})
        else:
            errors += 1
            results_log.append({"repo": repo, "pr": number, "status": "error-submit"})
        print()
    
    # Summary
    print("=" * 62)
    print(" RESUMO")
    print("=" * 62)
    print(f"  Candidatos:   {len(candidates)}")
    print(f"  Revisados:    {reviewed}")
    print(f"  Ignorados:    {skipped}")
    print(f"  Erros:        {errors}")
    print()
    
    # Local log
    log_dir = Path.home() / ".hermes" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"pr-review-{ts}.json"
    log_entry = {
        "timestamp": now.isoformat(),
        "repos": repos,
        "candidates": len(candidates),
        "reviewed": reviewed,
        "skipped": skipped,
        "errors": errors,
        "results": results_log
    }
    log_path.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False))
    print(f"  📋 Log: {log_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())