# Selenium + Railway - Versão 1 segura

Esta versão foi ajustada para que **nenhuma credencial fique no repositório**.

## O que esta versão faz

- sobe uma interface simples em Streamlit;
- mostra um botão **Rodar script**;
- executa o login no `auth.mindsight.com.br/{tenant}`;
- captura o OTP no Gmail via IMAP;
- exibe logs e screenshot final.

## Arquivos do projeto

- `app.py` -> interface web com botão de execução;
- `runner.py` -> lógica do Selenium e captura de OTP;
- `Dockerfile` -> build do container com Chromium e ChromeDriver;
- `.env.example` -> referência dos nomes das variáveis, sem valores reais;
- `.gitignore` -> bloqueia arquivos `.env` e outros artefatos locais.

## Como tratar os dados confidenciais

### Regra

- não criar `.env` com credenciais reais dentro do repositório;
- não colocar senhas no `.env.example`;
- cadastrar tudo em **Railway > Service > Variables**.

### O que deixar no `.env.example`

Apenas os nomes das variáveis, sem valores:

```env
TENANT=
MINDSIGHT_EMAIL=
MINDSIGHT_PASSWORD=
GMAIL_EMAIL=
GMAIL_APP_PASSWORD=
HEADLESS=true
```

## Variáveis para cadastrar no Railway

Cadastre manualmente no serviço:

- `TENANT`
- `MINDSIGHT_EMAIL`
- `MINDSIGHT_PASSWORD`
- `GMAIL_EMAIL`
- `GMAIL_APP_PASSWORD`
- `HEADLESS`

## Deploy

1. Suba estes arquivos para um repositório no GitHub.
2. No Railway, crie um novo projeto a partir do GitHub.
3. Confirme que o `Dockerfile` está na raiz.
4. Cadastre as variáveis em **Service > Variables**.
5. Aguarde o build.
6. Gere um domínio público.
7. Abra a URL e clique em **Rodar script**.

## Observações

- Para Gmail, normalmente você precisa usar **App Password**.
- Esta versão é para validar ambiente, login, OTP e estabilidade do Selenium no Railway.
- Depois disso, a mesma base pode ser adaptada para cron job.
