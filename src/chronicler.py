import json
import os
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


def generate_gemini_chronicle(
    api_key,
    transcription_path,
    output_path,
    context_glossary,
    template,
    model=None
):
    """Lê a transcrição, baixa o prompt do GitHub, chama o Gemini e salva o resultado."""

    # 1. Carregar configurações dos modelos
    try:
        gemini_cfg = _load_gemini_config()
    except Exception as e:
        print(f"❌ Erro ao carregar configuração do Gemini: {e}")
        return

    # 2. Baixar o prompt do GitHub
    prompt_url = f"https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/refs/heads/main/prompts/{template}.md"
    try:
        response = requests.get(prompt_url)
        response.raise_for_status()
        base_prompt = response.text
        print("✅ Prompt base baixado do GitHub com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao baixar o prompt: {e}")
        return

    # 3. Configura o cliente da API
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"ERRO: Falha ao configurar o cliente Gemini: {e}")
        return

    # 4. Ler a transcrição
    try:
        with open(transcription_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado em {transcription_path}")
        return

    # 5. Montar o Prompt
    full_prompt = f"""
    **BLOCO DE TEXTO TRANSCRITO:**
    --- INÍCIO DA TRANSCRIÇÃO ---
    {transcription_text}
    --- FIM DA TRANSCRIÇÃO ---

    **IMPORTANTE:** Use o glossário a seguir para corrigir nomes: {context_glossary}

    {base_prompt}
    """

    # 6. Resolver fila de modelos (padrão do JSON ou override informado)
    default_models = gemini_cfg.get("default_models", [])
    if model is None:
        model_priority_queue = list(default_models)
    elif isinstance(model, list):
        model_priority_queue = list(model)
    else:
        model_priority_queue = [model] + [m for m in default_models if m != model]

    if not model_priority_queue:
        print("ERRO: Nenhum modelo configurado em 'default_models' ou informado via parâmetro.")
        return

    max_tokens = gemini_cfg.get("max_output_tokens", 16384)
    fallback_codes = set(gemini_cfg.get("fallback_error_codes", [429]))
    no_sampling_prefixes = tuple(gemini_cfg.get("no_sampling_prefixes", []))
    sampling_params = gemini_cfg.get("sampling_params", {})

    response = None

    # 7. Chamada à API com fallback automático
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
            print(f"\nEnviando solicitação ao modelo {current_model} (Isso pode levar alguns segundos)...")
            response = client.models.generate_content(
                model=current_model,
                contents=full_prompt,
                config=generation_config
            )
            break

        except APIError as e:
            if e.code in fallback_codes and current_model != model_priority_queue[-1]:
                print(f"⚠️ Cota excedida no {current_model} (Erro {e.code}). Tentando fallback...")
                continue
            print(f"ERRO DE API ({e.code}): {e.message}")
            return
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return

    if not response or not response.text:
        print("⚠️ O modelo não gerou resposta (possível bloqueio de segurança).")
        return

    final_chronicle = response.text

    # 8. Salvar Resultado
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_chronicle)

    print(f"✅ SUCESSO! Crônica salva em: {output_path}")