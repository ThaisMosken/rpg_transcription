import soundfile as sf
from faster_whisper import WhisperModel

def execute_transcription(input_file, output_file, glossary_names, device="cuda", model_precision="float16", model_name="large-v2"):
    """
    Realiza a transcrição de um áudio utilizando Faster-Whisper.
    """
    
    print(f"📦 Carregando modelo: {model_name} em {device} ({model_precision}).")

    # Duração do arquivo
    audio_info = sf.info(input_file)
    duration_min = int(audio_info.duration // 60)
    duration_sec = int(audio_info.duration % 60)
    print(f"🎙️ Duração do áudio: {duration_min}min {duration_sec}s")

    if duration_min > 190:
        print(f"⚠️ Atenção: o áudio tem mais de 190 minutos. Pode ser necessário dividi-lo em múltiplas partes para evitar erros na transcrição")

    # Configuração do modelo baseada no device
    compute_type = model_precision if device == "cuda" else "int8"
    
    model = WhisperModel(model_name, device=device, compute_type=model_precision)

    # Preparação do prompt
    prompt_string = ", ".join(glossary_names)

    # Transcrição
    segments, info = model.transcribe(
        input_file,
        language="pt", 
        vad_filter=True, 
        word_timestamps=False, 
        initial_prompt=prompt_string 
    )

    # Processar e salvar o texto
    with open(output_file, "w", encoding="utf-8") as f:
        print(f"Salvando o texto em: {output_file}")
        for segment in segments:
            f.write(f"{segment.text}\n")
            
    print("\nTranscrição CONCLUÍDA!")