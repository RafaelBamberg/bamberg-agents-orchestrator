# Trabalho em paralelo: vários agentes no mesmo repositório

O usuário roda o Claude Code e o Codex por conta própria, ao mesmo tempo, no mesmo repositório. Cada agente trabalha na sua própria branch e na sua própria worktree, sem atrapalhar os outros e sem apagar o trabalho de ninguém.

Siga estas regras **e também** as instruções do projeto em que está trabalhando (`AGENTS.md`, `CLAUDE.md` e equivalentes na raiz do projeto e nas pastas que tocar). Leia essas instruções antes de começar. Se uma regra do projeto conflitar com estas, siga a do projeto; pedidos explícitos do usuário prevalecem sobre ambas.

Para o passo a passo com os comandos, use a skill `bamberg-task`.

## Sua branch e sua worktree

- Use a branch com o nome **exato** que o usuário der, por exemplo `feat/teste`. Não acrescente prefixos. Se ele não der um nome, escolha um nome curto e descritivo e informe qual escolheu.
- Trabalhe numa worktree própria, em `.dev/<pasta>` dentro do repositório, onde `<pasta>` é o nome da branch com `/` trocado por `-` (`feat/teste` → `.dev/feat-teste`). Crie essa worktree antes de editar qualquer arquivo.
- A pasta `.dev/` não é versionada. Se o projeto ainda não a ignora, acrescente `.dev/` ao exclude local do Git (`.git/info/exclude`), sem alterar arquivos versionados.
- Se a branch pedida já estiver aberta em outra worktree, ela é de outro agente. Não a use; avise o usuário.
- O checkout principal não precisa estar limpo. A worktree parte do último commit da base, então alterações sem commit do checkout principal não aparecem nela. Avise o usuário quando isso acontecer.

## Não atrapalhe os outros agentes

- Edite arquivos apenas dentro da sua worktree. Ler o resto do repositório é permitido.
- Não rode `git checkout`, `git switch`, `git reset`, `git clean`, `git stash` ou `git restore` no checkout principal nem em worktrees de outros agentes.
- Não apague, renomeie, faça rebase ou push em branches que não são suas.
- Não remova worktrees de outros agentes e não rode `git worktree prune`.
- Não use `--force` em push, `git worktree remove` ou `git branch -D`, a menos que o usuário peça.
- Se precisar de uma mudança que está na branch de outro agente, não copie nem edite o trabalho dele; avise o usuário.
- Recursos compartilhados, como portas, bancos de dados e containers, podem estar em uso por outro agente. Antes de subir um serviço, verifique se a porta está livre e prefira uma porta diferente da padrão.

## Git na sua branch

- Você pode fazer commits na sua branch e push dela (`git push -u origin <branch>`).
- Abra PR quando o usuário pedir ou quando a tarefa incluir isso.
- Merge na branch principal ou em branches de outros só com pedido explícito do usuário.

## Ao terminar

Informe a branch, a worktree, os commits, o link do PR (se houver), as verificações que rodou e o que ficou pendente. Remova a sua worktree só se o usuário pedir, e nunca com alterações sem commit.
