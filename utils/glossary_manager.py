import requests

class GlossaryManager:
    """Gerencia a busca e combinação de glossários para a transcrição."""
    
    # URL base onde os arquivos .md estão guardados (ajuste se necessário)
    BASE_URL = "https://raw.githubusercontent.com/ThaisMosken/rpg_transcription/main/lore/"
    
    MESA_CONFIG = {
        "id": "glossary_id.md", #ID: Icewind Dale, mesa dos Zéfiros
        "dia": "glossary_dia.md"  #DiA: Descent into Avernos, mesa do Inferno
    }

    def __init__(self, mesa_id):
        self.mesa_id = mesa_id.lower() if mesa_id else ""
        self.geral_url = f"{self.BASE_URL}glossary.md"
        
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
        geral = self._fetch_content(self.geral_url)
        
        # 2. Busca o glossário específico se o ID existir no mapa
        especifico = ""
        filename = self.MESA_CONFIG.get(self.mesa_id)
        if filename:
            especifico = self._fetch_content(f"{self.BASE_URL}{filename}")
        
        # 3. Combina e limpa espaços extras
        return f"### GLOSSÁRIO GERAL\n{geral}\n\n### GLOSSÁRIO DA MESA\n{especifico}".strip()