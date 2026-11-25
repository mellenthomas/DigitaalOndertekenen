import requests
import base64
import zipfile
import os
import io
import truststore
import pyodbc
import logging
import subprocess
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv

## CONFIG ##
load_dotenv()

truststore.inject_into_ssl()

today = f'{datetime.now():%Y%m%d}'
TYPST = os.environ["TYPST"]
TYPST_TEMPLATE = os.environ["TYPST_TEMPLATE"]
DSN = os.environ["DSN"]
UID = os.environ["UID"]
PWD = os.environ["PWD"]
SQL_DIR = os.environ["SQL_DIR"]
OUTPUT_DIR=os.environ["OUTPUT_DIR"]
SIGNED=os.environ["SIGNED"]
BASE_URL=os.environ["BASE_URL"]
AUTH_URL=os.environ["AUTH_URL"]
CLIENTID=os.environ["CLIENTID"]
CLIENTSECRET=os.environ["CLIENTSECRET"]
SCOPE_USER=os.environ["SCOPE_USER"]

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),                          # console
        logging.FileHandler(f"POCT_DigitaalOndertekenen_{today}.log", encoding="utf-8"), # file
    ],
)

############

## POCT Aanvragen ophalen LAB400 ##

def load_sql(name: str) -> str:
    return Path(rf"{SQL_DIR}\{name}.sql").read_text(encoding="utf-8")

def to_serializable(obj):
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, date):
        return obj.strftime("%Y-%m-%d")
    return obj

def POCT_aanvragen_ophalen():
    conn = pyodbc.connect(f"DSN={DSN};UID={UID};PWD={PWD}")
    cursor = conn.cursor()
    sql = load_sql("POCT")
    
    cursor.execute(sql)

    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))
    results = to_serializable(results)

    for x in results:
        aanvraagnummer = x['AANVRAAGNUMMER']
        naam = x['NAAM']
        voornaam = x['VOORNAAM']
        geboortedatum = x['GEBOORTEDATUM']
        insz = x['INSZ']
        geslacht = x['GESLACHT']
        aanvrager = x['AANVRAGERNAAM'] + ", " + x['AANVRAGERVOORNAAM']
        riziv = x['RIZIV']
        email = x['EMAIL']
        aanvraagdatum = x['AANVRAAGDATUM']
        analyses = x['ANALYSES']
        if email == "":
            email = riziv
        output = rf"{OUTPUT_DIR}\{email}"
        os.makedirs(output, exist_ok=True)

        result = subprocess.run([
            rf"{TYPST}",
            "compile",
            rf"{TYPST_TEMPLATE}",
            rf"{output}\{aanvraagnummer}.pdf",
            "--input", f"aanvraag={aanvraagnummer}",
            "--input", f"naam={naam}",
            "--input", f"voornaam={voornaam}",
            "--input", f"geboortedatum={geboortedatum}",
            "--input", f"INSZ={insz}",
            "--input", f"aanvrager={aanvrager}",
            "--input", f"RIZIV={riziv}",
            "--input", f"aanvraagdatum={aanvraagdatum}",
            "--input", f"analyses={analyses}",
            "--input", f"geslacht={geslacht}",
            "--pdf-standard",
            "a-4",
        ], capture_output=True, text=True)
        logger.info("%s %s %s %s %s", email, aanvraagnummer, result.returncode, result.stdout, result.stderr)

    conn.close()

## Digitaal Ondertekenen ##

def get_token():
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
    }
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENTID,
        'client_secret': CLIENTSECRET,
    }
    resp = requests.post(AUTH_URL, headers=headers, data=payload)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        global access_token
        access_token = get_scope_auth_token(json_data.get('access_token'))
    else:
        resp.raise_for_status()

def get_scope_auth_token(access):
    url = BASE_URL + '/v4/authenticate/scope'
    headers = {
        'Authorization': 'bearer ' + access,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    payload = {
        "user_email": SCOPE_USER
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        logger.info(json_data)
        return json_data.get('access_token')
    else:
        logger.info(resp.content)
        resp.raise_for_status()

def add_package(package_name: str):
    url = BASE_URL + '/v4/packages'
    package_id = 0
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    logger.info(headers)
    payload = {
        "package_name": package_name,
        "workflow_mode": "ONLY_OTHERS"
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        package_id = json_data.get('package_id')
        logger.info(json_data)
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()
    return package_id

def add_documents(package_id, folder):
    url = BASE_URL + f"/v4/packages/{package_id}/documents/base64"
    pdf_files = sorted(folder.glob("*.pdf"))

    for pdf_path in pdf_files:
        data = pdf_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        logger.info(f"{pdf_path.name}: {len(b64)} chars base64")
        headers = {
            'Authorization': 'bearer ' + access_token,
            'Content-type': 'application/json',
            'accept': 'application/json',
            'x-file-name': pdf_path.name,
            'x-convert-document': 'false',
            'x-source': 'ZOL_POCT_Aanvragen_Digitaal_Ondertekenen',
            'x-base64': 'true'
        }
        payload = {
            "document": b64
        }
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            json_data = resp.json()
            pdf_path.unlink()
            if not any(Path(pdf_path.parent).iterdir()):
                pdf_path.parent.rmdir()
            logger.info(json_data)
        else:
            logger.info("Status:", resp.status_code)
            logger.info("Body:", resp.text)
            resp.raise_for_status()

def add_workflow_users(package_id, user_name, user_email):
    url = BASE_URL + f"/v4/packages/{package_id}/workflow/users"
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    payload = [
        {
            "user_email": user_email,
            "user_name": user_name,
            "email_notification": True,
            "role": "SIGNER",
            "signing_order": 0,
            "delivery_method": "EMAIL",
        }
    ]
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        logger.info(json_data)
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()

def add_signature_field(package_id):
    url = BASE_URL + f"/v4/packages/{package_id}/details"
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers)
    json_data = resp.json()
    documents = json_data.get('documents')
    for document in documents:
        document_id = document.get('id')
        url = BASE_URL + f"/v4/packages/{package_id}/documents/{document_id}/fields/signature"
        payload = {
            "order": 1,
            "page_no": 1,
            "field_name": "",
            "level_of_assurance": [
                "QUALIFIED_ELECTRONIC_SIGNATURE"
            ],
            "dimensions": {
                "x": 430,
                "y": 100,
                "width": 100,
                "height": 40
            },
            "display": "VISIBLE",
        }
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            json_data = resp.json()
            logger.info(json_data)
        else:
            logger.info("Status:", resp.status_code)
            logger.info("Body:", resp.text)
            resp.raise_for_status()

def share_package(package_id):
    url = BASE_URL + f"/v4/packages/{package_id}/workflow"
    package_id = 0
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.post(url, headers=headers)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        logger.info(json_data)
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()
def get_all_signed_packages():
    url = BASE_URL + f"/v4/packages/COMPLETED/1/100"
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        logger.info(json_data)
        for package in json_data:
            logger.info(package.get('package_id'))
            package_id = package.get('package_id')
            download_package(package_id)

    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()

def get_package_details(package_id):
    url = BASE_URL + f"/v4/packages/{package_id}/details"
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code in (200, 201):
        json_data = resp.json()
        return json_data
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()

def download_package(package_id):
    url = BASE_URL + f"/v4/packages/{package_id}"
    os.makedirs(SIGNED, exist_ok=True)
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.get(url, headers=headers, allow_redirects=True)
    if resp.status_code in (200, 201):
        data = resp.content
        if zipfile.is_zipfile(io.BytesIO(data)):
            # Meerdere documenten -> zip direct uitpakken uit memory (geen tussentijds bestand)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                bad = zf.testzip()  # None = geen corrupte entries
                if bad is not None:
                    raise RuntimeError(f"Corrupte zip-entry: {bad}")
                names = zf.namelist()
                logger.info(f"[{package_id}] ZIP gedetecteerd ({len(names)} bestanden):")
                for n in names:
                    logger.info(f"    - {n}")
                zf.extractall(SIGNED)
                logger.info(f"[{package_id}] Uitgepakt naar: {os.path.abspath(SIGNED)}")
        elif data.startswith(b"%PDF"):
            # Eén document -> gewoon PDF opslaan
            pdf_path = os.path.join(SIGNED, f"package_{package_id}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(data)
            logger.info(f"[{package_id}] Enkel PDF-document, opgeslagen als {pdf_path} "
                f"({len(data):,} bytes)")
        else:
            # Onverwachte inhoud — laat begin van payload zien voor debugging
            raise RuntimeError(f"[{package_id}] Onverwacht content-type, begint met: {data[:16]!r}")
        delete_package(package_id)
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()

def delete_package(package_id):
    url = BASE_URL + f"/v4/packages/{package_id}"
    headers = {
        'Authorization': 'bearer ' + access_token,
        'Content-type': 'application/json',
        'accept': 'application/json'
    }
    resp = requests.delete(url, headers=headers)
    if resp.status_code in (200, 201):
        data = resp
        logger.info(data.content)
    else:
        logger.info("Status:", resp.status_code)
        logger.info("Body:", resp.text)
        resp.raise_for_status()

def Digitaal_Ondertekenen():
    pdf_folders = Path(OUTPUT_DIR)
    get_token()

    for folder in pdf_folders.iterdir():
        if folder.is_dir() and "@" in str(folder):
            user_email = str(folder.parts[-1])
            user_name = user_email.split("@")[0].replace(".", " ")
            
            package_id = add_package("POCT aanvragen van " + user_name)
            logger.info(package_id)
            add_documents(package_id, folder)
            add_workflow_users(package_id, user_name, user_email)
            add_signature_field(package_id)
            share_package(package_id)
    ## Alle getekende documenten downloaden en verwijderen van platform:
    get_all_signed_packages()
    
if __name__ == "__main__":
    POCT_aanvragen_ophalen()
    #Digitaal_Ondertekenen()
