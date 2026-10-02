# Bamberg

Instruções para o Claude Code e o Codex trabalharem ao mesmo tempo no mesmo repositório, cada um na sua branch, sem atrapalhar nem apagar o trabalho do outro. Estes arquivos dizem como eles devem se comportar.

- [`AGENTS.md`](AGENTS.md): as regras. O Codex lê `AGENTS.md`; o Claude Code lê `CLAUDE.md`, que importa o mesmo arquivo.
- [`skills/bamberg-task/SKILL.md`](skills/bamberg-task/SKILL.md): o passo a passo com os comandos Git (worktree, commit, push, PR). Fica disponível em `.claude/skills/` e `.agents/skills/`.

## Como funciona

Cada agente recebe do usuário o nome de uma branch, por exemplo `feat/teste`, e trabalha numa worktree própria em `.dev/feat-teste`. A pasta `.dev/` não é versionada. Ele faz commit e push da própria branch e abre PR quando pedido. Não mexe no checkout principal, em worktrees ou branches de outros agentes, e não usa `--force`.

## Usar em outro projeto

Nesta máquina, as regras valem para qualquer projeto:

- `~/.claude/CLAUDE.md` importa `/home/user/bamberg-cli/AGENTS.md`.
- `~/.codex/AGENTS.md` instrui o Codex a ler e seguir esse arquivo.
- A skill está ligada em `~/.claude/skills/bamberg-task` e `~/.agents/skills/bamberg-task`.

O Claude Code e o Codex também carregam o `AGENTS.md`/`CLAUDE.md` do próprio projeto, e os agentes seguem os dois. Se este checkout mudar de lugar, atualize esses três caminhos.

Ao abrir cada agente, diga a branch e a tarefa, por exemplo: "Na branch `feat/teste`, adicione um log em `scripts/setup.mjs`, faça commit, push e abra o PR."
