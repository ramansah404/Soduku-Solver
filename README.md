# Sudoku AI Mini-Capstone: Backtracking vs Constraint Propagation with Heuristics

An interactive, educational Sudoku Solver web application designed to demonstrate the algorithmic differences between **Basic Recursive Backtracking** and **Constraint Propagation with the Minimum Remaining Values (MRV) Heuristic**.

The application features **real-time step-by-step execution visualization** and an **in-browser Python source code inspector** that displays and highlights the exact code running in the backend.

---

## 1. Project Overview & Architecture

### Technology Stack
- **Backend Language:** Python 3.10+ (tested on Python 3.14)
- **Backend Framework:** Flask 3.x (minimal dependencies, no external AI/ML frameworks or databases)
- **Frontend:** Vanilla HTML5, Modern CSS (custom dark theme with 3×3 Sudoku block separation), Vanilla JavaScript
- **Test Suite:** Python standard library `unittest`

### Project Folder Structure
```text
sudoku-ai-project/
├── frontend/
│   ├── index.html         # Webpage layout, 9x9 grid, controls, code viewer, and benchmarks
│   ├── style.css          # Modern dark-theme stylesheet with grid highlighting and animations
│   └── script.js          # Client-side UI logic, API calls, playback engine, code highlighter
├── backend/
│   ├── app.py             # Flask web server, API routing, and static file delivery
│   ├── validator.py       # Board structure, clue duplicate checks, move & solution verification
│   ├── solver/
│   │   ├── __init__.py    # Solver package export
│   │   ├── backtracking.py     # Algorithm A: Naive recursive backtracking with event tracing
│   │   └── improved_solver.py  # Algorithm B: Constraint propagation, naked singles & MRV heuristic
│   └── tests/
│       └── test_solver.py # 26 automated unit tests covering validation, solvers, and APIs
├── requirements.txt       # Python dependencies (Flask>=3.0.0)
└── README.md              # Documentation, setup guide, and algorithm explanation
```

---

## 2. Quickstart Guide (Windows)

### Prerequisites
- Python 3.10 or higher installed. (Check with `python --version` in PowerShell or Command Prompt).

### Step 1: Clone or Open the Project
Open PowerShell and navigate to the project directory:
```powershell
cd "c:\Users\Raman sah\Desktop\Soduku AI"
```

### Step 2: (Optional) Create & Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment in PowerShell
.\venv\Scripts\Activate.ps1
```
*(If script execution is disabled on your system, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or skip creating a virtual environment).*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application Server
```powershell
python backend/app.py
```
Output will indicate:
```text
 * Running on http://127.0.0.1:5000
```

### Step 5: Open in Your Browser
Open your favorite web browser and visit:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 3. Running Automated Tests

Run the test suite from the project root using `unittest`:
```powershell
python -m unittest discover -s backend/tests -p "test_*.py" -v
```
Or directly:
```powershell
python backend/tests/test_solver.py
```

### Test Coverage (30 Passing Tests):
- **Board Structure & Dimension Validation:** 9×9 verification, non-list detection, missing rows/cols.
- **Value Range Validation:** Rejection of negative numbers, numbers > 9, strings, booleans, and floats.
- **Clue Conflict Validation:** Detects duplicate clues in any row, column, or 3×3 box.
- **Algorithm Correctness:**
  - Solves known solvable puzzles.
  - Verifies solution satisfies Sudoku rules (no duplicates, no empty cells).
  - Verifies original given clues are strictly preserved.
  - Verifies both algorithms arrive at identical valid solutions.
- **Unsolvable Puzzle Handling:** Correctly detects mathematically unsolvable puzzles without crashing or false positives.
- **CSP & Constraint Propagation Logic:** Tests peer generation (20 peers per cell), domain initialization, candidate elimination, and contradiction detection.
- **Flask Endpoints:** Tests `/` (index), `/api/examples`, `/api/solve`, `/api/compare`, and `/api/source` security whitelist (blocks arbitrary path traversal).
- **Comparative Metrics Formulas & Safety:**
  - Speedup Ratio: `Speedup = BT Time / Improved Time`
  - Execution-Time Improvement %: `((BT Time - Improved Time) / BT Time) * 100`
  - Search-Node Reduction %: `((BT Nodes - Improved Nodes) / BT Nodes) * 100`
  - Candidate-Attempt Reduction %: `((BT Attempts - Improved Attempts) / BT Attempts) * 100`
  - Safe zero-division handling for all boundary conditions.
- **Trace Event Completeness:** Confirms genuine generation of `select_cell`, `failed_choice`, `init_domains`, `select_mrv`, `place_number`, `eliminate_candidate`, and `backtrack` events.

---

## 4. Algorithmic Breakdown: Backtracking vs. Improved Solver

### Algorithm A: Basic Backtracking (`backend/solver/backtracking.py`)
- **How it works:**
  1. Finds the first empty cell (`0`) scanning row-by-row from top-left to bottom-right.
  2. Tries candidate digits 1 through 9 sequentially.
  3. Checks whether the digit violates row, column, or 3×3 box constraints using `is_safe()`.
  4. If legal, places the digit and recursively calls itself to solve the remaining board.
  5. If a dead end is reached (no digit 1-9 is legal for a later cell), it resets the cell to 0 and backtracks to try the next candidate.
- **Characteristics:**
  - Simple, elegant recursive depth-first search.
  - **Weakness:** Blinds itself to future consequences. It can waste thousands of search nodes exploring branches that were already doomed by earlier assignments.

### Algorithm B: Constraint Propagation + MRV Heuristic (`backend/solver/improved_solver.py`)
- **How it works:**
  1. **Candidate Domains:** Every cell maintains a set of possible remaining numbers $\{1..9\}$. Clues reduce their neighbors' sets immediately upon initialization.
  2. **Constraint Propagation (Forward Checking):** When digit $d$ is assigned to cell $(r, c)$, $d$ is immediately removed from the candidate sets of all 20 peers (same row, column, and 3×3 box).
  3. **Naked Singles:** If any peer's candidate domain shrinks to a single number $\{v\}$, that cell is auto-filled and cascades its own constraints.
  4. **Contradiction Detection:** If any unassigned cell's candidate domain becomes empty ($\emptyset$), a contradiction is detected immediately. The solver abandons the branch early without exploring deeper nodes.
  5. **MRV Heuristic (Minimum Remaining Values):** Instead of picking empty cells blindly in scan order, MRV chooses the cell with the **fewest remaining candidates** (e.g., 2 candidates instead of 8). This dramatically lowers the branching factor ($2 \times 2$ vs $9 \times 9$) and triggers early failures at the top of the search tree.
- **Characteristics:**
  - Exponentially smaller search trees on hard puzzles.
  - Typically solves hard puzzles with a fraction of the recursive search nodes compared to naive backtracking.

---

## 5. API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /` | `GET` | Serves the single-page application (`frontend/index.html`). |
| `GET /api/examples` | `GET` | Returns curated sample puzzles (Easy, Medium, Hard, Expert, Unsolvable, Invalid). |
| `GET /api/source?solver=<name>` | `GET` | Safely returns the genuine Python source code of the selected solver (`backtracking` or `improved`). Whitelisted to prevent directory traversal. |
| `POST /api/solve` | `POST` | Validates and solves a 9×9 board using the selected algorithm. Supports `visualize: true` to return event execution trace. |
| `POST /api/compare` | `POST` | Runs **both** algorithms on the exact same board without tracing overhead to return fair, high-resolution performance benchmarks with speedup ratios and reduction percentages. |

---

## 6. How the Frontend Communicates with Flask

1. **State Initialization:** When `index.html` loads, `script.js` requests `/api/examples` and `/api/source?solver=improved`.
2. **Interactive Editing:** Users can edit any cell directly (using digits 1-9 or arrow keys for fast navigation).
3. **Solving:** When the user clicks **"Solve Puzzle"**, the frontend sends a `POST` request with JSON `{ "board": [[...]], "algorithm": "improved", "visualize": false }`. Flask validates the board via `validator.py`, calls the solver, and responds with the solved board and execution metrics.
4. **Reset Puzzle:** Clicking **"Reset"** restores the puzzle to its starting clues without wiping the grid.
5. **Step-by-Step Visualization:** Clicking **"Visualize Step-by-Step"** requests `{ visualize: true }`. Flask records genuine execution events (`check_candidate`, `place_number`, `eliminate_candidate`, `select_mrv`, `backtrack`). The frontend animates the board and highlights the active line number directly in the source code viewer.
6. **Benchmarking:** Clicking **"Compare Both"** sends the board to `/api/compare`, which runs both solvers with `time.perf_counter()` and presents side-by-side performance cards with speedup metrics and reduction percentages.
