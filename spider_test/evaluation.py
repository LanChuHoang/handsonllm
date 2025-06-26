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
        easy_count = len(self.details_df.query("hardness == 'easy'"))
        medium_count = len(self.details_df.query("hardness == 'medium'"))
        hard_count = len(self.details_df.query("hardness == 'hard'"))
        extra_count = len(self.details_df.query("hardness == 'extra'"))
        total = len(self.details)
        assert easy_count + medium_count + hard_count + extra_count == total

        easy_correct = len(self.details_df.query("hardness == 'easy' & is_match"))
        medium_correct = len(self.details_df.query("hardness == 'medium' & is_match"))
        hard_correct = len(self.details_df.query("hardness == 'hard' & is_match"))
        extra_correct = len(self.details_df.query("hardness == 'extra' & is_match"))
        total_correct = len(self.details_df.query("is_match"))
        assert (
            total_correct
            == easy_correct + medium_correct + hard_correct + extra_correct
        )

        easy_execution_accuracy = round((easy_correct / easy_count) * 100, 2)
        medium_execution_accuracy = round((medium_correct / medium_count) * 100, 2)
        hard_execution_accuracy = round((hard_correct / hard_count) * 100, 2)
        extra_execution_accuracy = round((extra_correct / extra_count) * 100, 2)
        total_execution_accuracy = round((total_correct / total) * 100, 2)

        summary_data = {
            "easy": f"{easy_correct}/{easy_count} ({easy_execution_accuracy}%)",
            "medium": f"{medium_correct}/{medium_count} ({medium_execution_accuracy}%)",
            "hard": f"{hard_correct}/{hard_count} ({hard_execution_accuracy}%)",
            "extra": f"{extra_correct}/{extra_count} ({extra_execution_accuracy}%)",
            "total": f"{total_correct}/{total} ({total_execution_accuracy}%)",
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


def _normalize_rows(rows: List[Tuple]) -> List[Tuple[str, ...]]:
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


def _is_match(sol_rows: List[Tuple], ans_rows: List[Tuple]) -> bool:
    if len(sol_rows) != len(ans_rows):
        return False
    norm_sol_rows = _normalize_rows(sol_rows)
    norm_ans_rows = _normalize_rows(ans_rows)
    return norm_sol_rows == norm_ans_rows


def evaluate_sql(
    input_file: str, solution_file: str, answer_file: str, db_root: str
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
    inputs = pd.read_csv(input_file).to_dict(orient="records")
    sols = _load_lines(solution_file)
    ans = _load_lines(answer_file)

    if len(sols) != len(ans):
        raise ValueError(
            f"Line count mismatch: {len(sols)} solutions vs {len(ans)} answers."
        )

    result = []

    for question_number, (sol_line, ans_sql, input_data) in enumerate(
        zip(sols, ans, inputs)
    ):
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
            is_match = _is_match(sol_rows, ans_rows)
            error = f"Not match: {sol_rows} != {ans_rows}" if not is_match else None

        result.append(
            {
                "question_number": question_number,
                "question": input_data["question"],
                "hardness": input_data["hardness"],
                "db_path": db_path,
                "solution": sql,
                "answer": ans_sql,
                "error": error,
                "is_match": is_match,
            }
        )

    return EvaluationResult(details=result)
