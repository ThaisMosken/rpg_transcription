import os
from utils.glossary_manager import GlossaryManager


def build_folder_layout(project_folder, table_id):
    """
    Deriva as pastas do pipeline no Drive a partir da pasta do projeto e da sigla da mesa
    (case sensitive, sem normalização):

        <project_folder>/
        ├── config/                        notion_config.json
        ├── workbench/                     área de trabalho: .wav, partes, transcrição, crônica e log em revisão
        └── archive/
            ├── chronicles/<MESA>/
            ├── logs/<MESA>/               logs individuais + consolidados
            └── transcriptions/<MESA>/
    """
    archive_folder = os.path.join(project_folder, "archive")
    return {
        "config_folder": os.path.join(project_folder, "config"),
        "workbench_folder": os.path.join(project_folder, "workbench"),
        "archive_chronicles_folder": os.path.join(archive_folder, "chronicles", table_id),
        "archive_transcriptions_folder": os.path.join(archive_folder, "transcriptions", table_id),
        "archive_logs_folder": os.path.join(archive_folder, "logs", table_id),
    }


def setup_session(table_id, session_number, project_folder):
    """
    Centraliza a derivação de caminhos e o carregamento do glossário de uma sessão.

    Todos os arquivos de trabalho da sessão (áudio, transcrição, crônica e log) ficam em
    workbench/. A pasta archive/ só é tocada pelo bloco "Arquivar sessão".

    Os arquivos de áudio divididos em partes (IDxx_parte_NNN.wav) não são tratados aqui:
    eles são detectados automaticamente por transcribe_session (src/transcription_processor.py).
    """
    session_id = f"{table_id}{session_number}"
    layout = build_folder_layout(project_folder, table_id)

    # 1. Derivação de caminhos (tudo em workbench/)
    workbench_folder = layout["workbench_folder"]
    os.makedirs(workbench_folder, exist_ok=True)

    input_file = os.path.join(workbench_folder, f"{session_id}w.wav")
    output_txt_file = os.path.join(workbench_folder, f"{session_id}_transcricao_final.txt")
    output_chronicle_file = os.path.join(workbench_folder, f"{session_id}_cronica.md")
    log_output_file = os.path.join(workbench_folder, f"{session_id}_log.md")

    # 2. Processamento do glossário
    manager = GlossaryManager(table_id)
    context_glossary = manager.get_full_glossary()

    glossary_names = []
    for line in context_glossary.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue
        name = line.strip("- *").strip()
        if name:  # descarta entradas vazias (ex.: linha "- " sem nome)
            glossary_names.append(name)

    return {
        "session_id": session_id,
        "input_file": input_file,
        "output_txt_file": output_txt_file,
        "output_chronicle_file": output_chronicle_file,
        "log_output_file": log_output_file,
        "context_glossary": context_glossary,
        "glossary_names": glossary_names,
        **layout
    }