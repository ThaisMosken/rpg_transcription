import requests
from google import genai
from google.genai.errors import APIError

def gerar_cronica_gemini(api_key, caminho_transcricao, caminho_saida, glossario_contexto):
    """Lê a transcrição, baixa o prompt do GitHub, chama o Gemini e salva o resultado."""
    
    # 1. Baixar o prompt do GitHub
    url_prompt = "https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/refs/heads/main/prompts/template_cronica_v1.md"
    try:
        response = requests.get(url_prompt)
        response.raise_for_status()
        prompt_base = response.text
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
        with open(caminho_transcricao, 'r', encoding='utf-8') as f:
            transcricao_texto = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado em {caminho_transcricao}")
        return

    # 4. Montar o Prompt
    prompt_completo = f"""
    **BLOCO DE TEXTO TRANSCRITO:**
    --- INÍCIO DA TRANSCRIÇÃO ---
    {transcricao_texto}
    --- FIM DA TRANSCRIÇÃO ---

    **IMPORTANTE:** Use o glossário a seguir para corrigir nomes: {glossario_contexto}

    {prompt_base}
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
            model='gemini-2.0-flash', # Note: Ajustado para o nome oficial atual se necessário
            contents=prompt_completo,
            config=generation_config
        )
        
        cronica_final = response.text
        
        if not cronica_final:
            print("⚠️ O modelo não gerou resposta (possível bloqueio de segurança).")
            return

        # 6. Salvar Resultado
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(cronica_final)
            
        print(f"✅ SUCESSO! Crônica salva em: {caminho_saida}")
        
    except APIError as e:
        print(f"ERRO DE API: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")