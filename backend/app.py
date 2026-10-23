"""
Flask Application Backend for Sudoku AI Mini-Capstone
Serves frontend assets, exposes solver APIs, comparison benchmarks,
and securely serves solver source code for the in-browser code viewer.
"""

import os
import sys
import copy

# Ensure project root directory is in sys.path so 'backend' package imports work cleanly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import Dict, Any

from backend.validator import (
    validate_board_structure,
    validate_initial_puzzle,
    is_solved_board,
    preserves_clues
)
from backend.solver.backtracking import solve_backtracking
from backend.solver.improved_solver import solve_improved

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
SOLVER_DIR = os.path.join(BASE_DIR, "backend", "solver")

app = Flask(__name__, static_folder=FRONTEND_DIR)

# Configure CORS to allow deployed Vercel frontend or local development origins
# Set ALLOWED_ORIGINS (or FRONTEND_URL) in production (e.g. "https://my-app.vercel.app")
raw_allowed_origins = os.environ.get("ALLOWED_ORIGINS") or os.environ.get("FRONTEND_URL") or ""
if raw_allowed_origins.strip():
    allowed_origins = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]
else:
    # Default safe origins for local development (Flask server and local frontend servers)
    allowed_origins = [
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ]

CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# Curated example puzzles for testing and user exploration
SAMPLE_PUZZLES = {
    "easy": {
        "name": "Easy Puzzle",
        "description": "Standard easy puzzle with many given clues. Solved in single-digit milliseconds.",
        "board": [
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
    },
    "medium": {
        "name": "Medium Puzzle",
        "description": "Moderate clue density requiring deeper search tree exploration.",
        "board": [
            [0, 0, 0, 2, 6, 0, 7, 0, 1],
            [6, 8, 0, 0, 7, 0, 0, 9, 0],
            [1, 9, 0, 0, 0, 4, 5, 0, 0],
            [8, 2, 0, 1, 0, 0, 0, 4, 0],
            [0, 0, 4, 6, 0, 2, 9, 0, 0],
            [0, 5, 0, 0, 0, 3, 0, 2, 8],
            [0, 0, 9, 3, 0, 0, 0, 7, 4],
            [0, 4, 0, 0, 5, 0, 0, 3, 6],
            [7, 0, 3, 0, 1, 8, 0, 0, 0]
        ]
    },
    "hard": {
        "name": "Hard Puzzle",
        "description": "Challenging puzzle where MRV and forward-checking exhibit clear speed advantages.",
        "board": [
            [0, 2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 6, 0, 0, 0, 0, 3],
            [0, 7, 4, 0, 8, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 0, 0, 2],
            [0, 8, 0, 0, 4, 0, 0, 1, 0],
            [6, 0, 0, 5, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 7, 8, 0],
            [5, 0, 0, 0, 0, 9, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 4, 0]
        ]
    },
    "expert": {
        "name": "Expert (Arto Inkala's AI Escargot style)",
        "description": "Minimal clues designed to force extensive backtracking for naive solvers.",
        "board": [
            [8, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 3, 6, 0, 0, 0, 0, 0],
            [0, 7, 0, 0, 9, 0, 2, 0, 0],
            [0, 5, 0, 0, 0, 7, 0, 0, 0],
            [0, 0, 0, 0, 4, 5, 7, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 3, 0],
            [0, 0, 1, 0, 0, 0, 0, 6, 8],
            [0, 0, 8, 5, 0, 0, 0, 1, 0],
            [0, 9, 0, 0, 0, 0, 4, 0, 0]
        ]
    },
    "unsolvable": {
        "name": "Valid but Unsolvable",
        "description": "Initial clues violate no rules, but mathematically cannot be completed to a valid Sudoku.",
        "board": [
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
    },
    "invalid_clues": {
        "name": "Invalid Puzzle (Duplicate Clues)",
        "description": "Has duplicate clues (two 5s in row 1) to test input validator error handling.",
        "board": [
            [5, 3, 0, 0, 7, 0, 0, 0, 5],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]
    }
}


# ==========================================
# Frontend Serving Routes
# ==========================================

@app.route("/", methods=["GET"])
def index():
    """Serves the main frontend single-page application."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint for Render and uptime monitoring."""
    return jsonify({"status": "ok"}), 200


# ==========================================
# Solver and API Endpoints
# ==========================================

@app.route("/api/examples", methods=["GET"])
def get_examples():
    """Returns curated example puzzles."""
    return jsonify({
        "status": "success",
        "examples": SAMPLE_PUZZLES
    })


@app.route("/api/source", methods=["GET"])
def get_solver_source():
    """
    Safely retrieves the genuine Python source code of the selected solver.
    Strictly whitelists allowed files to prevent arbitrary file access or path traversal.
    """
    solver_param = request.args.get("solver", "").strip().lower()

    whitelisted_files = {
        "backtracking": "backtracking.py",
        "improved": "improved_solver.py"
    }

    if solver_param not in whitelisted_files:
        return jsonify({
            "status": "error",
            "message": f"Invalid solver requested '{solver_param}'. Allowed values: 'backtracking', 'improved'."
        }), 400

    filename = whitelisted_files[solver_param]
    file_path = os.path.join(SOLVER_DIR, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()

        lines = code_content.splitlines()
        return jsonify({
            "status": "success",
            "solver": solver_param,
            "filename": f"backend/solver/{filename}",
            "code": code_content,
            "total_lines": len(lines)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to read source file: {str(e)}"
        }), 500


@app.route("/api/solve", methods=["POST"])
def solve():
    """
    Solves a Sudoku puzzle using the requested algorithm.
    Validates the initial board, runs the algorithm, verifies the output,
    and returns metrics and optional execution trace.
    """
    data = request.get_json(silent=True)
    if not data or "board" not in data:
        return jsonify({
            "status": "error",
            "message": "Malformed request. JSON body must include 'board' (9x9 grid)."
        }), 400

    board = data["board"]
    algorithm = str(data.get("algorithm", "improved")).strip().lower()
    visualize = bool(data.get("visualize", False))

    # 1. Structural and clue validation
    is_valid, error_msg = validate_initial_puzzle(board)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": f"Invalid puzzle: {error_msg}"
        }), 400

    # 2. Algorithm selection & execution
    if algorithm == "backtracking":
        result = solve_backtracking(board, record_trace=visualize)
        algo_display = "Basic Backtracking"
    elif algorithm == "improved":
        result = solve_improved(board, record_trace=visualize)
        algo_display = "Constraint Propagation + MRV"
    else:
        return jsonify({
            "status": "error",
            "message": f"Unknown algorithm '{algorithm}'. Must be 'backtracking' or 'improved'."
        }), 400

    # 3. Check if solved
    if not result["solved"]:
        return jsonify({
            "status": "unsolvable",
            "solved": False,
            "algorithm": algo_display,
            "message": "The puzzle is valid, but has no possible solution (unsolvable).",
            "metrics": {
                "execution_time_ms": result["execution_time_ms"],
                "candidate_attempts": result["candidate_attempts"],
                "search_nodes": result["search_nodes"],
                "is_valid_solution": False
            },
            "board": board,
            "trace": result.get("trace", []),
            "trace_capped": result.get("trace_capped", False)
        }), 200

    # 4. Verify solution correctness & preservation of clues
    is_correct, sol_err = is_solved_board(result["board"])
    clues_ok, clue_err = preserves_clues(board, result["board"])

    if not is_correct or not clues_ok:
        return jsonify({
            "status": "error",
            "message": f"Solver integrity check failed: {sol_err or clue_err}"
        }), 500

    return jsonify({
        "status": "success",
        "solved": True,
        "algorithm": algo_display,
        "board": result["board"],
        "metrics": {
            "execution_time_ms": result["execution_time_ms"],
            "candidate_attempts": result["candidate_attempts"],
            "search_nodes": result["search_nodes"],
            "is_valid_solution": True
        },
        "trace": result.get("trace", []),
        "trace_capped": result.get("trace_capped", False)
    }), 200


@app.route("/api/compare", methods=["POST"])
def compare():
    """
    Executes BOTH algorithms on the exact same Sudoku puzzle input.
    Provides fair, side-by-side performance metrics.
    """
    data = request.get_json(silent=True)
    if not data or "board" not in data:
        return jsonify({
            "status": "error",
            "message": "Malformed request. JSON body must include 'board' (9x9 grid)."
        }), 400

    board = data["board"]

    # Validate initial puzzle
    is_valid, error_msg = validate_initial_puzzle(board)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": f"Invalid puzzle: {error_msg}"
        }), 400

    # Execute both solvers cleanly with independent deep copies of the puzzle
    res_backtracking = solve_backtracking(copy.deepcopy(board), record_trace=False)
    res_improved = solve_improved(copy.deepcopy(board), record_trace=False)

    # Validate solutions
    bt_valid = res_backtracking["solved"] and is_solved_board(res_backtracking["board"])[0] and preserves_clues(board, res_backtracking["board"])[0]
    imp_valid = res_improved["solved"] and is_solved_board(res_improved["board"])[0] and preserves_clues(board, res_improved["board"])[0]

    # Calculate performance ratios and reduction percentages safely
    bt_time = res_backtracking["execution_time_ms"]
    imp_time = res_improved["execution_time_ms"]
    bt_nodes = res_backtracking["search_nodes"]
    imp_nodes = res_improved["search_nodes"]
    bt_attempts = res_backtracking["candidate_attempts"]
    imp_attempts = res_improved["candidate_attempts"]

    # Speedup ratio: Basic Backtracking time / Improved Solver time
    speedup = None
    if imp_time > 0:
        speedup = round(bt_time / imp_time, 2)
    elif bt_time == 0 and imp_time == 0:
        speedup = 1.0

    # Execution-time improvement: ((BT time - Improved time) / BT time) * 100
    time_improvement_pct = None
    if bt_time > 0:
        time_improvement_pct = round(((bt_time - imp_time) / bt_time) * 100.0, 2)
    elif bt_time == 0 and imp_time == 0:
        time_improvement_pct = 0.0

    # Search-node reduction: ((BT nodes - Improved nodes) / BT nodes) * 100
    node_reduction_pct = None
    if bt_nodes > 0:
        node_reduction_pct = round(((bt_nodes - imp_nodes) / bt_nodes) * 100.0, 2)
    elif bt_nodes == 0 and imp_nodes == 0:
        node_reduction_pct = 0.0

    # Candidate-attempt reduction: ((BT attempts - Improved attempts) / BT attempts) * 100
    attempt_reduction_pct = None
    if bt_attempts > 0:
        attempt_reduction_pct = round(((bt_attempts - imp_attempts) / bt_attempts) * 100.0, 2)
    elif bt_attempts == 0 and imp_attempts == 0:
        attempt_reduction_pct = 0.0

    return jsonify({
        "status": "success",
        "backtracking": {
            "name": "Basic Backtracking",
            "solved": res_backtracking["solved"],
            "execution_time_ms": bt_time,
            "candidate_attempts": bt_attempts,
            "search_nodes": bt_nodes,
            "is_valid_solution": bt_valid,
            "board": res_backtracking["board"]
        },
        "improved": {
            "name": "Constraint Propagation + MRV",
            "solved": res_improved["solved"],
            "execution_time_ms": imp_time,
            "candidate_attempts": imp_attempts,
            "search_nodes": imp_nodes,
            "is_valid_solution": imp_valid,
            "board": res_improved["board"]
        },
        "speedup_ratio": speedup,
        "metrics_analysis": {
            "speedup_ratio": speedup,
            "time_improvement_pct": time_improvement_pct,
            "node_reduction_pct": node_reduction_pct,
            "attempt_reduction_pct": attempt_reduction_pct,
            "timing_method": "Single-run measurement with Python time.perf_counter() on identical board copies without tracing overhead."
        }
    }), 200


# ==========================================
# Static Asset Catch-All Route (Placed after API endpoints)
# ==========================================

@app.route("/<path:path>", methods=["GET"])
def static_files(path):
    """Serves static CSS, JS, and asset files securely from frontend/."""
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return jsonify({"status": "error", "message": "Not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
