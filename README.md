# 🎯 Vaga Radar

Monitor automático de vagas **júnior e estágio**, priorizando remoto (mas
aceitando presencial), incluindo vagas internacionais. Roda de graça no
GitHub Actions e te avisa por e-mail assim que aparece algo novo.

## Como funciona

1. A cada 3 horas, o GitHub Actions roda `main.py`.
2. O script busca vagas em 3 fontes gratuitas (sem precisar de chave de API):
   - [Remotive](https://remotive.com) — vagas remotas de tecnologia
   - [Arbeitnow](https://arbeitnow.com) — vagas internacionais (foco Europa)
   - [RemoteOK](https://remoteok.com) — vagas remotas
3. Filtra por palavras-chave de nível (júnior, estágio, trainee...) e área
   (developer, engineer, python...), excluindo vagas sênior.
4. Compara com `sent_jobs.json` para não repetir vagas já enviadas.
5. Envia um e-mail com as vagas novas e salva o histórico de volta no repositório.

## Configuração (passo a passo)

### 1. Crie um repositório no GitHub
Suba esses arquivos para um repositório novo (pode ser privado).

### 2. Gere uma senha de app do Gmail
Se for usar Gmail para enviar os e-mails:
1. Ative a verificação em duas etapas na sua conta Google.
2. Acesse [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Gere uma senha de app para "Mail" — vai gerar um código de 16 letras.

*(Se preferir outro provedor de e-mail, ajuste `SMTP_SERVER` e `SMTP_PORT`
como variáveis de ambiente no workflow.)*

### 3. Configure os Secrets no GitHub
No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Nome            | Valor                                      |
|-----------------|---------------------------------------------|
| `EMAIL_FROM`    | seu e-mail (ex: `voce@gmail.com`)           |
| `EMAIL_PASSWORD`| a senha de app gerada no passo 2            |
| `EMAIL_TO`      | e-mail que vai receber os alertas (pode ser o mesmo) |

### 4. Ative o Actions
Vá na aba **Actions** do repositório e ative os workflows, se pedido.
Você pode rodar manualmente clicando em "Run workflow" para testar.

## Personalizando o filtro

No topo do `main.py`, edite as listas:
- `PALAVRAS_CHAVE_NIVEL` — termos de júnior/estágio
- `PALAVRAS_CHAVE_AREA` — áreas de interesse (adicione "node", "react" etc conforme for aprendendo)
- `PALAVRAS_EXCLUIR` — termos de senioridade a evitar

## Próximos passos possíveis
- Adicionar a API da [Adzuna](https://developer.adzuna.com/) (grátis, precisa
  de cadastro) para cobrir muito mais países e vagas presenciais.
- Guardar as vagas em uma planilha ou banco de dados além do e-mail.
- Adicionar filtro por stack específica que você já sabe (Python, SQL...).