# Bamberg CLI: instruções para agentes que mantêm este repositório

Este repositório implementa um orquestrador de Claude Code e Codex. Mantenha as garantias no código; instruções em Markdown sozinhas não impõem isolamento.

## Limites de trabalho

- Trabalhe apenas na tarefa solicitada e neste checkout. Não crie worktrees, branches ou diretórios irmãos por conta própria.
- Não execute `bamberg cleanup` como agente. A limpeza é uma operação manual do usuário no terminal principal.
- Não faça `git push`, merge, rebase, remoção forçada de worktree ou exclusão de branch sem pedido explícito do usuário.
- Não leia, copie ou registre credenciais OAuth, arquivos `auth.json`, `.credentials.json` ou o conteúdo de `.bamberg/config.json`. Testes devem usar dados fictícios.

## Invariantes da implementação

- Uma tarefa tem exatamente uma branch `bamberg/<nome>` e uma worktree em `<repo>/.bamberg/worktrees/<nome>`; nomes e caminhos não podem se sobrepor.
- Agentes executam dentro de `bwrap`, com escrita apenas na worktree própria, no perfil da conta escolhida e em `/tmp` privado. O Git compartilhado e as outras worktrees ficam sem escrita.
- O operador controla a integração. `cleanup` não pode usar `--force`, apagar branch/commits ou remover arquivos alterados, novos ou ignorados.
- O contrato em `skills/bamberg-task/SKILL.md` é injetado na execução de **ambos** os provedores. Atualize esse arquivo quando mudar regras de tarefa; mantenha testes que confirmem a injeção.
- O estado `.bamberg/` é local ao projeto alvo e ignorado por `.git/info/exclude`; jamais coloque dados de conta no Git.

## Verificação

Rode `python3 -m unittest discover -s tests -v` após mudanças de comportamento. Confira `git status --short` e `git ls-files` antes de concluir. Documente comandos e limites reais no `README.md`.

Para orquestrar tarefas com este CLI, use a skill `bamberg-orchestrator` quando ela estiver disponível; o fluxo também está em `README.md`.
