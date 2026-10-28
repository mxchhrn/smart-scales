import shutil
import plyvel
import sqlite3
# sqlcipher3 is the maintained binding, pysqlcipher3 no longer builds on python 3.13+
try:
    from sqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    from pysqlcipher3 import dbapi2 as sqlcipher
from . import functions_helper as fhelper

def check_db(db_path: str) -> bool:
    with open(db_path, "rb") as f:
        header = f.read(16)

    if header.startswith(b"SQLite format 3"):
        print("{}seems to be readable.".format(db_path))
    
    try:
        sqlite3.connect(db_path).execute("SELECT name FROM sqlite_master WHERE type='table'")
        return True
    except sqlite3.DatabaseError:
        return False

# get the content of a sqlite database as dict without column names (only tuples) 
def get_sqlite_db_data(db_path: str) -> dict:
    t_data = {}
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for t in tables:
        cursor.execute(f"SELECT * FROM {t[0]}")
        t_data[t[0]] = cursor.fetchall()
    cursor.close()
    db.close()
    return t_data

# get content of a sqlite db as dict with column names
def get_sqlite_db_as_dict(db_path: str, database_key: str = None) -> dict:
    t_data = {}
    if check_db(db_path):
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
    else:
        if database_key:
            db = sqlcipher.connect(db_path)
            cursor = db.cursor()
            try:
                cursor.execute("PRAGMA key='{}';".format(database_key))
            except Exception:
                print("ERROR: not able to decrypt database.")
                return t_data
        else:
            print("ERROR: No key given to decrypt database.")
            return t_data
    # get table name
    cursor.execute("SELECT name FROM sqlite_master WHERE    type='table'")
    tables = cursor.fetchall()  
    for t in tables:
        table_name = t[0]   
        # select all
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()    
        # get column names
        col_names = [desc[0] for desc in cursor.description]    
        # convert into dict
        t_data[table_name] = [
            dict(zip(col_names, row)) for row in rows
        ]   
    cursor.close()
    db.close()
    
    return t_data

# get the content of a LevelDB as dict
def get_leveldb_kv_pairs(db_path: str) -> dict:
    # work on a tmp copy of the given LevelDB (to avoid changing the original data)
    tmp_path = './tmp_leveldb_' + fhelper.get_random(8)
    shutil.copytree(db_path, tmp_path)

    pairs = {}
    db = plyvel.DB(tmp_path, create_if_missing=False)
    for k, v in db:
        tmp_k = k.decode('ascii', errors='ignore')
        tmp_v = v.decode('ascii', errors='ignore')
        pairs[fhelper.remove_non_printable(tmp_k)] = fhelper.remove_non_printable(tmp_v)
    db.close()

    shutil.rmtree(tmp_path)

    return pairs
