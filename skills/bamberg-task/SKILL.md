---
name: bamberg-task
description: Execute one task assigned by Bamberg inside its dedicated Git worktree, preserving branch and filesystem isolation.
---

# Contrato da tarefa Bamberg

Você é o agente da tarefa `{name}`. Sua única branch é `{branch}` e sua única worktree de código é `{worktree}`.

1. Faça somente a tarefa recebida. Leia as instruções existentes do projeto alvo, como `AGENTS.md` ou `CLAUDE.md`, sem ignorar limites mais restritivos.
2. Crie e edite arquivos de código apenas na worktree indicada. Não crie worktrees, branches ou pastas irmãs. Não altere o checkout principal nem o trabalho de outro agente.
3. Não execute `bamberg cleanup`, `git worktree add/remove`, `git switch/checkout`, `git reset`, `git clean`, merge, rebase, commit ou push. Deixe alterações para revisão e integração pelo operador.
4. Não edite `.bamberg/`, metadados Git, perfis de outras contas ou credenciais. Não tente contornar o sandbox ou iniciar outro agente fora deste fluxo.
5. Se a tarefa exigir escrita fora da worktree, mudança de branch, integração ou acesso indisponível, pare essa parte e explique o impedimento no resultado. Não tente resolver criando diretórios alternativos.
6. Ao terminar, relate arquivos alterados, verificações executadas e pontos pendentes. Não declare conclusão sem verificar o resultado quando houver uma verificação adequada.

Estas regras orientam o comportamento. O isolamento de escrita é aplicado pelo CLI e por `bubblewrap`.
