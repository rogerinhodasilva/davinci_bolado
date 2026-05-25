import sqlite3
import os
import shutil
import time
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DavinciMonitor:
    def __init__(self):

        self.base_path = os.path.expanduser('~/.local/share/DaVinciResolve/Resolve Project Library/Resolve Projects/Users/guest/Projects/')
        self.db_path = None
        self.db_dir = None
        self.temp_db = "/tmp/timeline_monitor.db"
        self.last_known_files = set()
        self.new_files_queue = Queue()
        self.observer = Observer()

    def find_active_project(self):
        """Encontra o projeto que teve o Project.db alterado mais recentemente."""
        print("Buscando projeto ativo baseado em modificações recentes...")
        
        while True:
            latest_db = None
            last_mod_time = 0
            
            # Percorre todas as pastas de projeto
            for root, dirs, files in os.walk(self.base_path):
                if 'Project.db' in files:
                    db_full_path = os.path.join(root, 'Project.db')
                    mtime = os.path.getmtime(db_full_path)
                    
                    if mtime > last_mod_time:
                        last_mod_time = mtime
                        latest_db = db_full_path

            if latest_db:
                # Extrai o nome do projeto (nome da pasta que contém o Project.db)
                project_name = os.path.basename(os.path.dirname(latest_db))
                
                # Se o arquivo foi modificado nos últimos 30 segundos, assumimos que é o atual
                if time.time() - last_mod_time < 30:
                    print(f"\n[PROJETO ATIVO DETECTADO]: {project_name}")
                    self.db_path = latest_db
                    self.db_dir = os.path.dirname(self.db_path)
                    return project_name
            
            time.sleep(2)

    def _query_db(self):
        """Lê os arquivos da tabela Sm2TiItem via cópia em RAM."""
        files = set()
        if not self.db_path: return files
        try:
            shutil.copy2(self.db_path, self.temp_db)
            conn = sqlite3.connect(self.temp_db)
            cursor = conn.cursor()
            query = "SELECT DISTINCT MediaFilePath FROM Sm2TiItem WHERE MediaFilePath IS NOT NULL AND MediaFilePath != '';"
            cursor.execute(query)
            files = {str(row[0]) for row in cursor.fetchall()}
            conn.close()
        except Exception:
            pass 
        return files

    def get_initial_queue(self):
        self.last_known_files = self._query_db()
        return list(self.last_known_files)

    def start_watching(self):
        class UpdateHandler(FileSystemEventHandler):
            def __init__(self, monitor):
                self.monitor = monitor
            def on_modified(self, event):
                if event.src_path == self.monitor.db_path:
                    current = self.monitor._query_db()
                    diff = current - self.monitor.last_known_files
                    if diff:
                        for f in diff:
                            self.monitor.last_known_files.add(f)
                            self.monitor.new_files_queue.put(f)

        self.observer.schedule(UpdateHandler(self), self.db_dir, recursive=False)
        self.observer.start()

    def get_next_new(self):
        return self.new_files_queue.get()

    def stop(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

if __name__ == "__main__":
    monitor = DavinciMonitor()
    
    # 1. Detecta o projeto baseado na última alteração de arquivo
    nome_projeto = monitor.find_active_project()

    # 2. Retorna a fila inicial
    iniciais = monitor.get_initial_queue()
    print(f"Arquivos iniciais em '{nome_projeto}': {len(iniciais)}")

    # 3. Inicia Watchdog
    monitor.start_watching()
    print(f"Monitorando novos itens em tempo real...")

    try:
        while True:
            novo_arquivo = monitor.get_next_new()
            print(f"NOVO DETECTADO: {novo_arquivo}")
    except KeyboardInterrupt:
        monitor.stop()