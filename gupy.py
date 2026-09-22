import requests

termos = ["estágio", "python", "desenvolvedor", "estagio", "junior"]

for termo in termos:
    resp = requests.get(
        "https://employability-portal.gupy.io/api/v1/jobs",
        params={
            "jobName": "estágio",
            "limit": 10,
            "sortBy": "publishedDate",
            "sortOrder": "desc",
        },
        timeout=15,
    )
    dados = resp.json()
    for vaga in dados.get("data", []):
        print(vaga.get("title"), "|", vaga.get("publishedDate"), "|", list(vaga.keys()))
