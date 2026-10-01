# Bamberg CLI

Orquestra tarefas paralelas no Claude Code e no Codex. Cada tarefa recebe uma branch `bamberg/<nome>` e uma worktree própria. Os agentes rodam em segundo plano; `bubblewrap` permite escrita apenas nessa worktree e no perfil da conta selecionada. O repositório principal, as demais worktrees e o diretório Git compartilhado ficam em leitura. Por isso, os agentes deixam as alterações sem commit para revisão e integração manual.

## Requisitos

- Linux com Python 3.10+, Git e `bubblewrap` (`bwrap`).
- `claude` e/ou `codex` instalados e disponíveis no `PATH`.
- Repositório Git com pelo menos um commit e árvore principal limpa antes de iniciar uma tarefa.

O projeto não instala dependências Python. Para invocar o CLI, use `python3 /caminho/para/bamberg-cli/bamberg` ou coloque o executável `bamberg` no `PATH`.

## Instruções e skills dos agentes

Este repositório inclui [`AGENTS.md`](AGENTS.md) para Codex e [`CLAUDE.md`](CLAUDE.md), que importa as mesmas regras para Claude Code. As skills canônicas ficam em `skills/`; links em `.agents/skills/` e `.claude/skills/` permitem descoberta automática no checkout do CLI.

Esses caminhos seguem a documentação de [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) e [skills do Codex](https://learn.chatgpt.com/docs/build-skills), além das regras de [memória](https://code.claude.com/docs/en/memory) e [skills do Claude Code](https://code.claude.com/docs/en/skills). `CODEX.md` não é necessário neste projeto: `AGENTS.md` é o arquivo de instruções reconhecido pelo Codex.

- `bamberg-orchestrator`: orienta a divisão, delegação, revisão e entrega ao operador.
- `bamberg-task`: define os limites de cada agente executor. O CLI injeta seu conteúdo como instrução adicional de sistema no Claude e de desenvolvedor no Codex, com nome, branch e worktree da tarefa. Isso funciona mesmo quando o projeto alvo está em outro repositório.

Para que a skill de orquestração seja descoberta em **qualquer** projeto seu, execute uma vez `bamberg skills install`. O comando cria links em `~/.agents/skills/` e `~/.claude/skills/`, sem substituir skills existentes. A instalação é pessoal e explícita; ela não altera o repositório alvo. Se mover ou remover o checkout do Bamberg CLI, instale novamente a partir do novo caminho.

Instruções Markdown ajudam os agentes a seguir o fluxo. O bloqueio efetivo de escrita em outras worktrees vem do sandbox `bubblewrap`; arquivos de instrução não substituem esse isolamento. Instruções existentes no projeto alvo continuam sendo lidas pelos próprios CLIs.

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

## Limpeza manual e segura

Depois de revisar e salvar as alterações da tarefa, volte à **raiz da worktree principal** e rode o comando em seu próprio terminal:

```sh
bamberg cleanup api
```

O CLI mostra o caminho e exige que você digite `APAGAR api` no terminal. Não existe opção para pular essa confirmação. Um agente iniciado pelo CLI não tem terminal interativo nem permissão de escrita no diretório Git compartilhado; ele não consegue executar a limpeza. Isso é uma proteção contra os agentes orquestrados, não autenticação contra outra pessoa ou processo que já tenha acesso irrestrito à sua conta do sistema. O comando aceita somente tarefas cadastradas e concluídas ou interrompidas. Ele recusa a remoção se a worktree tiver alterações, arquivos novos ou ignorados, se um processo ainda estiver ativo ou se a worktree principal estiver suja. Não usa `--force`.

A limpeza remove apenas a worktree da tarefa. A branch `bamberg/api`, seus commits, o registro da tarefa e o log permanecem. O CLI confere o commit e o estado da worktree principal antes e depois da operação. Para tarefas com alterações ainda sem commit, salve-as na branch da tarefa e revise o resultado antes de executar `cleanup`.

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
