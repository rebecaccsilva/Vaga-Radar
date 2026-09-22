import requests
from datetime import datetime, timezone
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import requests


def horas_desde_publicacao(data_publicacao_str):
    data_publicacao = datetime.fromisoformat(data_publicacao_str)
    if data_publicacao.tzinfo is None:
        data_publicacao = data_publicacao.replace(tzinfo=timezone.utc)
    agora = datetime.now(timezone.utc)
    diferenca = agora - data_publicacao
    return diferenca.total_seconds() / 3600


def buscar_remotive():
    resp = requests.get(
        "https://remotive.com/api/remote-jobs",
        params={"category": "software-dev"},
        timeout=15,
    )
    dados = resp.json()
    lista_vagas = dados["jobs"]

    vagas_simplificadas = []
    for vaga in lista_vagas:
        vagas_simplificadas.append(
            {
                "id": f"remotive-{vaga['id']}",
                "titulo": vaga["title"],
                "empresa": vaga["company_name"],
                "local": vaga["candidate_required_location"],
                "url": vaga["url"],
                "salario": vaga["salary"] or "Não informado",
                "publicada_em": vaga["publication_date"],
                "remoto": True,
            }
        )
    return vagas_simplificadas


def buscar_arbeitnow():
    resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
    dados = resp.json()
    lista_vagas = dados["data"]

    vagas_simplificadas = []
    for vaga in lista_vagas:
        publicada_em = datetime.fromtimestamp(
            vaga["created_at"], tz=timezone.utc
        ).isoformat()

        vagas_simplificadas.append(
            {
                "id": f"arbeitnow-{vaga['slug']}",
                "titulo": vaga["title"],
                "empresa": vaga["company_name"],
                "local": vaga["location"] or "Não informado",
                "url": vaga["url"],
                "salario": "Não informado",  # Arbeitnow não fornece esse dado
                "publicada_em": publicada_em,
                "remoto": vaga["remote"],
            }
        )
    return vagas_simplificadas


def buscar_github():
    vagas = []
    for repo in REPOS_GITHUB:
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/issues",
                params={"state": "open", "per_page": 100},
                headers={"Accept": "application/vnd.github+json"},
                timeout=15,
            )
            resp.raise_for_status()
            issues = resp.json()
        except requests.RequestException as e:
            print(f"[GitHub] erro ao buscar {repo}: {e}")
            continue

        for issue in issues:
            if "pull_request" in issue:
                continue  

            titulo_bruto = issue["title"]
            match = re.match(r"\[(.*?)\]\s*(.*)", titulo_bruto)
            if match:
                cidade, titulo = match.group(1), match.group(2)
            else:
                cidade, titulo = "", titulo_bruto
                
            remoto = "remoto" in cidade.lower() or "remote" in cidade.lower()

            vagas.append(
                {
                    "id": f"github-{repo.split('/')[0]}-{issue['number']}",
                    "titulo": titulo,
                    "empresa": "",
                    "local": cidade,
                    "descricao": issue.get("body") or "",
                    "url": issue["html_url"],
                    "publicada_em": issue["created_at"],
                    "salario": "Não informado",
                    "remoto": remoto,
                }
            )

    print(f"[GitHub] buscadas: {len(vagas)}")
    return vagas


def buscar_gupy():
    vagas=[]
    ids_vistos=set()
    
    for termo in GUPY_TERMOS_BUSCA:
        try:
            resp= requests.get("https://employability-portal.gupy.io/api/v1/jobs", params={"jobName":termo, "limit":50, "sortBy": "publishedDate", "sortOrder": "desc"}, timeout=15,)
            resp.raise_for_status()
            dados= resp.json()
        except requests.RequestException as e:
            print(f"[Gupy] erro na busca '{termo}': {e}")
            continue
        
        for vaga in dados.get("data", []):
            vid= str(vaga.get("id"))
            if not vid or vid in ids_vistos:
                continue
            ids_vistos.add(vid)
            
            publicada= vaga.get("publishedDate")
            if not publicada:
                continue
            
            cidade = vaga.get("city") or ""
            estado= vaga.get("state") or ""
            local= ", ".join(p for p in [cidade, estado] if p) or "Não Informado"
            
            vagas.append({
                "id": f"gupy-{vid}",
                "titulo": vaga.get("name") or "",
                "empresa": vaga.get("careerPageName") or "",
                "local": local, 
                "url": vaga.get("jobUrl") or "", "salario": "Não informado", "publicada_em": publicada, "remoto": bool(vaga.get("isRemoteWork"),)
            })

    print(f"[Gupy] buscadas: {len(vagas)}")
    return vagas

PALAVRAS_NIVEL = [
    "junior",
    "júnior",
    "jr.",
    "entry level",
    "entry-level",
    "estagio",
    "estágio",
    "internship",
    "intern",
    "trainee",
    "graduate",
]
PALAVRAS_AREA = [
    "developer",
    "engineer",
    "software",
    "programmer",
    "python",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "data",
    "dev",
]
PALAVRAS_EXCLUIR = [
    "senior",
    "sênior",
    "sr.",
    "staff",
    "lead",
    "principal",
    "manager",
    "head of",
    "architect",
    "master",
]

GUPY_TERMOS_BUSCA= ["estágio", "júnior", "trainee", "jovem aprendiz"]

LIMITE_HORAS = 30 * 24  # 30 dias em horas
ARQUIVOS_ENVIADOS = "sent_jobs.json"

REPOS_GITHUB = ["frontendbr/vagas", "backend-br/vagas"]

EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")


def texto_contem_alguma(texto, palavras):
    texto = texto.lower()
    return any(palavra in texto for palavra in palavras)


def local_aceitavel(local, remoto):
    if remoto:
        return True
    local = local.lower()
    return "rio de janeiro" in local or "brazil" not in local


def eh_vaga_relevante(vaga):
    texto_completo = f"{vaga['titulo']} {vaga['empresa']}"
    tem_nivel = texto_contem_alguma(texto_completo, PALAVRAS_NIVEL)
    tem_area = texto_contem_alguma(texto_completo, PALAVRAS_AREA)
    tem_excluida = texto_contem_alguma(texto_completo, PALAVRAS_EXCLUIR)
    local_ok = local_aceitavel(vaga["local"], vaga["remoto"])
    dentro_prazo = horas_desde_publicacao(vaga["publicada_em"]) <= LIMITE_HORAS
    return tem_nivel and tem_area and not tem_excluida and local_ok and dentro_prazo


def carregar_enviados():
    if os.path.exists(ARQUIVOS_ENVIADOS):
        with open(ARQUIVOS_ENVIADOS, "r", encoding="utf-8") as arquivo:
            return set(json.load(arquivo))
    return set()


def salvar_enviados(ids_enviados):
    with open(ARQUIVOS_ENVIADOS, "w", encoding="utf-8") as arquivo:
        json.dump(list(ids_enviados), arquivo, ensure_ascii=False, indent=2)


def enviar_email(vagas):
    corpo = "\n\n".join(
        f"{vaga['titulo']} - {vaga['empresa']}\n{vaga['local']} | {vaga['salario']}\n{vaga['url']}"
        for vaga in vagas
    )

    mensagem = MIMEMultipart()
    mensagem["Subject"] = f"{len(vagas)} nova(s) vaga(s) encontradas"
    mensagem["From"] = EMAIL_FROM
    mensagem["To"] = EMAIL_TO
    mensagem.attach(MIMEText(corpo, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(EMAIL_FROM, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_FROM, EMAIL_TO, mensagem.as_string())


vagas_simplificadas = buscar_remotive() + buscar_arbeitnow() + buscar_github() + buscar_gupy()
print(f"Total de vagas coletadas: {len(vagas_simplificadas)}")


vagas_relevantes = [vaga for vaga in vagas_simplificadas if eh_vaga_relevante(vaga)]
vagas_relevantes.sort(key=lambda vaga: horas_desde_publicacao(vaga["publicada_em"]))

print(f"Vagas relevantes: {len(vagas_relevantes)}")
for v in vagas_relevantes:
    horas = horas_desde_publicacao(v["publicada_em"])
    print(f"- {v['titulo']} | {v['empresa']} | {v['local']} | há {horas:.1f}h  ")


ids_ja_enviados = carregar_enviados()
vagas_novas = [vaga for vaga in vagas_relevantes if vaga["id"] not in ids_ja_enviados]

print(f"Vagas novas (nunca enviadas): {len(vagas_novas)}")

if vagas_novas:
    enviar_email(vagas_novas)
    ids_ja_enviados.update(vaga["id"] for vaga in vagas_novas)
    salvar_enviados(ids_ja_enviados)
    print("E-mail enviado!")
else:
    print("Nenhuma vaga nova pra enviar.")
