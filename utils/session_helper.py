import os
from utils.glossary_manager import GlossaryManager

def setup_session(id_mesa, num_sessao, pasta_projeto, parte_arquivo=""):
    """
    Centraliza a derivação de caminhos e carregamento de glossário.
    """
    id_sessao = f"{id_mesa}{num_sessao}"
    
    # 1. Derivação de Caminhos
    if parte_arquivo:
        arquivo_entrada = os.path.join(pasta_projeto, f"{id_sessao}_parte_{parte_arquivo}.wav")
        arquivo_txt_saida = os.path.join(pasta_projeto, f"{id_sessao}_transcricao_final_parte_{parte_arquivo}.txt")
    else:
        arquivo_entrada = os.path.join(pasta_projeto, f"{id_sessao}w.wav")
        arquivo_txt_saida = os.path.join(pasta_projeto, f"{id_sessao}_transcricao_final.txt")

    arquivo_cronica_saida = os.path.join(pasta_projeto, f"{id_sessao}_cronica.md")

    # 2. Processamento do Glossário
    manager = GlossaryManager(id_mesa)
    glossario_contexto = manager.get_full_glossary()
    
    glossario_nomes = [
        linha.strip("- *").strip()
        for linha in glossario_contexto.split('\n')
        if linha.strip() and not linha.startswith('#')
    ]

    return {
        "id_sessao": id_sessao,
        "arquivo_entrada": arquivo_entrada,
        "arquivo_txt_saida": arquivo_txt_saida,
        "arquivo_cronica_saida": arquivo_cronica_saida,
        "glossario_contexto": glossario_contexto,
        "glossario_nomes": glossario_nomes
    }