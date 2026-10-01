# Bamberg CLI

Orquestra tarefas paralelas no Claude Code e no Codex. Cada tarefa recebe uma branch `bamberg/<nome>` e uma worktree própria. Os agentes rodam em segundo plano; `bubblewrap` permite escrita apenas nessa worktree e no perfil da conta selecionada. O repositório principal, as demais worktrees e o diretório Git compartilhado ficam em leitura. Por isso, os agentes deixam as alterações sem commit para revisão e integração manual.

## Requisitos

- Linux com Python 3.10+, Git e `bubblewrap` (`bwrap`).
- `claude` e/ou `codex` instalados e disponíveis no `PATH`.
- Repositório Git com pelo menos um commit e árvore principal limpa antes de iniciar uma tarefa.

O projeto não instala dependências Python. Para invocar o CLI, use `python3 /caminho/para/bamberg-cli/bamberg` ou coloque o executável `bamberg` no `PATH`.

## Contas

Use um diretório de perfil exclusivo por conta. O identificador é usado em comandos; `--label` pode ser o email da conta. O CLI não armazena senhas ou tokens no arquivo de configuração. As credenciais permanecem nos diretórios de perfil dos próprios provedores.

```sh
bamberg account add claude-pessoal --provider claude --home ~/.config/bamberg/claude-pessoal --label pessoal@example.com
bamberg account add claude-trabalho --provider claude --home ~/.config/bamberg/claude-trabalho --label trabalho@example.com
bamberg account add codex-pessoal --provider codex --home ~/.config/bamberg/codex-pessoal --label pessoal@example.com
bamberg account login claude-pessoal
bamberg account login claude-trabalho
bamberg account login codex-pessoal
bamberg account list
```

`account login` chama `claude auth login` ou `codex login` com `CLAUDE_CONFIG_DIR` ou `CODEX_HOME` apontando para o perfil correspondente. Para aproveitar uma sessão já autenticada, cadastre seu diretório existente (`~/.claude` ou `~/.codex`) como uma das contas.

## Tarefas

```sh
bamberg run api --account claude-pessoal --task "Implementar a API de pedidos"
bamberg run tests --account codex-pessoal --task "Criar testes da API de pedidos"
bamberg jobs
bamberg log api
bamberg stop tests
```

As worktrees ficam em `.bamberg/worktrees/` **dentro do repositório**, ignoradas pelo Git por uma entrada no `.git/info/exclude` local, e os logs e metadados em `.bamberg/jobs/`. O CLI não cria worktrees irmãs do repositório. A única criação de diretório fora dele é o perfil indicado explicitamente em `account add --home`. Uma segunda tarefa com o mesmo nome ou branch é recusada. A worktree continua disponível após a conclusão para inspecionar o diff e integrar as alterações; não há remoção automática.

```sh
git -C .bamberg/worktrees/api diff
git -C .bamberg/worktrees/api status
```

O sandbox protege contra escrita local em outras worktrees, mesmo que uma tarefa peça isso. O CLI desativa hooks do Git ao criar worktrees, pois essa etapa ocorre fora do sandbox. Ele não impede leitura de arquivos acessíveis ao usuário nem chamadas de rede pelos agentes. Scripts ou hooks do repositório executados pelo agente dentro do sandbox também ficam sujeitos ao mesmo limite de escrita. Contas com diretórios de perfil sobrepostos são recusadas.

## Uso por conta

```sh
bamberg usage
bamberg /usage
bamberg usage --timezone America/Sao_Paulo
```

Mostra a porcentagem consumida e o horário de reset das janelas de 5 horas e semanal para cada conta OAuth cadastrada. São limites de uso da assinatura, não uma contagem exata de tokens. Se um serviço omitir uma janela ou recusar a consulta, a conta aparece com `Indisponível`; o CLI não fabrica valores. Tokens de API não fornecem essas janelas.

As consultas usam os endpoints de uso acessíveis pelas sessões OAuth dos CLIs: [Anthropic](https://github.com/anthropics/claude-code/issues/30930) e [Codex](https://github.com/openai/codex/issues/39850). Esses endpoints e formatos podem mudar; o CLI aceita as variantes de resposta documentadas nos testes. O fuso padrão é `America/Sao_Paulo`.

## Testes

```sh
python3 -m unittest discover -s tests -v
```
