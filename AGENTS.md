# Trabalho em paralelo: vários agentes no mesmo repositório

O usuário roda o Claude Code e o Codex por conta própria, ao mesmo tempo, no mesmo repositório, e pode abrir várias instâncias do mesmo agente, por exemplo o Claude em três terminais, cada um com uma tarefa diferente. Cada instância é um agente separado: trabalha na sua própria branch e na sua própria worktree, em paralelo, sem atrapalhar as outras e sem apagar o trabalho de ninguém.

Nestas regras, "outro agente" é qualquer outra instância, inclusive outra sessão do Claude Code ou do Codex igual a você. Uma branch ou worktree é sua apenas se foi você, nesta sessão, quem a criou, ou se o usuário mandou você usá-la; não é sua só porque foi criada pelo mesmo tipo de agente.

Estas regras tratam **apenas** do trabalho em paralelo: branch, worktree, convivência com os outros agentes e entrega por PR. Para todo o resto (código, testes, estilo), valem as instruções do próprio projeto (`AGENTS.md`, `CLAUDE.md`), que você segue junto com estas. Em conflito, vale a do projeto e um pedido explícito do usuário prevalece sobre ambas, exceto que as regras da seção "Git na sua branch" valem mesmo contra as instruções do projeto.

Não copie estas regras para o `AGENTS.md`, o `CLAUDE.md` ou outro arquivo do projeto, nem altere esses arquivos por causa deste fluxo.

Para o passo a passo com os comandos, use a skill `bamberg-task`.

## Sua branch e sua worktree

- Use a branch com o nome **exato** que o usuário der, por exemplo `feat/teste`, sem acrescentar prefixos a ele. Se ele não der um nome, crie um a partir da demanda, com prefixo semântico (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/` etc.) e o número da issue, se houver, e informe qual escolheu. Exemplo: "issue 57 - Problemas com o cartão" → `fix/card-adjustment-issue-57`.
- Os projetos ficam em `development/<projeto>-dev/<projeto>`, e o usuário abre os agentes nesse checkout. Trabalhe numa worktree própria em `development/<projeto>-dev/.<projeto>-tmp/<pasta>`, ou seja, `../.<projeto>-tmp/<pasta>` a partir do checkout, onde `<pasta>` é o nome da branch com `/` trocado por `-`. Exemplo: em `development/fechalead-dev/fechalead`, a branch `feat/teste` fica em `development/fechalead-dev/.fechalead-tmp/feat-teste`. Crie essa worktree antes de editar qualquer arquivo.
- A pasta `.<projeto>-tmp` fica fora do repositório do projeto e é limpa pelo usuário depois do desenvolvimento. Não a crie em outro lugar nem altere o `.gitignore` do projeto por causa dela.
- Se a branch já estiver aberta em outra worktree, ou se a pasta da worktree já existir, ela é de outro agente. Não a use. Se o nome foi dado pelo usuário, avise-o; se foi você quem escolheu, escolha outro nome.
- Se `git worktree add` falhar porque a branch ou a pasta já existe, outro agente pode tê-la criado no mesmo instante. Trate como ocupada, como no item acima, e não force.
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

Estas regras valem mesmo que as instruções do projeto digam outra coisa.

- Use mensagens de commit semânticas, com o mesmo tipo das branches: `fix: ajusta validação do cartão`, `feat: ...`, `chore: ...`.
- Não faça merge (`git merge`, `gh pr merge` ou pela interface do GitHub), a menos que o usuário peça explicitamente.
- Nunca suba nada direto para a `main`, em hipótese alguma. Faça commit e push apenas da sua branch (`git push -u origin <branch>`).
- Ao terminar a tarefa, sempre abra um pull request da sua branch. A descrição do PR deve dizer o que foi feito e terminar com `by: Claude Code` ou `by: Codex`, conforme o agente que você é.
- Se o usuário pedir ajustes, faça commit do ajuste e push para a mesma branch, para que ele entre no PR em que você está trabalhando. Só não suba se o usuário pedir explicitamente para não subir.

## Ao terminar

Informe a branch, a worktree e o link do PR. Remova a sua worktree só se o usuário pedir, e nunca com alterações sem commit.
