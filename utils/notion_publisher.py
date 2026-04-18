import re
import requests
from notion_client import Client

class NotionPublisher:
    def __init__(self, token, databases_config):
        self.token = token
        self.notion = Client(auth=token)
        self.databases_config = databases_config
        self.generic_terms = ["aldeões", "habitantes", "guardas", "multidão", "plebeus", "cultistas", "crianças"]
        
        # Headers necessários para as chamadas via requests
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def _clean_name(self, text):
        cleaned_text = text.replace("**", "")
        cleaned_text = re.split(r'[:\(]', cleaned_text)[0]
        return cleaned_text.strip("- *")

    def _process_rich_text(self, text):
        parts = re.split(r'(\*\*[^*]+\*\*)', text)
        rich_text_list = []
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                rich_text_list.append({
                    "type": "text",
                    "text": {"content": part[2:-2]},
                    "annotations": {"bold": True}
                })
            elif part:
                rich_text_list.append({"type": "text", "text": {"content": part}})
        return rich_text_list

    def find_or_create_entry(self, database_id, raw_name):
        name = self._clean_name(raw_name)
        name_lower = name.lower()
        if not name or len(name) > 60 or "nenhum" in name_lower: return None
        if any(termo in name_lower for termo in self.generic_terms): return None

        query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
        payload = {"filter": {"property": "Nome", "title": {"equals": name}}}
        
        try:
            response = requests.post(query_url, headers=self.headers, json=payload)
            results = response.json().get("results", [])
            if results: 
                return results[0]["id"]

            # Criação da página
            new_page = self.notion.pages.create(
                parent={"database_id": database_id},
                properties={"Nome": {"title": [{"text": {"content": name}}]}}
            )
            return new_page["id"]
        except Exception as e:
            print(f"⚠️ Erro ao processar '{name}': {e}")
            return None

    def parse_markdown_to_blocks(self, text_lines):
        blocks = []
        style_map = {
            "### ": ("heading_3", "blue_background", 4),
            "## ":  ("heading_2", "blue", 3),
            "# ":   ("heading_1", "default", 2),
            ">":    ("quote", "gray", 1),
            "* ":   ("bulleted_list_item", "default", 2),
            "- ":   ("bulleted_list_item", "default", 2)
        }

        for line in text_lines:
            line = line.strip()
            if not line: continue

            block_type, color, offset = "paragraph", "default", 0
            for prefix, (t, c, o) in style_map.items():
                if line.startswith(prefix):
                    block_type, color, offset = t, c, o
                    break
            
            content = line[offset:].strip()
            blocks.append({
                "object": "block",
                "type": block_type,
                block_type: {"rich_text": self._process_rich_text(content), "color": color}
            })
        return blocks[:100]

    def publish_session(self, table_id, session_number, date, file_path):
        if table_id not in self.databases_config:
            raise ValueError(f"Mesa '{table_id}' não encontrada na configuração.")
            
        config = self.databases_config[table_id]

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        epic_title = lines[0].strip().replace("#", "").strip()
        full_text = "".join(lines)

        def extrair(marker):
            match = re.search(f"{marker}:?(.*?)(?:\n\n|\n#|\n[A-Z]|$)", full_text, re.DOTALL | re.IGNORECASE)
            return [line_item.strip() for line_item in match.group(1).split('\n') if line_item.strip()] if match else []

        # NPCs específicos da mesa
        npc_ids = [self.find_or_create_entry(config['DB_NPCS'], npc_name) for npc_name in extrair("NPCs encontrados")]

        # Monta as propriedades base
        properties = {
            "Nome": {"title": [{"text": {"content": f"Sessão {session_number}"}}]},
            "Título": {"rich_text": [{"text": {"content": epic_title}}]},
            "Sessão": {"number": int(session_number)},
            "Data": {"date": {"start": date}},
            "NPCs": {"relation": [{"id": value} for value in npc_ids if value]}
        }

        # Adiciona Campanha apenas se estiver definida no config
        if "DB_CAMPAIGN" in config:
            properties["Campanha"] = {"rich_text": [{"text": {"content": config["DB_CAMPAIGN"]}}]}

        # Criação da página principal da sessão
        result = self.notion.pages.create(
            parent={"database_id": config['DB_SESSAO']},
            properties=properties,
            children=self.parse_markdown_to_blocks(lines)
        )
        
        return result["id"]