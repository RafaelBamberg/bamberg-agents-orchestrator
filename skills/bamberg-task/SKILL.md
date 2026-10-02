---
name: bamberg-task
description: Trabalhar numa tarefa em paralelo com outros agentes (Claude Code, Codex, inclusive várias instâncias do mesmo) no mesmo repositório, numa branch e worktree próprias, com commit, push e PR, sem atrapalhar nem apagar o trabalho dos outros. Use ao iniciar qualquer tarefa de código quando outros agentes podem estar trabalhando no mesmo repositório, ou quando o usuário der o nome de uma branch para a tarefa.
---

# Tarefa em branch e worktree próprias

Este fluxo cobre só branch, worktree e convivência com outros agentes. Outro agente é qualquer outra instância, inclusive outra sessão do Claude Code ou do Codex igual a você; só são suas a branch e a worktree que você criou nesta sessão ou que o usuário mandou usar. Verificações seguem as instruções do projeto. Mensagens de commit são semânticas (`fix: ...`, `feat: ...`, `chore: ...`). Não faça merge (`git merge`, `gh pr merge` ou pelo GitHub) a menos que o usuário peça explicitamente, e nunca suba nada direto para a `main`. Abaixo, `<branch>` é o nome exato dado pelo usuário ou, se ele não der, um nome criado a partir da demanda com prefixo semântico e o número da issue, se houver ("issue 57 - Problemas com o cartão" → `fix/card-adjustment-issue-57`), `<pasta>` é o mesmo nome com `/` trocado por `-` e `<projeto>` é o nome da pasta do checkout (em `development/fechalead-dev/fechalead`, é `fechalead`). Os comandos rodam a partir do checkout.

## 1. Preparar

No checkout do projeto (`development/<projeto>-dev/<projeto>`):

```sh
git worktree list
git branch --list '<branch>'
```

- Se `<branch>` aparece em `git worktree list`, ou se a pasta `../.<projeto>-tmp/<pasta>` já existe, ela é de outro agente. Se o nome foi dado pelo usuário, pare e avise-o; se foi você quem escolheu, escolha outro nome.
- Branch nova, partindo da base pedida pelo usuário (ou da branch atual do checkout principal):

```sh
git worktree add -b '<branch>' '../.<projeto>-tmp/<pasta>' <base>
```

- Branch existente que não está em nenhuma worktree, quando o usuário pedir para continuá-la:

```sh
git worktree add '../.<projeto>-tmp/<pasta>' '<branch>'
```

Se `git worktree add` falhar porque a branch ou a pasta já existe, outro agente pode tê-la criado ao mesmo tempo: trate como ocupada (regra acima) e não force.

Se `git status --short` no checkout principal mostrar arquivos modificados, avise o usuário que essas alterações não estão na sua worktree.

## 2. Trabalhar

- Faça tudo dentro de `../.<projeto>-tmp/<pasta>`: edição, instalação de dependências, testes e build.
- Confira com `git -C '../.<projeto>-tmp/<pasta>' branch --show-current` que você está na `<branch>` antes de commitar.
- Antes de subir servidores, verifique se a porta está livre.

## 3. Entregar

```sh
git -C '../.<projeto>-tmp/<pasta>' add <arquivos>
git -C '../.<projeto>-tmp/<pasta>' commit -m '<tipo>: <mensagem>'
git -C '../.<projeto>-tmp/<pasta>' push -u origin '<branch>'
```

Sempre abra o PR ao terminar. A descrição diz o que foi feito e termina com `by: Claude Code` ou `by: Codex`, conforme o agente que você é:

```sh
cd '../.<projeto>-tmp/<pasta>' && gh pr create --head '<branch>' --title '<título>' --body '<o que foi feito>

by: Claude Code'
```

Relate a branch, a worktree e o link do PR.

## 4. Ajustes pedidos depois

Faça commit e push do ajuste na mesma branch; o PR aberto é atualizado sozinho, sem abrir outro. Só não suba se o usuário pedir explicitamente para não subir.

```sh
git -C '../.<projeto>-tmp/<pasta>' add <arquivos>
git -C '../.<projeto>-tmp/<pasta>' commit -m '<tipo>: <mensagem>'
git -C '../.<projeto>-tmp/<pasta>' push
```

## 5. Remover a worktree (só se o usuário pedir)

```sh
git -C '../.<projeto>-tmp/<pasta>' status --short   # precisa estar vazio
git worktree remove '../.<projeto>-tmp/<pasta>'
```

Sem `--force`. A branch e os commits continuam existindo.
