"""DatasetAnalysisAgent — computes summary statistics for CSV/tabular uploads."""

from __future__ import annotations

import csv
import io
import logging
import statistics
from typing import Any

from tasks.task_model import Task
from ._sandbox import read_file_safe

logger = logging.getLogger(__name__)


class DatasetAnalysisAgent:
    """Analyses CSV files in the upload sandbox.

    Task payload expected keys:
        upload_id (str): UUID of the upload directory.
        filename (str): Name of the CSV file to analyse.
    """

    name = "dataset_analysis"
    description = "Reads a CSV file and computes descriptive statistics."

    async def handle_task(self, task: Task) -> dict[str, Any]:
        upload_id: str = task.payload.get("upload_id", "")
        filename: str = task.payload.get("filename", "")

        if not upload_id or not filename:
            raise ValueError("Task payload must include 'upload_id' and 'filename'.")

        logger.info("DatasetAnalysisAgent analysing %s/%s", upload_id, filename)
        raw = read_file_safe(upload_id, filename)
        stats = self._analyse_csv(raw)
        return {
            "type": "dataset_analysis",
            "upload_id": upload_id,
            "filename": filename,
            **stats,
        }

    # ------------------------------------------------------------------ #
    # CSV analysis helpers                                                  #
    # ------------------------------------------------------------------ #

    def _analyse_csv(self, raw: str) -> dict[str, Any]:
        reader = csv.DictReader(io.StringIO(raw))
        columns = reader.fieldnames or []
        rows: list[dict[str, str]] = list(reader)
        row_count = len(rows)

        if not columns or row_count == 0:
            return {"columns": columns, "row_count": row_count, "column_stats": {}}

        col_stats: dict[str, Any] = {}
        for col in columns:
            values = [r.get(col, "") for r in rows]
            non_empty = [v for v in values if v.strip() != ""]
            numeric_vals = self._to_numeric(non_empty)

            stat: dict[str, Any] = {
                "total": row_count,
                "non_empty": len(non_empty),
                "missing": row_count - len(non_empty),
                "unique": len(set(non_empty)),
            }

            if numeric_vals:
                stat.update(
                    {
                        "numeric": True,
                        "min": min(numeric_vals),
                        "max": max(numeric_vals),
                        "mean": statistics.mean(numeric_vals),
                        "median": statistics.median(numeric_vals),
                        "stdev": statistics.stdev(numeric_vals) if len(numeric_vals) > 1 else 0.0,
                    }
                )
            else:
                # Categorical: top-5 values by frequency
                freq: dict[str, int] = {}
                for v in non_empty:
                    freq[v] = freq.get(v, 0) + 1
                top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
                stat.update(
                    {
                        "numeric": False,
                        "top_values": [{"value": v, "count": c} for v, c in top5],
                    }
                )

            col_stats[col] = stat

        # Sample rows (up to 5) so the caller can render a preview.
        sample = rows[:5]

        return {
            "columns": list(columns),
            "row_count": row_count,
            "column_stats": col_stats,
            "sample_rows": sample,
        }

    @staticmethod
    def _to_numeric(values: list[str]) -> list[float]:
        result: list[float] = []
        for v in values:
            try:
                result.append(float(v.replace(",", "").strip()))
            except ValueError:
                return []  # Not a numeric column
        return result
