import sqlite3
import os
import shutil

# Script usado para procurar coisas dentro do .db do projeto

def scan_full_db_structure(db_path):
    """
    Varredura profunda para encontrar tabelas, índices ou views, 
    mesmo que o filtro padrão falhe.
    """
    db = ''
    temp_copy = "/tmp/full_scan_debug.db"
    shutil.copy2(db_path, temp_copy)
    
    try:
        conn = sqlite3.connect(temp_copy)
        cursor = conn.cursor()
        
        print(f"--- INICIANDO VARREDURA COMPLETA: {os.path.basename(db_path)} ---")
        
        # 1. Tentativa sem filtro de TYPE (mostra TUDO: tabelas, índices, triggers)
        try:
            cursor.execute("SELECT type, name, tbl_name, sql FROM sqlite_master;")
            items = cursor.fetchall()
            
            if not items:
                print("Aviso: sqlite_master retornou vazio. Tentando comandos PRAGMA...")
            else:
                for itype, name, tbl_name, sql in items:
                    print(f"[{itype.upper()}] Nome: {name} | Tabela Relacionada: {tbl_name}")
                    db = db + str(f"[{itype.upper()}] Nome: {name} | Tabela Relacionada: {tbl_name}\n")
                    if itype == 'table':
                        # Se acharmos uma tabela, listamos as colunas imediatamente
                        cursor.execute(f"PRAGMA table_info('{name}');")
                        cols = cursor.fetchall()
                        print(f"   |-- Colunas: {[c[1] for c in cols]}")
                        db = db + str(f"   |-- Colunas: {[c[1] for c in cols]}\n")
        except Exception as e:
            print(f"Erro ao ler sqlite_master: {e}")

        # 2. Comando de contingência: Listar databases e tabelas via PRAGMA
        print("\n--- TESTANDO METADADOS DE CONTINGÊNCIA ---")
        try:
            cursor.execute("PRAGMA database_list;")
            print(f"Database List: {cursor.fetchall()}")
            
            # Algumas builds do Resolve usam tabelas temporárias ou nomes específicos
            cursor.execute("SELECT * FROM sqlite_temp_master;")
            temp_items = cursor.fetchall()
            print(f"Itens Temporários encontrados: {len(temp_items)}")
        except:
            print("Metadados de contingência não retornaram dados adicionais.")

        conn.close()
    except Exception as e:
        print(f"Erro crítico no acesso: {e}")
    finally:
        if os.path.exists(temp_copy):
            os.remove(temp_copy)
    return db


# def deep_search_string(db_path, search_term):
#     """
#     Procura por uma string em todas as tabelas e colunas do banco de dados.
#     """
#     temp_copy = "/tmp/deep_search.db"
#     shutil.copy2(db_path, temp_copy)
    
#     results = []
    
#     try:
#         conn = sqlite3.connect(temp_copy)
#         cursor = conn.cursor()
        
#         # 1. Pega todas as tabelas
#         cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#         tables = [row[0] for row in cursor.fetchall()]
        
#         print(f"--- Iniciando busca por: '{search_term}' ---")
        
#         for table in tables:
#             # 2. Pega todas as colunas da tabela
#             cursor.execute(f"PRAGMA table_info('{table}');")
#             columns = [col[1] for col in cursor.fetchall()]
            
#             for column in columns:
#                 try:
#                     # 3. Tenta encontrar a string na coluna específica
#                     # Usamos LIKE para busca parcial e CAST para garantir que números virem texto
#                     query = f"SELECT `{column}` FROM `{table}` WHERE CAST(`{column}` AS TEXT) LIKE ? LIMIT 5;"
#                     cursor.execute(query, (f"%{search_term}%",))
#                     match = cursor.fetchone()
                    
#                     if match:
#                         print(f"[ACHADO] Tabela: {table} | Coluna: {column} | Valor: {match[0]}")
#                         results.append((table, column))
#                 except sqlite3.OperationalError:
#                     # Ignora colunas que não permitem busca textual ou erros de sintaxe em nomes especiais
#                     continue

#         conn.close()
#     except Exception as e:
#         print(f"Erro na busca: {e}")
#     finally:
#         if os.path.exists(temp_copy):
#             os.remove(temp_copy)
    
#     return results

import sqlite3
import shutil
import os

def deep_search_sqlite(db_path, search_term):
    """
    Ferramenta de diagnóstico para encontrar QUALQUER string dentro de um 
    banco SQLite, listando exatamente a Tabela e a Coluna.
    """
    # Nome do arquivo temporário para não travar o banco original
    temp_copy = "temp_diagnostic_search.db"
    
    if not os.path.exists(db_path):
        print(f"Erro: O arquivo {db_path} não foi encontrado.")
        return

    shutil.copy2(db_path, temp_copy)
    results = []

    try:
        conn = sqlite3.connect(temp_copy)
        cursor = conn.cursor()

        # 1. Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"--- Pesquisando por: '{search_term}' em {len(tables)} tabelas ---")

        for table in tables:
            try:
                # 2. Lista todas as colunas da tabela atual
                cursor.execute(f"PRAGMA table_info('{table}');")
                columns = [col[1] for col in cursor.fetchall()]

                for column in columns:
                    # 3. Busca o termo (case-insensitive via LIKE)
                    # CAST garante que possamos procurar strings em colunas de números
                    query = f"SELECT `{column}` FROM `{table}` WHERE CAST(`{column}` AS TEXT) LIKE ?"
                    cursor.execute(query, (f"%{search_term}%",))
                    
                    matches = cursor.fetchall()
                    if matches:
                        # Pegamos o valor único para mostrar um exemplo do que foi achado
                        sample_value = matches[0][0]
                        count = len(matches)
                        
                        print(f"✅ [ACHADO] Tabela: {table.ljust(20)} | Coluna: {column.ljust(15)} | Ocorrências: {count}")
                        print(f"   Exemplo: {sample_value}")
                        
                        results.append({
                            'table': table,
                            'column': column,
                            'count': count,
                            'sample': sample_value
                        })

            except sqlite3.OperationalError as e:
                # Ignora erros de tabelas virtuais ou permissões internas do SQLite
                continue

        conn.close()
    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        if os.path.exists(temp_copy):
            os.remove(temp_copy)

    if not results:
        print("--- Nenhum resultado encontrado ---")
    
    return results

# --- USO MANUAL ---
if __name__ == "__main__":
    # Coloque aqui o caminho do seu Project.db ou qualquer outro .db
    DB_FILE = "/home/user/.local/share/DaVinciResolve/Resolve Project Library/Resolve Projects/Users/guest/Projects/project/Project.db" 
    TERMO = "" # Exemplo: nome de um clipe ou parte de um caminho
    
    #deep_search_sqlite(DB_FILE, TERMO)

# Exemplo de uso:
# Busque pelo nome de um arquivo que você sabe que está no projeto
#deep_search_string('/home/user/.local/share/DaVinciResolve/Resolve Project Library/Resolve Projects/Users/guest/Projects/project/Project.db', "Reel20")

# Uso


with open('estr.txt', 'w') as arq:
    arq.write(scan_full_db_structure("/home/user/.local/share/DaVinciResolve/Resolve Project Library/Resolve Projects/Users/guest/Projects/project/Project.db"))
