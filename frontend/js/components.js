/**
 * PMOPOLY - Reusable UI Components
 */

// ── Dice Animation ──
export function showDice(value, die = 'D6') {
    return new Promise(resolve => {
        const overlay = document.getElementById('dice-overlay');
        const diceEl = document.getElementById('dice-value');
        overlay.style.display = 'flex';

        let count = 0;
        const maxCount = 10;
        const interval = setInterval(() => {
            const sides = parseInt(die.replace('D', ''));
            diceEl.textContent = Math.floor(Math.random() * sides) + 1;
            count++;
            if (count >= maxCount) {
                clearInterval(interval);
                diceEl.textContent = value;
                setTimeout(() => {
                    overlay.style.display = 'none';
                    resolve();
                }, 800);
            }
        }, 80);
    });
}

// ── Card Modal (interactive with all outcomes) ──

const D20_RANGES = [
    { key: '1', label: '1', min: 1, max: 1 },
    { key: '2-10', label: '2–10', min: 2, max: 10 },
    { key: '11-15', label: '11–15', min: 11, max: 15 },
    { key: '16-19', label: '16–19', min: 16, max: 19 },
    { key: '20', label: '20', min: 20, max: 20 },
];

function getMatchingRange(d20) {
    return D20_RANGES.find(r => d20 >= r.min && d20 <= r.max);
}

function effectClass(text) {
    if (!text) return 'neutral';
    const t = text.toLowerCase();
    if (t.includes('lämna tillbaka') || t.includes('kvalitetskrav') || t.includes('hållbarhetskrav'))
        return 'bad';
    if (t.includes('riskbuffert') || t === 'ingen effekt')
        return 'good';
    return 'neutral';
}

/**
 * Show card with all outcomes. Player rolls D20 via button.
 * Called when card_drawn event arrives (no result yet).
 */
export function showCard(card, sendAction) {
    const modal = document.getElementById('card-modal');
    const body = document.getElementById('card-modal-body');
    const closeBtn = document.getElementById('card-modal-close');
    closeBtn.style.display = 'none';

    const effects = card.effects || {};
    const outcomesHtml = D20_RANGES.map(r => {
        const eff = effects[r.key] || 'Ingen effekt';
        const cls = effectClass(eff);
        return `<div class="card-outcome-row ${cls}" data-range="${r.key}">
            <span class="cor-range">${r.label}</span>
            <span class="cor-effect">${eff}</span>
        </div>`;
    }).join('');

    body.innerHTML = `
        <h3>${card.rubrik || 'Kort'}</h3>
        <div class="card-type">${card.typ || ''}</div>
        <div class="card-text">${card.text || ''}</div>
        <div class="card-outcomes">${outcomesHtml}</div>
        <div id="card-roll-area">
            <button class="btn btn-warning" id="btn-card-roll-d20" style="font-size:1.3rem;padding:14px 28px;margin-top:8px;width:100%">
                🎲 Slå D20
            </button>
        </div>
    `;

    modal.style.display = 'flex';

    if (sendAction) {
        document.getElementById('btn-card-roll-d20').addEventListener('click', function() {
            sendAction({ action: 'roll_card_d20' });
            this.disabled = true;
            this.textContent = 'Slår...';
        });
    }
}

/**
 * Update card modal after D20 roll result comes in.
 * Highlights matching row, shows result + optional reroll/OK buttons.
 */
export function updateCardResult(d20Result, effect, riskbuffertar, sendAction) {
    const body = document.getElementById('card-modal-body');
    const closeBtn = document.getElementById('card-modal-close');
    if (!body) return;

    // Highlight matching row
    const matchRange = getMatchingRange(d20Result);
    body.querySelectorAll('.card-outcome-row').forEach(row => {
        row.classList.remove('active');
        if (matchRange && row.dataset.range === matchRange.key) {
            row.classList.add('active');
        }
    });

    // Show D20 result
    const rollArea = document.getElementById('card-roll-area');
    if (rollArea) {
        const cls = effectClass(effect);
        const isBad = d20Result <= 10;
        const canReroll = isBad && riskbuffertar > 0;

        rollArea.innerHTML = `
            <div id="card-d20-result">
                <span class="d20-label">D20:</span>
                <span class="d20-value">${d20Result}</span>
                <span class="d20-arrow">→</span>
                <span class="d20-effect ${cls}">${effect}</span>
            </div>
            ${canReroll ? `
                <div class="card-reroll-btns">
                    <button class="btn btn-warning" id="btn-card-reroll">Slå om (Rb: ${riskbuffertar})</button>
                    <button class="btn btn-secondary" id="btn-card-keep">Behåll</button>
                </div>
            ` : ''}
        `;

        if (canReroll) {
            document.getElementById('btn-card-reroll').onclick = () => {
                sendAction({ action: 'use_riskbuffert', value: true });
            };
            document.getElementById('btn-card-keep').onclick = () => {
                sendAction({ action: 'use_riskbuffert', value: false });
            };
        } else {
            // Show OK button
            closeBtn.style.display = '';
            closeBtn.onclick = () => {
                document.getElementById('card-modal').style.display = 'none';
                sendAction({ action: 'continue' });
            };
        }
    }
}

/**
 * Close card modal programmatically.
 */
export function closeCardModal() {
    document.getElementById('card-modal').style.display = 'none';
}

// ── Player Status Bar ──
export function renderPlayerBar(players, currentPlayerId, myPlayerId) {
    const bar = document.getElementById('player-bar');
    if (!bar) return;

    bar.innerHTML = players.map(p => `
        <div class="player-status ${p.id === currentPlayerId ? 'active' : ''}"
             style="border-color: ${p.id === currentPlayerId ? p.color : 'transparent'}">
            <div class="ps-name" style="color:${p.color}">
                ${p.name} ${p.id === myPlayerId ? '(du)' : ''}
            </div>
            <div class="ps-stats">
                <div class="ps-stat">
                    <div class="label">Projekt</div>
                    <div class="value">${p.projects?.length || 0}</div>
                </div>
                <div class="ps-stat">
                    <div class="label">BTA</div>
                    <div class="value">${p.total_bta || 0}</div>
                </div>
                <div class="ps-stat">
                    <div class="label">Rb</div>
                    <div class="value">${p.riskbuffertar || 0}</div>
                </div>
                <div class="ps-stat">
                    <div class="label">Q-krav</div>
                    <div class="value">${p.q_krav}</div>
                </div>
                <div class="ps-stat">
                    <div class="label">H-krav</div>
                    <div class="value">${p.h_krav}</div>
                </div>
                <div class="ps-stat">
                    <div class="label">ABT</div>
                    <div class="value">${p.abt_budget || 0} Mkr</div>
                </div>
            </div>
        </div>
    `).join('');
}

// ══════════════════════════════════════
// Board Rendering
// ══════════════════════════════════════

const SQ_W = 80, SQ_H = 70, STEP = 85;

// ── Phase 1 Board Layout (7×7 perimeter, 24 squares) ──
const BOARD_LAYOUT = [
    // Top row (left→right): 1-7
    { nr: 1, x: 10, y: 10 }, { nr: 2, x: 10+STEP, y: 10 }, { nr: 3, x: 10+STEP*2, y: 10 },
    { nr: 4, x: 10+STEP*3, y: 10 }, { nr: 5, x: 10+STEP*4, y: 10 }, { nr: 6, x: 10+STEP*5, y: 10 },
    { nr: 7, x: 10+STEP*6, y: 10 },
    // Right column (top→bottom): 8-13
    { nr: 8, x: 10+STEP*6, y: 10+STEP }, { nr: 9, x: 10+STEP*6, y: 10+STEP*2 },
    { nr: 10, x: 10+STEP*6, y: 10+STEP*3 }, { nr: 11, x: 10+STEP*6, y: 10+STEP*4 },
    { nr: 12, x: 10+STEP*6, y: 10+STEP*5 }, { nr: 13, x: 10+STEP*6, y: 10+STEP*6 },
    // Bottom row (right→left): 14-19
    { nr: 14, x: 10+STEP*5, y: 10+STEP*6 }, { nr: 15, x: 10+STEP*4, y: 10+STEP*6 },
    { nr: 16, x: 10+STEP*3, y: 10+STEP*6 }, { nr: 17, x: 10+STEP*2, y: 10+STEP*6 },
    { nr: 18, x: 10+STEP, y: 10+STEP*6 }, { nr: 19, x: 10, y: 10+STEP*6 },
    // Left column (bottom→top): 20-24
    { nr: 20, x: 10, y: 10+STEP*5 }, { nr: 21, x: 10, y: 10+STEP*4 },
    { nr: 22, x: 10, y: 10+STEP*3 }, { nr: 23, x: 10, y: 10+STEP*2 },
    { nr: 24, x: 10, y: 10+STEP },
];

// ── Phase 2+3 Board Layout (PL + GF combined, 24 squares) ──
// Path starts bottom-right (Stödfunktioner) going counterclockwise:
// Bottom row R→L (1-7), Left column B→T (8-12), Top row L→R (13-19), Right column T→B (20-24)
// Squares 1-13: PL planning steps
// Square 14: Transition to Genomförande
// Squares 15-22: GF faskort 1-8
// Squares 23-24: Garanti + Slutsammanställning
const PL_GF_LAYOUT = [
    // Bottom row (right→left): 1-7
    { nr: 1, x: 10+STEP*6, y: 10+STEP*6 },  // Stödfunktioner
    { nr: 2, x: 10+STEP*5, y: 10+STEP*6 },  // MARK
    { nr: 3, x: 10+STEP*4, y: 10+STEP*6 },  // HUSUNDERBYGGNAD
    { nr: 4, x: 10+STEP*3, y: 10+STEP*6 },  // Digitalisering
    { nr: 5, x: 10+STEP*2, y: 10+STEP*6 },  // STOMME
    { nr: 6, x: 10+STEP, y: 10+STEP*6 },    // INSTALLATIONER
    { nr: 7, x: 10, y: 10+STEP*6 },          // Operativt team
    // Left column (bottom→top): 8-12
    { nr: 8, x: 10, y: 10+STEP*5 },          // GEMENSAMMA ARBETEN
    { nr: 9, x: 10, y: 10+STEP*4 },          // YTTERTAK
    { nr: 10, x: 10, y: 10+STEP*3 },         // FASADER
    { nr: 11, x: 10, y: 10+STEP*2 },         // Marknadsteam
    { nr: 12, x: 10, y: 10+STEP },           // STOMKOMPLETTERING
    // Top row (left→right): 13-19
    { nr: 13, x: 10, y: 10 },                // INV YTSKIKT
    { nr: 14, x: 10+STEP, y: 10 },           // GENOMFÖRANDE start
    { nr: 15, x: 10+STEP*2, y: 10 },         // Faskort 1
    { nr: 16, x: 10+STEP*3, y: 10 },         // Faskort 2
    { nr: 17, x: 10+STEP*4, y: 10 },         // Faskort 3
    { nr: 18, x: 10+STEP*5, y: 10 },         // Faskort 4
    { nr: 19, x: 10+STEP*6, y: 10 },         // Faskort 5
    // Right column (top→bottom): 20-24
    { nr: 20, x: 10+STEP*6, y: 10+STEP },    // Faskort 6
    { nr: 21, x: 10+STEP*6, y: 10+STEP*2 },  // Faskort 7
    { nr: 22, x: 10+STEP*6, y: 10+STEP*3 },  // Faskort 8
    { nr: 23, x: 10+STEP*6, y: 10+STEP*4 },  // Garantibesiktning
    { nr: 24, x: 10+STEP*6, y: 10+STEP*5 },  // Slutsammanställning
];

// ── Phase 4 Board Layout (24 squares, 6 per quarter) ──
// Path starts bottom-right going counterclockwise, same grid
// Each quarter occupies ~6 squares
const F4_LAYOUT = [
    // Quarter 1: Bottom row R→L (1-6) + corner
    { nr: 1, x: 10+STEP*6, y: 10+STEP*6 },
    { nr: 2, x: 10+STEP*5, y: 10+STEP*6 },
    { nr: 3, x: 10+STEP*4, y: 10+STEP*6 },
    { nr: 4, x: 10+STEP*3, y: 10+STEP*6 },
    { nr: 5, x: 10+STEP*2, y: 10+STEP*6 },
    { nr: 6, x: 10+STEP, y: 10+STEP*6 },
    // Quarter 2: Left column B→T (7-12)
    { nr: 7, x: 10, y: 10+STEP*6 },
    { nr: 8, x: 10, y: 10+STEP*5 },
    { nr: 9, x: 10, y: 10+STEP*4 },
    { nr: 10, x: 10, y: 10+STEP*3 },
    { nr: 11, x: 10, y: 10+STEP*2 },
    { nr: 12, x: 10, y: 10+STEP },
    // Quarter 3: Top row L→R (13-18)
    { nr: 13, x: 10, y: 10 },
    { nr: 14, x: 10+STEP, y: 10 },
    { nr: 15, x: 10+STEP*2, y: 10 },
    { nr: 16, x: 10+STEP*3, y: 10 },
    { nr: 17, x: 10+STEP*4, y: 10 },
    { nr: 18, x: 10+STEP*5, y: 10 },
    // Quarter 4: Right column T→B (19-24)
    { nr: 19, x: 10+STEP*6, y: 10 },
    { nr: 20, x: 10+STEP*6, y: 10+STEP },
    { nr: 21, x: 10+STEP*6, y: 10+STEP*2 },
    { nr: 22, x: 10+STEP*6, y: 10+STEP*3 },
    { nr: 23, x: 10+STEP*6, y: 10+STEP*4 },
    { nr: 24, x: 10+STEP*6, y: 10+STEP*5 },
];

// ── Shared rendering helpers ──

function renderPlayerTokens(players, layout, w, h) {
    const tokenOffsets = [
        { dx: -12, dy: -12 }, { dx: 12, dy: -12 },
        { dx: -12, dy: 12 }, { dx: 12, dy: 12 },
    ];
    let html = '';
    for (let i = 0; i < players.length; i++) {
        const p = players[i];
        const pos = layout.find(l => l.nr === p.position);
        if (!pos) continue;

        const off = tokenOffsets[i] || { dx: 0, dy: 0 };
        const cx = pos.x + w/2 + off.dx;
        const cy = pos.y + h/2 + off.dy;

        html += `
            <circle class="player-token" cx="${cx}" cy="${cy}" r="12"
                    fill="${p.color}" stroke="white" stroke-width="2.5"/>
            <text x="${cx}" y="${cy + 4}" text-anchor="middle"
                  fill="white" font-size="10" font-weight="700">
                ${p.name.charAt(0)}
            </text>
        `;
    }
    return html;
}

function renderTokenAt(player, boardPos, layout, playerIdx) {
    const tokenOffsets = [
        { dx: -12, dy: -12 }, { dx: 12, dy: -12 },
        { dx: -12, dy: 12 }, { dx: 12, dy: 12 },
    ];
    const pos = layout.find(l => l.nr === boardPos);
    if (!pos) return '';

    const off = tokenOffsets[playerIdx] || { dx: 0, dy: 0 };
    const cx = pos.x + SQ_W/2 + off.dx;
    const cy = pos.y + SQ_H/2 + off.dy;

    return `
        <circle class="player-token" cx="${cx}" cy="${cy}" r="12"
                fill="${player.color}" stroke="white" stroke-width="2.5"/>
        <text x="${cx}" y="${cy + 4}" text-anchor="middle"
              fill="white" font-size="10" font-weight="700">
            ${player.name.charAt(0)}
        </text>
    `;
}

function renderCenterPanel(lines, cx, cy, width, height) {
    let html = `
        <rect x="${cx - width/2}" y="${cy - height/2}" width="${width}" height="${height}"
              rx="12" fill="rgba(15,52,96,0.92)" stroke="#f0c929" stroke-width="2"/>`;
    let y = cy - height/2 + 30;
    for (const line of lines) {
        html += `<text x="${cx}" y="${y}" text-anchor="middle"
              fill="${line.color || 'white'}" font-size="${line.size || 13}" font-weight="${line.bold ? '700' : '400'}">
            ${line.text}
        </text>`;
        y += (line.gap || 25);
    }
    return html;
}

function truncate(str, max) {
    return str.length > max ? str.substring(0, max - 1) + '...' : str;
}

// ══════════════════════════════════════
// Phase 1 Board (Projektutveckling)
// ══════════════════════════════════════
export function renderBoard(boardSquares, players) {
    const svg = document.getElementById('game-board');
    if (!svg) return;

    let html = `<image href="/img/boards/phase1.jpg" x="0" y="0" width="610" height="610"
                       preserveAspectRatio="xMidYMid slice" opacity="0.9"/>`;

    html += renderPlayerTokens(players, BOARD_LAYOUT, SQ_W, SQ_H);
    svg.innerHTML = html;
}

// ══════════════════════════════════════
// Phase 2+3 Board (Planering + Genomförande)
// ══════════════════════════════════════

function getPlanGFPosition(gameState, player) {
    const pending = gameState.pending_action || {};
    const subState = gameState.sub_state || '';
    const isCurrentPlayer = player.id === gameState.current_player_id;

    if (isCurrentPlayer && pending.player_id === player.id) {
        // Phase 2: planning steps 1-13 → board positions 1-13
        if (gameState.phase === 'phase2_planering') {
            return pending.step || 1;
        }
        // Phase 3: faskort 1-8 → board positions 15-22, garanti → 23, summary → 24
        if (gameState.phase === 'phase3_genomforande') {
            if (subState.includes('garanti')) return 23;
            if (subState.includes('summary') || subState.includes('forskott')) return 24;
            const fasNr = pending.fas_nr || 0;
            if (fasNr > 0) return 14 + fasNr; // 15-22
            if (subState.includes('buy_support')) return 14;
            return 14;
        }
    }

    // Non-active players: show at step they've completed or start
    if (gameState.phase === 'phase3_genomforande') return 14; // at GF start
    return 1; // at PL start
}

export function renderPlanGFBoard(gameState) {
    const svg = document.getElementById('game-board');
    if (!svg) return;

    // Use phase2.jpg for both PL and GF (combined board)
    let html = `<image href="/img/boards/phase2.jpg" x="0" y="0" width="610" height="610"
                       preserveAspectRatio="xMidYMid slice" opacity="0.9"/>`;

    // Player tokens
    const players = gameState.players || [];
    for (let i = 0; i < players.length; i++) {
        const boardPos = getPlanGFPosition(gameState, players[i]);
        html += renderTokenAt(players[i], boardPos, PL_GF_LAYOUT, i);
    }

    // Center info panel
    const pending = gameState.pending_action || {};
    const subState = gameState.sub_state || '';
    const lines = [];

    if (gameState.phase === 'phase2_planering') {
        const step = pending.step || 0;
        const totalSteps = pending.total_steps || 13;
        lines.push({ text: 'Fas 2: Planering', color: '#f0c929', size: 16, bold: true });
        if (step > 0) {
            lines.push({ text: `Steg ${step}/${totalSteps}`, size: 14 });
            if (pending.slot_name) lines.push({ text: pending.slot_name, size: 13, color: '#3498db' });
        }
    } else {
        // Phase 3
        const faskort = pending.faskort || {};
        const fasNr = pending.fas_nr || '';
        const fasNamn = faskort.namn || '';

        lines.push({ text: 'Fas 3: Genomförande', color: '#f0c929', size: 16, bold: true });

        if (subState.includes('buy_support')) {
            lines.push({ text: 'Köp externt stöd?', size: 14 });
        } else if (subState.includes('faskort') || subState.includes('level') || subState.includes('play')) {
            if (fasNr) lines.push({ text: `Faskort ${fasNr}/8`, size: 15, bold: true });
            if (fasNamn) lines.push({ text: truncate(fasNamn, 30), size: 13 });
            if (subState.includes('play')) lines.push({ text: 'Spela kompetenskort', size: 12, color: '#3498db' });
            else if (subState.includes('level')) lines.push({ text: 'Välj utfallsnivå', size: 12, color: '#3498db' });
        } else if (subState.includes('penalty')) {
            lines.push({ text: 'Konsekvenskort', size: 15, bold: true, color: '#e74c3c' });
        } else if (subState.includes('garanti')) {
            lines.push({ text: 'Garantibesiktning', size: 15, bold: true, color: '#e67e22' });
        } else if (subState.includes('summary') || subState.includes('forskott')) {
            lines.push({ text: 'Genomförande klar!', size: 15, bold: true, color: '#2ecc71' });
        }

        // Requirements
        const reqs = pending.reqs || {};
        const fulfilled = pending.fulfilled || {};
        if (Object.keys(reqs).length > 0) {
            const parts = Object.entries(reqs).map(([k, v]) => {
                const done = fulfilled[k] || 0;
                return `${k}:${done}/${v}`;
            }).join('  ');
            lines.push({ text: parts, size: 12, color: '#aaa' });
        }
    }

    // Current player indicator
    const curPlayer = players.find(p => p.id === gameState.current_player_id);
    if (curPlayer) {
        lines.push({ text: `${curPlayer.name}s tur`, size: 12, color: curPlayer.color, bold: true });
    }

    if (lines.length > 0) {
        html += renderCenterPanel(lines, 305, 305, 320, 30 + lines.length * 25);
    }

    svg.innerHTML = html;
}

// ══════════════════════════════════════
// Phase 4 Board (Förvaltning)
// ══════════════════════════════════════

// Map F4 sub_state to step within quarter (1-6)
function getF4StepInQuarter(subState) {
    if (subState.includes('world_event') || subState.includes('hire')) return 1;
    if (subState.includes('rent')) return 2;
    if (subState.includes('mgmt')) return 3;
    if (subState.includes('energy')) return 4;
    if (subState.includes('market')) return 5;
    if (subState.includes('rehire') || subState.includes('final')) return 6;
    return 1;
}

function getF4Position(gameState) {
    const quarter = gameState.f4_quarter || 1;
    const subState = gameState.sub_state || '';
    const stepInQ = getF4StepInQuarter(subState);
    return (quarter - 1) * 6 + stepInQ;
}

export function renderPhase4Board(gameState) {
    const svg = document.getElementById('game-board');
    if (!svg) return;

    let html = `<image href="/img/boards/phase4.jpg" x="0" y="0" width="610" height="610"
                       preserveAspectRatio="xMidYMid slice" opacity="0.9"/>`;

    // Player tokens
    const players = gameState.players || [];
    const boardPos = getF4Position(gameState);
    const curPlayerId = gameState.current_player_id;

    for (let i = 0; i < players.length; i++) {
        // Show current player at active position, others nearby
        const pos = players[i].id === curPlayerId ? boardPos : Math.max(1, boardPos - 1);
        html += renderTokenAt(players[i], pos, F4_LAYOUT, i);
    }

    // Center info panel
    const pending = gameState.pending_action || {};
    const subState = gameState.sub_state || '';
    const quarter = gameState.f4_quarter || pending.quarter || 1;

    const lines = [];
    lines.push({ text: 'Fas 4: Förvaltning', color: '#f0c929', size: 16, bold: true });
    lines.push({ text: `Kvartal ${quarter}/4`, size: 15, bold: true });

    if (subState.includes('hire')) lines.push({ text: 'Anställ personal', size: 13, color: '#27ae60' });
    else if (subState.includes('rent')) lines.push({ text: 'Hyresförhandling', size: 13, color: '#f39c12' });
    else if (subState.includes('mgmt')) lines.push({ text: 'Händelsekort', size: 13, color: '#c0392b' });
    else if (subState.includes('energy')) lines.push({ text: 'Energiuppgradering', size: 13, color: '#16a085' });
    else if (subState.includes('market')) lines.push({ text: 'Fastighetsmarknad', size: 13, color: '#d35400' });
    else if (subState.includes('final')) lines.push({ text: 'Slutvärdering', size: 13, color: '#2ecc71' });
    else if (pending.message) lines.push({ text: truncate(pending.message, 28), size: 12 });

    const curPlayer = players.find(p => p.id === curPlayerId);
    if (curPlayer) {
        lines.push({ text: `${curPlayer.name}s tur`, size: 12, color: curPlayer.color, bold: true });
        const ek = curPlayer.eget_kapital || 0;
        const props = (curPlayer.fastigheter || curPlayer.projects || []).length;
        lines.push({ text: `EK: ${ek} Mkr | Fastigheter: ${props}`, size: 11, color: '#aaa' });
    }

    html += renderCenterPanel(lines, 305, 305, 300, 30 + lines.length * 25);
    svg.innerHTML = html;
}


// ── Instruction System ──

import { INSTRUCTIONS } from './instructions.js';

const _shownInstructions = new Set();

const LEVEL_CYCLE = ['all', 'rules', 'none'];
const LEVEL_LABELS = { all: '\u{1F4D6} Tips + Regler', rules: '\u{1F4CB} Regler', none: '\u{1F507} Av' };

export function getInstructionLevel() {
    return localStorage.getItem('pmopoly_instructions') || 'rules';
}

export function cycleInstructionLevel() {
    const current = getInstructionLevel();
    const idx = LEVEL_CYCLE.indexOf(current);
    const next = LEVEL_CYCLE[(idx + 1) % LEVEL_CYCLE.length];
    localStorage.setItem('pmopoly_instructions', next);
    return next;
}

export function getInstructionLabel(level) {
    return LEVEL_LABELS[level] || LEVEL_LABELS.rules;
}

export function showInstruction(key) {
    const level = getInstructionLevel();
    if (level === 'none') return;
    if (_shownInstructions.has(key)) return;

    const data = INSTRUCTIONS[key];
    if (!data) return;

    _shownInstructions.add(key);

    const modal = document.getElementById('instruction-modal');
    const title = document.getElementById('instr-title');
    const body = document.getElementById('instr-body');
    if (!modal || !title || !body) return;

    title.textContent = data.title;

    let html = '';
    if (data.rules) {
        html += `<div class="instr-rules">${_nl2p(data.rules)}</div>`;
    }
    if (level === 'all' && data.strategy) {
        html += `<div class="instr-strategy"><strong>Strategitips:</strong> ${data.strategy}</div>`;
    }
    body.innerHTML = html;
    modal.style.display = 'flex';

    const closeBtn = document.getElementById('instr-close');
    const handler = () => {
        modal.style.display = 'none';
        closeBtn.removeEventListener('click', handler);
    };
    closeBtn.addEventListener('click', handler);
}

function _nl2p(text) {
    return text.split('\n\n').map(p =>
        `<p>${p.replace(/\n/g, '<br>')}</p>`
    ).join('');
}


// ── Preview Modal ──

export function showPreview(html, onConfirm) {
    const modal = document.getElementById('preview-modal');
    if (!modal) return;
    document.getElementById('preview-body').innerHTML = html;
    modal.style.display = 'flex';

    const confirmBtn = document.getElementById('preview-confirm');
    const cancelBtn = document.getElementById('preview-cancel');
    const close = () => { modal.style.display = 'none'; };

    confirmBtn.onclick = () => { close(); onConfirm(); };
    cancelBtn.onclick = close;
}

function _projImgUrl(namn) {
    return `/img/projects/${encodeURIComponent(namn)}.jpg`;
}

function _sign(v) { return v >= 0 ? `+${v}` : `${v}`; }

export function previewProject(opt) {
    const p = opt.top || opt;
    const imgUrl = _projImgUrl(p.namn);
    return `
        <div class="detail-project-header">
            <img class="detail-project-img" src="${imgUrl}" alt="${p.namn}" onerror="this.style.display='none'">
            <div>
                <h3>${p.namn}</h3>
                <div class="card-type">${p.typ}</div>
            </div>
        </div>
        <div class="detail-grid">
            <div class="detail-row"><span>BTA</span><span>${p.bta} kvm</span></div>
            <div class="detail-row"><span>Formfaktor</span><span>${p.formfaktor}</span></div>
            <div class="detail-row"><span>Kostnad</span><span>${p.kostnad} Mkr</span></div>
            <div class="detail-row"><span>Anskaffning</span><span>${p.anskaffning} Mkr</span></div>
            <div class="detail-row"><span>Kvalitet (Q)</span><span>${p.kvalitet}</span></div>
            <div class="detail-row"><span>Hållbarhet (H)</span><span>${p.hallbarhet}</span></div>
            <div class="detail-row"><span>Tid (T)</span><span>${p.tid} mån</span></div>
            <div class="detail-row"><span>Nämndbeslut</span><span>≥${p.namndbeslut}</span></div>
        </div>
    `;
}

export function previewSupplier(opt) {
    const kompStr = Object.entries(opt.kompetenser || {}).filter(([,v]) => v > 0).map(([k,v]) => `${k}: ${v}`).join(', ');
    return `
        <h3>Leverantör — Nivå ${opt.niva}</h3>
        ${opt.beskrivning ? `<p style="color:var(--text-muted);margin-bottom:12px">${opt.beskrivning}</p>` : ''}
        <div class="detail-grid">
            ${opt.kostnad != null ? `<div class="detail-row"><span>Kostnad</span><span>${opt.kostnad} Mkr</span></div>` : ''}
            <div class="detail-row"><span>Kvalitet</span><span>${_sign(opt.q)}</span></div>
            <div class="detail-row"><span>Hållbarhet</span><span>${_sign(opt.h)}</span></div>
            <div class="detail-row"><span>Tid</span><span>${_sign(opt.t)} mån</span></div>
            <div class="detail-row"><span>Erfarenhet</span><span>${_sign(opt.erfarenhet)}</span></div>
            ${kompStr ? `<div class="detail-row"><span>Kompetenser</span><span>${kompStr}</span></div>` : ''}
        </div>
    `;
}

export function previewOrg(opt) {
    const kompStr = Object.entries(opt.kompetenser || {}).filter(([,v]) => v > 0).map(([k,v]) => `${k}: ${v}`).join(', ');
    return `
        <h3>Organisation — Nivå ${opt.niva}</h3>
        <div class="detail-grid">
            <div class="detail-row"><span>Kostnad</span><span>${opt.kostnad_mkr} Mkr</span></div>
            <div class="detail-row"><span>Kvalitet</span><span>${_sign(opt.q)}</span></div>
            <div class="detail-row"><span>Hållbarhet</span><span>${_sign(opt.h)}</span></div>
            <div class="detail-row"><span>Tid</span><span>${_sign(opt.t)} mån</span></div>
            <div class="detail-row"><span>Erfarenhet</span><span>${_sign(opt.erfarenhet)}</span></div>
            ${opt.riskbuffert ? `<div class="detail-row"><span>Riskbuffert</span><span>+${opt.riskbuffert}</span></div>` : ''}
            ${kompStr ? `<div class="detail-row"><span>Kompetenser</span><span>${kompStr}</span></div>` : ''}
        </div>
    `;
}

export function previewStaff(s) {
    return `
        <h3>${s.namn}</h3>
        <div class="card-type">${s.roll} — ${s.specialisering || ''}</div>
        <div class="detail-grid">
            <div class="detail-row"><span>Kapacitet</span><span>${s.kapacitet} fastigheter</span></div>
            <div class="detail-row"><span>Lön</span><span>${s.lon} Mkr/kvartal</span></div>
            <div class="detail-row"><span>Förhandling</span><span>${s.forhandling ? 'D' + s.forhandling : '—'}</span></div>
        </div>
    `;
}

export function previewMarketBuy(b) {
    return `
        <h3>${b.namn}</h3>
        <div class="card-type">${b.typ}</div>
        <div class="detail-grid">
            <div class="detail-row"><span>BTA</span><span>${b.bta} kvm</span></div>
            <div class="detail-row"><span>Driftnetto</span><span>${b.driftnetto} Mkr/kv</span></div>
            <div class="detail-row"><span>Energiklass</span><span>${b.ek}</span></div>
            <div class="detail-row"><span>Fastighetsvärde</span><span>${b.fv} Mkr</span></div>
            <div class="detail-row"><span>Pris (30%)</span><span>${b.cost_30} Mkr</span></div>
        </div>
    `;
}
