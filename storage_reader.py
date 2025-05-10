import os
import sys
import threading
from queue import Queue
# from winreg import ConnectRegistry, OpenKey, EnumKey, QueryValueEx, HKEY_LOCAL_MACHINE

# ----------------------------------------
# CONFIGURAÇÕES DE PASTAS “SEGURAS” PARA REMOÇÃO
SAFE_SUBPATHS = [
    os.path.join("Windows", "Temp"),
    os.path.join("Users", os.sep, "AppData", "Local", "Temp"),
    os.path.join("Windows", "SoftwareDistribution", "Download"),
    os.path.join("Windows", "Prefetch"),
    "Cache",
    "Logs",
]
# ----------------------------------------


def sizeof_fmt(num, suffix='B'):
    """Converte bytes em formato legível (KB, MB, GB...)"""
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Y{suffix}"


def folder_size(path):
    """Calcula tamanho de todos os arquivos em path (recursivo)."""
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except (OSError, PermissionError):
                continue
    return total


def is_removable(path):
    """Retorna True se path corresponder a alguma pasta de cache/temp/log definida."""
    p = path.lower()
    for sub in SAFE_SUBPATHS:
        if sub.lower() in p:
            return True
    return False


def worker(q, results):
    while True:
        name, path = q.get()
        if name is None:
            break
        size = folder_size(path)
        removable = is_removable(path)
        results.append((name, path, size, removable))
        q.task_done()


def main():
    if os.name != 'nt':
        print("Este script foi projetado para Windows.")
        sys.exit(1)

    # Determina drive onde o Windows está instalado (e.g. "C:\\")
    system_drive = os.environ.get("SystemDrive", "C:") + os.sep
    print(f"Varrendo raiz do disco: {system_drive}\n")

    # Lista todas as pastas de primeiro nível na raiz
    root_dirs = []
    try:
        for entry in os.listdir(system_drive):
            full = os.path.join(system_drive, entry)
            if os.path.isdir(full):
                root_dirs.append((entry, full))
    except PermissionError:
        print("Permissão negada ao listar raiz do disco.")
        sys.exit(1)

    # Configura fila e pool de threads
    q = Queue()
    results = []
    num_threads = min(8, len(root_dirs))
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(q, results), daemon=True)
        t.start()
        threads.append(t)

    # Enfileira cada pasta da raiz
    for name, path in root_dirs:
        q.put((name, path))

    # Aguarda término
    q.join()
    for _ in threads:
        q.put((None, None))

    # Ordena por tamanho decrescente
    results.sort(key=lambda x: x[2], reverse=True)

    # Exibe tabela no terminal
    print(f"{'Pasta':25} {'Tamanho':>12}  {'Removível':>10}  Caminho")
    print("-" * 90)
    for name, path, size, removable in results:
        flag = "Sim" if removable else "Não"
        print(f"{name[:23]:25} {sizeof_fmt(size):>12}  {flag:>10}  {path}")


if __name__ == "__main__":
    main()
