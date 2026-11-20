import gc
import glob
import os
import re
import subprocess

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


def _extract_part_label(wav_path):
    """Retorna o número da parte como aparece no nome do arquivo (ex.: '000'), ou None."""
    match = re.search(r"_parte_(\d+)\.wav$", os.path.basename(wav_path))
    return match.group(1) if match else None


def _free_gpu_memory_and_report():
    """Libera memória da GPU entre as partes e mostra o uso atual."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True
        )
        print(f"🧠 Memória da GPU (usada, total): {result.stdout.strip()}")
    except FileNotFoundError:
        pass


def _count_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _transcribe_to_file_safely(wav_path, txt_path, glossary_names, device, model_precision, model_name):
    """
    Transcreve para um arquivo temporário e só renomeia ao terminar sem erro,
    para uma queda do Colab não deixar um .txt truncado que pareça completo.
    """
    tmp_txt = txt_path + ".tmp"
    execute_transcription(
        input_file=wav_path,
        output_file=tmp_txt,
        glossary_names=glossary_names,
        device=device,
        model_precision=model_precision,
        model_name=model_name
    )
    os.replace(tmp_txt, txt_path)


def transcribe_session(
    session_id,
    project_folder,
    input_file,
    output_file,
    glossary_names,
    device="cuda",
    model_precision="float16",
    model_name="large-v2"
):
    """
    Transcreve uma sessão detectando automaticamente se o áudio foi dividido em partes.

    - Se existirem arquivos '{session_id}_parte_NNN.wav' em project_folder, transcreve cada parte
      (pulando as que já têm '{session_id}_transcricao_final_parte_NNN.txt') e junta todas,
      em ordem, em output_file (sobrescrevendo-o). Os .txt das partes são mantidos.
    - Caso contrário, transcreve input_file (arquivo único) para output_file.
    """
    wav_pattern = os.path.join(glob.escape(project_folder), f"{glob.escape(session_id)}_parte_*.wav")
    wav_parts = sorted(
        (p for p in glob.glob(wav_pattern) if _extract_part_label(p) is not None),
        key=lambda p: int(_extract_part_label(p))
    )

    # Arquivo único
    if not wav_parts:
        print(f"ℹ️ Nenhuma parte encontrada. Transcrevendo arquivo único: {input_file}")
        _transcribe_to_file_safely(
            input_file, output_file, glossary_names, device, model_precision, model_name
        )
        return output_file

    # Várias partes
    print(f"🔎 {len(wav_parts)} partes encontradas para {session_id}.")

    part_txt_files = []
    transcribed, skipped = 0, 0

    for idx, wav_path in enumerate(wav_parts, start=1):
        label = _extract_part_label(wav_path)
        part_txt = os.path.join(project_folder, f"{session_id}_transcricao_final_parte_{label}.txt")
        part_txt_files.append(part_txt)

        # Checkpoint: só pula se o .txt existe e não está vazio
        if os.path.exists(part_txt) and os.path.getsize(part_txt) > 0:
            print(f"\n[{idx}/{len(wav_parts)}] ⏭️ Parte {label} já transcrita. Pulando.")
            skipped += 1
            continue

        print(f"\n[{idx}/{len(wav_parts)}] 🎙️ Transcrevendo parte {label}...")
        _transcribe_to_file_safely(
            wav_path, part_txt, glossary_names, device, model_precision, model_name
        )
        transcribed += 1
        _free_gpu_memory_and_report()

    # Junção das partes em ordem
    print(f"\n🧩 Juntando {len(part_txt_files)} partes em: {output_file}")
    with open(output_file, "w", encoding="utf-8") as merged:
        for part_txt in part_txt_files:
            with open(part_txt, "r", encoding="utf-8") as f:
                content = f.read().rstrip("\n")
            if content:
                merged.write(content + "\n")

    # Resumo
    print("\n📋 RESUMO")
    print(f"  Partes encontradas: {len(wav_parts)} | transcritas agora: {transcribed} | puladas: {skipped}")
    for part_txt in part_txt_files:
        print(f"  {os.path.basename(part_txt)}: {_count_lines(part_txt)} linhas")
    print(f"  {os.path.basename(output_file)}: {_count_lines(output_file)} linhas (final)")
    print("✅ Transcrição consolidada. Pode seguir para o Bloco 5.")

    return output_file