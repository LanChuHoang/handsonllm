# evaluator.py

import sqlite3
from typing import List, Tuple, Dict, Any
import pandas as pd


class EvaluationResult:
    """
    Holds the detailed results of the SQL evaluation.
    """

    def __init__(self, details: List[Dict[str, Any]]):
        self.details = details
        self.details_df = pd.DataFrame(self.details)
        self.summary_data = self.to_summary_data()

    def to_summary_data(self) -> Dict[str, Any]:
        summary_data = {
            "total": len(self.details),
            "correct": self.details_df["is_match"].sum(),
            "execution_accuracy": round(
                (self.details_df["is_match"].sum() / len(self.details)) * 100, 2
            ),
        }
        return summary_data


def _load_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def _fetch_results(db_path: str, query: str) -> List[Tuple]:
    """
    Execute the given SQL query against the SQLite database at db_path,
    fetch all rows, sort them, and return as a list of tuples.
    """
    conn = sqlite3.connect(db_path)
    conn.text_factory = lambda b: b.decode("utf-8", errors="ignore")

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    finally:
        conn.close()
    # normalize every value to a str, treating None or '' both as ''
    normalized: List[Tuple[str, ...]] = []
    for row in rows:
        new_row = []
        for v in row:
            if v is None or v == "":
                new_row.append("")
            else:
                new_row.append(str(v))
        normalized.append(tuple(new_row))

    return sorted(normalized)


def evaluate_sql(
    solution_file: str, answer_file: str, db_root: str
) -> EvaluationResult:
    """
    Compare the "correct" SQLs in solution_file against the user-provided
    SQLs in answer_file by executing each pair on its respective SQLite DB.

    Parameters
    ----------
    solution_file : str
        Path to the file where each line is "<sql>\\t<db_id>".
    answer_file : str
        Path to the file where each line is the user-generated SQL answer.
    db_root : str
        Path to the folder containing "<db_id>.sqlite" databases.

    Returns
    -------
    EvaluationResult
        An object containing total count, correct count, per-db match flags,
        and an overall accuracy percentage.
    """
    sols = _load_lines(solution_file)
    ans = _load_lines(answer_file)

    if len(sols) != len(ans):
        raise ValueError(
            f"Line count mismatch: {len(sols)} solutions vs {len(ans)} answers."
        )

    result = []

    for sol_line, ans_sql in zip(sols, ans):
        try:
            sql, db_id = sol_line.split("\t")
        except Exception as e:
            raise ValueError(f"Invalid solution file: {sol_line}") from e

        db_path = f"{db_root.rstrip('/')}/{db_id}/{db_id}.sqlite"
        try:
            sol_rows = _fetch_results(db_path, sql)
        except Exception as e:
            raise ValueError(f"Invalid solution file: {sol_line}") from e

        try:
            ans_rows = _fetch_results(db_path, ans_sql)
        except Exception as e:
            # Query execution error (e.g., syntax error, missing DB)
            error = repr(e)
            is_match = False
        else:
            error = None
            try:
                assert sol_rows == ans_rows
            except Exception:
                error = f"Not match: {sol_rows} != {ans_rows}"
                is_match = False
            else:
                error = None
                is_match = True

        result.append(
            {
                "db_path": db_path,
                "solution": sql,
                "answer": ans_sql,
                "error": error,
                "is_match": is_match,
            }
        )

    return EvaluationResult(details=result)
