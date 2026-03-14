def alinhar_transcricao_com_diarizacao(segmentos_whisper, segmentos_diarizacao):
    """
    Alinha segmentos do Whisper com turnos de fala do pyannote
    por maior sobreposição de tempo.

    Retorna lista de dicts:
      [{"falante": "SPEAKER_00", "inicio": float, "fim": float, "texto": str}, ...]
    """

    def calcular_sobreposicao(a_inicio, a_fim, b_inicio, b_fim):
        inicio = max(a_inicio, b_inicio)
        fim    = min(a_fim,    b_fim)
        return max(0.0, fim - inicio)

    resultado = []

    for seg in segmentos_whisper:
        melhor_falante = "SPEAKER_DESCONHECIDO"
        melhor_overlap = 0.0

        for turno in segmentos_diarizacao:
            overlap = calcular_sobreposicao(
                seg["inicio"], seg["fim"],
                turno["inicio"], turno["fim"]
            )
            if overlap > melhor_overlap:
                melhor_overlap = overlap
                melhor_falante = turno["falante"]

        resultado.append({
            "falante": melhor_falante,
            "inicio":  seg["inicio"],
            "fim":     seg["fim"],
            "texto":   seg["texto"]
        })

    return resultado


def salvar_transcricao_diarizada(segmentos_alinhados, arquivo_saida):
    """
    Salva a transcrição com rótulos de falante no formato:

    [00:00:05 - 00:00:12] SPEAKER_00: Texto do segmento aqui.
    """
    def formatar_tempo(segundos):
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    falante_atual = None
    buffer_texto  = []
    buffer_inicio = None
    buffer_fim    = None

    linhas = []

    def flush_buffer():
        if buffer_texto:
            texto = " ".join(buffer_texto).strip()
            ts_inicio = formatar_tempo(buffer_inicio)
            ts_fim    = formatar_tempo(buffer_fim)
            linhas.append(f"[{ts_inicio} - {ts_fim}] {falante_atual}: {texto}")

    for seg in segmentos_alinhados:
        if seg["falante"] != falante_atual:
            flush_buffer()
            falante_atual = seg["falante"]
            buffer_texto  = [seg["texto"]]
            buffer_inicio = seg["inicio"]
            buffer_fim    = seg["fim"]
        else:
            buffer_texto.append(seg["texto"])
            buffer_fim = seg["fim"]

    flush_buffer()  # último bloco

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"💾 Arquivo salvo em: {arquivo_saida}")
    print(f"   Total de blocos de fala: {len(linhas)}")