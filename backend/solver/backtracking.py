"""
Algorithm A: Basic Backtracking Sudoku Solver

How Backtracking Works (in simple English):
1. Scan the 9x9 board from top-left to bottom-right to find the first empty cell (value 0).
2. If no empty cell is found, the puzzle is solved!
3. If an empty cell is found at (row, col), test numbers 1 through 9 one by one.
4. For each number:
   a. Check if it obeys Sudoku rules (no duplicate in the row, column, or 3x3 box).
   b. If legal, place that number into the cell.
   c. Recursively attempt to solve the rest of the board.
   d. If the recursive call succeeds, we are done!
   e. If the recursive call hits a dead end (no valid numbers can fill a later cell),
      undo the choice (reset cell back to 0) and try the next candidate.
5. If numbers 1-9 are all exhausted without success, return False (triggering a backtrack).
"""

import time
import copy
from typing import List, Tuple, Optional, Dict, Any


def find_empty_cell(board: List[List[int]]) -> Optional[Tuple[int, int]]:
    """
    Finds the first empty cell (containing 0) scanning row by row.
    Returns (row, col) or None if the board is completely filled.
    """
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return (r, c)
    return None


def is_safe(board: List[List[int]], row: int, col: int, num: int) -> bool:
    """
    Checks if placing `num` at (row, col) violates row, column, or 3x3 box rules.
    """
    # 1. Row check
    for c in range(9):
        if board[row][c] == num:
            return False

    # 2. Column check
    for r in range(9):
        if board[r][col] == num:
            return False

    # 3. 3x3 Box check
    box_start_row = (row // 3) * 3
    box_start_col = (col // 3) * 3
    for r in range(box_start_row, box_start_row + 3):
        for c in range(box_start_col, box_start_col + 3):
            if board[r][c] == num:
                return False

    return True


def solve_backtracking(
    board: List[List[int]],
    record_trace: bool = False,
    max_trace_steps: int = 600
) -> Dict[str, Any]:
    """
    Solves a Sudoku board using standard depth-first Backtracking search.

    Args:
        board: 9x9 list of lists representing the Sudoku puzzle (0 = empty).
        record_trace: If True, records solver steps for visualization.
        max_trace_steps: Maximum number of trace events to record.

    Returns:
        Dictionary with:
            - solved: bool
            - board: solved 9x9 board (or original if unsolvable)
            - execution_time_ms: time taken in milliseconds
            - candidate_attempts: number of candidate placements tested
            - search_nodes: number of recursive calls (decision points)
            - trace: list of event objects (if record_trace=True)
            - trace_capped: whether trace reached max_trace_steps
    """
    # Create a deep copy to never mutate the caller's input board
    working_board = copy.deepcopy(board)

    # Counters for metrics
    stats = {
        "candidate_attempts": 0,
        "search_nodes": 0,
        "trace_capped": False
    }
    trace_events: List[Dict[str, Any]] = []

    def record_event(event_type: str, row: int, col: int, num: int, message: str, line_number: int):
        if not record_trace:
            return
        if len(trace_events) >= max_trace_steps:
            stats["trace_capped"] = True
            return
        trace_events.append({
            "type": event_type,
            "row": row,
            "col": col,
            "val": num,
            "message": message,
            "line": line_number,
            "board_snapshot": copy.deepcopy(working_board)
        })

    def backtrack_recursive() -> bool:
        stats["search_nodes"] += 1

        # Step 1: Find next empty cell
        empty_pos = find_empty_cell(working_board)
        if empty_pos is None:
            # All cells are filled legally -> Puzzle Solved!
            record_event("solved", -1, -1, 0, "All cells filled successfully!", 118)
            return True

        row, col = empty_pos
        record_event(
            "select_cell", row, col, 0,
            f"Selected first empty cell scanning row-by-row at ({row + 1}, {col + 1})",
            120
        )

        # Step 2: Try numbers 1 through 9
        for num in range(1, 10):
            stats["candidate_attempts"] += 1
            safe = is_safe(working_board, row, col, num)

            record_event(
                "check_candidate", row, col, num,
                f"Testing candidate {num} at ({row + 1}, {col + 1}): {'Valid' if safe else 'Constraint Conflict'}",
                130
            )

            if safe:
                # Step 3: Place candidate
                working_board[row][col] = num
                record_event(
                    "place_number", row, col, num,
                    f"Placed valid candidate {num} at ({row + 1}, {col + 1})",
                    140
                )

                # Step 4: Recurse
                if backtrack_recursive():
                    return True

                # Step 5: Undo choice on dead end (Backtrack)
                working_board[row][col] = 0
                record_event(
                    "backtrack", row, col, 0,
                    f"Dead end reached in subtree. Backtracking: reset ({row + 1}, {col + 1}) to 0",
                    152
                )
            else:
                record_event(
                    "failed_choice", row, col, num,
                    f"Candidate {num} rejected: violates row, column, or box constraint",
                    130
                )

        return False

    # Measure real execution time using high-resolution perf_counter
    start_time = time.perf_counter()
    is_solved = backtrack_recursive()
    end_time = time.perf_counter()

    execution_time_ms = round((end_time - start_time) * 1000.0, 3)

    return {
        "solved": is_solved,
        "board": working_board if is_solved else copy.deepcopy(board),
        "execution_time_ms": execution_time_ms,
        "candidate_attempts": stats["candidate_attempts"],
        "search_nodes": stats["search_nodes"],
        "trace": trace_events,
        "trace_capped": stats["trace_capped"]
    }
