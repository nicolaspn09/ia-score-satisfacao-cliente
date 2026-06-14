import os
import oracledb
from sqlalchemy import create_engine


def connection_postgres(database):
    # Lê variáveis de ambiente
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASS")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    # Cria e retorna o engine
    return create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')


def conectar_oracle():
    uid = "kauebaesso"
    pwd = "COMPANY_NAME"
    db  = "10.1.1.20/pdb1"
    connection = oracledb.connect(uid + "/" + pwd + "@" + db)
    return connection
