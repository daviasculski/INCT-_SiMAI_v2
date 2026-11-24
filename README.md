# Projeto Extensionista - INCT SIMAI #
Integrantes do grupo:
- Davi iasculski
- Otavio Quadros
- Matheus Masera
- Gustavo Azambuja
- Ghabriel Molina

Para manter o ambiente isolado, o que ajuda na reprodutibilidade, crie um ambiente virtual antes:

Comandos Windows:

`python -m venv .venv`
`.venv\Scripts\activate`

Comandos Linux/Mac:

`python3 -m venv .venv`
`source .venv/bin/activate`

Instalar bibliotecas necessárias:

`pip install -r requirements.txt`

## Dashboard

Para executar o dashboard localmente após instalar as dependências:

```powershell
streamlit run app.py
```

O painel **Análise Contextual e Externa** combina a simulação de alagamentos do
INCT SIMAI com as tabelas 22.4 e 22.6 da pesquisa PEERS/IBGE. Use o controle
de nível do Guaíba e o seletor de dimensão para explorar os gráficos.
