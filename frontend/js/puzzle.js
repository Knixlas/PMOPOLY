/**
 * Puzzle placement phase — three layers:
 *   1. Mark (base 4×4 + expansion pieces)
 *   2. Ground projects (FÖRSKOLOR, LOKAL, KONTOR) — on mark, no overlap
 *   3. Bostäder (BRF, Hyresrätt) — must sit on top of ground projects
 */
import { state, sendAction } from './app.js';

const TYPE_COLORS = {
    'BRF': '#1A4D24', 'Hyresrätt': '#4D1A1A', 'FÖRSKOLOR': '#0F3D5C',
    'LOKAL': '#7A4A10', 'KONTOR': '#321F50'
};

const TYPE_COLORS_LIGHT = {
    'BRF': '#2D7A3A', 'Hyresrätt': '#8A3030', 'FÖRSKOLOR': '#1A6B9A',
    'LOKAL': '#C87820', 'KONTOR': '#5B3A8A'
};

const MARK_COLOR = '#8B7355';
const MARK_COLOR_LIGHT = '#A0926B';

const BOSTADER_TYPES = new Set(['BRF', 'Hyresrätt']);
function isBostad(typ) { return BOSTADER_TYPES.has(typ); }

// ── Rotation / flip helpers ──

function rotate90(cells) { return cells.map(([r, c]) => [c, -r]); }
function flipH(cells) { return cells.map(([r, c]) => [r, -c]); }

function normalize(cells) {
    const minR = Math.min(...cells.map(c => c[0]));
    const minC = Math.min(...cells.map(c => c[1]));
    return cells.map(([r, c]) => [r - minR, c - minC])
                .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

function allOrientations(cells) {
    const orientations = [];
    let current = cells.map(c => [...c]);
    for (let i = 0; i < 4; i++) {
        orientations.push(normalize(current));
        orientations.push(normalize(flipH(current)));
        current = rotate90(current);
    }
    return orientations;
}

// ── Interaction state ──

// Shared selection state for both drag and tap modes
let dragState = null;
let selectState = null;  // tap-to-place: {id, kind, typ, orientations, orientationIdx}
let lastPointerPos = { clientX: 0, clientY: 0 };
const isTouch = window.matchMedia('(pointer: coarse)').matches;

// Select a piece (tap mode for touch devices)
export function selectPiece(id, kind, typ, shapeCells) {
    const orientations = allOrientations(shapeCells);
    selectState = { id, kind, typ, orientations, orientationIdx: 0 };
    // Re-render to show selection highlight and preview
    if (state.gameState) {
        renderPuzzleBoard(state.gameState);
        const panel = document.getElementById('action-panel');
        if (panel) renderPuzzleAction(panel, state.gameState);
    }
}

export function clearSelection() {
    selectState = null;
}

export function getSelectState() { return selectState; }

// Place the selected piece at grid position
function tapPlaceAt(row, col) {
    if (!selectState) return;
    const cells = selectState.orientations[selectState.orientationIdx];
    const targetCells = cells.map(([r, c]) => [r + row, c + col]);
    const valid = checkPlacementValid(targetCells);
    if (!valid) return;

    if (selectState.kind === 'mark_expansion') {
        sendAction({ action: 'puzzle_place_mark_expansion', piece_id: selectState.id, cells: targetCells });
    } else {
        sendAction({ action: 'puzzle_place_project', project_id: selectState.id, cells: targetCells });
    }
    selectState = null;
}

// Drag start (desktop / pointer devices)
export function startDrag(id, kind, typ, shapeCells, event) {
    lastPointerPos = { clientX: event.clientX, clientY: event.clientY };
    const orientations = allOrientations(shapeCells);
    dragState = {
        id, kind, typ, shapeCells,
        orientationIdx: 0,
        orientations,
        ghostEl: null,
    };
    createGhost(event);
    document.addEventListener('pointermove', onDragMove);
    document.addEventListener('pointerup', onDragEnd);
}

function createGhost(event) {
    if (dragState.ghostEl) dragState.ghostEl.remove();
    const cells = dragState.orientations[dragState.orientationIdx];
    const ghost = document.createElement('div');
    ghost.className = 'puzzle-ghost';
    const maxR = Math.max(...cells.map(c => c[0]));
    const maxC = Math.max(...cells.map(c => c[1]));
    ghost.style.gridTemplateRows = `repeat(${maxR + 1}, 1fr)`;
    ghost.style.gridTemplateColumns = `repeat(${maxC + 1}, 1fr)`;

    const bg = dragState.kind === 'mark_expansion'
        ? MARK_COLOR_LIGHT
        : (TYPE_COLORS_LIGHT[dragState.typ] || '#888');
    for (const [r, c] of cells) {
        const cell = document.createElement('div');
        cell.className = 'puzzle-ghost-cell';
        cell.style.gridRow = r + 1;
        cell.style.gridColumn = c + 1;
        cell.style.background = bg;
        ghost.appendChild(cell);
    }
    document.body.appendChild(ghost);
    dragState.ghostEl = ghost;
    positionGhost(event);
}

function positionGhost(event) {
    if (!dragState?.ghostEl) return;
    const ghost = dragState.ghostEl;
    const gridEl = document.querySelector('.puzzle-grid');
    const cellSize = gridEl ? gridEl.offsetWidth / 10 : 30;
    const cells = dragState.orientations[dragState.orientationIdx];
    const maxR = Math.max(...cells.map(c => c[0]));
    const maxC = Math.max(...cells.map(c => c[1]));
    ghost.style.width = `${(maxC + 1) * cellSize}px`;
    ghost.style.height = `${(maxR + 1) * cellSize}px`;
    ghost.style.left = `${event.clientX - cellSize / 2}px`;
    ghost.style.top = `${event.clientY - cellSize / 2}px`;
}

function onDragMove(event) {
    event.preventDefault();
    lastPointerPos = { clientX: event.clientX, clientY: event.clientY };
    positionGhost(event);
    highlightTarget(event);
}

function getDropRowCol(event) {
    const gridEl = document.querySelector('.puzzle-grid');
    if (!gridEl) return null;
    const rect = gridEl.getBoundingClientRect();
    const cellSize = rect.width / 10;
    return {
        row: Math.floor((event.clientY - rect.top) / cellSize),
        col: Math.floor((event.clientX - rect.left) / cellSize),
    };
}

function highlightTarget(event) {
    document.querySelectorAll('.puzzle-cell.drag-valid, .puzzle-cell.drag-invalid')
        .forEach(el => { el.classList.remove('drag-valid', 'drag-invalid'); });

    const pos = getDropRowCol(event);
    if (!pos) return;
    const cells = dragState.orientations[dragState.orientationIdx];
    const targetCells = cells.map(([r, c]) => [r + pos.row, c + pos.col]);
    const valid = checkPlacementValid(targetCells);
    const gridEl = document.querySelector('.puzzle-grid');

    for (const [r, c] of targetCells) {
        const cellEl = gridEl?.querySelector(`.puzzle-cell[data-row="${r}"][data-col="${c}"]`);
        if (cellEl) cellEl.classList.add(valid ? 'drag-valid' : 'drag-invalid');
    }
}

function checkPlacementValid(targetCells) {
    const puzzle = state.gameState?.my_puzzle;
    if (!puzzle) return false;

    if (dragState.kind === 'mark_expansion') {
        // Mark expansion: must be adjacent to grid, not overlap grid, within bounds
        const gridSet = new Set(puzzle.grid_cells.map(([r, c]) => `${r},${c}`));
        // Remove own previous placement
        const old = puzzle.mark_placements?.[dragState.id];
        if (old) for (const rc of old.cells) gridSet.delete(`${rc[0]},${rc[1]}`);

        let adjacent = false;
        for (const [r, c] of targetCells) {
            if (r < 0 || r >= 10 || c < 0 || c >= 10) return false;
            if (gridSet.has(`${r},${c}`)) return false; // overlap
            for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
                if (gridSet.has(`${r+dr},${c+dc}`)) adjacent = true;
            }
        }
        return adjacent;
    }

    // Project placement
    const gridSet = new Set(puzzle.grid_cells.map(([r, c]) => `${r},${c}`));
    const typ = dragState.typ;

    if (isBostad(typ)) {
        // Bostäder must sit on top of ground projects, not on empty grid cells
        const groundOccupied = new Set();
        const bostadOccupied = new Set();
        for (const [pid, pl] of Object.entries(puzzle.placements)) {
            if (pid === dragState.id) continue;
            const shape = puzzle.shapes?.[pid];
            if (shape && isBostad(shape.typ)) {
                for (const [r, c] of pl.cells) bostadOccupied.add(`${r},${c}`);
            } else if (shape) {
                for (const [r, c] of pl.cells) groundOccupied.add(`${r},${c}`);
            }
        }
        return targetCells.every(([r, c]) =>
            r >= 0 && r < 10 && c >= 0 && c < 10 &&
            groundOccupied.has(`${r},${c}`) &&
            !bostadOccupied.has(`${r},${c}`)
        );
    } else {
        // Ground project: no overlap with other ground projects
        const groundOccupied = new Set();
        for (const [pid, pl] of Object.entries(puzzle.placements)) {
            if (pid === dragState.id) continue;
            const shape = puzzle.shapes?.[pid];
            if (shape && !isBostad(shape.typ)) {
                for (const [r, c] of pl.cells) groundOccupied.add(`${r},${c}`);
            }
        }
        return targetCells.every(([r, c]) =>
            r >= 0 && r < 10 && c >= 0 && c < 10 &&
            gridSet.has(`${r},${c}`) &&
            !groundOccupied.has(`${r},${c}`)
        );
    }
}

function onDragEnd(event) {
    document.removeEventListener('pointermove', onDragMove);
    document.removeEventListener('pointerup', onDragEnd);
    document.querySelectorAll('.puzzle-cell.drag-valid, .puzzle-cell.drag-invalid')
        .forEach(el => { el.classList.remove('drag-valid', 'drag-invalid'); });

    if (!dragState) return;

    const pos = getDropRowCol(event);
    if (pos) {
        const cells = dragState.orientations[dragState.orientationIdx];
        const targetCells = cells.map(([r, c]) => [r + pos.row, c + pos.col]);
        const valid = checkPlacementValid(targetCells);

        if (valid) {
            if (dragState.kind === 'mark_expansion') {
                sendAction({
                    action: 'puzzle_place_mark_expansion',
                    piece_id: dragState.id,
                    cells: targetCells,
                });
            } else {
                sendAction({
                    action: 'puzzle_place_project',
                    project_id: dragState.id,
                    cells: targetCells,
                });
            }
        }
    }

    if (dragState.ghostEl) dragState.ghostEl.remove();
    dragState = null;
}

function onKeyDown(e) {
    if (!dragState) return;
    if (e.key === 'r' || e.key === 'R') {
        dragState.orientationIdx = (dragState.orientationIdx + 2) % dragState.orientations.length;
        createGhost(lastPointerPos);
        highlightTarget(lastPointerPos);
    } else if (e.key === 'f' || e.key === 'F') {
        dragState.orientationIdx = (dragState.orientationIdx ^ 1);
        createGhost(lastPointerPos);
        highlightTarget(lastPointerPos);
    }
}

let keyListenerAdded = false;

// ── Grid rendering ──

export function renderPuzzleBoard(gs) {
    const boardEl = document.getElementById('board-container');
    if (!boardEl) return;

    if (!keyListenerAdded) {
        document.addEventListener('keydown', onKeyDown);
        keyListenerAdded = true;
    }

    const puzzle = gs.my_puzzle;
    if (!puzzle) {
        boardEl.innerHTML = '<p>Väntar på pusseldata...</p>';
        return;
    }

    const gridSet = new Set(puzzle.grid_cells.map(([r, c]) => `${r},${c}`));
    const baseSet = new Set();
    for (let r = 2; r <= 5; r++) for (let c = 2; c <= 5; c++) baseSet.add(`${r},${c}`);

    // Build layer maps
    // Layer 1: mark expansion cells (non-base grid cells)
    const markExpCells = new Set();
    for (const [, mp] of Object.entries(puzzle.mark_placements || {})) {
        for (const rc of mp.cells) markExpCells.add(`${rc[0]},${rc[1]}`);
    }

    // Layer 2: ground project cells
    const groundMap = {};  // key -> {pid, typ}
    // Layer 3: bostad cells
    const bostadMap = {};  // key -> {pid, typ}
    for (const [pid, pl] of Object.entries(puzzle.placements)) {
        const shape = puzzle.shapes?.[pid];
        const typ = shape?.typ || '';
        const map = isBostad(typ) ? bostadMap : groundMap;
        for (const [r, c] of pl.cells) {
            map[`${r},${c}`] = { pid, typ };
        }
    }

    let html = '<div class="puzzle-grid">';
    for (let r = 0; r < 10; r++) {
        for (let c = 0; c < 10; c++) {
            const key = `${r},${c}`;
            const inGrid = gridSet.has(key);
            const inBase = baseSet.has(key);
            const inMarkExp = markExpCells.has(key);
            const ground = groundMap[key];
            const bostad = bostadMap[key];

            let cls = 'puzzle-cell';
            let style = '';

            // Top-most visible layer determines appearance
            if (bostad) {
                cls += ' occupied bostad-layer';
                style = `background:${TYPE_COLORS_LIGHT[bostad.typ] || '#666'};`;
            } else if (ground) {
                cls += ' occupied ground-layer';
                style = `background:${TYPE_COLORS_LIGHT[ground.typ] || '#666'};`;
            } else if (inGrid) {
                if (inBase) cls += ' base';
                else if (inMarkExp) cls += ' expansion';
                else cls += ' base';  // should not happen
            } else {
                cls += ' inactive';
            }

            html += `<div class="${cls}" data-row="${r}" data-col="${c}" style="${style}"></div>`;
        }
    }
    html += '</div>';
    boardEl.innerHTML = html;

    // Tap-to-place: add click handlers on grid cells and show preview
    if (selectState) {
        const gridEl = boardEl.querySelector('.puzzle-grid');
        if (gridEl) {
            // Show preview of selected piece shape on hover/focus
            const cells = selectState.orientations[selectState.orientationIdx];
            gridEl.querySelectorAll('.puzzle-cell').forEach(cellEl => {
                const r = parseInt(cellEl.dataset.row);
                const c = parseInt(cellEl.dataset.col);
                cellEl.addEventListener('click', () => tapPlaceAt(r, c));
            });

            // Highlight valid placement area (center of grid as preview)
            const previewRow = 3, previewCol = 3;
            const previewCells = cells.map(([dr, dc]) => [dr + previewRow, dc + previewCol]);
            const valid = checkPlacementValid(previewCells);
            for (const [pr, pc] of previewCells) {
                const el = gridEl.querySelector(`.puzzle-cell[data-row="${pr}"][data-col="${pc}"]`);
                if (el) el.classList.add(valid ? 'drag-valid' : 'drag-invalid');
            }
        }
    }
}

// ── Action panel ──

export function renderPuzzleAction(panel, gs) {
    const puzzle = gs.my_puzzle;
    if (!puzzle) { panel.innerHTML = '<p class="muted">Laddar...</p>'; return; }

    if (puzzle.confirmed) {
        let html = '<div class="puzzle-confirmed-msg">';
        html += '<h3>Kvartersplan bekräftad!</h3>';
        html += `<p>${Object.keys(puzzle.placements).length} projekt placerade.</p>`;
        html += '<p class="muted">Väntar på övriga spelare...</p>';
        html += '</div>';
        if (gs.puzzle_status) {
            html += renderStatusList(gs.puzzle_status);
        }
        panel.innerHTML = html;
        return;
    }

    let html = '<h3>Kvartersplanering</h3>';

    const placedCount = Object.keys(puzzle.placements).length;
    const totalProjects = Object.keys(puzzle.shapes).length;
    const markPieces = puzzle.mark_pieces || [];
    const unplacedMark = markPieces.filter(p => !p.placed);
    const placedMark = markPieces.filter(p => p.placed);

    html += `<div class="puzzle-stats">
        <span>${placedCount}/${totalProjects} projekt</span>
        <span>${placedMark.length}/${markPieces.length} markbitar</span>
    </div>`;

    if (isTouch) {
        html += '<div class="puzzle-hint">Tryck på en bit, rotera/spegla, tryck på rutnätet för att placera.</div>';
    } else {
        html += '<div class="puzzle-hint">Dra bitar till rutnätet. R = rotera, F = spegla.</div>';
    }
    html += `<div class="puzzle-touch-controls">
        <button class="puzzle-touch-btn" id="puzzle-rotate-btn">↻ Rotera</button>
        <button class="puzzle-touch-btn" id="puzzle-flip-btn">↔ Spegla</button>
    </div>`;

    html += '<div class="puzzle-inventory">';

    // ── Mark expansion pieces (unplaced) ──
    if (unplacedMark.length > 0) {
        html += '<div class="puzzle-section-label">Markexpansioner</div>';
        for (const piece of unplacedMark) {
            const isSelected = selectState && selectState.id === piece.id;
            html += `<div class="puzzle-inv-item puzzle-selectable ${isSelected ? 'selected' : ''}" data-mark-id="${piece.id}">
                <div class="puzzle-inv-header" style="background:${MARK_COLOR}">
                    Mark ${piece.cells.length} rutor
                </div>
            </div>`;
        }
    }
    // Placed mark pieces
    if (placedMark.length > 0) {
        for (const piece of placedMark) {
            html += `<div class="puzzle-inv-item placed">
                <div class="puzzle-inv-header" style="background:${MARK_COLOR}">
                    Mark ${piece.cells.length} rutor
                    <button class="puzzle-remove-btn" data-mark-remove="${piece.id}" title="Ta bort">✕</button>
                </div>
            </div>`;
        }
    }

    // ── Ground projects (unplaced) ──
    const shapes = puzzle.shapes || {};
    const placements = puzzle.placements || {};
    const groundProjects = Object.entries(shapes).filter(([, s]) => !isBostad(s.typ));
    const bostadProjects = Object.entries(shapes).filter(([, s]) => isBostad(s.typ));

    const unplacedGround = groundProjects.filter(([pid]) => !placements[pid]);
    const unplacedBostad = bostadProjects.filter(([pid]) => !placements[pid]);

    if (unplacedGround.length > 0) {
        html += '<div class="puzzle-section-label">Markplansprojekt</div>';
        for (const [pid, shape] of unplacedGround) {
            const bg = TYPE_COLORS[shape.typ] || '#555';
            const isSelected = selectState && selectState.id === pid;
            html += `<div class="puzzle-inv-item puzzle-selectable ${isSelected ? 'selected' : ''}" data-pid="${pid}" data-typ="${shape.typ}">
                <div class="puzzle-inv-header" style="background:${bg}">
                    ${shape.namn} <span class="puzzle-inv-cells">${shape.cells.length}</span>
                </div>
            </div>`;
        }
    }

    if (unplacedBostad.length > 0) {
        html += '<div class="puzzle-section-label">Bostäder (byggs ovanpå)</div>';
        for (const [pid, shape] of unplacedBostad) {
            const bg = TYPE_COLORS[shape.typ] || '#555';
            const isSelected = selectState && selectState.id === pid;
            html += `<div class="puzzle-inv-item puzzle-selectable ${isSelected ? 'selected' : ''}" data-pid="${pid}" data-typ="${shape.typ}">
                <div class="puzzle-inv-header" style="background:${bg}">
                    ${shape.namn} <span class="puzzle-inv-cells">${shape.cells.length}</span>
                </div>
            </div>`;
        }
    }

    // ── Placed projects ──
    const placedEntries = Object.entries(placements);
    if (placedEntries.length > 0) {
        html += '<div class="puzzle-section-label">Placerade</div>';
        for (const [pid] of placedEntries) {
            const shape = shapes[pid];
            if (!shape) continue;
            const bg = TYPE_COLORS[shape.typ] || '#555';
            html += `<div class="puzzle-inv-item placed">
                <div class="puzzle-inv-header" style="background:${bg}">
                    ${shape.namn}
                    <button class="puzzle-remove-btn" data-pid="${pid}" title="Ta bort">✕</button>
                </div>
            </div>`;
        }
    }

    html += '</div>';

    // Confirm button
    html += `<button class="btn btn-lg puzzle-confirm-btn" ${placedCount === 0 ? 'disabled' : ''}>
        Klar (${placedCount} projekt)
    </button>`;

    if (gs.puzzle_status) html += renderStatusList(gs.puzzle_status);

    panel.innerHTML = html;

    // ── Interaction handlers ──
    // All selectable items (projects + mark pieces) — tap opens modal, desktop drag
    panel.querySelectorAll('.puzzle-selectable').forEach(el => {
        const pid = el.dataset.pid;
        const markId = el.dataset.markId;
        const id = pid || markId;

        let shapeCells, kind, typ;
        if (pid) {
            const shape = shapes[pid];
            if (!shape) return;
            shapeCells = shape.cells;
            kind = 'project';
            typ = shape.typ;
        } else if (markId) {
            const piece = markPieces.find(p => p.id === markId);
            if (!piece) return;
            shapeCells = piece.cells;
            kind = 'mark_expansion';
            typ = 'mark';
        }
        if (!shapeCells) return;

        el.style.cursor = 'pointer';
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            openPieceModal(id, kind, typ, shapeCells);
        });
    });

    // Remove buttons (projects)
    panel.querySelectorAll('.puzzle-remove-btn[data-pid]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            sendAction({ action: 'puzzle_remove_project', project_id: el.dataset.pid });
        });
    });

    // Remove buttons (mark pieces)
    panel.querySelectorAll('.puzzle-remove-btn[data-mark-remove]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            sendAction({ action: 'puzzle_remove_mark_expansion', piece_id: el.dataset.markRemove });
        });
    });

    // Rotate/flip buttons (work for both tap-select and drag modes)
    const rotateBtn = panel.querySelector('#puzzle-rotate-btn');
    if (rotateBtn) {
        rotateBtn.addEventListener('click', () => {
            const s = selectState || dragState;
            if (!s) return;
            s.orientationIdx = (s.orientationIdx + 2) % s.orientations.length;
            if (dragState) { createGhost(lastPointerPos); highlightTarget(lastPointerPos); }
            if (selectState && state.gameState) { renderPuzzleBoard(state.gameState); }
        });
    }
    const flipBtn = panel.querySelector('#puzzle-flip-btn');
    if (flipBtn) {
        flipBtn.addEventListener('click', () => {
            const s = selectState || dragState;
            if (!s) return;
            s.orientationIdx = (s.orientationIdx ^ 1);
            if (dragState) { createGhost(lastPointerPos); highlightTarget(lastPointerPos); }
            if (selectState && state.gameState) { renderPuzzleBoard(state.gameState); }
        });
    }

    // Confirm button
    const confirmBtn = panel.querySelector('.puzzle-confirm-btn');
    if (confirmBtn && placedCount > 0) {
        confirmBtn.addEventListener('click', () => {
            sendAction({ action: 'puzzle_confirm' });
        });
    }
}

function renderStatusList(statuses) {
    let html = '<div class="puzzle-status-list">';
    for (const ps of statuses) {
        const icon = ps.confirmed ? '✓' : '...';
        html += `<div class="puzzle-status-item ${ps.confirmed ? 'done' : ''}">
            <span>${icon}</span> ${ps.name}: ${ps.placed_count} projekt
        </div>`;
    }
    return html + '</div>';
}

// ── Piece selection modal ──

export function openPieceModal(id, kind, typ, shapeCells) {
    // Close any existing modal
    closePieceModal();

    const orientations = allOrientations(shapeCells);
    let orientationIdx = 0;

    // Carry over orientation if re-opening same piece
    if (selectState && selectState.id === id) {
        orientationIdx = selectState.orientationIdx;
    }

    const color = typ === 'mark'
        ? MARK_COLOR_LIGHT
        : (TYPE_COLORS_LIGHT[typ] || '#777');
    const bg = typ === 'mark'
        ? MARK_COLOR
        : (TYPE_COLORS[typ] || '#555');

    const modal = document.createElement('div');
    modal.id = 'puzzle-piece-modal';
    modal.className = 'puzzle-modal-overlay';

    function renderModalContent() {
        const cells = orientations[orientationIdx];
        modal.innerHTML = `
            <div class="puzzle-modal" style="border-color:${bg}">
                <div class="puzzle-modal-title" style="background:${bg}">
                    ${kind === 'mark_expansion' ? `Mark ${shapeCells.length} rutor` : (state.gameState?.my_puzzle?.shapes?.[id]?.namn || id)}
                </div>
                <div class="puzzle-modal-shape">
                    ${renderMiniShape(cells, color, 24)}
                </div>
                <div class="puzzle-modal-buttons">
                    <button class="puzzle-modal-btn" id="pm-rotate">↻ Rotera</button>
                    <button class="puzzle-modal-btn" id="pm-flip">↔ Spegla</button>
                </div>
                <button class="puzzle-modal-btn puzzle-modal-place" id="pm-place">Placera ▸</button>
                <button class="puzzle-modal-btn puzzle-modal-cancel" id="pm-cancel">Avbryt</button>
            </div>`;

        modal.querySelector('#pm-rotate').addEventListener('click', (e) => {
            e.stopPropagation();
            orientationIdx = (orientationIdx + 2) % orientations.length;
            renderModalContent();
        });
        modal.querySelector('#pm-flip').addEventListener('click', (e) => {
            e.stopPropagation();
            orientationIdx = (orientationIdx ^ 1);
            renderModalContent();
        });
        modal.querySelector('#pm-place').addEventListener('click', (e) => {
            e.stopPropagation();
            // Select piece and close modal — user taps grid to place
            selectState = { id, kind, typ, orientations, orientationIdx };
            closePieceModal();
            if (state.gameState) {
                renderPuzzleBoard(state.gameState);
            }
        });
        modal.querySelector('#pm-cancel').addEventListener('click', (e) => {
            e.stopPropagation();
            closePieceModal();
        });
    }

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closePieceModal();
    });

    document.body.appendChild(modal);
    renderModalContent();
}

function closePieceModal() {
    const existing = document.getElementById('puzzle-piece-modal');
    if (existing) existing.remove();
}


function renderMiniShape(cells, color, cellSize) {
    if (!cells || cells.length === 0) return '';
    const sz = cellSize || 20;
    // Normalize to (0,0) origin
    const minR = Math.min(...cells.map(c => c[0]));
    const minC = Math.min(...cells.map(c => c[1]));
    const norm = cells.map(([r, c]) => [r - minR, c - minC]);
    const maxR = Math.max(...norm.map(c => c[0]));
    const maxC = Math.max(...norm.map(c => c[1]));
    const cellSet = new Set(norm.map(([r, c]) => `${r},${c}`));

    const sizeStyle = sz !== 20 ? `style="grid-template-columns:repeat(${maxC + 1},${sz}px);grid-template-rows:repeat(${maxR + 1},${sz}px)"` :
        `style="grid-template-columns:repeat(${maxC + 1},1fr);grid-template-rows:repeat(${maxR + 1},1fr)"`;
    let html = `<div class="mini-shape" ${sizeStyle}>`;
    for (let r = 0; r <= maxR; r++) {
        for (let c = 0; c <= maxC; c++) {
            const cellStyle = sz !== 20 ? `width:${sz}px;height:${sz}px;min-width:${sz}px;min-height:${sz}px;` : '';
            if (cellSet.has(`${r},${c}`)) {
                html += `<div class="mini-shape-cell" style="background:${color};${cellStyle}"></div>`;
            } else {
                html += `<div class="mini-shape-empty" style="${cellStyle}"></div>`;
            }
        }
    }
    html += '</div>';
    return html;
}

// ── Info panel ──

export function renderPuzzleInfo(gs) {
    const panel = document.getElementById('info-content');
    if (!panel) return;
    const puzzle = gs.my_puzzle;
    if (!puzzle) return;

    let html = '<div class="puzzle-info">';
    html += '<h3>Kvartersplan</h3>';

    const me = gs.players.find(p => p.id === state.playerId);
    if (me) {
        html += `<div class="puzzle-info-stats">
            <div>Projekt: ${me.projects.length}</div>
            <div>BTA: ${me.total_bta} kvm</div>
            <div>Markbitar: ${(puzzle.mark_pieces || []).length}</div>
        </div>`;
    }

    html += '<div class="puzzle-legend">';
    html += '<div class="puzzle-legend-item"><span class="legend-cell base"></span> Bas (4×4)</div>';
    html += '<div class="puzzle-legend-item"><span class="legend-cell expansion"></span> Markexpansion</div>';
    html += '<div class="puzzle-legend-item"><span class="legend-cell ground"></span> Markplansprojekt</div>';
    html += '<div class="puzzle-legend-item"><span class="legend-cell bostad"></span> Bostad (ovanpå)</div>';
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
}
