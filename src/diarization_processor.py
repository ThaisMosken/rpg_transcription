from pyannote.audio import Pipeline
import torch

def executar_diarizacao(arquivo_entrada, hf_token, num_falantes=None):
    """
    Executa a diarização de um áudio usando pyannote.audio.
    
    Retorna uma lista de dicts:
      [{"inicio": float, "fim": float, "falante": "SPEAKER_00"}, ...]
    """
    print("🎙️ Carregando pipeline de diarização (pyannote)...")
    
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token
    )
    
    # Usa GPU se disponível
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = pipeline.to(device)
    print(f"   Rodando diarização em: {device}")

    # Parâmetros opcionais de número de falantes
    diarize_kwargs = {}
    if num_falantes:
        diarize_kwargs["num_speakers"] = num_falantes

    print("⏳ Iniciando diarização (pode levar alguns minutos para áudios longos)...")
    diarizacao = pipeline(arquivo_entrada, **diarize_kwargs)

    # Converte para lista de dicts simples
    segmentos = []
    for turno, _, falante in diarizacao.itertracks(yield_label=True):
        segmentos.append({
            "inicio": turno.start,
            "fim":    turno.end,
            "falante": falante
        })

    print(f"✅ Diarização concluída. {len(segmentos)} turnos de fala detectados.")
    return segmentos