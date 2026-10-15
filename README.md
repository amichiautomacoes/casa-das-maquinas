# Casa das Máquinas — Dashboard

Aplicação de indicadores em Flask, Dash, Plotly e Pandas, com dados consultados no BigQuery. Este repositório contém somente a visualização e os arquivos necessários à implantação; o ETL e os dados locais ficam fora do versionamento.

A interface apresenta somente a **Visão Geral Executiva**, com seus KPIs, análises de mídia, mix e clientes e resultado financeiro.

## Implantar no EasyPanel

1. Crie um serviço **App**, conecte este repositório e selecione a branch `main`.
2. Use a raiz do repositório como **Build Path** (`/`) e o **Dockerfile** da raiz como builder.
3. Configure `GOOGLE_APPLICATION_CREDENTIALS` no ambiente do serviço com o Base64 do JSON completo da conta de serviço, em uma única linha. As demais variáveis de [visualizacao/.env.example](visualizacao/.env.example) servem de referência para personalização; o Docker já define os padrões de produção.
4. Configure a porta interna do domínio como **8505**. O container já define `PORT=8505` e `TRUST_PROXY=true`.
5. Faça o deploy e abra `/dashboard/`. A rota `/` redireciona para o dashboard; `/healthz` permite conferir a saúde da aplicação.

O Base64 do JSON completo inclui a chave e o e-mail da conta; basta copiar a variável `GOOGLE_APPLICATION_CREDENTIALS` do `.env` local para o EasyPanel. A aplicação também aceita JSON direto, arquivo JSON montado ou chave PEM acompanhada de `GCP_SERVICE_ACCOUNT_EMAIL` e `GCP_PROJECT_ID`. A imagem não contém o `.env` nem o JSON local de desenvolvimento. O token do GitHub deve ser configurado na conexão do repositório no EasyPanel.

O container usa Gunicorn em `0.0.0.0:8505`, executa com usuário sem privilégios e inclui uma verificação de saúde. Os indicadores e o financeiro mensal são carregados ao iniciar cada processo; reinicie o serviço para atualizar os dados consultados.

## Executar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r visualizacao/requirements.txt
Copy-Item visualizacao/.env.example .env
# Preencha as credenciais no .env antes de iniciar.
.\.venv\Scripts\python.exe -m visualizacao.run
```

Abra <http://127.0.0.1:8505/dashboard/>.

## Validar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s visualizacao/tests -v
```

Os testes usam dados sintéticos, sem consultar o BigQuery.

Consulte a [documentação técnica](visualizacao/README.md) e o [briefing visual](visualizacao/visual.md) para arquitetura, regras dos indicadores e padrões da interface.
