import requests
from datetime import datetime, timezone
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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
]
LIMITE_HORAS = 30 * 24  # 30 dias em horas
ARQUIVOS_ENVIADOS = "sent_jobs.json"

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


vagas_simplificadas = buscar_remotive() + buscar_arbeitnow()
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
