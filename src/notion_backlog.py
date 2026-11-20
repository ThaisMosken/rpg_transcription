import os
import re
import time

import requests

from utils.notion_publisher import NotionPublisher

NOTION_API_VERSION = "2022-06-28"


def find_chronicle_files(chronicles_folder, table_id):
    """
    Varre a pasta e retorna as crônicas '{table_id}<num>_cronica.md' ordenadas pelo número
    da sessão (independente de zeros à esquerda ou lacunas na numeração).

    Cada item traz:
      - 'session_number': int, usado na comparação com as sessões já cadastradas no Notion;
      - 'session_label': texto numérico como está no arquivo (ex.: "001"), usado no campo
        Nome da página ("Sessão 001"), mantendo o padrão das páginas já existentes;
      - 'file_name' e 'file_path'.
    """
    pattern = re.compile(rf"^{re.escape(table_id)}(\d+)_cronica\.md$")
    found = []

    for file_name in os.listdir(chronicles_folder):
        match = pattern.match(file_name)
        if match:
            found.append({
                "session_number": int(match.group(1)),
                "session_label": match.group(1),
                "file_name": file_name,
                "file_path": os.path.join(chronicles_folder, file_name),
            })

    # Desempate pelo nome mantém a ordem estável se existirem, p. ex., "DIA01" e "DIA001"
    found.sort(key=lambda item: (item["session_number"], item["file_name"]))
    return found


def list_existing_session_numbers(notion_token, notion_config, table_id):
    """
    Consulta o database de sessões da mesa e retorna o conjunto de números de sessão
    já cadastrados (set de int), com paginação e o mesmo filtro 'DB_CAMPAIGN' usado
    por NotionPublisher.publish_session ao gravar.

    Diferente de session_logger.fetch_notion_session_dates, NÃO engole erros: se a consulta
    falhar, a exceção sobe, para que o lote pare antes de publicar (e duplicar) qualquer coisa.
    Também conta a sessão mesmo que ela não tenha data preenchida.
    """
    if table_id not in notion_config:
        raise ValueError(f"Mesa '{table_id}' não encontrada em notion_config.json.")

    cfg = notion_config[table_id]
    query_url = f"https://api.notion.com/v1/databases/{cfg['DB_SESSAO']}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    payload = {"page_size": 100}
    if cfg.get("DB_CAMPAIGN"):
        payload["filter"] = {
            "property": "Campanha",
            "rich_text": {"equals": cfg["DB_CAMPAIGN"]},
        }

    existing = set()
    while True:
        response = requests.post(query_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        for page in data.get("results", []):
            number = page.get("properties", {}).get("Sessão", {}).get("number")
            if number is not None:
                existing.add(int(number))

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    return existing


def publish_backlog_sessions(
    notion_token,
    notion_config,
    table_id,
    chronicles_folder,
    default_date,
    sleep_seconds=0.3
):
    """
    Publica no Notion, em lote, as crônicas '{table_id}<num>_cronica.md' de `chronicles_folder`.

    - Sessões cujo número já existe no Notion são puladas (sem sobrescrever).
    - Todas as sessões publicadas recebem `default_date` (YYYY-MM-DD), pois as datas reais
      das campanhas antigas não foram registradas.
    - Um erro em uma sessão não interrompe o lote; o resumo final lista o que deu errado.

    Retorna um dicionário com as listas 'published', 'skipped' e 'failed' (nomes dos arquivos).
    """
    if not os.path.isdir(chronicles_folder):
        print(f"❌ Pasta de crônicas não encontrada: {chronicles_folder}")
        return None

    if table_id not in notion_config:
        print(f"❌ Mesa '{table_id}' não encontrada em notion_config.json.")
        return None

    chronicles = find_chronicle_files(chronicles_folder, table_id)
    if not chronicles:
        print(f"⚠️ Nenhuma crônica '{table_id}<num>_cronica.md' encontrada em {chronicles_folder}.")
        return {"published": [], "skipped": [], "failed": []}

    print(f"🔎 {len(chronicles)} crônicas encontradas para '{table_id}'.")

    try:
        existing_numbers = list_existing_session_numbers(notion_token, notion_config, table_id)
    except Exception as e:
        print(f"❌ Não foi possível consultar as sessões já cadastradas no Notion: {e}")
        print("🛑 Lote cancelado antes de publicar qualquer sessão (evita duplicatas).")
        return None

    print(f"📅 {len(existing_numbers)} sessões já cadastradas no Notion para '{table_id}'.")
    print(f"⚠️ Todas as sessões publicadas receberão a data padrão: {default_date}")

    publisher = NotionPublisher(token=notion_token, databases_config=notion_config)

    summary = {"published": [], "skipped": [], "failed": []}
    print("-" * 50)

    for item in chronicles:
        file_name = item["file_name"]

        if item["session_number"] in existing_numbers:
            print(f"⏭️ {file_name}: sessão {item['session_number']} já existe no Notion. Pulando.")
            summary["skipped"].append(file_name)
            continue

        try:
            print(f"📄 {file_name}...", end=" ")
            publisher.publish_session(
                table_id=table_id,
                session_number=item["session_label"],
                date=default_date,
                file_path=item["file_path"]
            )
            print("✅")
            summary["published"].append(file_name)
            # Evita duplicar caso existam dois arquivos com o mesmo número (ex.: DIA01 e DIA001)
            existing_numbers.add(item["session_number"])
        except Exception as e:
            print(f"❌ Erro: {e}")
            summary["failed"].append(file_name)

        time.sleep(sleep_seconds)

    print("-" * 50)
    print(
        f"✨ Concluído: {len(summary['published'])} publicadas | "
        f"{len(summary['skipped'])} puladas (já existiam) | "
        f"{len(summary['failed'])} com erro."
    )
    for file_name in summary["failed"]:
        print(f"  ❌ {file_name}")

    return summary