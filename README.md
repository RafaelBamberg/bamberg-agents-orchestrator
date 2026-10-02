# bamberg-agent-instructions

Instruções para o Claude Code e o Codex trabalharem ao mesmo tempo no mesmo repositório, cada instância na sua branch, sem atrapalhar nem apagar o trabalho das outras. Vale também para várias instâncias do mesmo agente: por exemplo, o Claude em três terminais, cada um com uma tarefa diferente. Estes arquivos dizem como eles devem se comportar.

- [`AGENTS.md`](AGENTS.md): as regras. O Codex lê `AGENTS.md`; o Claude Code lê `CLAUDE.md`, que importa o mesmo arquivo.
- [`skills/bamberg-task/SKILL.md`](skills/bamberg-task/SKILL.md): o passo a passo com os comandos Git (worktree, commit, push, PR). Fica disponível em `.claude/skills/` e `.agents/skills/`.

## Estrutura

Os projetos ficam em `development/`, que não é versionada:

```
development/fechalead-dev/
├── fechalead/          ← clone do projeto; abra o claude e o codex aqui
└── .fechalead-tmp/     ← worktrees dos agentes, uma por branch
    ├── feat-teste/
    └── fix-login/
```

Cada instância (de qualquer agente) recebe do usuário o nome de uma branch, por exemplo `feat/teste` (ou cria um a partir da demanda, como `fix/card-adjustment-issue-57`), e trabalha em `.fechalead-tmp/feat-teste`. Ela faz commits semânticos (`fix: ...`, `feat: ...`) e push só da própria branch, sempre abre um PR ao terminar (com o que foi feito e `by: Claude Code` ou `by: Codex`) e sobe os ajustes que você pedir para esse mesmo PR. Não faz merge sem você pedir e nunca sobe direto para a `main`. Não mexe no checkout principal nem em worktrees ou branches de outras instâncias, mesmo que sejam do mesmo agente, e não usa `--force`. Depois do desenvolvimento, você limpa a pasta `.<projeto>-tmp`.

## Como as regras chegam aos agentes

As regras valem só dentro de `development/`:

- O Claude Code lê os `CLAUDE.md` das pastas acima de onde é aberto, então carrega o `CLAUDE.md` deste repositório.
- O Codex só lê `AGENTS.md` dentro do repositório do projeto. Por isso, `~/.codex/AGENTS.md` o instrui a seguir `/home/user/bamberg-cli/AGENTS.md` quando estiver dentro de `development/`.
- A skill está ligada em `~/.claude/skills/bamberg-task` e `~/.agents/skills/bamberg-task`.

Os dois agentes também seguem o `AGENTS.md`/`CLAUDE.md` do próprio projeto. Nenhum arquivo do projeto é alterado por este fluxo. Se este checkout mudar de lugar, atualize os caminhos acima.

Ao abrir cada instância, diga uma branch diferente e a tarefa, por exemplo: "Na branch `feat/teste`, adicione um log em `scripts/setup.mjs`."
