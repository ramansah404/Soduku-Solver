/**
 * Sudoku AI Mini-Capstone — Frontend Interactions & Visualization Engine
 * Implements:
 * 1. 9x9 Sudoku grid management with arrow key navigation and peer highlighting.
 * 2. Example loading, board parsing, and clue protection.
 * 3. Dynamic solver execution via Flask API (/api/solve).
 * 4. Step-by-step genuine execution tracing and source code line highlighting.
 * 5. Side-by-side solver performance comparison (/api/compare).
 * 6. Live server-side source code viewer (/api/source).
 */

// Configurable API Base URL helper:
// Uses window.SUDOKU_API_BASE_URL (or window.API_BASE_URL) when configured.
// Defaults to empty string '' (relative paths) for local development or unified Flask serving.
function getApiEndpoint(path) {
    const rawBase = window.SUDOKU_API_BASE_URL || window.API_BASE_URL || '';
    const cleanBase = rawBase.replace(/\/+$/, '');
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${cleanBase}${cleanPath}`;
}

// Application State
const state = {
    selectedAlgorithm: 'improved', // 'improved' or 'backtracking'
    activeSourceView: 'improved',
    initialClues: Array.from({ length: 9 }, () => Array(9).fill(0)),
    examples: {},
    sourceCache: {},

    // Visualization state
    trace: [],
    traceCapped: false,
    traceAlgorithm: null,
    currentStepIndex: 0,
    isPlaying: false,
    playTimer: null,
    playbackSpeedMs: 150
};

// Explanations for Solvers
const ALGO_DESCRIPTIONS = {
    backtracking: {
        title: "Basic Backtracking (Algorithm A)",
        summary: "A pure depth-first recursive search algorithm. It scans the board sequentially to find the first empty cell, attempts numbers 1 through 9, and checks row/column/box constraints. When a dead end is encountered, it resets the cell to 0 and backtracks to the previous decision point. It does not perform lookahead or domain pruning."
    },
    improved: {
        title: "Constraint Propagation + MRV (Algorithm B)",
        summary: "An intelligent Constraint Satisfaction Problem (CSP) solver. It tracks candidate domains for each empty cell. Placing a number immediately eliminates that candidate from all 20 peer cells. If a peer has only 1 remaining candidate, it automatically triggers cascade filling (naked singles). When branching is required, the MRV (Minimum Remaining Values) heuristic picks the cell with the fewest possible choices, drastically minimizing branching factors."
    }
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    buildSudokuGrid();
    setupEventListeners();
    loadExamplesFromAPI();
    loadSourceCode('improved');
    loadSourceCode('backtracking');
    updateAlgoExplanation('improved');
});

// ============================================================================
// 1. Grid Construction & Keyboard Navigation
// ============================================================================

function buildSudokuGrid() {
    const gridContainer = document.getElementById('sudoku-grid');
    gridContainer.innerHTML = '';

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const input = document.createElement('input');
            input.type = 'text';
            input.maxLength = 1;
            input.className = 'grid-cell';
            input.id = `cell-${r}-${c}`;
            input.dataset.row = r;
            input.dataset.col = c;
            input.autocomplete = 'off';
            input.inputMode = 'numeric';

            // Cell Input Handler
            input.addEventListener('input', (e) => handleCellInput(e, r, c));
            input.addEventListener('keydown', (e) => handleCellKeydown(e, r, c));
            input.addEventListener('focus', () => highlightPeers(r, c));
            input.addEventListener('blur', clearPeerHighlights);

            gridContainer.appendChild(input);
        }
    }
}

function handleCellInput(e, row, col) {
    const val = e.target.value.trim();
    if (!/^[1-9]$/.test(val)) {
        e.target.value = '';
        state.initialClues[row][col] = 0;
        e.target.classList.remove('clue', 'solved');
    } else {
        const num = parseInt(val, 10);
        e.target.value = num;
        state.initialClues[row][col] = num;
        e.target.classList.add('clue');
        e.target.classList.remove('solved');
    }
    clearPeerHighlights();
    highlightPeers(row, col);
}

function handleCellKeydown(e, row, col) {
    let nextRow = row;
    let nextCol = col;

    switch (e.key) {
        case 'ArrowUp':
            nextRow = Math.max(0, row - 1);
            break;
        case 'ArrowDown':
            nextRow = Math.min(8, row + 1);
            break;
        case 'ArrowLeft':
            nextCol = Math.max(0, col - 1);
            break;
        case 'ArrowRight':
            nextCol = Math.min(8, col + 1);
            break;
        case 'Backspace':
        case 'Delete':
            e.target.value = '';
            state.initialClues[row][col] = 0;
            e.target.classList.remove('clue', 'solved');
            return;
        default:
            return;
    }

    if (nextRow !== row || nextCol !== col) {
        e.preventDefault();
        const nextCell = document.getElementById(`cell-${nextRow}-${nextCol}`);
        if (nextCell) nextCell.focus();
    }
}

function highlightPeers(focusedRow, focusedCol) {
    const boxStartRow = Math.floor(focusedRow / 3) * 3;
    const boxStartCol = Math.floor(focusedCol / 3) * 3;

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.getElementById(`cell-${r}-${c}`);
            if (!cell) continue;

            const isSameRow = r === focusedRow;
            const isSameCol = c === focusedCol;
            const isSameBox = r >= boxStartRow && r < boxStartRow + 3 && c >= boxStartCol && c < boxStartCol + 3;

            if (isSameRow || isSameCol || isSameBox) {
                cell.classList.add('highlight-peer');
            } else {
                cell.classList.remove('highlight-peer');
            }
        }
    }
}

function clearPeerHighlights() {
    document.querySelectorAll('.grid-cell').forEach(cell => {
        cell.classList.remove('highlight-peer');
    });
}

function getBoardFromGrid() {
    const board = [];
    for (let r = 0; r < 9; r++) {
        const row = [];
        for (let c = 0; c < 9; c++) {
            const cell = document.getElementById(`cell-${r}-${c}`);
            const val = parseInt(cell.value, 10);
            row.push(isNaN(val) ? 0 : val);
        }
        board.push(row);
    }
    return board;
}

function setBoardToGrid(board, markClues = false) {
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.getElementById(`cell-${r}-${c}`);
            const val = board[r][c];
            cell.value = val === 0 ? '' : val;

            cell.classList.remove('clue', 'solved', 'vis-active', 'vis-placed', 'vis-backtrack');
            if (markClues && val !== 0) {
                cell.classList.add('clue');
            }
        }
    }
}

function clearGrid() {
    stopVisualization();
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.getElementById(`cell-${r}-${c}`);
            cell.value = '';
            cell.className = 'grid-cell';
            state.initialClues[r][c] = 0;
        }
    }
    document.getElementById('board-mode-badge').textContent = 'Input Mode';
    document.getElementById('metrics-card').classList.add('hidden');
    document.getElementById('comparison-content').classList.add('hidden');
    document.getElementById('comparison-empty').classList.remove('hidden');
    document.getElementById('vis-control-panel').classList.add('hidden');
    showStatus('info', 'Grid Cleared', 'Enter your puzzle clues or load an example.');
}

function resetPuzzle() {
    stopVisualization();
    setBoardToGrid(state.initialClues, true);
    document.getElementById('board-mode-badge').textContent = 'Clues Loaded';
    document.getElementById('metrics-card').classList.add('hidden');
    document.getElementById('comparison-content').classList.add('hidden');
    document.getElementById('comparison-empty').classList.remove('hidden');
    showStatus('info', 'Puzzle Reset', 'Restored puzzle back to initial clues. Any solved numbers or visualizer states have been cleared.');
}

// ============================================================================
// 2. Event Listeners Setup
// ============================================================================

function setupEventListeners() {
    // Clear, Reset & Load Example
    document.getElementById('clear-grid-btn').addEventListener('click', clearGrid);
    document.getElementById('reset-puzzle-btn').addEventListener('click', resetPuzzle);
    document.getElementById('load-example-btn').addEventListener('click', loadSelectedExample);

    // Algorithm Selector Pills
    document.getElementById('algo-btn-improved').addEventListener('click', () => setAlgorithm('improved'));
    document.getElementById('algo-btn-backtracking').addEventListener('click', () => setAlgorithm('backtracking'));

    // Code Tabs
    document.getElementById('tab-improved').addEventListener('click', () => switchSourceTab('improved'));
    document.getElementById('tab-backtracking').addEventListener('click', () => switchSourceTab('backtracking'));

    // Main Actions
    document.getElementById('solve-btn').addEventListener('click', () => executeSolve(false));
    document.getElementById('visualize-btn').addEventListener('click', () => executeSolve(true));
    document.getElementById('compare-btn').addEventListener('click', executeCompare);
    document.getElementById('run-compare-btn').addEventListener('click', executeCompare);

    // Visualization Controls
    document.getElementById('vis-btn-play').addEventListener('click', togglePlayPause);
    document.getElementById('vis-btn-next').addEventListener('click', stepForward);
    document.getElementById('vis-btn-prev').addEventListener('click', stepBackward);
    document.getElementById('vis-btn-start').addEventListener('click', jumpToStart);
    document.getElementById('vis-btn-end').addEventListener('click', jumpToEnd);
    document.getElementById('vis-btn-reset').addEventListener('click', stopVisualization);

    // Speed Slider
    const speedSlider = document.getElementById('vis-speed-slider');
    const speedLabel = document.getElementById('vis-speed-label');
    speedSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        speedLabel.textContent = `${val}x`;
        // Speed scale: 1 -> 500ms, 5 -> 150ms, 10 -> 30ms
        state.playbackSpeedMs = Math.round(550 - (val * 50));
        if (state.isPlaying) {
            pauseVisualization();
            startVisualizationPlayback();
        } else if (state.trace && state.trace.length > 0) {
            updateVisualizationStep(true);
        }
    });

    // Notification close
    document.getElementById('status-close').addEventListener('click', () => {
        document.getElementById('status-banner').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('status-banner').style.opacity = '1';
            showStatus('info', 'Ready', 'Select an algorithm, load an example, or enter your own puzzle.');
        }, 200);
    });
}

function setAlgorithm(algo) {
    state.selectedAlgorithm = algo;

    const btnImp = document.getElementById('algo-btn-improved');
    const btnBt = document.getElementById('algo-btn-backtracking');

    if (algo === 'improved') {
        btnImp.classList.add('active');
        btnImp.setAttribute('aria-checked', 'true');
        btnBt.classList.remove('active');
        btnBt.setAttribute('aria-checked', 'false');
    } else {
        btnBt.classList.add('active');
        btnBt.setAttribute('aria-checked', 'true');
        btnImp.classList.remove('active');
        btnImp.setAttribute('aria-checked', 'false');
    }

    // Also switch the code tab to match the selected algorithm
    switchSourceTab(algo);
}

function switchSourceTab(algo) {
    state.activeSourceView = algo;
    document.getElementById('tab-improved').classList.toggle('active', algo === 'improved');
    document.getElementById('tab-backtracking').classList.toggle('active', algo === 'backtracking');
    updateAlgoExplanation(algo);

    // Reset scroll position to top when switching files unless active trace restores it
    const scrollArea = document.getElementById('code-scroll-area');
    if (scrollArea && (!state.trace || state.trace.length === 0 || state.activeSourceView !== state.traceAlgorithm)) {
        scrollArea.scrollTop = 0;
    }

    loadSourceCode(algo);

    // If switching to the algorithm currently being traced, re-sync highlight immediately
    if (state.trace && state.trace.length > 0 && state.activeSourceView === state.traceAlgorithm) {
        const currentStep = state.trace[state.currentStepIndex];
        if (currentStep && currentStep.line) {
            highlightCodeLine(currentStep.line, true);
        }
    } else {
        highlightCodeLine(null);
    }
}

function updateAlgoExplanation(algo) {
    const container = document.getElementById('algo-explanation');
    const info = ALGO_DESCRIPTIONS[algo];
    container.innerHTML = `<strong>${info.title}:</strong><p>${info.summary}</p>`;
}

// ============================================================================
// 3. API Communication: Examples & Source Code
// ============================================================================

async function loadExamplesFromAPI() {
    try {
        const res = await fetch(getApiEndpoint('/api/examples'));
        const data = await res.json();
        if (data.status === 'success') {
            state.examples = data.examples;
        }
    } catch (err) {
        console.error('Failed to load examples:', err);
    }
}

function loadSelectedExample() {
    const select = document.getElementById('example-select');
    const key = select.value;
    if (!key || !state.examples[key]) return;

    const ex = state.examples[key];
    stopVisualization();

    // Deep copy example board
    state.initialClues = JSON.parse(JSON.stringify(ex.board));
    setBoardToGrid(ex.board, true);

    document.getElementById('board-mode-badge').textContent = `${ex.name}`;
    document.getElementById('metrics-card').classList.add('hidden');
    document.getElementById('comparison-content').classList.add('hidden');
    document.getElementById('comparison-empty').classList.remove('hidden');

    showStatus('info', ex.name, ex.description);
}

async function loadSourceCode(algo) {
    const codeDisplay = document.getElementById('code-display');
    const pathBadge = document.getElementById('code-path-badge');
    const labelBadge = document.getElementById('source-filename-label');

    const expectedFile = algo === 'improved' ? 'backend/solver/improved_solver.py' : 'backend/solver/backtracking.py';
    pathBadge.textContent = expectedFile;
    labelBadge.textContent = expectedFile;

    // Check cache first
    if (state.sourceCache[algo]) {
        renderSource(state.sourceCache[algo]);
        return;
    }

    try {
        const res = await fetch(getApiEndpoint(`/api/source?solver=${algo}`));
        const data = await res.json();
        if (data.status === 'success') {
            state.sourceCache[algo] = data.code;
            renderSource(data.code);
        } else {
            codeDisplay.innerHTML = `<div class="code-line-row"><span class="line-num">-</span><span class="line-text"># Error loading code: ${escapeHtml(data.message)}</span></div>`;
        }
    } catch (err) {
        codeDisplay.innerHTML = `<div class="code-line-row"><span class="line-num">-</span><span class="line-text"># Network error fetching source code: ${escapeHtml(err.message)}</span></div>`;
    }
}

function renderSource(code) {
    const codeDisplay = document.getElementById('code-display');
    if (!codeDisplay) return;

    // Normalize newlines and split
    let lines = code.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    // If the file ends with a trailing newline, remove the extra empty element to match Python line counts
    if (lines.length > 0 && lines[lines.length - 1] === '') {
        lines.pop();
    }

    let rowsHtml = '';
    lines.forEach((lineText, idx) => {
        const lineNum = idx + 1;
        // Non-breaking space for empty lines so row height remains uniform
        const escaped = lineText.length === 0 ? '&nbsp;' : escapeHtml(lineText);
        rowsHtml += `<div class="code-line-row" id="code-line-${lineNum}" data-line="${lineNum}"><span class="line-num">${lineNum}</span><span class="line-text">${escaped}</span></div>`;
    });

    codeDisplay.innerHTML = rowsHtml;

    // Restore line highlight if this algorithm's file is actively being traced
    if (state.trace && state.trace.length > 0 && state.activeSourceView === state.traceAlgorithm) {
        const currentStep = state.trace[state.currentStepIndex];
        if (currentStep && currentStep.line) {
            highlightCodeLine(currentStep.line);
        }
    } else {
        highlightCodeLine(null);
    }
}

function highlightCodeLine(lineNum, smooth = false) {
    // Clear previous highlighted lines
    document.querySelectorAll('.code-line-row.highlighted').forEach(el => el.classList.remove('highlighted'));

    const badge = document.getElementById('active-line-badge');

    // Parse and validate line number metadata gracefully (Requirement 7)
    const parsedLine = parseInt(lineNum, 10);
    const hasValidLine = !isNaN(parsedLine) && parsedLine > 0;

    // If no line number, idle state, or currently looking at a different file than the active trace
    if (!hasValidLine || (state.trace && state.trace.length > 0 && state.activeSourceView !== state.traceAlgorithm)) {
        if (badge) {
            if (state.trace && state.trace.length > 0 && state.activeSourceView !== state.traceAlgorithm) {
                badge.textContent = `Line: Idle (Viewing ${state.activeSourceView === 'improved' ? 'MRV' : 'Backtracking'})`;
            } else {
                badge.textContent = 'Line: Idle';
            }
        }
        return;
    }

    if (badge) badge.textContent = `Line: ${parsedLine}`;

    const targetRow = document.getElementById(`code-line-${parsedLine}`);
    const scrollArea = document.getElementById('code-scroll-area');

    if (targetRow && scrollArea) {
        targetRow.classList.add('highlighted');

        // Accurately center targetRow in the scrollArea viewport
        const rowRect = targetRow.getBoundingClientRect();
        const areaRect = scrollArea.getBoundingClientRect();
        const relativeTop = rowRect.top - areaRect.top;
        const targetScrollTop = scrollArea.scrollTop + relativeTop - (scrollArea.clientHeight / 2) + (rowRect.height / 2);

        scrollArea.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: smooth ? 'smooth' : 'auto'
        });
    }
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// ============================================================================
// 4. Solve Execution (/api/solve)
// ============================================================================

async function executeSolve(visualize = false) {
    stopVisualization();
    const currentBoard = getBoardFromGrid();

    // Cache initial clues if board was manually entered
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            if (currentBoard[r][c] !== 0 && !document.getElementById(`cell-${r}-${c}`).classList.contains('solved')) {
                state.initialClues[r][c] = currentBoard[r][c];
            }
        }
    }

    showStatus('info', 'Solving...', `Executing ${state.selectedAlgorithm === 'improved' ? 'Constraint Propagation + MRV' : 'Basic Backtracking'}...`);

    try {
        const res = await fetch(getApiEndpoint('/api/solve'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                board: state.initialClues,
                algorithm: state.selectedAlgorithm,
                visualize: visualize
            })
        });

        const data = await res.json();

        // 1. Validator error (400 Bad Request)
        if (res.status === 400 || data.status === 'error') {
            showStatus('error', 'Validation Error', data.message);
            return;
        }

        // 2. Unsolvable puzzle (valid clues, but mathematically no solution)
        if (data.status === 'unsolvable' || !data.solved) {
            showStatus('warning', 'Unsolvable Puzzle', data.message || 'This puzzle is valid, but has no possible solution.');
            displayMetrics(data.metrics, data.algorithm, false);
            return;
        }

        // 3. Solved successfully
        if (data.status === 'success' && data.solved) {
            displayMetrics(data.metrics, data.algorithm, true);

            // Hide previous comparison benchmark so results are not confused
            document.getElementById('comparison-content').classList.add('hidden');
            document.getElementById('comparison-empty').classList.remove('hidden');

            if (visualize && data.trace && data.trace.length > 0) {
                // Launch visualization mode
                initVisualization(data.trace, data.trace_capped);
                if (data.trace_capped) {
                    showStatus('warning', 'Trace Capped (600 Events)', `Displaying first 600 events. Complete search explored ${data.metrics.search_nodes.toLocaleString()} nodes in ${data.metrics.execution_time_ms} ms.`);
                } else {
                    showStatus('success', 'Execution Trace Ready', `Recorded ${data.trace.length} genuine solver events. Play back step-by-step.`);
                }
            } else {
                // Apply final solved board directly
                renderSolvedBoard(data.board);
                showStatus('success', 'Solved Successfully!', `Completed in ${data.metrics.execution_time_ms} ms (${data.metrics.search_nodes} search nodes). Solution verified valid.`);
            }
        }
    } catch (err) {
        showStatus('error', 'Server Error', `Failed to connect to backend: ${err.message}`);
    }
}

function renderSolvedBoard(solvedBoard) {
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.getElementById(`cell-${r}-${c}`);
            const val = solvedBoard[r][c];
            cell.value = val;

            if (state.initialClues[r][c] !== 0) {
                cell.className = 'grid-cell clue';
            } else {
                cell.className = 'grid-cell solved';
            }
        }
    }
    document.getElementById('board-mode-badge').textContent = 'Solved';
}

function displayMetrics(metrics, algoName, isSolved) {
    const card = document.getElementById('metrics-card');
    card.classList.remove('hidden');

    const titleEl = document.getElementById('single-metrics-title');
    if (titleEl) titleEl.textContent = `Single-Run Metrics: ${algoName}`;
    const subtitleEl = document.getElementById('single-metrics-subtitle');
    if (subtitleEl) subtitleEl.textContent = `Direct single-solver execution metrics on current puzzle`;

    document.getElementById('metric-algo-badge').textContent = isSolved ? 'Solved' : 'Unsolvable';
    document.getElementById('metric-algo-badge').className = isSolved ? 'badge badge-success' : 'badge badge-outline';

    document.getElementById('metric-time').textContent = `${metrics.execution_time_ms} ms`;
    document.getElementById('metric-nodes').textContent = metrics.search_nodes.toLocaleString();
    document.getElementById('metric-attempts').textContent = metrics.candidate_attempts.toLocaleString();

    const validityEl = document.getElementById('metric-validity');
    if (metrics.is_valid_solution) {
        validityEl.textContent = 'Verified Valid';
        validityEl.className = 'metric-value highlight-emerald';
    } else {
        validityEl.textContent = isSolved ? 'Unverified' : 'No Solution';
        validityEl.className = 'metric-value highlight-yellow';
    }

    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ============================================================================
// 5. Execution Visualization Playback Engine
// ============================================================================

function initVisualization(traceEvents, isCapped = false) {
    state.trace = traceEvents;
    state.traceCapped = Boolean(isCapped);
    state.traceAlgorithm = state.selectedAlgorithm;
    state.currentStepIndex = 0;

    const panel = document.getElementById('vis-control-panel');
    panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const cappedBanner = document.getElementById('vis-capped-banner');
    if (cappedBanner) {
        cappedBanner.classList.toggle('hidden', !state.traceCapped);
    }

    // Switch to active algorithm source viewer to highlight matching lines
    switchSourceTab(state.selectedAlgorithm);

    updateVisualizationStep(true);
    startVisualizationPlayback();
}

function updateVisualizationStep(smooth = false) {
    if (!state.trace || state.trace.length === 0) return;

    if (state.currentStepIndex < 0) state.currentStepIndex = 0;
    if (state.currentStepIndex >= state.trace.length) state.currentStepIndex = state.trace.length - 1;

    const step = state.trace[state.currentStepIndex];
    if (!step) return;

    const total = state.trace.length;

    // Update Counter & Description with explicit capped indicator if applicable
    let counterText = `Step ${state.currentStepIndex + 1} of ${total}`;
    if (state.traceCapped) {
        counterText += ' (Trace capped at 600 events)';
    }
    document.getElementById('vis-step-counter').textContent = counterText;
    document.getElementById('vis-description').textContent = step.message || '';

    // Update Board Snapshot
    if (step.board_snapshot) {
        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                const cell = document.getElementById(`cell-${r}-${c}`);
                const val = step.board_snapshot[r][c];
                cell.value = val === 0 ? '' : val;

                // Retain clue style
                if (state.initialClues[r][c] !== 0) {
                    cell.className = 'grid-cell clue';
                } else if (val !== 0) {
                    cell.className = 'grid-cell solved';
                } else {
                    cell.className = 'grid-cell';
                }
            }
        }
    }

    // Clear transient visualizer cell states before applying new step state
    document.querySelectorAll('.grid-cell').forEach(cell => {
        cell.classList.remove('vis-active', 'vis-placed', 'vis-backtrack');
    });

    // Highlight Active Event Cell
    if (step.row >= 0 && step.col >= 0) {
        const activeCell = document.getElementById(`cell-${step.row}-${step.col}`);
        if (activeCell) {
            if (step.type === 'check_candidate' || step.type === 'select_mrv' || step.type === 'select_cell') {
                activeCell.classList.add('vis-active');
            } else if (step.type === 'place_number' || step.type === 'naked_single') {
                activeCell.classList.add('vis-placed');
            } else if (step.type === 'backtrack' || step.type === 'contradiction' || step.type === 'failed_choice') {
                activeCell.classList.add('vis-backtrack');
            }
        }
    }

    // Highlight genuine source line only if viewing the algorithm being traced
    if (state.activeSourceView === state.traceAlgorithm) {
        highlightCodeLine(step.line, smooth);
    } else {
        highlightCodeLine(null);
    }
}

function startVisualizationPlayback() {
    if (state.isPlaying) return;
    state.isPlaying = true;
    document.getElementById('vis-btn-play').innerHTML = '&#10074;&#10074;'; // Pause icon

    state.playTimer = setInterval(() => {
        if (state.currentStepIndex < state.trace.length - 1) {
            state.currentStepIndex++;
            updateVisualizationStep(false);
        } else {
            pauseVisualization();
        }
    }, state.playbackSpeedMs);
}

function pauseVisualization() {
    state.isPlaying = false;
    if (state.playTimer) {
        clearInterval(state.playTimer);
        state.playTimer = null;
    }
    document.getElementById('vis-btn-play').innerHTML = '&#9658;'; // Play icon
    if (state.trace && state.trace.length > 0) {
        updateVisualizationStep(true);
    }
}

function togglePlayPause() {
    if (state.isPlaying) {
        pauseVisualization();
    } else {
        if (state.currentStepIndex >= state.trace.length - 1) {
            state.currentStepIndex = 0;
        }
        updateVisualizationStep(true);
        startVisualizationPlayback();
    }
}

function stepForward() {
    pauseVisualization();
    if (state.currentStepIndex < state.trace.length - 1) {
        state.currentStepIndex++;
        updateVisualizationStep(true);
    }
}

function stepBackward() {
    pauseVisualization();
    if (state.currentStepIndex > 0) {
        state.currentStepIndex--;
        updateVisualizationStep(true);
    }
}

function jumpToStart() {
    pauseVisualization();
    state.currentStepIndex = 0;
    updateVisualizationStep(true);
}

function jumpToEnd() {
    pauseVisualization();
    state.currentStepIndex = state.trace.length > 0 ? state.trace.length - 1 : 0;
    updateVisualizationStep(true);
}

function stopVisualization() {
    pauseVisualization();
    state.trace = [];
    state.traceCapped = false;
    state.traceAlgorithm = null;
    state.currentStepIndex = 0;

    document.getElementById('vis-control-panel').classList.add('hidden');
    const cappedBanner = document.getElementById('vis-capped-banner');
    if (cappedBanner) cappedBanner.classList.add('hidden');

    // Clean up transient cell classes
    document.querySelectorAll('.grid-cell').forEach(cell => {
        cell.classList.remove('vis-active', 'vis-placed', 'vis-backtrack');
    });

    highlightCodeLine(null);
}

// ============================================================================
// 6. Solver Benchmark Comparison (/api/compare)
// ============================================================================

async function executeCompare() {
    stopVisualization();

    // Hide single-run metrics card so it's not confused with side-by-side benchmark
    document.getElementById('metrics-card').classList.add('hidden');
    const currentBoard = getBoardFromGrid();

    // Cache clues
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            if (currentBoard[r][c] !== 0 && !document.getElementById(`cell-${r}-${c}`).classList.contains('solved')) {
                state.initialClues[r][c] = currentBoard[r][c];
            }
        }
    }

    showStatus('info', 'Benchmarking...', 'Running both solvers on the exact same puzzle in parallel...');

    try {
        const res = await fetch(getApiEndpoint('/api/compare'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ board: state.initialClues })
        });

        const data = await res.json();

        if (res.status === 400 || data.status === 'error') {
            showStatus('error', 'Comparison Failed', data.message);
            return;
        }

        renderComparisonResults(data);
        showStatus('success', 'Benchmark Complete', 'Side-by-side solver metrics measured and displayed.');
    } catch (err) {
        showStatus('error', 'Benchmark Error', `Failed to execute comparison: ${err.message}`);
    }
}

function renderComparisonResults(data) {
    document.getElementById('comparison-empty').classList.add('hidden');
    const content = document.getElementById('comparison-content');
    content.classList.remove('hidden');

    const bt = data.backtracking;
    const imp = data.improved;
    const analysis = data.metrics_analysis || {};

    // Raw Backtracking stats
    document.getElementById('cmp-bt-time').textContent = `${bt.execution_time_ms} ms`;
    document.getElementById('cmp-bt-nodes').textContent = bt.search_nodes.toLocaleString();
    document.getElementById('cmp-bt-attempts').textContent = bt.candidate_attempts.toLocaleString();
    const btStatusEl = document.getElementById('cmp-bt-status');
    if (bt.solved && bt.is_valid_solution) {
        btStatusEl.textContent = 'Solved (Valid)';
        btStatusEl.className = 'val status-tag status-success';
    } else if (bt.solved) {
        btStatusEl.textContent = 'Solved (Unverified)';
        btStatusEl.className = 'val status-tag status-warning';
    } else {
        btStatusEl.textContent = 'Unsolvable';
        btStatusEl.className = 'val status-tag status-unsolvable';
    }

    // Raw Improved stats
    document.getElementById('cmp-imp-time').textContent = `${imp.execution_time_ms} ms`;
    document.getElementById('cmp-imp-nodes').textContent = imp.search_nodes.toLocaleString();
    document.getElementById('cmp-imp-attempts').textContent = imp.candidate_attempts.toLocaleString();
    const impStatusEl = document.getElementById('cmp-imp-status');
    if (imp.solved && imp.is_valid_solution) {
        impStatusEl.textContent = 'Solved (Valid)';
        impStatusEl.className = 'val status-tag status-success';
    } else if (imp.solved) {
        impStatusEl.textContent = 'Solved (Unverified)';
        impStatusEl.className = 'val status-tag status-warning';
    } else {
        impStatusEl.textContent = 'Unsolvable';
        impStatusEl.className = 'val status-tag status-unsolvable';
    }

    // Relative Performance & Reduction Metrics
    const speedupEl = document.getElementById('cmp-speedup');
    const timePctEl = document.getElementById('cmp-time-pct');
    const nodePctEl = document.getElementById('cmp-node-pct');
    const attemptPctEl = document.getElementById('cmp-attempt-pct');

    // 1. Speedup Ratio: BT time / Imp time
    if (speedupEl) {
        if (analysis.speedup_ratio != null) {
            speedupEl.textContent = `${analysis.speedup_ratio}×`;
            speedupEl.className = analysis.speedup_ratio >= 1.0 ? 'ratio-val highlight-cyan' : 'ratio-val highlight-yellow';
        } else {
            speedupEl.textContent = (bt.execution_time_ms === 0 && imp.execution_time_ms === 0) ? '1.0×' : 'N/A';
        }
    }

    // 2. Time Improvement: ((BT time - Imp time) / BT time) * 100
    if (timePctEl) {
        if (analysis.time_improvement_pct != null) {
            const prefix = analysis.time_improvement_pct > 0 ? '+' : '';
            timePctEl.textContent = `${prefix}${analysis.time_improvement_pct}%`;
            timePctEl.className = analysis.time_improvement_pct >= 0 ? 'ratio-val highlight-emerald' : 'ratio-val highlight-yellow';
        } else {
            timePctEl.textContent = '0.0%';
        }
    }

    // 3. Search-Node Reduction: ((BT nodes - Imp nodes) / BT nodes) * 100
    if (nodePctEl) {
        if (analysis.node_reduction_pct != null) {
            const prefix = analysis.node_reduction_pct > 0 ? '+' : '';
            nodePctEl.textContent = `${prefix}${analysis.node_reduction_pct}%`;
            nodePctEl.className = analysis.node_reduction_pct >= 0 ? 'ratio-val highlight-purple' : 'ratio-val highlight-yellow';
        } else {
            nodePctEl.textContent = '0.0%';
        }
    }

    // 4. Candidate-Attempt Reduction: ((BT attempts - Imp attempts) / BT attempts) * 100
    if (attemptPctEl) {
        if (analysis.attempt_reduction_pct != null) {
            const prefix = analysis.attempt_reduction_pct > 0 ? '+' : '';
            attemptPctEl.textContent = `${prefix}${analysis.attempt_reduction_pct}%`;
            attemptPctEl.className = analysis.attempt_reduction_pct >= 0 ? 'ratio-val highlight-yellow' : 'ratio-val highlight-yellow';
        } else {
            attemptPctEl.textContent = '0.0%';
        }
    }

    // Scientific Speedup Summary
    const headline = document.getElementById('speedup-headline');
    const desc = document.getElementById('speedup-description');

    if (!bt.solved && !imp.solved) {
        headline.textContent = 'Puzzle is Valid but Mathematically Unsolvable';
        desc.textContent = `Both solvers exhaustively searched all possible decision trees (Backtracking: ${bt.search_nodes} nodes; MRV: ${imp.search_nodes} nodes) and mathematically proved no valid solution exists for these initial clues.`;
    } else if (analysis.speedup_ratio != null && analysis.speedup_ratio > 1.0) {
        headline.textContent = `Constraint Propagation + MRV is ${analysis.speedup_ratio}× faster!`;
        const nodeDiff = bt.search_nodes - imp.search_nodes;
        desc.textContent = `The MRV heuristic and forward checking pruned ${nodeDiff.toLocaleString()} search nodes (${analysis.node_reduction_pct}% reduction), eliminating dead ends before guessing.`;
    } else if (analysis.speedup_ratio != null && analysis.speedup_ratio < 1.0) {
        headline.textContent = `Backtracking was faster on this low-difficulty puzzle`;
        desc.textContent = `For puzzles with high clue density, simple Backtracking solved the grid in ${bt.execution_time_ms} ms without candidate-domain maintenance overhead. MRV explored ${imp.search_nodes} nodes vs Backtracking's ${bt.search_nodes} nodes.`;
    } else {
        headline.textContent = `Both algorithms performed with equivalent speed`;
        desc.textContent = `Both solvers evaluated puzzle constraints quickly: Backtracking in ${bt.execution_time_ms} ms (${bt.search_nodes} nodes); MRV in ${imp.execution_time_ms} ms (${imp.search_nodes} nodes).`;
    }

    const compSection = document.getElementById('comparison-section');
    if (compSection) {
        compSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// ============================================================================
// 7. Notification Banner Helper
// ============================================================================

function showStatus(type, title, message) {
    const banner = document.getElementById('status-banner');
    const icon = document.getElementById('status-icon');
    const titleEl = document.getElementById('status-title');
    const msgEl = document.getElementById('status-message');

    banner.className = `status-banner ${type}`;
    titleEl.textContent = title;
    msgEl.textContent = message;

    if (type === 'success') {
        icon.innerHTML = '&#10004;';
    } else if (type === 'error') {
        icon.innerHTML = '&#9888;';
    } else if (type === 'warning') {
        icon.innerHTML = '&#9888;';
    } else {
        icon.innerHTML = '&#9432;';
    }
}
