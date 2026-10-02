---
name: bamberg-task
description: Trabalhar numa tarefa em paralelo com outros agentes (Claude Code, Codex) no mesmo repositório, numa branch e worktree próprias, com commit, push e PR, sem atrapalhar nem apagar o trabalho dos outros. Use ao iniciar qualquer tarefa de código quando outros agentes podem estar trabalhando no mesmo repositório, ou quando o usuário der o nome de uma branch para a tarefa.
---

# Tarefa em branch e worktree próprias

Siga as regras do `AGENTS.md` deste fluxo. Abaixo, `<branch>` é o nome exato dado pelo usuário e `<pasta>` é o mesmo nome com `/` trocado por `-`.

## 1. Preparar

Na raiz do repositório:

```sh
git worktree list
git branch --list '<branch>'
```

- Se `<branch>` aparece em `git worktree list`, ela é de outro agente: pare e avise o usuário.
- Leia o `AGENTS.md`/`CLAUDE.md` do projeto e siga-os junto com este fluxo.
- Garanta que `.dev/` não seja versionado. Se `git check-ignore -q .dev/x` falhar, acrescente ao exclude local, sem alterar arquivos versionados:

```sh
git check-ignore -q .dev/x || echo '.dev/' >> "$(git rev-parse --git-path info/exclude)"
```

- Branch nova, partindo da base pedida pelo usuário (ou da branch atual do checkout principal):

```sh
git worktree add -b '<branch>' '.dev/<pasta>' <base>
```

- Branch existente que não está em nenhuma worktree, quando o usuário pedir para continuá-la:

```sh
git worktree add '.dev/<pasta>' '<branch>'
```

Se `git status --short` no checkout principal mostrar arquivos modificados, avise o usuário que essas alterações não estão na sua worktree.

## 2. Trabalhar

- Faça tudo dentro de `.dev/<pasta>`: edição, instalação de dependências, testes e build.
- Confira com `git -C '.dev/<pasta>' branch --show-current` que você está na `<branch>` antes de commitar.
- Antes de subir servidores, verifique se a porta está livre.

## 3. Entregar

```sh
git -C '.dev/<pasta>' add <arquivos>
git -C '.dev/<pasta>' commit -m '<mensagem>'
git -C '.dev/<pasta>' push -u origin '<branch>'
```

Para abrir PR, quando pedido:

```sh
cd '.dev/<pasta>' && gh pr create --head '<branch>' --title '<título>' --body '<descrição>'
```

Relate a branch, a worktree, os commits, o link do PR, as verificações executadas e as pendências.

## 4. Remover a worktree (só se o usuário pedir)

```sh
git -C '.dev/<pasta>' status --short   # precisa estar vazio
git worktree remove '.dev/<pasta>'
```

Sem `--force`. A branch e os commits continuam existindo.
