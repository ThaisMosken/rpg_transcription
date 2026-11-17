import json
import os
import re
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
        print(f"✅ Template '{template}' baixado do GitHub com sucesso!")
        return response.text
    except Exception as github_err:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_path = os.path.join(repo_root, "prompts", f"{template}.md")
        if os.path.exists(local_path):
            print(f"⚠️ Usando template local '{local_path}' (GitHub indisponível: {github_err}).")
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
        raise RuntimeError(f"Não foi possível carregar o template '{template}': {github_err}")


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

    # Ordena numericamente pelo número inteiro da sessão (001 < 08 < 10 < 100)
    matched_logs.sort(key=lambda item: item[0])

    # Agrupa em faixas fixas de 20 sessões (1-20 -> Parte 1, 21-40 -> Parte 2, etc.)
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


def generate_gemini_log(
    api_key,
    transcription_path,
    chronicle_path,
    output_path,
    context_glossary,
    table_id,
    session_id,
    session_date,
    template="template_log_v1",
    model=None,
    batch_size=20
):
    """
    Gera o log factual individual da sessão cruzando transcrição, crônica e glossário,
    e atualiza os arquivos consolidados na pasta Logs.
    """
    # 1. Carregar configurações dos modelos
    try:
        gemini_cfg = _load_gemini_config()
    except Exception as e:
        print(f"❌ Erro ao carregar configuração do Gemini: {e}")
        return

    # 2. Carregar prompt base
    try:
        base_prompt = _load_prompt_template(template)
    except Exception as e:
        print(f"❌ Erro ao carregar o prompt de log: {e}")
        return

    # 3. Configurar cliente da API
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ Falha ao configurar o cliente Gemini: {e}")
        return

    # 4. Ler transcrição e crônica revisada
    try:
        with open(transcription_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo de transcrição não encontrado: {transcription_path}")
        return

    try:
        with open(chronicle_path, "r", encoding="utf-8") as f:
            chronicle_text = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo de crônica não encontrado: {chronicle_path}")
        return

    # 5. Montar prompt completo
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

    # 6. Resolver fila de modelos (mesma lógica do chronicler.py)
    default_models = gemini_cfg.get("default_models", [])
    if model is None:
        modelos_prioridade = list(default_models)
    elif isinstance(model, list):
        modelos_prioridade = list(model)
    else:
        modelos_prioridade = [model] + [m for m in default_models if m != model]

    if not modelos_prioridade:
        print("❌ Nenhum modelo configurado em 'default_models' ou informado via parâmetro.")
        return

    max_tokens = gemini_cfg.get("max_output_tokens", 16384)
    fallback_codes = set(gemini_cfg.get("fallback_error_codes", [429]))
    no_sampling_prefixes = tuple(gemini_cfg.get("no_sampling_prefixes", []))
    sampling_params = gemini_cfg.get("sampling_params", {})

    response = None

    # 7. Chamada à API com fallback automático
    for modelo_atual in modelos_prioridade:
        if modelo_atual.startswith(no_sampling_prefixes):
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens
            )
        else:
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                **sampling_params
            )

        try:
            print(f"\nGerando Log Factual com o modelo {modelo_atual} (Isso pode levar alguns segundos)...")
            response = client.models.generate_content(
                model=modelo_atual,
                contents=full_prompt,
                config=generation_config
            )
            break

        except APIError as e:
            if e.code in fallback_codes and modelo_atual != modelos_prioridade[-1]:
                print(f"⚠️ Cota excedida no {modelo_atual} (Erro {e.code}). Tentando fallback...")
                continue
            print(f"❌ ERRO DE API ({e.code}): {e.message}")
            return
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            return

    if not response or not response.text:
        print("⚠️ O modelo não gerou resposta (possível bloqueio de segurança).")
        return

    # 8. Salvar Log Individual diretamente na pasta Logs
    logs_folder = os.path.dirname(output_path)
    os.makedirs(logs_folder, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text.strip() + "\n")

    print(f"✅ SUCESSO! Log individual salvo em: {output_path}")

    # 9. Atualizar consolidação de 20 em 20 sessões
    consolidate_session_logs(
        logs_folder=logs_folder,
        table_id=table_id,
        batch_size=batch_size
    )