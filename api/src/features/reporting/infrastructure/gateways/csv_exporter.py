import asyncio
import csv


def _write_csv(path: str, results: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)


class CsvExporter:
    async def export(self, path: str, rows: list[dict[str, str]]) -> None:
        await asyncio.to_thread(_write_csv, path, rows)
