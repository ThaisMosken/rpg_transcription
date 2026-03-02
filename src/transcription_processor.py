from faster_whisper import WhisperModel

def executar_transcricao(arquivo_entrada, arquivo_saida, glossario_nomes, dispositivo="cuda", precisao_modelo="float16"):
    """
    Realiza a transcrição de um áudio utilizando Faster-Whisper.
    """
    
    print(f"Iniciando a transcrição com Faster-Whisper usando {dispositivo}.")

    # Configuração do modelo baseada no dispositivo
    if dispositivo == "cuda":
        model = WhisperModel("large-v2", device="cuda", compute_type=precisao_modelo)
    else:
        model = WhisperModel("large-v2", device="cpu", compute_type="int8")

    # Preparação do prompt
    prompt_string = ", ".join(glossario_nomes)

    # Transcrição
    segments, info = model.transcribe(
        arquivo_entrada,
        language="pt", 
        vad_filter=True, 
        word_timestamps=False, 
        initial_prompt=prompt_string 
    )

    # Processar e salvar o texto
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        print(f"Salvando o texto em: {arquivo_saida}")
        for segment in segments:
            f.write(f"{segment.text}\n")
            
    print("\nTranscrição CONCLUÍDA!")