# Import Taiga API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

🇧🇷 Português | 🇬🇧 [English](README.md)

> Este é o README em português. A versão em inglês ([README.md](README.md)) é
> a referência principal do projeto e pode ser atualizada primeiro.

Ferramenta em Python para extrair itens (bugs/defeitos) de um relatório `.md`
de QA e criá-los — ou corrigir suas tags depois de criados — como **Issues**
no [Taiga](https://www.taiga.io/) via API REST, sem passar pela criação
manual na interface.

Não é específica de nenhum projeto: a forma como o relatório é interpretado
(como reconhecer cada item, como extrair a severidade, como mapear seções do
relatório para tags do Taiga) fica num arquivo de configuração à parte — ver
[`config.example.json`](config.example.json).

## Por que

Criar dezenas de issues manualmente, um a um, colando campos na UI do Taiga,
é lento e sujeito a erro (severidade errada, tag esquecida, campo em branco).
Este projeto automatiza isso a partir de um relatório de QA já escrito em
Markdown, mantendo um **dry-run por padrão** (nada é criado sem `--apply`
explícito) e um **log local** que evita duplicar issues em reexecuções.

## Requisitos

- Python 3.9+
- Uma conta Taiga com usuário/senha (login "normal"; login via SSO/GitHub/
  GitLab não tem senha e não funciona com este fluxo de autenticação)

```bash
pip install -r requirements.txt
```

## Configuração

### 1. Credenciais (`.env`)

Copie `.env.example` para `.env` e preencha:

```
TAIGA_URL=https://api.taiga.io
TAIGA_WEB_URL=https://tree.taiga.io
TAIGA_PROJECT_SLUG=meu-slug-de-projeto
TAIGA_USER=
TAIGA_PASSWORD=
```

- `TAIGA_URL` — host da **API**. No Taiga Cloud é `https://api.taiga.io`
  (não confundir com o domínio da interface web). Numa instância self-hosted
  costuma ser o mesmo host da interface, ex.: `https://taiga.minhaempresa.com`.
- `TAIGA_WEB_URL` — host da **interface web**, usado só para montar links
  clicáveis no log de import. Se omitido, usa o mesmo valor de `TAIGA_URL`
  (correto para a maioria das instâncias self-hosted). No Taiga Cloud é
  `https://tree.taiga.io` (diferente do host da API).
- `TAIGA_PROJECT_SLUG` — slug do projeto, visível na URL do projeto no Taiga
  (`.../project/<slug>`).
- `.env` nunca é commitado (está no `.gitignore`); a senha é usada só em
  tempo de execução para obter um token via `POST /api/v1/auth` — não fica
  persistida em disco.

### 2. Config de extração (`config.json`)

Copie `config.example.json` para `config.json` e adapte ao seu relatório.
Campos:

| Campo | Descrição |
|---|---|
| `source_label` | Nome do relatório de origem, só para referência na descrição de cada issue criado. |
| `bug_heading_pattern` | Regex com 2 grupos de captura: `(id)` e `(título)` do cabeçalho de cada item no `.md`. Ex.: `^####\s+(BUG-\d{8}-\d{2})\s+—\s+(.*)$`. |
| `severity_pattern` | Regex com 1 grupo de captura: o dígito de severidade dentro do texto do item (essa linha é removida da descrição final). |
| `base_tags` | Lista de tags aplicadas a **todo** item (ex.: o nome do módulo/produto testado). |
| `default_tag` | Tag usada quando nenhuma regra de `heading_tag_rules` bate. |
| `transversal_tag` | Tag adicional aplicada a itens marcados `"transversal": true` (ex.: bugs que afetam o sistema todo, não uma tela específica). |
| `heading_tag_rules` | Lista ordenada de `{pattern, tag, transversal}`. Ao percorrer o `.md` linha a linha, a primeira regra cujo `pattern` bate com uma linha de cabeçalho (`##`, `###`, ...) passa a valer para todo item encontrado depois, até a próxima regra bater. Uma regra sem `tag` **reseta** o mapeamento (útil para seções que não têm tag própria). Regras mais específicas devem vir antes de regras mais genéricas na lista. |
| `fallback_tag_by_keyword` | Lista de `{keyword, tag}` usada só quando `heading_tag_rules` não define nenhuma tag para o item — procura a `keyword` no corpo do item e usa a `tag` correspondente. |

`config.json` também não é commitado — o mapeamento de seções costuma
refletir a estrutura/nomenclatura interna de um projeto específico.

## Uso

### 1. Descoberta (só leitura)

Confirma que as credenciais funcionam e lista os IDs de tipo de issue,
severidade e status configurados no seu projeto Taiga:

```bash
python taiga_discover.py
```

### 2. Extrair o relatório para JSON

```bash
python taiga_import.py extract --report caminho/para/relatorio.md --config config.json --out taiga-import.json
```

Revise o `taiga-import.json` gerado antes do próximo passo — é a chance de
conferir subject/descrição/severidade/tags de cada item antes de qualquer
chamada de escrita à API.

### 3. Criar os issues no Taiga

Por padrão roda em **dry-run** (mostra os payloads, não cria nada):

```bash
python taiga_import.py apply --input taiga-import.json
```

Teste com um item antes de criar todos:

```bash
python taiga_import.py apply --input taiga-import.json --apply --only BUG-20260915-01
```

Criar o restante (reexecuções pulam automaticamente o que já está no log):

```bash
python taiga_import.py apply --input taiga-import.json --apply
```

Para manter um registro permanente de uma execução real (não só os arquivos
de trabalho temporários), passe caminhos `--out`/`--log` dentro de
`reports/` — veja [`reports/README.md`](reports/README.md) (em inglês) para
a convenção de nomes. Diferente de `taiga-import.json`/`import-log.csv`
padrão, arquivos em `reports/` são commitados no repositório como histórico
de importações.

Flags úteis: `--issue-type` (padrão `Bug`), `--sev1`/`--sev2`/`--sev3` (nomes
de severidade do Taiga para as escalas 1/2/3 do seu relatório — padrão
`Minor`/`Normal`/`Critical`, os nomes default do Taiga), `--log` (arquivo de
rastreio, padrão `import-log.csv`).

### 4. Corrigir tags de issues já criados

Se você mudar as regras do `config.json` depois de já ter criado issues,
`retag` reaplica as tags do JSON extraído em cada issue já registrado no log
(usa optimistic concurrency — busca a `version` atual do issue antes de
gravar):

```bash
python taiga_import.py retag --input taiga-import.json          # dry-run
python taiga_import.py retag --input taiga-import.json --apply  # aplica
```

### 5. Atribuir issues a um membro do projeto

A partir de um CSV de log de import (de uma corrida `apply --apply`
anterior), atribui cada issue do log a um membro do projeto. A busca é por
nome completo, porque a API do Taiga não expõe o e-mail de outros membros:

```bash
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe"            # dry-run
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe" --apply     # aplica
python taiga_assign.py --log reports/import-log-2026-09-15.csv --name "Jane Doe" --apply --only BUG-20260915-01
```

## Arquivos

| Arquivo | Versionado? | Descrição |
|---|---|---|
| `taiga_common.py` | sim | Cliente HTTP (auth, GET/POST/PATCH) e loader de `.env`. |
| `taiga_discover.py` | sim | Lista tipos/severidades/status do projeto configurado. |
| `taiga_import.py` | sim | `extract` / `apply` / `retag`. |
| `taiga_assign.py` | sim | Atribui issues de um CSV de log de import a um membro do projeto, por nome. |
| `config.example.json` | sim | Modelo de config de extração (genérico). |
| `.env.example` | sim | Modelo de credenciais. |
| `config.json` | não | Sua config real, específica do relatório/projeto. |
| `.env` | não | Suas credenciais reais. |
| `taiga-import.json`, `import-log.csv` (raiz do repo) | não | Saída de trabalho da execução em andamento — dados do seu relatório, não do repositório. |
| `reports/*.json`, `reports/*.csv` | sim | Histórico permanente de execuções `--apply` passadas, mantido de propósito — veja [`reports/README.md`](reports/README.md). |

## Segurança

- Sem `--apply`, nenhum comando grava nada no Taiga.
- `.env` e `config.json` nunca são commitados.
- A senha nunca é salva em disco pelo script — só o token de sessão (em
  memória, durante a execução).

Veja [SECURITY.md](.github/SECURITY.md) para saber como reportar uma vulnerabilidade.

## Como contribuir

Contribuições, relatos de bugs e pedidos de funcionalidade são bem-vindos —
veja [CONTRIBUTING.md](CONTRIBUTING.md) para saber como começar, e siga o
[Código de Conduta](CODE_OF_CONDUCT.md).

## Contato

Mantido por **Gabriel Vidal**.

- E-mail: [gabrielvidalsoda@gmail.com](mailto:gabrielvidalsoda@gmail.com)
- WhatsApp: [+55 (85) 99406-4049](https://bit.ly/4reII3v)
- LinkedIn: [linkedin.com/in/gabrielvidalsoda](https://www.linkedin.com/in/gabrielvidalsoda)

## Licença

[MIT](LICENSE) © 2026 Gabriel Vidal
