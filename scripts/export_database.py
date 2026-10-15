"""Exporta snapshot SQLite consistente, inclusive quando o banco usa WAL."""

import argparse
import os
import sqlite3
from pathlib import Path
from dotenv import dotenv_values
from contextlib import closing


def export_database(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("Banco de origem nao encontrado.")
    if source == destination:
        raise ValueError("Origem e destino devem ser diferentes.")
    # Exclusivo: nao substituir banco nem backup existente.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Falha na integridade do backup.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(
        description="Backup consistente do banco para migrar ao servidor; nao inclui .env."
    )
    parser.add_argument("output", help="Arquivo .sqlite3 novo para o backup")
    parser.add_argument(
        "--database", help="Banco de origem; padrao DATABASE_PATH do .env"
    )
    args = parser.parse_args()
    values = dotenv_values(".env")
    source = (
        args.database
        or os.getenv("DATABASE_PATH")
        or values.get("DATABASE_PATH")
        or "data/monitor.sqlite3"
    )
    try:
        target = export_database(source, args.output)
    except (ValueError, OSError, sqlite3.Error) as exc:
        raise SystemExit(
            "Falha no backup: "
            + type(exc).__name__
            + ". Confira origem, permissao e se o destino ja existe."
        ) from None
    print("Backup criado: " + str(target))


if __name__ == "__main__":
    main()
