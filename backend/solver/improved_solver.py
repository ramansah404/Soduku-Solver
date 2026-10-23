"""
Algorithm B: Constraint Propagation + Minimum Remaining Values (MRV) Heuristic

How this solver improves over Basic Backtracking (in simple English):

1. Candidates (Domains):
   Instead of guessing blindly from 1 to 9, each cell maintains a set of "possible candidates"
   (numbers not yet taken in its row, column, or 3x3 box).

2. Constraint Propagation (Forward Checking & Naked Singles):
   When a number is assigned to a cell, that number is immediately removed (eliminated)
   from the candidates of all its neighboring cells (row, column, and box peers).
   If any neighbor is left with only 1 possible candidate (a "Naked Single"), that cell
   is automatically filled, triggering further eliminations.

3. Contradiction Detection:
   If an empty cell ever ends up with 0 remaining candidates, we immediately know
   that a previous choice was incorrect. We stop early and backtrack without wasting time.

4. MRV Heuristic (Minimum Remaining Values):
   When a guess is needed, Basic Backtracking just picks the next empty cell in order.
   In contrast, MRV picks the cell with the FEWEST remaining candidates (e.g. 2 candidates
   instead of 8). This dramatically reduces the branching factor and catches dead ends early.
"""

import time
import copy
from typing import List, Tuple, Optional, Dict, Set, Any


def get_peers(row: int, col: int) -> Set[Tuple[int, int]]:
    """
    Returns the set of all 20 peer cells for (row, col):
    cells in the same row, same column, or same 3x3 box (excluding itself).
    """
    peers = set()

    # Same row
    for c in range(9):
        if c != col:
            peers.add((row, c))

    # Same column
    for r in range(9):
        if r != row:
            peers.add((r, col))

    # Same 3x3 box
    box_row = (row // 3) * 3
    box_col = (col // 3) * 3
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if r != row or c != col:
                peers.add((r, c))

    return peers


# Precompute peers for all 81 cells for maximum performance
ALL_PEERS: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {
    (r, c): get_peers(r, c) for r in range(9) for c in range(9)
}


def initialize_domains(board: List[List[int]]) -> Optional[Dict[Tuple[int, int], Set[int]]]:
    """
    Initializes candidate sets for every cell based on the starting board clues.
    If a cell has a clue `val`, its domain is {val}.
    If empty, its domain starts as {1..9} minus values present in its peers.
    Returns None if any contradiction exists in initial clues.
    """
    domains: Dict[Tuple[int, int], Set[int]] = {}

    # Initialize fixed clues and empty domains
    for r in range(9):
        for c in range(9):
            val = board[r][c]
            if val != 0:
                domains[(r, c)] = {val}
            else:
                domains[(r, c)] = set(range(1, 10))

    # Eliminate initial clues from peers
    for (r, c), possible in list(domains.items()):
        val = board[r][c]
        if val != 0:
            for pr, pc in ALL_PEERS[(r, c)]:
                if (pr, pc) in domains and val in domains[(pr, pc)]:
                    domains[(pr, pc)].discard(val)
                    if len(domains[(pr, pc)]) == 0:
                        return None  # Contradiction in initial clues

    return domains


def solve_improved(
    board: List[List[int]],
    record_trace: bool = False,
    max_trace_steps: int = 600
) -> Dict[str, Any]:
    """
    Solves Sudoku using Constraint Propagation and the MRV heuristic.

    Args:
        board: 9x9 list of lists representing the Sudoku puzzle (0 = empty).
        record_trace: If True, records solver events for visualization.
        max_trace_steps: Maximum number of trace events to record.

    Returns:
        Dictionary with:
            - solved: bool
            - board: solved 9x9 board (or original if unsolvable)
            - execution_time_ms: time taken in milliseconds
            - candidate_attempts: number of candidate values tested
            - search_nodes: number of recursive decision points
            - trace: list of event objects (if record_trace=True)
            - trace_capped: whether trace reached max_trace_steps
    """
    stats = {
        "candidate_attempts": 0,
        "search_nodes": 0,
        "trace_capped": False
    }
    trace_events: List[Dict[str, Any]] = []

    def build_board_snapshot(domains_dict: Dict[Tuple[int, int], Set[int]]) -> List[List[int]]:
        """Constructs a 9x9 board snapshot from current single-valued domains."""
        snapshot = [[0] * 9 for _ in range(9)]
        for (r, c), vals in domains_dict.items():
            if len(vals) == 1:
                snapshot[r][c] = next(iter(vals))
        return snapshot

    def record_event(
        event_type: str,
        row: int,
        col: int,
        val: int,
        message: str,
        line_number: int,
        current_domains: Dict[Tuple[int, int], Set[int]]
    ):
        if not record_trace:
            return
        if len(trace_events) >= max_trace_steps:
            stats["trace_capped"] = True
            return
        trace_events.append({
            "type": event_type,
            "row": row,
            "col": col,
            "val": val,
            "message": message,
            "line": line_number,
            "board_snapshot": build_board_snapshot(current_domains),
            "candidates_count": len(current_domains.get((row, col), set()))
        })

    def propagate(
        domains: Dict[Tuple[int, int], Set[int]],
        cell: Tuple[int, int],
        assigned_val: int
    ) -> bool:
        """
        Propagates constraint: removes assigned_val from peers of cell.
        If any peer is reduced to 1 candidate, cascades constraint propagation.
        Returns False if contradiction (domain becomes empty), True otherwise.
        """
        peers = ALL_PEERS[cell]
        for peer in peers:
            peer_domain = domains[peer]
            if assigned_val in peer_domain:
                peer_domain.remove(assigned_val)

                record_event(
                    "eliminate_candidate", peer[0], peer[1], assigned_val,
                    f"Eliminated candidate {assigned_val} from ({peer[0] + 1}, {peer[1] + 1}) due to assignment at ({cell[0] + 1}, {cell[1] + 1})",
                    173,
                    domains
                )

                # Contradiction check: no candidate left for this peer
                if len(peer_domain) == 0:
                    record_event(
                        "contradiction", peer[0], peer[1], 0,
                        f"Contradiction! Cell ({peer[0] + 1}, {peer[1] + 1}) has 0 remaining candidates",
                        183,
                        domains
                    )
                    return False

                # Naked single: exactly 1 candidate remaining, propagate forward
                if len(peer_domain) == 1:
                    naked_val = next(iter(peer_domain))
                    record_event(
                        "naked_single", peer[0], peer[1], naked_val,
                        f"Naked single found: cell ({peer[0] + 1}, {peer[1] + 1}) must be {naked_val}",
                        194,
                        domains
                    )
                    if not propagate(domains, peer, naked_val):
                        return False

        return True

    def select_mrv_cell(domains: Dict[Tuple[int, int], Set[int]]) -> Optional[Tuple[int, int]]:
        """
        Selects unassigned cell with the Minimum Remaining Values (MRV).
        Returns None if all cells have exactly 1 value (solved).
        """
        min_candidates = 10
        best_cell = None

        for (r, c), possible in domains.items():
            count = len(possible)
            if count > 1 and count < min_candidates:
                min_candidates = count
                best_cell = (r, c)
                if min_candidates == 2:
                    # Can't get fewer than 2 candidates for an unassigned cell
                    break

        return best_cell

    def search_recursive(domains: Dict[Tuple[int, int], Set[int]]) -> Optional[Dict[Tuple[int, int], Set[int]]]:
        stats["search_nodes"] += 1

        # Step 1: Select cell with Minimum Remaining Values
        mrv_cell = select_mrv_cell(domains)
        if mrv_cell is None:
            # All cells have exactly 1 candidate and no contradictions -> Solved!
            record_event("solved", -1, -1, 0, "Puzzle successfully solved via MRV & Propagation!", 232, domains)
            return domains

        r, c = mrv_cell
        candidates = sorted(list(domains[mrv_cell]))

        record_event(
            "select_mrv", r, c, 0,
            f"MRV selected cell ({r + 1}, {c + 1}) with {len(candidates)} candidates: {candidates}",
            229,
            domains
        )

        # Step 2: Try each candidate for the MRV cell
        for candidate in candidates:
            stats["candidate_attempts"] += 1

            record_event(
                "place_number", r, c, candidate,
                f"Trying candidate {candidate} at MRV cell ({r + 1}, {c + 1})",
                258,
                domains
            )

            # Clone domains before propagating so we can backtrack cleanly
            domains_copy = {pos: set(vals) for pos, vals in domains.items()}
            domains_copy[mrv_cell] = {candidate}

            if propagate(domains_copy, mrv_cell, candidate):
                result = search_recursive(domains_copy)
                if result is not None:
                    return result

            # Contradiction encountered or branch failed -> Backtrack
            record_event(
                "backtrack", r, c, candidate,
                f"Dead end with candidate {candidate} at ({r + 1}, {c + 1}). Backtracking...",
                265,
                domains
            )

        return None

    # Measure execution time using time.perf_counter()
    start_time = time.perf_counter()

    initial_domains = initialize_domains(board)
    if initial_domains is None:
        end_time = time.perf_counter()
        return {
            "solved": False,
            "board": copy.deepcopy(board),
            "execution_time_ms": round((end_time - start_time) * 1000.0, 3),
            "candidate_attempts": 0,
            "search_nodes": 0,
            "trace": trace_events,
            "trace_capped": stats["trace_capped"]
        }

    record_event(
        "init_domains", -1, -1, 0,
        "Initialized candidate domains for all 81 cells based on starting clues and peer constraint elimination",
        72,
        initial_domains
    )

    final_domains = search_recursive(initial_domains)
    end_time = time.perf_counter()
    execution_time_ms = round((end_time - start_time) * 1000.0, 3)

    is_solved = final_domains is not None
    if is_solved:
        solved_board = [[0] * 9 for _ in range(9)]
        for (r, c), vals in final_domains.items():
            solved_board[r][c] = next(iter(vals))
    else:
        solved_board = copy.deepcopy(board)

    return {
        "solved": is_solved,
        "board": solved_board,
        "execution_time_ms": execution_time_ms,
        "candidate_attempts": stats["candidate_attempts"],
        "search_nodes": stats["search_nodes"],
        "trace": trace_events,
        "trace_capped": stats["trace_capped"]
    }
