---
name: bamberg-orchestrator
description: Orchestrate parallel Claude Code and Codex tasks with the Bamberg CLI, including account selection, isolated worktrees, status review, and safe handoff to the human operator.
---

# Orquestração com Bamberg

Use esta skill quando o usuário pedir para distribuir tarefas entre Claude Code e Codex ou acompanhar tarefas já iniciadas pelo CLI.

1. Entre na raiz do repositório **alvo**. Verifique a branch principal, `git status --short`, `bamberg account list` e `bamberg jobs`. Não use o repositório de instalação do CLI como projeto alvo por engano.
2. Divida o pedido em tarefas com objetivos verificáveis e nomes únicos. Cada `bamberg run <nome> --account <id> --task <descrição>` cria sua própria branch e worktree dentro de `.bamberg/worktrees/`. Não crie worktrees manualmente ou diretórios irmãos.
3. Use apenas contas cadastradas pelo operador. Para autenticação, peça que ele execute `bamberg account login <id>` no próprio terminal; não abra, copie ou exponha arquivos de credenciais.
4. Acompanhe com `bamberg jobs` e `bamberg log <nome>`. Revise as mudanças com `git -C .bamberg/worktrees/<nome> status` e `git -C .bamberg/worktrees/<nome> diff`. Relate conflitos de integração potenciais; não faça merge ou push sem autorização.
5. `bamberg cleanup` é exclusivo do operador humano no checkout principal. Nunca execute, automatize ou contorne sua confirmação. Entregue ao usuário o nome da tarefa e indique a limpeza somente depois que ele revisar e salvar o trabalho. O comando recusa worktrees com mudanças ou arquivos extras e preserva a branch.

Se o CLI recusar uma operação, reporte a causa. Não tente contornar o sandbox, a exclusividade de branch ou os limites de escrita.
