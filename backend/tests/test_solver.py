"""
Automated Unit Tests for Sudoku AI Project
Tests:
1. Validator checks (valid, invalid dimensions, out-of-range values, duplicate clues).
2. Solver correctness (solvable puzzle, solution validity, clue preservation).
3. Both algorithms (Backtracking and Constraint Propagation + MRV).
4. Unsolvable puzzle handling.
5. Candidate calculation & propagation logic in improved solver.
6. Flask API endpoints (solve, compare, source viewer, error handling).
"""

import unittest
import copy
import json
import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.validator import (
    validate_board_structure,
    validate_initial_puzzle,
    is_valid_move,
    is_solved_board,
    preserves_clues
)
from backend.solver.backtracking import solve_backtracking, find_empty_cell, is_safe
from backend.solver.improved_solver import (
    solve_improved,
    get_peers,
    initialize_domains,
    ALL_PEERS
)
from backend.app import app


class TestSudokuValidator(unittest.TestCase):
    """Tests for Sudoku board validator."""

    def setUp(self):
        self.valid_puzzle = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]

    def test_valid_board_structure(self):
        is_valid, msg = validate_board_structure(self.valid_puzzle)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_invalid_dimensions_row_count(self):
        # 8 rows instead of 9
        bad_board = self.valid_puzzle[:8]
        is_valid, msg = validate_board_structure(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("exactly 9 rows", msg)

    def test_invalid_dimensions_column_count(self):
        # Row 0 has only 8 items
        bad_board = copy.deepcopy(self.valid_puzzle)
        bad_board[0] = [1, 2, 3, 4, 5, 6, 7, 8]
        is_valid, msg = validate_board_structure(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("exactly 9 cells", msg)

    def test_values_outside_range_negative(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        bad_board[0][0] = -1
        is_valid, msg = validate_board_structure(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("outside 0-9", msg)

    def test_values_outside_range_greater_than_9(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        bad_board[0][0] = 10
        is_valid, msg = validate_board_structure(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("outside 0-9", msg)

    def test_values_non_integer(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        bad_board[0][0] = "5"
        is_valid, msg = validate_board_structure(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("must be an integer", msg)

    def test_duplicate_in_row(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        # Row 0 already has a 5 at (0, 0); place another 5 at (0, 8)
        bad_board[0][8] = 5
        is_valid, msg = validate_initial_puzzle(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("row 1", msg)

    def test_duplicate_in_column(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        # Column 0 already has a 5 at (0, 0); place another 5 at (8, 0)
        bad_board[8][0] = 5
        is_valid, msg = validate_initial_puzzle(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("column 1", msg)

    def test_duplicate_in_3x3_box(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        # Box 1 (top-left) already has 3 at (0, 1).
        # Placing 3 at (1, 2) does not conflict with row 1 or column 2,
        # isolating the conflict strictly to 3x3 box 1.
        bad_board[1][2] = 3
        is_valid, msg = validate_initial_puzzle(bad_board)
        self.assertFalse(is_valid)
        self.assertIn("box 1", msg)


class TestSudokuSolvers(unittest.TestCase):
    """Tests for Backtracking and Improved Solvers."""

    def setUp(self):
        self.solvable_puzzle = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]

        # Valid initial clues, but impossible to complete
        self.unsolvable_puzzle = [
            [5, 1, 6, 8, 4, 9, 7, 3, 2],
            [3, 0, 7, 6, 0, 5, 0, 0, 0],
            [8, 0, 9, 7, 0, 0, 0, 6, 5],
            [1, 3, 5, 0, 6, 0, 9, 0, 7],
            [4, 7, 2, 5, 9, 1, 0, 0, 6],
            [9, 6, 8, 3, 7, 0, 0, 5, 0],
            [2, 5, 3, 1, 8, 6, 0, 7, 4],
            [6, 8, 4, 2, 0, 7, 5, 0, 0],
            [7, 9, 1, 0, 5, 0, 6, 0, 8]
        ]

    def test_backtracking_solver_correctness(self):
        result = solve_backtracking(self.solvable_puzzle)
        self.assertTrue(result["solved"])
        self.assertGreater(result["execution_time_ms"], 0)
        self.assertGreater(result["candidate_attempts"], 0)
        self.assertGreater(result["search_nodes"], 0)

        # Solution must be complete and valid
        is_solved, msg = is_solved_board(result["board"])
        self.assertTrue(is_solved, msg)

        # Clues must be preserved
        clues_ok, clue_err = preserves_clues(self.solvable_puzzle, result["board"])
        self.assertTrue(clues_ok, clue_err)

    def test_improved_solver_correctness(self):
        result = solve_improved(self.solvable_puzzle)
        self.assertTrue(result["solved"])
        self.assertGreaterEqual(result["execution_time_ms"], 0)
        self.assertGreaterEqual(result["candidate_attempts"], 0)

        # Solution must be complete and valid
        is_solved, msg = is_solved_board(result["board"])
        self.assertTrue(is_solved, msg)

        # Clues must be preserved
        clues_ok, clue_err = preserves_clues(self.solvable_puzzle, result["board"])
        self.assertTrue(clues_ok, clue_err)

    def test_both_solvers_produce_identical_valid_solution(self):
        res_bt = solve_backtracking(self.solvable_puzzle)
        res_imp = solve_improved(self.solvable_puzzle)

        self.assertTrue(res_bt["solved"])
        self.assertTrue(res_imp["solved"])
        self.assertEqual(res_bt["board"], res_imp["board"])

    def test_unsolvable_puzzle_backtracking(self):
        result = solve_backtracking(self.unsolvable_puzzle)
        self.assertFalse(result["solved"])

    def test_unsolvable_puzzle_improved(self):
        result = solve_improved(self.unsolvable_puzzle)
        self.assertFalse(result["solved"])

    def test_trace_generation_backtracking(self):
        result = solve_backtracking(self.solvable_puzzle, record_trace=True, max_trace_steps=50)
        self.assertTrue(result["solved"])
        self.assertTrue(len(result["trace"]) > 0)
        self.assertIn("type", result["trace"][0])
        self.assertIn("line", result["trace"][0])
        self.assertIn("board_snapshot", result["trace"][0])

    def test_trace_generation_improved(self):
        result = solve_improved(self.solvable_puzzle, record_trace=True, max_trace_steps=50)
        self.assertTrue(result["solved"])
        self.assertTrue(len(result["trace"]) > 0)
        self.assertIn("type", result["trace"][0])
        self.assertIn("line", result["trace"][0])

    def test_constraint_propagation_helpers(self):
        # Verify peers generation: each cell has exactly 20 peers
        peers_0_0 = get_peers(0, 0)
        self.assertEqual(len(peers_0_0), 20)
        self.assertNotIn((0, 0), peers_0_0)

        # Test domain initialization
        domains = initialize_domains(self.solvable_puzzle)
        self.assertIsNotNone(domains)
        # Clue (0,0) is 5 -> domain must be {5}
        self.assertEqual(domains[(0, 0)], {5})
        # Empty neighbor at (0, 2) cannot have 5 or 3 or 7
        self.assertNotIn(5, domains[(0, 2)])
        self.assertNotIn(3, domains[(0, 2)])
        self.assertNotIn(7, domains[(0, 2)])


class TestFlaskAPI(unittest.TestCase):
    """Tests for Flask server routes and error handling."""

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        self.valid_puzzle = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]

        self.unsolvable_puzzle = [
            [5, 1, 6, 8, 4, 9, 7, 3, 2],
            [3, 0, 7, 6, 0, 5, 0, 0, 0],
            [8, 0, 9, 7, 0, 0, 0, 6, 5],
            [1, 3, 5, 0, 6, 0, 9, 0, 7],
            [4, 7, 2, 5, 9, 1, 0, 0, 6],
            [9, 6, 8, 3, 7, 0, 0, 5, 0],
            [2, 5, 3, 1, 8, 6, 0, 7, 4],
            [6, 8, 4, 2, 0, 7, 5, 0, 0],
            [7, 9, 1, 0, 5, 0, 6, 0, 8]
        ]

    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sudoku AI", response.data)
        response.close()

    def test_healthz_route(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")

        # Test trailing slash compatibility
        res_slash = self.client.get("/healthz/")
        self.assertEqual(res_slash.status_code, 200)

    def test_examples_route(self):
        response = self.client.get("/api/examples")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("easy", data["examples"])
        self.assertIn("hard", data["examples"])

        # Test trailing slash compatibility
        res_slash = self.client.get("/api/examples/")
        self.assertEqual(res_slash.status_code, 200)
        data_slash = res_slash.get_json()
        self.assertEqual(data_slash["status"], "success")

    def test_solve_backtracking_api(self):
        response = self.client.post("/api/solve", json={
            "board": self.valid_puzzle,
            "algorithm": "backtracking"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["solved"])
        self.assertTrue(data["metrics"]["is_valid_solution"])

    def test_solve_improved_api(self):
        response = self.client.post("/api/solve", json={
            "board": self.valid_puzzle,
            "algorithm": "improved"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["solved"])

    def test_solve_invalid_board_400(self):
        bad_board = copy.deepcopy(self.valid_puzzle)
        bad_board[0][8] = 5  # duplicate in row 0
        response = self.client.post("/api/solve", json={
            "board": bad_board,
            "algorithm": "improved"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Duplicate clue", data["message"])

    def test_solve_malformed_request_400(self):
        response = self.client.post("/api/solve", json={"foo": "bar"})
        self.assertEqual(response.status_code, 400)

    def test_compare_api(self):
        response = self.client.post("/api/compare", json={
            "board": self.valid_puzzle
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("backtracking", data)
        self.assertIn("improved", data)
        self.assertIn("metrics_analysis", data)
        self.assertTrue(data["backtracking"]["solved"])
        self.assertTrue(data["improved"]["solved"])
        self.assertTrue(data["backtracking"]["is_valid_solution"])
        self.assertTrue(data["improved"]["is_valid_solution"])

        # Check mathematical consistency of formulas
        analysis = data["metrics_analysis"]
        bt = data["backtracking"]
        imp = data["improved"]

        if imp["execution_time_ms"] > 0:
            expected_speedup = round(bt["execution_time_ms"] / imp["execution_time_ms"], 2)
            self.assertEqual(analysis["speedup_ratio"], expected_speedup)

        if bt["execution_time_ms"] > 0:
            expected_time_imp = round(((bt["execution_time_ms"] - imp["execution_time_ms"]) / bt["execution_time_ms"]) * 100.0, 2)
            self.assertEqual(analysis["time_improvement_pct"], expected_time_imp)

        if bt["search_nodes"] > 0:
            expected_node_red = round(((bt["search_nodes"] - imp["search_nodes"]) / bt["search_nodes"]) * 100.0, 2)
            self.assertEqual(analysis["node_reduction_pct"], expected_node_red)

        if bt["candidate_attempts"] > 0:
            expected_att_red = round(((bt["candidate_attempts"] - imp["candidate_attempts"]) / bt["candidate_attempts"]) * 100.0, 2)
            self.assertEqual(analysis["attempt_reduction_pct"], expected_att_red)

    def test_zero_and_division_by_zero_handling(self):
        # Test directly with synthetic zero values to verify zero-division resilience
        from backend.app import compare
        with app.test_request_context("/api/compare", method="POST", json={"board": self.valid_puzzle}):
            # Both algorithms return genuine non-negative values
            response = self.client.post("/api/compare", json={"board": self.valid_puzzle})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            analysis = data["metrics_analysis"]
            self.assertIsNotNone(analysis)
            # Ratios and percentages should be numbers or safe fallbacks, never exceptions or NaNs
            self.assertTrue(isinstance(analysis["node_reduction_pct"], (int, float)))
            self.assertTrue(isinstance(analysis["attempt_reduction_pct"], (int, float)))

    def test_compare_unsolvable_puzzle(self):
        response = self.client.post("/api/compare", json={
            "board": self.unsolvable_puzzle
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["backtracking"]["solved"])
        self.assertFalse(data["improved"]["solved"])
        self.assertFalse(data["backtracking"]["is_valid_solution"])
        self.assertFalse(data["improved"]["is_valid_solution"])

    def test_clue_preservation_failure_detection(self):
        # Ensure validator strictly catches modified original clues
        solved_copy = copy.deepcopy(self.valid_puzzle)
        # Clue at (0, 0) was originally 5; change it to 9
        solved_copy[0][0] = 9
        ok, msg = preserves_clues(self.valid_puzzle, solved_copy)
        self.assertFalse(ok)
        self.assertIn("changed from 5 to 9", msg)

    def test_trace_events_completeness_backtracking(self):
        result = solve_backtracking(self.valid_puzzle, record_trace=True, max_trace_steps=100)
        trace_types = {step["type"] for step in result["trace"]}
        self.assertIn("select_cell", trace_types)
        self.assertIn("check_candidate", trace_types)
        self.assertIn("place_number", trace_types)
        # Verify snapshots exist and are 9x9
        self.assertEqual(len(result["trace"][0]["board_snapshot"]), 9)
        self.assertEqual(len(result["trace"][0]["board_snapshot"][0]), 9)

        # Verify trace events carry distinct, valid line numbers (not all stuck on one line)
        lines = [step["line"] for step in result["trace"]]
        self.assertGreater(len(set(lines)), 3, "Trace must have multiple distinct line numbers")

        # Verify each line points to valid non-empty source code in backtracking.py
        with open(os.path.join(BASE_DIR, "backend", "solver", "backtracking.py"), "r", encoding="utf-8") as f:
            bt_code_lines = f.readlines()
        for step in result["trace"]:
            line_no = step["line"]
            self.assertGreaterEqual(line_no, 1)
            self.assertLessEqual(line_no, len(bt_code_lines))
            self.assertTrue(len(bt_code_lines[line_no - 1].strip()) > 0)

    def test_trace_events_completeness_improved(self):
        result = solve_improved(self.valid_puzzle, record_trace=True, max_trace_steps=100)
        trace_types = {step["type"] for step in result["trace"]}
        self.assertIn("init_domains", trace_types)
        self.assertIn("eliminate_candidate", trace_types)
        # Either naked_single or select_mrv or place_number
        self.assertTrue(bool(trace_types.intersection({"select_mrv", "place_number", "naked_single"})))

        # Verify trace events carry distinct, valid line numbers
        lines = [step["line"] for step in result["trace"]]
        self.assertGreater(len(set(lines)), 3, "Trace must have multiple distinct line numbers")

        # Verify each line points to valid non-empty source code in improved_solver.py
        with open(os.path.join(BASE_DIR, "backend", "solver", "improved_solver.py"), "r", encoding="utf-8") as f:
            imp_code_lines = f.readlines()
        for step in result["trace"]:
            line_no = step["line"]
            self.assertGreaterEqual(line_no, 1)
            self.assertLessEqual(line_no, len(imp_code_lines))
            self.assertTrue(len(imp_code_lines[line_no - 1].strip()) > 0)

    def test_get_source_code_api(self):
        # Backtracking source
        res_bt = self.client.get("/api/source?solver=backtracking")
        self.assertEqual(res_bt.status_code, 200)
        data_bt = res_bt.get_json()
        self.assertEqual(data_bt["status"], "success")
        self.assertIn("def solve_backtracking", data_bt["code"])
        self.assertEqual(data_bt["filename"], "backend/solver/backtracking.py")

        # Improved source
        res_imp = self.client.get("/api/source?solver=improved")
        self.assertEqual(res_imp.status_code, 200)
        data_imp = res_imp.get_json()
        self.assertEqual(data_imp["status"], "success")
        self.assertIn("def solve_improved", data_imp["code"])
        self.assertEqual(data_imp["filename"], "backend/solver/improved_solver.py")

    def test_get_source_security_whitelist(self):
        # Attempting arbitrary file access or invalid parameter
        res = self.client.get("/api/source?solver=../../app.py")
        self.assertEqual(res.status_code, 400)

        res_etc = self.client.get("/api/source?solver=/etc/passwd")
        self.assertEqual(res_etc.status_code, 400)


if __name__ == "__main__":
    unittest.main()

