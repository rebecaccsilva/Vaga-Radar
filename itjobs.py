import os
import requests

resp= requests.get(
    "https://api.itjobs.pt/job/search.json",params={"api_key": os.environ["ITJOBS_API_KEY"], "q": "junior", "limit":5}, timeout=15,
)

dados = resp.json()
print(list(dados.keys()))
for vaga in dados.get("results",[]):
    print(list(vaga.keys()))
    print(vaga)
    break