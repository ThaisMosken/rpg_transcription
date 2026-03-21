import requests

class GlossaryManager:
    """Gerencia a busca e combinação de glossários para a transcrição."""
    
    # URL base onde os arquivos .md estão guardados (ajuste se necessário)
    BASE_URL = "https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/main/lore/"
    
    TABLE_CONFIG = {
        "dia": "glossary_dia.md",  #DiA: Descent into Avernos, mesa do Inferno
        "dit": "glossary_dit.md",  #DiT: Dead in Thay
        "id": "glossary_id.md", #ID: Icewind Dale, mesa dos Zéfiros
        "ooa": "glossary_ooa.md"  #OoA: Out of the Abyss
    }

    def __init__(self, table_id):
        self.table_id = table_id.lower() if table_id else ""
        self.general_url = f"{self.BASE_URL}glossary.md"
        
    def _fetch_content(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            return ""
        except Exception as e:
            print(f"Erro ao buscar glossário: {e}")
            return ""

    def get_full_glossary(self):
        # 1. Busca o glossário geral
        general_glossary = self._fetch_content(self.general_url)
        
        # 2. Busca o glossário específico se o ID existir no mapa
        specific_glossary = ""
        filename = self.TABLE_CONFIG.get(self.table_id)
        if filename:
            specific_glossary = self._fetch_content(f"{self.BASE_URL}{filename}")
        
        # 3. Combina e limpa espaços extras
        return f"### GLOSSÁRIO GERAL\n{general_glossary}\n\n### GLOSSÁRIO DA MESA\n{specific_glossary}".strip()