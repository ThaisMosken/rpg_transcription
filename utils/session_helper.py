import os
from utils.glossary_manager import GlossaryManager


def setup_session(table_id, session_number, project_folder):
    """
    Centraliza a derivação de caminhos e o carregamento do glossário de uma sessão.

    Os arquivos de áudio divididos em partes (IDxx_parte_NNN.wav) não são tratados aqui:
    eles são detectados automaticamente por transcribe_session (src/transcription_processor.py).
    """
    session_id = f"{table_id}{session_number}"

    # 1. Derivação de caminhos
    input_file = os.path.join(project_folder, f"{session_id}w.wav")
    output_txt_file = os.path.join(project_folder, f"{session_id}_transcricao_final.txt")
    output_chronicle_file = os.path.join(project_folder, f"{session_id}_cronica.md")
    logs_folder = os.path.join(project_folder, "Logs")
    log_output_file = os.path.join(logs_folder, f"{session_id}_log.md")

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
        "logs_folder": logs_folder,
        "log_output_file": log_output_file,
        "context_glossary": context_glossary,
        "glossary_names": glossary_names
    }