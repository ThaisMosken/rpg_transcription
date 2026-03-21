import os
from utils.glossary_manager import GlossaryManager

def setup_session(table_id, session_number, project_folder, file_part=""):
    """
    Centraliza a derivação de caminhos e carregamento de glossário.
    """
    session_id = f"{table_id}{session_number}"
    
    # 1. Derivação de Caminhos
    if file_part:
        input_file = os.path.join(project_folder, f"{session_id}_parte_{file_part}.wav")
        output_txt_file = os.path.join(project_folder, f"{session_id}_transcricao_final_parte_{file_part}.txt")
    else:
        input_file = os.path.join(project_folder, f"{session_id}w.wav")
        output_txt_file = os.path.join(project_folder, f"{session_id}_transcricao_final.txt")

    output_chronicle_file = os.path.join(project_folder, f"{session_id}_cronica.md")

    # 2. Processamento do Glossário
    manager = GlossaryManager(table_id)
    context_glossary = manager.get_full_glossary()
    
    glossary_names = [
        line.strip("- *").strip()
        for line in context_glossary.split('\n')
        if line.strip() and not line.startswith('#')
    ]

    return {
        "session_id": session_id,
        "input_file": input_file,
        "output_txt_file": output_txt_file,
        "output_chronicle_file": output_chronicle_file,
        "context_glossary": context_glossary,
        "glossary_names": glossary_names
    }