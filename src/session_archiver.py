import os
import re
import shutil

from src.session_logger import consolidate_session_logs
from utils.session_helper import build_folder_layout

# Pasta antiga onde as crônicas e transcrições eram arquivadas manualmente
LEGACY_ARCHIVE_FOLDER_NAME = "Crônicas e Transcrições"

# '<MESA><num>_cronica.md' ou '<MESA><num>_transcricao_final.txt'. A sigla é a parte antes
# do número, respeitando maiúsculas. As partes ('_transcricao_final_parte_NNN.txt'), os
# áudios, os logs e os configs não casam com o padrão e, portanto, nunca são movidos.
_LEGACY_FILE_PATTERN = re.compile(
    r"^(?P<table_id>[A-Za-z]+)(?P<number>\d+)_(?P<kind>cronica\.md|transcricao_final\.txt)$"
)


def ensure_folder_with_notice(folder):
    """
    Cria a pasta se ela não existir e avisa qual dos dois casos ocorreu.
    Como as siglas de mesa diferenciam maiúsculas, um erro de digitação (ex.: 'DiT' em vez
    de 'DIT') aparece aqui como "pasta nova criada". Retorna True se a pasta foi criada.
    """
    if os.path.isdir(folder):
        print(f"📁 Pasta existente: {folder}")
        return False
    os.makedirs(folder, exist_ok=True)
    print(f"🆕 Pasta NOVA criada: {folder}  (confira se a sigla da mesa está correta)")
    return True


def archive_session(project_folder, table_id, session_id, batch_size=20):
    """
    Bloco "Arquivar sessão": MOVE (não copia) a transcrição final, a crônica e o log de
    workbench/ para archive/transcriptions/<MESA>/, archive/chronicles/<MESA>/ e
    archive/logs/<MESA>/, e regera os consolidados de logs a partir da pasta de logs da mesa.

    - Se algum destino já tiver um arquivo com o mesmo nome, nada é movido (nunca sobrescreve).
    - Arquivos ausentes no workbench geram um aviso e os demais são arquivados normalmente.
    - Áudios (.wav), partes e outros arquivos do workbench não são tocados.
    """
    layout = build_folder_layout(project_folder, table_id)
    workbench = layout["workbench_folder"]

    plan = [
        (f"{session_id}_transcricao_final.txt", layout["archive_transcriptions_folder"]),
        (f"{session_id}_cronica.md", layout["archive_chronicles_folder"]),
        (f"{session_id}_log.md", layout["archive_logs_folder"]),
    ]

    to_move, missing, conflicts = [], [], []
    for file_name, dst_folder in plan:
        src = os.path.join(workbench, file_name)
        dst = os.path.join(dst_folder, file_name)
        if not os.path.exists(src):
            missing.append(file_name)
        elif os.path.exists(dst):
            conflicts.append(dst)
        else:
            to_move.append((src, dst))

    for file_name in missing:
        print(f"⚠️ Não encontrado em workbench/: {file_name}")

    if conflicts:
        print("🛑 Arquivamento cancelado: os destinos abaixo já existem (nada foi movido):")
        for dst in conflicts:
            print(f"  ❌ {dst}")
        return {"moved": [], "missing": missing, "conflicts": conflicts}

    if not to_move:
        print("⚠️ Nenhum arquivo da sessão encontrado em workbench/. Nada a arquivar.")
        return {"moved": [], "missing": missing, "conflicts": []}

    checked_folders = set()
    for _, dst in to_move:
        dst_folder = os.path.dirname(dst)
        if dst_folder not in checked_folders:
            ensure_folder_with_notice(dst_folder)
            checked_folders.add(dst_folder)

    moved = []
    for src, dst in to_move:
        shutil.move(src, dst)
        moved.append(dst)
        print(f"📦 Movido: {os.path.basename(dst)} → {os.path.dirname(dst)}")

    if any(dst.endswith("_log.md") for dst in moved):
        consolidate_session_logs(
            logs_folder=layout["archive_logs_folder"],
            table_id=table_id,
            batch_size=batch_size
        )

    print("✅ Sessão arquivada. O que sobrou em workbench/ (áudios, partes) deve ser apagado manualmente.")
    return {"moved": moved, "missing": missing, "conflicts": []}


def migrate_legacy_files(project_folder, dry_run=True, table_ids=None):
    """
    Execução única: move as transcrições e crônicas antigas para a nova estrutura.

    Origens: a raiz do projeto e a pasta 'Crônicas e Transcrições'.
    Destinos: archive/transcriptions/<MESA>/ e archive/chronicles/<MESA>/.

    - dry_run=True (padrão): só lista o que seria movido, por pasta de destino, sem alterar nada.
    - Um arquivo não é movido (e entra no relatório de conflitos) quando o destino já existe
      ou quando o mesmo nome aparece nas duas origens. Os demais são movidos normalmente.
    - table_ids: lista opcional de siglas (case sensitive) para migrar só algumas mesas.
    """
    origins = [project_folder, os.path.join(project_folder, LEGACY_ARCHIVE_FOLDER_NAME)]

    candidates = {}  # destino -> lista de origens que apontam para ele
    for origin in origins:
        if not os.path.isdir(origin):
            print(f"ℹ️ Origem não encontrada (ignorada): {origin}")
            continue
        for file_name in sorted(os.listdir(origin)):
            match = _LEGACY_FILE_PATTERN.match(file_name)
            src = os.path.join(origin, file_name)
            if not match or not os.path.isfile(src):
                continue
            table_id = match.group("table_id")
            if table_ids and table_id not in table_ids:
                continue
            layout = build_folder_layout(project_folder, table_id)
            dst_folder = (
                layout["archive_chronicles_folder"]
                if match.group("kind") == "cronica.md"
                else layout["archive_transcriptions_folder"]
            )
            candidates.setdefault(os.path.join(dst_folder, file_name), []).append(src)

    to_move, conflicts = [], []
    for dst, sources in candidates.items():
        if len(sources) > 1:
            conflicts.append((sources, "mesmo arquivo encontrado em mais de uma origem"))
        elif os.path.exists(dst):
            conflicts.append((sources, "o destino já existe"))
        else:
            to_move.append((sources[0], dst))

    mode = "SIMULAÇÃO (nada será alterado)" if dry_run else "EXECUÇÃO REAL"
    print(f"🔎 {mode}: {len(to_move)} arquivos a mover | {len(conflicts)} conflitos.\n")

    per_folder = {}
    for _, dst in to_move:
        per_folder[os.path.dirname(dst)] = per_folder.get(os.path.dirname(dst), 0) + 1
    for dst_folder in sorted(per_folder):
        status = "existente" if os.path.isdir(dst_folder) else "NOVA"
        print(f"  {per_folder[dst_folder]:>4} arquivo(s) → {dst_folder}  [pasta {status}]")

    if conflicts:
        print("\n⚠️ Conflitos (não serão movidos):")
        for sources, reason in conflicts:
            print(f"  ❌ {', '.join(sources)} — {reason}")

    if dry_run:
        print("\nℹ️ Simulação concluída. Confira a lista acima e rode de novo com dry_run=False.")
        return {"moved": [], "planned": to_move, "conflicts": conflicts}

    moved = []
    for src, dst in to_move:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved.append(dst)
    print(f"\n✅ Migração concluída: {len(moved)} arquivos movidos, {len(conflicts)} conflitos pendentes.")
    return {"moved": moved, "planned": to_move, "conflicts": conflicts}