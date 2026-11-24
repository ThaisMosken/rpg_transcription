from datetime import datetime
import json
import os
import re
import time
import requests
from google import genai
from google.genai import types
from google.genai.errors import APIError


def _load_gemini_config():
    """Carrega as configurações dos modelos Gemini a partir do JSON do repositório."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(repo_root, "config", "gemini_config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_prompt_template(template):
    """Baixa o prompt do GitHub com fallback para o arquivo local do repositório."""
    prompt_url = (
        f"https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/"
        f"refs/heads/main/prompts/{template}.md"
    )
    try:
        response = requests.get(prompt_url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as github_err:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(repo_root, "prompts", f"{template}.md")
        if os.path.exists(local_path):
            print(f"⚠️ Usando template local '{local_path}' (GitHub indisponível: {github_err}).")
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
        raise RuntimeError(f"Não foi possível carregar o template '{template}': {github_err}")


def fetch_notion_session_dates(notion_token, notion_config, table_id):
    """
    Consulta o database do Notion da mesa e retorna um dicionário {int(sessao): 'YYYY-MM-DD'}.
    Respeita paginacao (>100 registros) e o filtro opcional 'DB_CAMPAIGN'.
    """
    if table_id not in notion_config:
        print(f"⚠️ Mesa '{table_id}' não encontrada em notion_config.json.")
        return {}

    cfg = notion_config[table_id]
    database_id = cfg["DB_SESSAO"]
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {"page_size": 100}
    if "DB_CAMPAIGN" in cfg and cfg["DB_CAMPAIGN"]:
        payload["filter"] = {
            "property": "Campanha",
            "rich_text": {"equals": cfg["DB_CAMPAIGN"]}
        }

    dates_map = {}
    has_more = True
    next_cursor = None

    try:
        while has_more:
            if next_cursor:
                payload["start_cursor"] = next_cursor

            resp = requests.post(query_url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("results", []):
                props = page.get("properties", {})
                session_number = props.get("Sessão", {}).get("number")
                date_obj = props.get("Data", {}).get("date")
                start_date = date_obj.get("start") if date_obj else None

                if session_number is not None and start_date:
                    dates_map[int(session_number)] = start_date[:10]

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        print(f"📅 Notion consultado: {len(dates_map)} datas recuperadas para '{table_id}'.")

        # Alerta preventivo caso datas antigas tenham sido cadastradas com uma data padrão única
        if len(dates_map) >= 5 and len(set(dates_map.values())) == 1:
            print(
                "⚠️ ATENÇÃO: Todas as sessões retornaram a mesma data no Notion "
                "(possível data padrão histórica)."
            )

    except Exception as e:
        print(f"⚠️ Falha ao consultar datas no Notion (usando fallback de arquivo): {e}")

    return dates_map


def consolidate_session_logs(logs_folder, table_id, batch_size=20):
    """
    Varre a pasta de logs, ordena numericamente os arquivos '{table_id}<num>_log.md'
    (independente de zeros à esquerda ou lacunas na numeração) e gera os arquivos
    consolidados '{table_id}_Logs_Consolidados_Parte_X.md' em blocos de `batch_size` sessões.
    """
    if not os.path.exists(logs_folder):
        print(f"⚠️ Pasta de logs não encontrada: {logs_folder}")
        return []

    pattern = re.compile(rf"^{re.escape(table_id)}(\d+)_log\.md$")
    matched_logs = []

    for filename in os.listdir(logs_folder):
        match = pattern.match(filename)
        if match:
            session_num = int(match.group(1))
            matched_logs.append((session_num, filename))

    if not matched_logs:
        print(f"⚠️ Nenhum arquivo individual encontrado para a mesa '{table_id}' em {logs_folder}.")
        return []

    matched_logs.sort(key=lambda item: item[0])

    buckets = {}
    for session_num, filename in matched_logs:
        part_num = (max(session_num, 1) - 1) // batch_size + 1
        buckets.setdefault(part_num, []).append((session_num, filename))

    updated_files = []
    for part_num in sorted(buckets.keys()):
        entries = buckets[part_num]
        consolidated_filename = f"{table_id}_Logs_Consolidados_Parte_{part_num}.md"
        consolidated_path = os.path.join(logs_folder, consolidated_filename)

        sections = []
        included_ids = []
        for _, filename in entries:
            file_path = os.path.join(logs_folder, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                sections.append(content)
                included_ids.append(filename.replace("_log.md", ""))

        with open(consolidated_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(sections) + "\n")

        updated_files.append(consolidated_path)
        print(
            f"📦 Consolidado atualizado: {consolidated_filename} "
            f"({len(included_ids)} sessões: {', '.join(included_ids)})"
        )

    return updated_files


def _generate_log_markdown(
    client,
    gemini_cfg,
    base_prompt,
    transcription_path,
    chronicle_path,
    context_glossary,
    session_id,
    session_date,
    model=None
):
    """Executa a chamada à API do Gemini com fallback e retorna o Markdown do log."""
    with open(transcription_path, "r", encoding="utf-8") as f:
        transcription_text = f.read()

    with open(chronicle_path, "r", encoding="utf-8") as f:
        chronicle_text = f.read()

    full_prompt = f"""
    **METADADOS DA SESSÃO:**
    - ID da Sessão: {session_id}
    - Data da Sessão: {session_date}

    **GLOSSÁRIO DA CAMPANHA (Use para normalizar todos os nomes próprios):**
    {context_glossary}

    **CRÔNICA REVISADA DA SESSÃO:**
    --- INÍCIO DA CRÔNICA ---
    {chronicle_text}
    --- FIM DA CRÔNICA ---

    **BLOCO DE TEXTO TRANSCRITO (Fonte primária para detalhes granulares, valores e bastidores):**
    --- INÍCIO DA TRANSCRIÇÃO ---
    {transcription_text}
    --- FIM DA TRANSCRIÇÃO ---

    {base_prompt}
    """

    default_models = gemini_cfg.get("default_models", [])
    if model is None:
        model_priority_queue = list(default_models)
    elif isinstance(model, list):
        model_priority_queue = list(model)
    else:
        model_priority_queue = [model] + [m for m in default_models if m != model]

    if not model_priority_queue:
        raise ValueError("Nenhum modelo configurado em 'default_models' ou informado via parâmetro.")

    max_tokens = gemini_cfg.get("max_output_tokens", 16384)
    fallback_codes = set(gemini_cfg.get("fallback_error_codes", [429]))
    no_sampling_prefixes = tuple(gemini_cfg.get("no_sampling_prefixes", []))
    sampling_params = gemini_cfg.get("sampling_params", {})

    response = None

    for current_model in model_priority_queue:
        if current_model.startswith(no_sampling_prefixes):
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens
            )
        else:
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                **sampling_params
            )

        try:
            print(f"  🤖 Gerando {session_id} com {current_model}...")
            response = client.models.generate_content(
                model=current_model,
                contents=full_prompt,
                config=generation_config
            )
            break

        except APIError as e:
            if e.code in fallback_codes and current_model != model_priority_queue[-1]:
                print(f"  ⚠️ Cota excedida no {current_model} (Erro {e.code}). Tentando fallback...")
                continue
            raise RuntimeError(f"ERRO DE API ({e.code}): {e.message}")

    if not response or not response.text:
        raise RuntimeError("O modelo retornou resposta vazia (possível bloqueio de segurança).")

    return response.text.strip() + "\n"


def generate_gemini_log(
    api_key,
    transcription_path,
    chronicle_path,
    output_path,
    context_glossary,
    session_id,
    session_date,
    template="template_log_v1",
    model=None
):
    """
    Fluxo unitário (Bloco 6): gera o log da sessão atual em output_path (workbench).

    A consolidação dos logs NÃO é feita aqui: ela é refeita pelo bloco 'Arquivar sessão'
    (src/session_archiver.py), depois que o log já está em archive/logs/<TABLE>/.
    """
    try:
        gemini_cfg = _load_gemini_config()
        base_prompt = _load_prompt_template(template)
        client = genai.Client(api_key=api_key)

        log_md = _generate_log_markdown(
            client=client,
            gemini_cfg=gemini_cfg,
            base_prompt=base_prompt,
            transcription_path=transcription_path,
            chronicle_path=chronicle_path,
            context_glossary=context_glossary,
            session_id=session_id,
            session_date=session_date,
            model=model
        )
    except Exception as e:
        print(f"❌ Falha ao gerar log de {session_id}: {e}")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(log_md)

    print(f"✅ SUCESSO! Log salvo em: {output_path}")


def process_backlog_logs(
    api_key,
    chronicles_folder,
    transcriptions_folder,
    logs_folder,
    context_glossary,
    table_id,
    notion_token=None,
    notion_config=None,
    template="template_log_v1",
    model=None,
    batch_size=20,
    sleep_seconds=15,
    max_sessions_per_run=15,
    overwrite=False
):
    """
    Processa em lote (backlog) as sessões antigas já arquivadas, lendo as crônicas de
    `chronicles_folder` e as transcrições de `transcriptions_folder`, e gravando os logs
    direto em `logs_folder` (archive/logs/<TABLE>/), sem passar pelo workbench.
    Recupera datas do Notion, respeita limites de RPM/RPD e consolida ao final.
    """
    for folder, label in ((chronicles_folder, "crônicas"), (transcriptions_folder, "transcrições")):
        if not os.path.exists(folder):
            print(f"❌ Pasta de {label} não encontrada: {folder}")
            return

    os.makedirs(logs_folder, exist_ok=True)

    # 1. Descobrir e parear crônicas + transcrições da mesa
    chronicle_pattern = re.compile(rf"^({re.escape(table_id)}(\d+))_cronica\.md$")
    paired_sessions = []

    for filename in os.listdir(chronicles_folder):
        match = chronicle_pattern.match(filename)
        if not match:
            continue

        session_id = match.group(1)       # Ex.: DIA001 ou DIA01
        session_num = int(match.group(2)) # Ex.: 1
        chronicle_path = os.path.join(chronicles_folder, filename)
        transcription_path = os.path.join(transcriptions_folder, f"{session_id}_transcricao_final.txt")

        if not os.path.exists(transcription_path):
            print(f"⚠️ Pulando {session_id}: crônica encontrada, mas falta '{session_id}_transcricao_final.txt'.")
            continue

        output_path = os.path.join(logs_folder, f"{session_id}_log.md")
        paired_sessions.append({
            "session_num": session_num,
            "session_id": session_id,
            "chronicle_path": chronicle_path,
            "transcription_path": transcription_path,
            "output_path": output_path
        })

    paired_sessions.sort(key=lambda item: item["session_num"])
    print(f"🔎 {len(paired_sessions)} pares completos (crônica + transcrição) encontrados para '{table_id}'.")

    # 2. Filtrar apenas o que falta processar (checkpoint)
    pending_sessions = [
        s for s in paired_sessions
        if overwrite or not os.path.exists(s["output_path"])
    ]

    if not pending_sessions:
        print("✅ Todas as sessões encontradas já possuem arquivo _log.md! Atualizando apenas consolidados...")
        consolidate_session_logs(logs_folder=logs_folder, table_id=table_id, batch_size=batch_size)
        return

    to_process = pending_sessions[:max_sessions_per_run]
    remaining_after_run = len(pending_sessions) - len(to_process)
    print(
        f"📋 Pendentes: {len(pending_sessions)} | "
        f"Serão processadas nesta execução: {len(to_process)} "
        f"(restarão {remaining_after_run} para as próximas execuções)."
    )

    # 3. Buscar datas no Notion
    notion_dates = {}
    if notion_token and notion_config:
        notion_dates = fetch_notion_session_dates(notion_token, notion_config, table_id)

    # 4. Carregar config, template e cliente Gemini uma única vez
    try:
        gemini_cfg = _load_gemini_config()
        base_prompt = _load_prompt_template(template)
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ Falha na inicialização do lote: {e}")
        return

    # 5. Loop controlado por cadência
    processed_count = 0
    for idx, item in enumerate(to_process, start=1):
        s_num = item["session_num"]
        s_id = item["session_id"]

        if s_num in notion_dates:
            s_date = notion_dates[s_num]
            date_source = "Notion"
        else:
            mtime = os.path.getmtime(item["transcription_path"])
            s_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            date_source = "Data do arquivo (fallback)"

        print(f"\n[{idx}/{len(to_process)}] Processando {s_id} (Data: {s_date} [{date_source}])...")

        try:
            log_md = _generate_log_markdown(
                client=client,
                gemini_cfg=gemini_cfg,
                base_prompt=base_prompt,
                transcription_path=item["transcription_path"],
                chronicle_path=item["chronicle_path"],
                context_glossary=context_glossary,
                session_id=s_id,
                session_date=s_date,
                model=model
            )

            with open(item["output_path"], "w", encoding="utf-8") as f:
                f.write(log_md)

            processed_count += 1
            print(f"  ✅ Salvo: {item['output_path']}")

        except Exception as e:
            print(f"  ❌ Erro em {s_id}: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("🛑 Limite diário (RPD) ou de taxa atingido em todos os modelos. Encerrando lote com segurança.")
                break

        # Pausa entre chamadas para respeitar o teto de 5 RPM do Free Tier
        if idx < len(to_process):
            print(f"  ⏳ Aguardando {sleep_seconds}s (controle de RPM)...")
            time.sleep(sleep_seconds)

    # 6. Consolidação única ao final
    if processed_count > 0:
        print("\n🔄 Atualizando arquivos consolidados de 20 em 20 sessões...")
        consolidate_session_logs(logs_folder=logs_folder, table_id=table_id, batch_size=batch_size)

    print(f"\n🏁 Lote concluído: {processed_count} logs gerados nesta execução.")