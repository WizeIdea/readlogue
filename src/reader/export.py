from __future__ import annotations

from pathlib import Path

from reader.storage import connect, export_csv, export_jsonl


def export_datasets(database: str | Path, output_dir: str | Path = "exports") -> tuple[Path, Path]:
    output_path = Path(output_dir)
    with connect(database) as connection:
        csv_path = export_csv(connection, output_path / "reader.csv")
        jsonl_path = export_jsonl(connection, output_path / "reader.jsonl")
    return csv_path, jsonl_path