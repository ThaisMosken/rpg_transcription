import soundfile as sf
from faster_whisper import WhisperModel

def executar_transcricao(arquivo_entrada, arquivo_saida, glossario_nomes, dispositivo="cuda", precisao_modelo="float16", nome_modelo="large-v2"):
    """
    Realiza a transcrição de um áudio utilizando Faster-Whisper.
    """
    
    print(f"📦 Carregando modelo: {nome_modelo} em {dispositivo} ({precisao_modelo}).")

    # Duração do arquivo
    info_audio = sf.info(arquivo_entrada)
    duration_min = int(info_audio.duration // 60)
    duration_sec = int(info_audio.duration % 60)
    print(f"🎙️ Duração do áudio: {duration_min}min {duration_sec}s")

    if duration_min > 190:
        print(f"⚠️ Atenção: o áudio tem mais de 190 minutos. Pode ser necessário dividi-lo em múltiplas partes para evitar erros na transcrição")

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

    # Processar e salvar o texto
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        print(f"Salvando o texto em: {arquivo_saida}")
        for segment in segments:
            f.write(f"{segment.text}\n")
            
    print("\nTranscrição CONCLUÍDA!")

def executar_transcricao_com_segmentos(arquivo_entrada, glossario_nomes, dispositivo="cuda", precisao_modelo="float16", nome_modelo="large-v2"):
    """
    Igual a executar_transcricao, mas retorna os segmentos em vez de salvar.
    Usado como etapa intermediária para o pipeline com diarização.
    """
    import soundfile as sf
    from faster_whisper import WhisperModel

    print(f"📦 Carregando modelo: {nome_modelo} em {dispositivo} ({precisao_modelo}).")

    info_audio = sf.info(arquivo_entrada)
    duration_min = int(info_audio.duration // 60)
    duration_sec = int(info_audio.duration % 60)
    print(f"🎙️ Duração do áudio: {duration_min}min {duration_sec}s")

    comp_type = precisao_modelo if dispositivo == "cuda" else "int8"
    model = WhisperModel(nome_modelo, device=dispositivo, compute_type=comp_type)

    prompt_string = ", ".join(glossario_nomes)

    segments, info = model.transcribe(
        arquivo_entrada,
        language="pt",
        vad_filter=True,
        word_timestamps=False,       # False está ok para alinhamento por segmento
        initial_prompt=prompt_string
    )

    # Materializa o gerador em lista (necessário para iterar mais de uma vez)
    segmentos = [
        {"inicio": s.start, "fim": s.end, "texto": s.text.strip()}
        for s in segments
    ]

    print(f"✅ Transcrição concluída. {len(segmentos)} segmentos extraídos.")
    return segmentos