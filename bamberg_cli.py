"""Isolated Claude/Codex task runner. Python 3.10+, Linux bubblewrap."""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

STATE = ".bamberg"
IDENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class Error(Exception):
    pass


def git(*args, cwd=None, check=True):
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and p.returncode:
        raise Error(p.stderr.strip() or p.stdout.strip() or "git failed")
    return p.stdout.strip()


def root():
    git("rev-parse", "--show-toplevel")  # Fail clearly outside a Git repository.
    worktrees = git("worktree", "list", "--porcelain")
    return Path(worktrees.splitlines()[0][9:]).resolve()


def state_dir(repo):
    path = repo / STATE
    if path.is_symlink():
        raise Error("O diretório .bamberg não pode ser um link simbólico.")
    return path


def ensure_state_ignored(repo):
    exclude = Path(git("rev-parse", "--git-path", "info/exclude", cwd=repo))
    if not exclude.is_absolute():
        exclude = repo / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text() if exclude.exists() else ""
    if ".bamberg/" not in existing.splitlines():
        with exclude.open("a") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(".bamberg/\n")


@contextlib.contextmanager
def lock(repo):
    state = state_dir(repo)
    state.mkdir(mode=0o700, exist_ok=True)
    with (state / "lock").open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def save(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.chmod(temp, 0o600)
    temp.replace(path)


def read(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def config(repo):
    return read(state_dir(repo) / "config.json", {"accounts": {}})


def validate_id(value):
    if not IDENT.fullmatch(value):
        raise Error("Use apenas letras, números, _ ou - no identificador (até 64 caracteres).")
    return value


def account_add(repo, args):
    validate_id(args.id)
    home = Path(args.home).expanduser().resolve()
    if home == repo or home in repo.parents or repo in home.parents:
        raise Error("O diretório da conta precisa ficar fora do repositório.")
    ensure_state_ignored(repo)
    with lock(repo):
        cfg = config(repo)
        if args.id in cfg["accounts"]:
            raise Error("Identificador de conta já cadastrado.")
        for item in cfg["accounts"].values():
            other = Path(item["home"])
            if home == other or home in other.parents or other in home.parents:
                raise Error("Diretórios de contas não podem se sobrepor.")
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        cfg["accounts"][args.id] = {"provider": args.provider, "home": str(home), "label": args.label or args.id}
        save(state_dir(repo) / "config.json", cfg)
    print(f"Conta {args.id} cadastrada ({args.provider}).")


def get_account(repo, name):
    item = config(repo)["accounts"].get(name)
    if not item:
        raise Error(f"Conta desconhecida: {name}")
    return item


def account_env(item):
    env = os.environ.copy()
    # Prevent credentials from another active account taking precedence.
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY", "CODEX_ACCESS_TOKEN"):
        env.pop(key, None)
    env["CLAUDE_CONFIG_DIR" if item["provider"] == "claude" else "CODEX_HOME"] = item["home"]
    env["HOME"] = item["home"]
    env["XDG_CACHE_HOME"] = str(Path(item["home"]) / ".cache")
    env["XDG_CONFIG_HOME"] = str(Path(item["home"]) / ".config")
    env["XDG_DATA_HOME"] = str(Path(item["home"]) / ".local" / "share")
    return env


def account_login(repo, args):
    item = get_account(repo, args.id)
    binary = item["provider"]
    if not shutil.which(binary):
        raise Error(f"Executável {binary} não encontrado no PATH.")
    command = [binary, "auth", "login"] if binary == "claude" else [binary, "login"]
    return subprocess.call(command, env=account_env(item))


def ensure_ready(repo):
    if not git("rev-parse", "HEAD", cwd=repo, check=False):
        raise Error("Faça um commit inicial antes de criar worktrees: git add . && git commit -m 'Initial commit'")
    if git("status", "--porcelain", cwd=repo):
        raise Error("O repositório principal precisa estar limpo antes de criar uma tarefa.")
    if not shutil.which("bwrap"):
        raise Error("bubblewrap (bwrap) é necessário para isolamento de escrita.")
    probe = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--", "/usr/bin/true"], capture_output=True)
    if probe.returncode:
        raise Error("bubblewrap não está disponível neste sistema: " + probe.stderr.decode().strip())


def job_path(repo, name):
    return state_dir(repo) / "jobs" / (validate_id(name) + ".json")


def worktree_map(repo):
    out = git("worktree", "list", "--porcelain", cwd=repo)
    result = {}
    current = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = line[9:]
        elif line.startswith("branch ") and current:
            result[line[7:]] = current
    return result


def launch_worker(repo, name, output):
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_worker", str(repo), name],
                            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                            start_new_session=True, close_fds=True)


def start(repo, args):
    validate_id(args.name)
    item = get_account(repo, args.account)
    if not shutil.which(item["provider"]):
        raise Error(f"Executável {item['provider']} não encontrado.")
    ensure_state_ignored(repo)
    ensure_ready(repo)
    branch = f"bamberg/{args.name}"
    worktrees = state_dir(repo) / "worktrees"
    if worktrees.is_symlink():
        raise Error("O diretório .bamberg/worktrees não pode ser um link simbólico.")
    path = worktrees / args.name
    with lock(repo):
        if job_path(repo, args.name).exists() or path.exists() or path.is_symlink():
            raise Error("Esta tarefa já existe; escolha outro nome.")
        if git("show-ref", "--verify", f"refs/heads/{branch}", cwd=repo, check=False):
            raise Error("A branch da tarefa já existe.")
        if f"refs/heads/{branch}" in worktree_map(repo):
            raise Error("A branch já está ocupada por outra worktree.")
        # Checkout hooks run on the host, before the agent enters bubblewrap.
        git("-c", "core.hooksPath=/dev/null", "worktree", "add", "-b", branch, str(path), "HEAD", cwd=repo)
        job = {"name": args.name, "account": args.account, "provider": item["provider"], "branch": branch,
               "worktree": str(path), "task": args.task, "status": "starting", "created": dt.datetime.now(dt.timezone.utc).isoformat()}
        save(job_path(repo, args.name), job)
        log = state_dir(repo) / "jobs" / (args.name + ".log")
        with log.open("ab") as output:
            worker = launch_worker(repo, args.name, output)
        job = read(job_path(repo, args.name))
        job["pid"] = worker.pid
        save(job_path(repo, args.name), job)
    print(f"Iniciada: {args.name} | {item['provider']}:{args.account} | {branch}\nWorktree: {path}\nLog: {log}")


def worker(repo, name):
    path = job_path(repo, name)
    job = read(path)
    if not job:
        raise Error("Tarefa ausente.")
    item = get_account(repo, job["account"])
    wt = Path(job["worktree"])
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=wt)
    if branch != job["branch"] or worktree_map(repo).get("refs/heads/" + branch) != str(wt):
        raise Error("Branch/worktree divergente; execução cancelada.")
    prompt = (f"Tarefa: {job['task']}\n\nTrabalhe somente nesta worktree ({wt}) e branch ({branch}). "
              "Não altere outras worktrees, o repositório principal ou configurações de outras contas. "
              "Não tente fazer commit; deixe as mudanças para revisão.")
    if item["provider"] == "claude":
        cmd = ["claude", "-p", "--permission-mode", "acceptEdits", prompt]
    else:
        cmd = ["codex", "exec", "--sandbox", "workspace-write", "--cd", str(wt), prompt]
    # The host filesystem is read-only. Only this task's worktree and account
    # profile are writable. Git's shared administrative directory stays read-only.
    wrapped = ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--bind", str(wt), str(wt), "--bind", item["home"], item["home"],
               "--chdir", str(wt), "--", *cmd]
    with lock(repo):
        job = read(path)
        if job["status"] == "stopped":
            return 143
        job["status"] = "running"
        save(path, job)
    try:
        child = subprocess.Popen(wrapped, cwd=wt, env=account_env(item), start_new_session=True)
        with lock(repo):
            job = read(path)
            job["child_pid"] = child.pid
            save(path, job)
        code = child.wait()
    except Exception as exc:
        print(f"Erro ao executar agente: {exc}", flush=True)
        code = 1
    with lock(repo):
        job = read(path)
        if job["status"] != "stopped":
            job["status"] = "completed" if code == 0 else "failed"
        job["exit_code"] = code
        job["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save(path, job)
    return code


def jobs(repo):
    folder = state_dir(repo) / "jobs"
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        item = read(path)
        status = item["status"]
        if status in ("starting", "running"):
            try:
                os.kill(item.get("pid", -1), 0)
            except ProcessLookupError:
                status = "interrupted"
            except PermissionError:
                pass
        print(f"{item['name']:20} {status:12} {item['provider']}:{item['account']:16} {item['branch']}")


def details(repo, name):
    item = read(job_path(repo, name))
    if not item:
        raise Error("Tarefa não encontrada.")
    return item


def stop(repo, name):
    with lock(repo):
        item = details(repo, name)
        if item["status"] not in ("running", "starting"):
            raise Error("A tarefa não está em execução.")
        for key in ("child_pid", "pid"):
            pid = item.get(key)
            if pid:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        item["status"] = "stopped"
        save(job_path(repo, name), item)
    print(f"Tarefa {name} interrompida.")


def show_log(repo, name):
    details(repo, name)
    path = state_dir(repo) / "jobs" / (name + ".log")
    if path.exists():
        print(path.read_text(errors="replace")[-20000:])


def confirm_cleanup(name, branch, worktree):
    # Workers have no terminal, and there is deliberately no --yes option.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Error("Limpeza exige um terminal interativo usado por você.")
    phrase = f"APAGAR {name}"
    try:
        with open("/dev/tty", "r+") as terminal:
            terminal.write(f"Remover worktree {worktree}?\nA branch {branch} e os logs serão preservados.\nDigite {phrase} para confirmar: ")
            terminal.flush()
            answer = terminal.readline().strip()
    except OSError as exc:
        raise Error("Não foi possível ler a confirmação do terminal.") from exc
    if answer != phrase:
        raise Error("Limpeza cancelada; confirmação incorreta.")


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    # A zombie has exited; Linux may retain its PID until its parent reaps it.
    try:
        status = Path(f"/proc/{pid}/stat").read_text()
        if status.rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except FileNotFoundError:
        return False
    except (OSError, IndexError):
        pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def cleanup(repo, name):
    validate_id(name)
    if Path.cwd().resolve() != repo or Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd())).resolve() != repo:
        raise Error("Execute cleanup na raiz da worktree principal.")
    # Check this before reading task data, so even a failed attempt by a worker
    # or a script cannot disclose the interactive confirmation path.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Error("Limpeza exige um terminal interativo usado por você.")
    expected = state_dir(repo) / "worktrees" / name
    with lock(repo):
        item = details(repo, name)
        branch = f"bamberg/{name}"
        if item["branch"] != branch or item["worktree"] != str(expected):
            raise Error("Metadados da tarefa divergentes; limpeza cancelada.")
        if expected.is_symlink() or not expected.is_dir():
            raise Error("Worktree ausente ou alterada; limpeza cancelada.")
        if item["status"] not in ("completed", "failed", "stopped"):
            raise Error("A tarefa ainda não terminou. Aguarde ou use 'bamberg stop'.")
        if process_alive(item.get("pid")) or process_alive(item.get("child_pid")):
            raise Error("Ainda há processo da tarefa ativo; limpeza cancelada.")
        mapping = worktree_map(repo)
        if mapping.get("refs/heads/" + branch) != str(expected):
            raise Error("A branch não está vinculada à worktree esperada.")
        if git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=expected) != branch:
            raise Error("Branch da worktree divergente; limpeza cancelada.")
        main_branch = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=repo)
        if branch == main_branch:
            raise Error("A branch principal nunca pode ser removida por cleanup.")
        main_head = git("rev-parse", "HEAD", cwd=repo)
        main_status = git("status", "--porcelain", "--untracked-files=all", cwd=repo)
        if main_status:
            raise Error("A worktree principal precisa estar limpa antes da limpeza.")
        # --ignored catches files Git might otherwise silently delete, such as
        # build artifacts and .env files. No force-removal option is exposed.
        dirty = git("status", "--porcelain", "--untracked-files=all", "--ignored=matching", cwd=expected)
        if dirty:
            raise Error("A worktree contém alterações ou arquivos extras (inclusive ignorados). Revise e salve esses dados antes de limpar.\n" + dirty[:1000])
        confirm_cleanup(name, branch, expected)
        # Recheck after the human confirmation in case files changed meanwhile.
        if git("status", "--porcelain", "--untracked-files=all", "--ignored=matching", cwd=expected):
            raise Error("A worktree mudou durante a confirmação; limpeza cancelada.")
        if git("rev-parse", "HEAD", cwd=repo) != main_head or git("status", "--porcelain", "--untracked-files=all", cwd=repo) != main_status:
            raise Error("A branch principal mudou durante a confirmação; limpeza cancelada.")
        git("-c", "core.hooksPath=/dev/null", "worktree", "remove", str(expected), cwd=repo)
        item["status"] = "cleaned"
        item["cleaned"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save(job_path(repo, name), item)
        if git("rev-parse", "HEAD", cwd=repo) != main_head or git("status", "--porcelain", "--untracked-files=all", cwd=repo) != main_status:
            raise Error("A worktree principal mudou durante a limpeza; verifique o repositório imediatamente.")
        if not git("show-ref", "--verify", f"refs/heads/{branch}", cwd=repo, check=False):
            raise Error("A branch da tarefa não foi encontrada após a limpeza; verifique o repositório.")
    print(f"Worktree {name} removida. Branch {branch} e logs preservados.")


def request_json(url, token, headers=None):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "bamberg-cli/0.1", **(headers or {})})
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.load(response)


def token_from(item):
    home = Path(item["home"])
    if item["provider"] == "claude":
        data = read(home / ".credentials.json", {})
        return data.get("claudeAiOauth", {}).get("accessToken"), None
    data = read(home / "auth.json", {})
    tokens = data.get("tokens") or {}
    return tokens.get("access_token"), tokens.get("account_id")


def window(data, *keys):
    for key in keys:
        val = data.get(key)
        if isinstance(val, dict):
            percent = val.get("utilization", val.get("used_percent", val.get("percent")))
            if percent is None and isinstance(val.get("percent_left"), (int, float)):
                percent = 100 - val["percent_left"]
            if percent is None:
                continue
            reset = val.get("resets_at", val.get("reset_at", val.get("reset_time_ms")))
            if reset is None and val.get("reset_after_seconds") is not None:
                reset = time.time() + val["reset_after_seconds"]
            return float(percent), reset
    return None


def codex_windows(data):
    limits = data.get("rate_limit") or data.get("rate_limits") or data
    first = window(limits, "five_hour")
    second = window(limits, "weekly")
    for key in ("primary_window", "secondary_window"):
        val = limits.get(key)
        if not isinstance(val, dict):
            continue
        duration = val.get("limit_window_seconds") or val.get("window_seconds")
        if duration is None:
            if key == "primary_window" and not first:
                first = window(limits, key)
            elif key == "secondary_window" and not second:
                second = window(limits, key)
        elif duration <= 20000 and not first:
            first = window(limits, key)
        elif duration > 20000 and not second:
            second = window(limits, key)
    return first, second


def claude_windows(data):
    if isinstance(data, dict):
        return window(data, "five_hour"), window(data, "seven_day")
    if isinstance(data, list):
        rows = {row.get("kind"): row for row in data if isinstance(row, dict)}
        first = window({"session": rows.get("session")}, "session")
        second = window({"weekly_all": rows.get("weekly_all")}, "weekly_all")
        return first, second
    return None, None


def reset_text(value, timezone):
    if value is None:
        return "Reset indisponível"
    try:
        if isinstance(value, (float, int)):
            moment = dt.datetime.fromtimestamp(value / 1000 if value > 1e11 else value, dt.timezone.utc)
        else:
            moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "Reseta " + moment.astimezone(timezone).strftime("%d/%m %H:%M") + f" ({timezone.key})"
    except (ValueError, TypeError, OverflowError):
        return "Reset indisponível"


def meter(label, value, timezone):
    print(label)
    if value is None:
        print("Indisponível\n")
        return
    percent, reset = value
    count = max(0, min(40, round(percent * 40 / 100)))
    print("█" * count + "░" * (40 - count) + f" {percent:g}% usado")
    print(reset_text(reset, timezone) + "\n")


def usage(repo, args):
    try:
        timezone = ZoneInfo(args.timezone)
    except Exception:
        raise Error("Fuso horário inválido.")
    accounts = config(repo)["accounts"]
    if not accounts:
        raise Error("Nenhuma conta cadastrada. Use: bamberg account add ...")
    for name, item in accounts.items():
        print(f"{item['label']} ({name} — {item['provider']})")
        try:
            token, account_id = token_from(item)
            if not token:
                raise Error("Login OAuth ausente; execute account login para esta conta.")
            if item["provider"] == "claude":
                data = request_json("https://api.anthropic.com/api/oauth/usage", token, {"anthropic-beta": "oauth-2025-04-20"})
                first, second = claude_windows(data)
            else:
                headers = {"ChatGPT-Account-Id": account_id} if account_id else {}
                data = request_json("https://chatgpt.com/backend-api/wham/usage", token, headers)
                first, second = codex_windows(data)
            meter("Sessão atual (5h)", first, timezone)
            meter("Semana atual (todos os modelos)", second, timezone)
        except (OSError, ValueError, KeyError, urllib.error.HTTPError, Error) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                message = f"HTTP {exc.code} ao consultar uso; faça login novamente ou tente depois."
            else:
                message = str(exc)
            print("Uso indisponível: " + message + "\n")


def parser():
    p = argparse.ArgumentParser(prog="bamberg", description="Orquestra Claude e Codex em worktrees isoladas")
    sub = p.add_subparsers(dest="command", required=True)
    acc = sub.add_parser("account", help="Gerenciar contas")
    accsub = acc.add_subparsers(dest="action", required=True)
    add = accsub.add_parser("add")
    add.add_argument("id")
    add.add_argument("--provider", required=True, choices=("claude", "codex"))
    add.add_argument("--home", required=True, help="Diretório de perfil exclusivo desta conta")
    add.add_argument("--label", help="Email ou nome exibido")
    login = accsub.add_parser("login")
    login.add_argument("id")
    accsub.add_parser("list")
    run = sub.add_parser("run", help="Criar worktree e executar agente em segundo plano")
    run.add_argument("name")
    run.add_argument("--account", required=True)
    run.add_argument("--task", required=True)
    sub.add_parser("jobs")
    for action in ("log", "stop"):
        sp = sub.add_parser(action)
        sp.add_argument("name")
    clean = sub.add_parser("cleanup", help="Remover manualmente uma worktree concluída e limpa")
    clean.add_argument("name")
    u = sub.add_parser("usage", aliases=["/usage"])
    u.add_argument("--timezone", default="America/Sao_Paulo")
    hidden = sub.add_parser("_worker", help=argparse.SUPPRESS)
    hidden.add_argument("repo")
    hidden.add_argument("name")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "_worker":
            return worker(Path(args.repo), args.name)
        repo = root()
        if args.command == "account":
            if args.action == "add":
                account_add(repo, args)
            elif args.action == "login":
                return account_login(repo, args)
            else:
                for name, item in config(repo)["accounts"].items():
                    print(f"{name:20} {item['provider']:8} {item['label']} | {item['home']}")
        elif args.command == "run":
            start(repo, args)
        elif args.command == "jobs":
            jobs(repo)
        elif args.command == "log":
            show_log(repo, args.name)
        elif args.command == "stop":
            stop(repo, args.name)
        elif args.command == "cleanup":
            cleanup(repo, args.name)
        elif args.command in ("usage", "/usage"):
            usage(repo, args)
        return 0
    except Error as exc:
        print("Erro: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
