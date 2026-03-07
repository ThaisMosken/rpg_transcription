from faster_whisper import WhisperModel

def executar_transcricao(arquivo_entrada, arquivo_saida, glossario_nomes, dispositivo="cuda", precisao_modelo="float16", nome_modelo="large-v2"):
    """
    Realiza a transcrição de um áudio utilizando Faster-Whisper.
    """
    
    print(f"📦 Carregando modelo: {nome_modelo} em {dispositivo} ({precisao_modelo}).")

    # Configuração do modelo baseada no dispositivo
    comp_type = precisao_modelo if dispositivo == "cuda" else "int8"
    
    model = WhisperModel(nome_modelo, device=dispositivo, compute_type=precisao_modelo)

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

    # Duração do arquivo
    duration_total = info.duration
    duration_min = int(duration_total // 60)
    duration_sec = int(duration_total % 60)
    print(f"🎙️ Duração do áudio: {duration_min}min {duration_sec}s")

    if duracao_minutos > 190:
        print(f"⚠️ Atenção: o áudio tem mais de 190 minutos. Pode ser necessário dividi-lo em múltiplas partes para evitar erros na transcrição.")


    # Processar e salvar o texto
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        print(f"Salvando o texto em: {arquivo_saida}")
        for segment in segments:
            f.write(f"{segment.text}\n")
            
    print("\nTranscrição CONCLUÍDA!")