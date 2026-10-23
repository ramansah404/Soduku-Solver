"""
Sudoku Solvers package:
- Basic Backtracking (Algorithm A)
- Constraint Propagation + MRV (Algorithm B)
"""

from .backtracking import solve_backtracking
from .improved_solver import solve_improved

__all__ = ["solve_backtracking", "solve_improved"]
