import re
from notion_client import Client

class NotionPublisher:
    def __init__(self, token, databases_config):
        self.notion = Client(auth=token)
        self.config = databases_config
        self.termos_genericos = ["aldeões", "habitantes", "guardas", "multidão", "plebeus", "cultistas", "crianças"]

    def _limpar_nome(self, texto):
        limpo = texto.replace("**", "")
        limpo = re.split(r'[:\(]', limpo)[0]
        return limpo.strip("- *")

    def _processar_rich_text(self, texto):
        parts = re.split(r'(\*\*[^*]+\*\*)', texto)
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

    def encontrar_ou_criar_entrada(self, database_id, nome_bruto):
        nome = self._limpar_nome(nome_bruto)
        nome_low = nome.lower()
        if not nome or len(nome) > 60 or "nenhum" in nome_low: return None
        if any(termo in nome_low for termo in self.termos_genericos): return None

        # Busca usando o client oficial
        query = self.notion.databases.query(
            database_id=database_id,
            filter={"property": "Nome", "title": {"equals": nome}}
        )
        
        if query["results"]:
            return query["results"][0]["id"]

        new_page = self.notion.pages.create(
            parent={"database_id": database_id},
            properties={"Nome": {"title": [{"text": {"content": nome}}]}}
        )
        return new_page["id"]

    def parse_markdown_to_blocks(self, linhas_texto):
        blocos = []
        mapa_estilos = {
            "### ": ("heading_3", "blue_background", 4),
            "## ":  ("heading_2", "blue", 3),
            "# ":   ("heading_1", "default", 2),
            ">":    ("quote", "gray", 1),
            "* ":   ("bulleted_list_item", "default", 2),
            "- ":   ("bulleted_list_item", "default", 2)
        }

        for linha in linhas_texto:
            linha = linha.strip()
            if not linha: continue

            tipo, cor, offset = "paragraph", "default", 0
            for prefix, (t, c, o) in mapa_estilos.items():
                if linha.startswith(prefix):
                    tipo, cor, offset = t, c, o
                    break
            
            conteudo = linha[offset:].strip()
            blocos.append({
                "object": "block",
                "type": tipo,
                tipo: {"rich_text": self._processar_rich_text(conteudo), "color": cor}
            })
        return blocos[:100] # Limite da API do Notion por chamada

    def publicar_sessao(self, mesa_id, num_sessao, data, arquivo_path):
        if mesa_id not in self.databases_config:
            raise ValueError(f"Mesa '{mesa_id}' não encontrada no arquivo de configuração.")
            
        conf = self.databases_config[mesa_id]

        with open(arquivo_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()

        titulo_epico = linhas[0].strip().replace("#", "").strip()
        inteiro_texto = "".join(linhas)

        # Extração de NPCs e Itens
        def extrair(marcador):
            match = re.search(f"{marcador}:?(.*?)(?:\n\n|\n#|\n[A-Z]|$)", inteiro_texto, re.DOTALL | re.IGNORECASE)
            return [l.strip() for l in match.group(1).split('\n') if l.strip()] if match else []

        ids_npcs = [self.encontrar_ou_criar_entrada(self.config['DB_NPCS'], n) for n in extrair("NPCs encontrados")]
        ids_itens = [self.encontrar_ou_criar_entrada(self.config['DB_ITENS'], i) for i in extrair("Itens obtidos")]

        # Criar a página da Sessão
        res = self.notion.pages.create(
            parent={"database_id": self.config['MAPPING'][mesa_id]},
            properties={
                "Nome": {"title": [{"text": {"content": f"Sessão {num_sessao}"}}]},
                "Título": {"rich_text": [{"text": {"content": titulo_epico}}]},
                "Sessão": {"number": int(num_sessao)},
                "Data": {"date": {"start": data}},
                "NPCs": {"relation": [{"id": v} for v in ids_npcs if v]},
                "Itens": {"relation": [{"id": v} for v in ids_itens if v]}
            },
            children=self.parse_markdown_to_blocks(linhas)
        )
        
        return res["id"]