import gc
import torch
import whisperx
import soundfile as sf

def executar_transcricao(arquivo_entrada, arquivo_saida, glossario_nomes, hf_token, dispositivo="cuda", precisao_modelo="float16", nome_modelo="large-v2"):
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

     # Preparação do prompt
    prompt_string = ", ".join(glossario_nomes)

    # Carrega o áudio na memória
    audio = whisperx.load_audio(arquivo_entrada)

    # --- ETAPA 1: TRANSCRIÇÃO ---
    print("1. Iniciando transcrição (Faster-Whisper via WhisperX)...")
    model = whisperx.load_model(nome_modelo, dispositivo, compute_type=comp_type)
    
    # Transcreve passando o idioma e o glossário como prompt inicial
    result = model.transcribe(
        audio, 
        batch_size=16, 
        language="pt",
        # O WhisperX repassa kwargs para o Faster-Whisper
        initial_prompt=prompt_string
    )
    
    # Limpeza CRÍTICA de memória da GPU
    del model
    gc.collect()
    torch.cuda.empty_cache()

    # --- ETAPA 2: ALINHAMENTO ---
    print("2. Alinhando os tempos das palavras (Forced Alignment)...")
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=dispositivo)
    result = whisperx.align(result["segments"], model_a, metadata, audio, dispositivo, return_char_alignments=False)
    
    del model_a
    gc.collect()
    torch.cuda.empty_cache()

    # --- ETAPA 3: DIARIZAÇÃO ---
    print("3. Executando Diarização (Pyannote)...")
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=dispositivo)
    
    # Você pode ajustar min_speakers e max_speakers se souber o tamanho da mesa (ex: min=3, max=6)
    diarize_segments = diarize_model(audio)
    
    # Atribui os locutores aos segmentos de texto
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # --- SALVANDO O RESULTADO ---
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        print(f"Salvando o texto final em: {arquivo_saida}")
        for segment in result["segments"]:
            # Pega o locutor. Se falhar, coloca DESCONHECIDO
            speaker = segment.get('speaker', 'DESCONHECIDO')
            
            # Formata a saída: [00.00s] SPEAKER_00: "Texto da fala"
            f.write(f"[{segment['start']:.2f}s] {speaker}: {segment['text'].strip()}\n")
            
    print("\n✅ Transcrição e Diarização CONCLUÍDAS!")