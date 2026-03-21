import requests
from google import genai
from google.genai.errors import APIError

def generate_gemini_chronicle(api_key, transcription_path, output_path, context_glossary, model, template):
    """Lê a transcrição, baixa o prompt do GitHub, chama o Gemini e salva o resultado."""
    
    # 1. Baixar o prompt do GitHub
    prompt_url = f"https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/refs/heads/main/prompts/{template}.md"
    try:
        response = requests.get(prompt_url)
        response.raise_for_status()
        base_prompt = response.text
        print("✅ Prompt base baixado do GitHub com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao baixar o prompt: {e}")
        return

    # 2. Configura o cliente da API
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"ERRO: Falha ao configurar o cliente Gemini: {e}")
        return

    # 3. Ler a transcrição
    try:
        with open(transcription_path, 'r', encoding='utf-8') as f:
            transcription_text = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado em {transcription_path}")
        return

    # 4. Montar o Prompt
    full_prompt = f"""
    **BLOCO DE TEXTO TRANSCRITO:**
    --- INÍCIO DA TRANSCRIÇÃO ---
    {transcription_text}
    --- FIM DA TRANSCRIÇÃO ---

    **IMPORTANTE:** Use o glossário a seguir para corrigir nomes: {context_glossary}

    {base_prompt}
    """

    # 5. Configuração e Chamada
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "max_output_tokens": 8192,
    }

    try:
        print("\nEnviando solicitação ao modelo Gemini (Isso pode levar alguns segundos)...")
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=generation_config
        )
        
        final_chronicle = response.text
        
        if not final_chronicle:
            print("⚠️ O modelo não gerou resposta (possível bloqueio de segurança).")
            return

        # 6. Salvar Resultado
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_chronicle)
            
        print(f"✅ SUCESSO! Crônica salva em: {output_path}")
        
    except APIError as e:
        print(f"ERRO DE API: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")