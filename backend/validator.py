"""
Sudoku Board Validator
Provides validation functions for Sudoku boards:
1. Shape and range validation (9x9 grid, integers 0-9).
2. Initial puzzle consistency (no duplicate clues in any row, column, or 3x3 box).
3. Move validity check (is a number legal at row, col).
4. Completed puzzle verification (full 9x9 grid, no blanks, strictly valid).
5. Clue preservation check (ensure solver did not alter initial numbers).
"""

from typing import List, Tuple, Optional


def validate_board_structure(board) -> Tuple[bool, str]:
    """
    Checks that the board is a 9x9 grid containing integers between 0 and 9.
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(board, list) or len(board) != 9:
        return False, "Board must be a list of exactly 9 rows."

    for r_idx, row in enumerate(board):
        if not isinstance(row, list) or len(row) != 9:
            return False, f"Row {r_idx + 1} must contain exactly 9 cells."
        for c_idx, val in enumerate(row):
            # Check integer type (boolean is a subclass of int in Python, so exclude bool)
            if isinstance(val, bool) or not isinstance(val, int):
                return False, f"Cell at row {r_idx + 1}, column {c_idx + 1} must be an integer (0-9)."
            if val < 0 or val > 9:
                return False, f"Cell at row {r_idx + 1}, column {c_idx + 1} has value {val}, which is outside 0-9."

    return True, ""


def validate_initial_puzzle(board: List[List[int]]) -> Tuple[bool, str]:
    """
    Validates structure and ensures there are no duplicate clues in any row,
    column, or 3x3 subgrid.
    Returns:
        (is_valid, error_message)
    """
    valid_struct, err = validate_board_structure(board)
    if not valid_struct:
        return False, err

    # Check rows for duplicates
    for r in range(9):
        seen = set()
        for c in range(9):
            val = board[r][c]
            if val != 0:
                if val in seen:
                    return False, f"Duplicate clue '{val}' found in row {r + 1}."
                seen.add(val)

    # Check columns for duplicates
    for c in range(9):
        seen = set()
        for r in range(9):
            val = board[r][c]
            if val != 0:
                if val in seen:
                    return False, f"Duplicate clue '{val}' found in column {c + 1}."
                seen.add(val)

    # Check 3x3 boxes for duplicates
    for box_row in range(0, 9, 3):
        for box_col in range(0, 9, 3):
            seen = set()
            for r in range(box_row, box_row + 3):
                for c in range(box_col, box_col + 3):
                    val = board[r][c]
                    if val != 0:
                        if val in seen:
                            box_num = (box_row // 3) * 3 + (box_col // 3) + 1
                            return False, f"Duplicate clue '{val}' found in 3x3 box {box_num}."
                        seen.add(val)

    return True, ""


def is_valid_move(board: List[List[int]], row: int, col: int, num: int) -> bool:
    """
    Checks if placing `num` at `(row, col)` is legally allowed by Sudoku rules.
    Assumes `num` is between 1 and 9.
    """
    # Check row constraint
    for c in range(9):
        if c != col and board[row][c] == num:
            return False

    # Check column constraint
    for r in range(9):
        if r != row and board[r][col] == num:
            return False

    # Check 3x3 box constraint
    start_row = (row // 3) * 3
    start_col = (col // 3) * 3
    for r in range(start_row, start_row + 3):
        for c in range(start_col, start_col + 3):
            if (r != row or c != col) and board[r][c] == num:
                return False

    return True


def is_solved_board(board: List[List[int]]) -> Tuple[bool, str]:
    """
    Validates that a board is completely and correctly solved:
    - 9x9 structure with integers 1-9 (no zeros).
    - Every row contains numbers 1 through 9.
    - Every column contains numbers 1 through 9.
    - Every 3x3 box contains numbers 1 through 9.
    """
    valid_struct, err = validate_board_structure(board)
    if not valid_struct:
        return False, err

    # Check for empty cells
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return False, f"Board is incomplete: empty cell at row {r + 1}, column {c + 1}."

    # Validate rows, columns, and 3x3 boxes
    expected_set = set(range(1, 10))

    for r in range(9):
        if set(board[r]) != expected_set:
            return False, f"Row {r + 1} does not contain all numbers from 1 to 9."

    for c in range(9):
        col_vals = {board[r][c] for r in range(9)}
        if col_vals != expected_set:
            return False, f"Column {c + 1} does not contain all numbers from 1 to 9."

    for box_row in range(0, 9, 3):
        for box_col in range(0, 9, 3):
            box_vals = {
                board[r][c]
                for r in range(box_row, box_row + 3)
                for c in range(box_col, box_col + 3)
            }
            if box_vals != expected_set:
                box_num = (box_row // 3) * 3 + (box_col // 3) + 1
                return False, f"Box {box_num} does not contain all numbers from 1 to 9."

    return True, "Solution is valid and complete."


def preserves_clues(initial_board: List[List[int]], solved_board: List[List[int]]) -> Tuple[bool, str]:
    """
    Checks if all non-zero clues from the initial board are preserved
    with the exact same values in the solved board.
    """
    for r in range(9):
        for c in range(9):
            init_val = initial_board[r][c]
            if init_val != 0:
                if solved_board[r][c] != init_val:
                    return False, f"Initial clue at ({r + 1}, {c + 1}) changed from {init_val} to {solved_board[r][c]}."
    return True, ""
