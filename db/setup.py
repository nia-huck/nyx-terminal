"""Nyx Terminal — Setup PostgreSQL.

Crea la base de datos, usuario y ejecuta el schema.
Luego corre el seed para poblar con datos iniciales.

Uso:
    python -m db.setup
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
import psycopg.sql
from dotenv import load_dotenv

load_dotenv()

SCHEMA_FILE = Path(__file__).parent / "schema.sql"

# Config — se puede override via .env
DB_NAME = os.getenv("NYX_DB_NAME", "nyx")
DB_USER = os.getenv("NYX_DB_USER", "nyx")
DB_PASS = os.getenv("NYX_DB_PASS", "nyx")
DB_HOST = os.getenv("NYX_DB_HOST", "localhost")
DB_PORT = os.getenv("NYX_DB_PORT", "5432")
PG_ADMIN_USER = os.getenv("PG_ADMIN_USER", "postgres")
PG_ADMIN_PASS = os.getenv("PG_ADMIN_PASS", "postgres")


def create_database():
    """Crea la base de datos y el usuario si no existen."""
    print("Conectando como admin...")
    admin_dsn = f"postgresql://{PG_ADMIN_USER}:{PG_ADMIN_PASS}@{DB_HOST}:{DB_PORT}/postgres"

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        # Crear usuario si no existe
        exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", [DB_USER]
        ).fetchone()
        if not exists:
            # DDL no soporta parametros, pero el user/pass son controlados por nosotros
            conn.execute(psycopg.sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
                psycopg.sql.Identifier(DB_USER),
                psycopg.sql.Literal(DB_PASS),
            ))
            print(f"  Usuario '{DB_USER}' creado")
        else:
            print(f"  Usuario '{DB_USER}' ya existe")

        # Crear base de datos si no existe
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", [DB_NAME]
        ).fetchone()
        if not exists:
            conn.execute(psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                psycopg.sql.Identifier(DB_NAME),
                psycopg.sql.Identifier(DB_USER),
            ))
            print(f"  Base de datos '{DB_NAME}' creada")
        else:
            print(f"  Base de datos '{DB_NAME}' ya existe")

        # Dar permisos
        conn.execute(psycopg.sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
            psycopg.sql.Identifier(DB_NAME),
            psycopg.sql.Identifier(DB_USER),
        ))


def run_schema():
    """Ejecuta el schema SQL."""
    print("Ejecutando schema...")
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    with psycopg.connect(dsn) as conn:
        conn.execute(schema_sql)
        conn.commit()

    print("  Schema aplicado correctamente")


def update_env():
    """Agrega DATABASE_URL al .env si no existe."""
    env_path = Path(__file__).parent.parent / ".env"
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if "DATABASE_URL" not in content:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\nDATABASE_URL={db_url}\n")
            print(f"  DATABASE_URL agregada a .env")
        else:
            print(f"  DATABASE_URL ya existe en .env")
    else:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"DATABASE_URL={db_url}\n")
        print(f"  .env creado con DATABASE_URL")


def main():
    print("=" * 50)
    print("NYX TERMINAL — Setup PostgreSQL")
    print("=" * 50)

    try:
        create_database()
    except Exception as e:
        print(f"\nError creando DB: {e}")
        print(f"\nAsegurate de que PostgreSQL esta corriendo y que el usuario admin es correcto.")
        print(f"Configuracion actual:")
        print(f"  Admin: {PG_ADMIN_USER}:{PG_ADMIN_PASS}@{DB_HOST}:{DB_PORT}")
        print(f"  Target: {DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        print(f"\nPodes configurar via .env: PG_ADMIN_USER, PG_ADMIN_PASS, NYX_DB_*")
        sys.exit(1)

    try:
        run_schema()
    except Exception as e:
        print(f"\nError ejecutando schema: {e}")
        sys.exit(1)

    update_env()

    print()
    print("Setup completado. Ahora ejecuta: python -m db.seed")


if __name__ == "__main__":
    main()
