/**
 * PMOPOLY - Game view controller
 */
import { state, sendAction, addEventLog } from './app.js';
import { renderBoard, renderPlanGFBoard, renderPhase4Board, renderPlayerBar, showDice, showCard, updateCardResult, closeCardModal, showInstruction, cycleInstructionLevel, getInstructionLevel, getInstructionLabel } from './components.js';
import { renderPhase1Action } from './phase1.js';
import { renderPhase2Action } from './phase2.js';
import { renderPhase3Action } from './phase3.js';
import { renderPhase4Action } from './phase4.js';
import { renderPuzzleBoard, renderPuzzleAction, renderPuzzleInfo } from './puzzle.js';

// Board square definitions (must match backend config.py)
const BOARD_SQUARES = [
    { nr: 1, typ: "start", namn: "Stadsbyggnads-kontoret" },
    { nr: 2, typ: "projekt", namn: "Förskola", projekt_typer: ["FÖRSKOLOR"] },
    { nr: 3, typ: "projekt", namn: "Hyresrätt", projekt_typer: ["Hyresrätt"] },
    { nr: 4, typ: "kort", namn: "Dialog", kort_typ: "dialog" },
    { nr: 5, typ: "projekt", namn: "BRF", projekt_typer: ["BRF"] },
    { nr: 6, typ: "stjarna", namn: "Stjärna" },
    { nr: 7, typ: "stadshuset", namn: "Stadshuset" },
    { nr: 8, typ: "projekt", namn: "Lokal", projekt_typer: ["LOKAL"] },
    { nr: 9, typ: "kort", namn: "Politik", kort_typ: "politik" },
    { nr: 10, typ: "projekt", namn: "BRF + Kontor", projekt_typer: ["BRF", "KONTOR"] },
    { nr: 11, typ: "projekt", namn: "Kontor", projekt_typer: ["KONTOR"] },
    { nr: 12, typ: "stjarna", namn: "Stjärna" },
    { nr: 13, typ: "kort", namn: "Dialog", kort_typ: "dialog" },
    { nr: 14, typ: "projekt", namn: "Lokal + Hyresrätt", projekt_typer: ["LOKAL", "Hyresrätt"] },
    { nr: 15, typ: "lansstyrelsen", namn: "Länsstyrelsen" },
    { nr: 16, typ: "projekt", namn: "Förskola", projekt_typer: ["FÖRSKOLOR"] },
    { nr: 17, typ: "kort", namn: "Politik", kort_typ: "politik" },
    { nr: 18, typ: "projekt", namn: "Lokal + Förskola", projekt_typer: ["LOKAL", "FÖRSKOLOR"] },
    { nr: 19, typ: "skonhetsradet", namn: "Skönhetsrådet" },
    { nr: 20, typ: "stjarna", namn: "Stjärna" },
    { nr: 21, typ: "kort", namn: "Dialog", kort_typ: "dialog" },
    { nr: 22, typ: "projekt", namn: "Hyresrätt", projekt_typer: ["Hyresrätt"] },
    { nr: 23, typ: "kort", namn: "Politik", kort_typ: "politik" },
    { nr: 24, typ: "projekt", namn: "BRF", projekt_typer: ["BRF"] },
];

let _lastPhase = null;

export function initGame() {
    _lastPhase = null;
}

export function handleGameState(gs) {
    state.gameState = gs;
    window._lastGameState = gs;

    // Update phase indicator
    updatePhaseIndicator(gs);

    // Trigger instructions on phase change
    if (gs.phase !== _lastPhase) {
        _lastPhase = gs.phase;
        showInstruction(gs.phase);
    }

    // Render board - each phase gets its own board
    const boardEl = document.getElementById('board-container');
    const phase1Phases = ['phase1_mark_tomt', 'phase1_board', 'phase1_namndbeslut',
                          'phase1_placement', 'phase1_ekonomi'];
    if (phase1Phases.includes(gs.phase)) {
        renderBoard(BOARD_SQUARES, gs.players);
        if (boardEl) boardEl.style.display = '';
    } else if (gs.phase === 'puzzle_placement') {
        renderPuzzleBoard(gs);
        if (boardEl) boardEl.style.display = '';
    } else if (gs.phase === 'phase2_planering' || gs.phase === 'phase3_genomforande') {
        renderPlanGFBoard(gs);
        if (boardEl) boardEl.style.display = '';
    } else if (gs.phase === 'phase4_forvaltning') {
        renderPhase4Board(gs);
        if (boardEl) boardEl.style.display = '';
    } else {
        if (boardEl) boardEl.style.display = 'none';
    }

    // Update player bar
    renderPlayerBar(gs.players, gs.current_player_id, state.playerId);

    // Update assets panel
    renderAssetsPanel(gs);

    // Update turn indicator
    const turnEl = document.getElementById('turn-indicator');
    if (gs.phase === 'puzzle_placement') {
        turnEl.textContent = 'Alla placerar samtidigt';
        turnEl.style.background = 'var(--primary)';
        turnEl.style.color = '#fff';
    } else {
        const currentPlayer = gs.players.find(p => p.id === gs.current_player_id);
        if (currentPlayer) {
            const isMyTurn = gs.current_player_id === state.playerId;
            turnEl.textContent = isMyTurn ? 'Din tur!' : `${currentPlayer.name}s tur`;
            turnEl.style.background = isMyTurn ? 'var(--primary)' : 'var(--bg)';
            turnEl.style.color = isMyTurn ? '#fff' : 'var(--text-muted)';
        }
    }

    // Render info panel (left: zoomed square view)
    renderInfoPanel(gs);

    // Render action panel
    renderActionPanel(gs);
}

export function handleEvents(events) {
    for (const event of events) {
        const text = event.text || event.message || JSON.stringify(event);
        let icon = '';
        switch (event.type) {
            case 'dice_result': icon = '🎲'; break;
            case 'card_drawn': icon = '🃏'; break;
            case 'project_acquired': icon = '🏗️'; break;
            case 'riskbuffert': icon = '⭐'; break;
            case 'lap_complete': icon = '🔄'; break;
            case 'expansion': icon = '📐'; break;
            case 'namndbeslut': icon = event.passed ? '✅' : '❌'; break;
            case 'phase_change': icon = '📢'; break;
            case 'economics': icon = '💰'; break;
            case 'supplier_chosen': icon = '🔧'; break;
            case 'org_chosen': icon = '👥'; break;
            case 'planning_event': icon = '📋'; break;
            case 'planning_event_skip': icon = '⏭️'; break;
            case 'planning_reroll': icon = '🔄'; break;
            case 'planning_complete': icon = '✅'; break;
            case 'external_support_bought': icon = '🎭'; break;
            case 'faskort_resolved': icon = '📊'; break;
            case 'competence_card_played': icon = '🃏'; break;
            case 'penalty_applied': icon = '⚠️'; break;
            case 'penalty_reroll': icon = '🔄'; break;
            case 'garanti_applied': icon = '🔍'; break;
            case 'gf_summary': icon = '📈'; break;
            default: icon = '▸';
        }
        addEventLog(text, icon);

        // Show dice animation for dice results
        if (event.type === 'dice_result') {
            showDice(event.result, event.die);
        }

        // Show card modal (all outcomes, no result yet)
        if (event.type === 'card_drawn' && event.card) {
            showInstruction('first_card');
            showCard(event.card, sendAction);
        }

        // Update card modal with D20 result (after player rolls or rerolls)
        if (event.type === 'card_result' && event.d20_result) {
            const pending = window._lastGameState?.pending_action || {};
            const rb = pending.riskbuffertar || 0;
            updateCardResult(event.d20_result, event.effect, rb, sendAction);
        }
    }
}

function updatePhaseIndicator(gs) {
    const phaseEl = document.getElementById('phase-name');
    const subEl = document.getElementById('phase-sub');

    const phaseNames = {
        'phase1_mark_tomt': 'Fas 1: Mark & Tomt',
        'phase1_board': 'Fas 1: Brädspel',
        'phase1_namndbeslut': 'Fas 1: Nämndbeslut',
        'phase1_placement': 'Fas 1: Placering',
        'phase1_ekonomi': 'Fas 1: Ekonomi',
        'phase2_planering': 'Fas 2: Planering',
        'puzzle_placement': 'Kvartersplanering',
        'phase3_genomforande': 'Fas 3: Genomförande',
        'phase4_forvaltning': 'Fas 4: Förvaltning',
        'finished': 'Spelet är slut!',
    };

    // Use a span for phase text so toggle button isn't destroyed
    let phaseText = phaseEl.querySelector('.phase-text');
    if (!phaseText) {
        phaseEl.textContent = '';
        phaseText = document.createElement('span');
        phaseText.className = 'phase-text';
        phaseEl.appendChild(phaseText);
    }
    phaseText.textContent = phaseNames[gs.phase] || gs.phase;
    subEl.textContent = gs.sub_state || '';

    // Instruction toggle button
    let toggleBtn = document.getElementById('instruction-toggle');
    if (!toggleBtn) {
        toggleBtn = document.createElement('button');
        toggleBtn.id = 'instruction-toggle';
        toggleBtn.className = 'instruction-toggle';
        toggleBtn.addEventListener('click', () => {
            const newLevel = cycleInstructionLevel();
            toggleBtn.textContent = getInstructionLabel(newLevel);
        });
        phaseEl.appendChild(toggleBtn);
    }
    toggleBtn.textContent = getInstructionLabel(getInstructionLevel());
}

function renderInfoPanel(gs) {
    const panel = document.getElementById('info-content');
    if (!panel) return;

    const me = gs.players.find(p => p.id === state.playerId);
    const currentPlayer = gs.players.find(p => p.id === gs.current_player_id);
    const pending = gs.pending_action || {};
    let html = '';

    const phase1Phases = ['phase1_mark_tomt', 'phase1_board', 'phase1_namndbeslut',
                          'phase1_placement', 'phase1_ekonomi'];

    if (phase1Phases.includes(gs.phase)) {
        // Show current square info
        const pos = currentPlayer?.position || 1;
        const sq = BOARD_SQUARES.find(s => s.nr === pos);
        if (sq) {
            const sqColors = {
                'start': '#2980b9', 'projekt': '#27ae60', 'kort': '#8e44ad',
                'stjarna': '#f0c929', 'stadshuset': '#c0392b', 'lansstyrelsen': '#e67e22',
                'skonhetsradet': '#16a085'
            };
            const sqIcons = {
                'start': '🏛️', 'projekt': '🏗️', 'kort': '🃏',
                'stjarna': '⭐', 'stadshuset': '🏰', 'lansstyrelsen': '⚖️',
                'skonhetsradet': '🎨'
            };
            const sqDescriptions = {
                'start': 'Stadsbyggnadskontoret — startposition.',
                'projekt': `Här kan du förvärva ett projekt av typ: ${sq.projekt_typer?.join(', ') || ''}`,
                'kort': `${sq.namn}kort — Dra ett kort och slå D20.`,
                'stjarna': '+1 Riskbuffert!',
                'stadshuset': 'Stadshuset — Möjlighet att utöka tomtmark.',
                'lansstyrelsen': 'Länsstyrelsen — Minskar H-krav med 2.',
                'skonhetsradet': 'Skönhetsrådet — Minskar Q-krav med 2.',
            };

            html += `
                <div class="info-square" style="border-color:${sqColors[sq.typ] || '#555'}">
                    <div class="info-sq-icon">${sqIcons[sq.typ] || '▪'}</div>
                    <div class="info-sq-name">Ruta ${sq.nr}: ${sq.namn}</div>
                    <div class="info-sq-type">${sq.typ.toUpperCase()}</div>
                    <div class="info-sq-desc">${sqDescriptions[sq.typ] || ''}</div>
                </div>
            `;
        }

        // Show player stats summary
        if (me) {
            html += `
                <div class="info-stats">
                    <div class="info-stat-row"><span>Position</span><span>Ruta ${me.position}/24</span></div>
                    <div class="info-stat-row"><span>Varv</span><span>${me.laps || 0}</span></div>
                    <div class="info-stat-row"><span>Projekt</span><span>${me.projects?.length || 0}</span></div>
                    <div class="info-stat-row"><span>BTA</span><span>${me.total_bta || 0} kvm</span></div>
                    <div class="info-stat-row"><span>Riskbuffertar</span><span>${me.riskbuffertar || 0}</span></div>
                    <div class="info-stat-row"><span>Q-krav</span><span>${me.q_krav}</span></div>
                    <div class="info-stat-row"><span>H-krav</span><span>${me.h_krav}</span></div>
                </div>
            `;
        }
    } else if (gs.phase === 'puzzle_placement') {
        renderPuzzleInfo(gs);
        return;
    } else if (gs.phase === 'phase2_planering') {
        const step = pending.step || 0;
        const totalSteps = pending.total_steps || 13;
        html += `
            <div class="info-square" style="border-color:#3498db">
                <div class="info-sq-icon">📋</div>
                <div class="info-sq-name">Planering</div>
                <div class="info-sq-type">Steg ${step}/${totalSteps}</div>
                ${pending.slot_name ? `<div class="info-sq-desc">${pending.slot_name}</div>` : ''}
            </div>
        `;
        if (me) {
            html += `
                <div class="info-stats">
                    <div class="info-stat-row"><span>Kvalitet</span><span>${me.pl_q}/${me.q_krav}</span></div>
                    <div class="info-stat-row"><span>Hållbarhet</span><span>${me.pl_h}/${me.h_krav}</span></div>
                    <div class="info-stat-row"><span>Tid</span><span>${me.pl_t} mån</span></div>
                    <div class="info-stat-row"><span>ABT</span><span>${me.abt_budget} Mkr</span></div>
                    <div class="info-stat-row"><span>Riskbuffertar</span><span>${me.riskbuffertar}</span></div>
                    <div class="info-stat-row"><span>Erfarenhet</span><span>${me.total_erfarenhet}</span></div>
                </div>
            `;
        }
    } else if (gs.phase === 'phase3_genomforande') {
        const fasNr = pending.fas_nr || '';
        const faskort = pending.faskort || {};
        const subState = gs.sub_state || '';
        html += `
            <div class="info-square" style="border-color:#e67e22">
                <div class="info-sq-icon">⚙️</div>
                <div class="info-sq-name">Genomförande</div>
                ${fasNr ? `<div class="info-sq-type">Faskort ${fasNr}/8</div>` : ''}
                ${faskort.namn ? `<div class="info-sq-desc">${faskort.namn}</div>` : ''}
            </div>
        `;
        if (me) {
            html += `
                <div class="info-stats">
                    <div class="info-stat-row"><span>Kvalitet</span><span>${me.pl_q}/${me.q_krav}</span></div>
                    <div class="info-stat-row"><span>Hållbarhet</span><span>${me.pl_h}/${me.h_krav}</span></div>
                    <div class="info-stat-row"><span>Tid</span><span>${me.pl_t} mån</span></div>
                    <div class="info-stat-row"><span>ABT</span><span>${me.abt_budget} Mkr</span></div>
                    <div class="info-stat-row"><span>EK</span><span>${me.eget_kapital} Mkr</span></div>
                </div>
            `;
        }
    } else if (gs.phase === 'phase4_forvaltning') {
        const quarter = gs.f4_quarter || pending.quarter || 1;
        const subState = gs.sub_state || '';
        html += `
            <div class="info-square" style="border-color:#f0c929">
                <div class="info-sq-icon">🏢</div>
                <div class="info-sq-name">Förvaltning</div>
                <div class="info-sq-type">Kvartal ${quarter}/4</div>
            </div>
        `;
        if (me) {
            const props = (me.fastigheter || me.projects || []).length;
            html += `
                <div class="info-stats">
                    <div class="info-stat-row"><span>EK</span><span>${me.eget_kapital} Mkr</span></div>
                    <div class="info-stat-row"><span>Fastigheter</span><span>${props}</span></div>
                    <div class="info-stat-row"><span>Personal</span><span>${(me.staff || []).length}</span></div>
                    ${me.abt_loans_net > 0 ? `<div class="info-stat-row"><span>Lån</span><span>${me.abt_loans_net} Mkr</span></div>` : ''}
                </div>
            `;
        }
    } else {
        html = '<p class="muted">Väntar på fas...</p>';
    }

    panel.innerHTML = html;
}

function renderActionPanel(gs) {
    const panel = document.getElementById('action-content');
    const pending = gs.pending_action;
    const isMyTurn = pending && pending.player_id === state.playerId;

    if (gs.phase === 'finished') {
        renderFinished(panel, gs);
        return;
    }

    if (gs.phase === 'puzzle_placement') {
        renderPuzzleAction(panel, gs);
        return;
    }

    if (!pending) {
        panel.innerHTML = '<p class="muted">Väntar...</p>';
        return;
    }

    if (!isMyTurn) {
        const who = gs.players.find(p => p.id === pending.player_id);
        panel.innerHTML = `<p class="muted">Väntar på ${who?.name || 'spelare'}...</p>`;
        return;
    }

    // Route to phase-specific renderer
    if (gs.phase.startsWith('phase3')) {
        renderPhase3Action(panel, gs, pending);
    } else if (gs.phase.startsWith('phase2')) {
        renderPhase2Action(panel, gs, pending);
    } else if (gs.phase.startsWith('phase4')) {
        renderPhase4Action(panel, gs, pending);
    } else {
        renderPhase1Action(panel, gs, pending);
    }
}

function renderFinished(panel, gs) {
    let html = '<h3>🏆 Spelet är slut!</h3>';
    html += '<div class="f4-results">';

    const sorted = [...gs.players].sort((a, b) =>
        (b.f4_score_per_bta || 0) - (a.f4_score_per_bta || 0));

    // Header
    html += `<div class="f4-result-header">
        <span>Poäng per 1000 BTA = (FV×30% + EK + TB) / (BTA/1000)</span>
    </div>`;

    sorted.forEach((p, i) => {
        const medal = ['🥇', '🥈', '🥉'][i] || `${i + 1}.`;
        const hasScores = p.f4_score !== undefined && p.f4_score !== 0;
        html += `
            <div class="f4-result-row ${i === 0 ? 'winner' : ''}">
                <div class="f4-result-place">${medal}</div>
                <div class="f4-result-info">
                    <div class="f4-result-name">${p.name}</div>
                    ${hasScores ? `
                    <div class="f4-result-details">
                        FV×30%: ${p.f4_fv_30} |
                        EK: ${p.f4_real_ek} |
                        TB: ${p.f4_tb}
                    </div>
                    <div class="f4-result-props">
                        Fastigheter: ${(p.fastigheter || []).length} |
                        BTA: ${p.total_bta || 0} kvm
                    </div>
                    ` : `
                    <div class="f4-result-details">
                        ABT: ${p.abt_budget} Mkr | EK: ${p.eget_kapital} Mkr
                    </div>
                    `}
                </div>
                <div class="f4-result-score">
                    ${hasScores
                        ? `${p.f4_score_per_bta} Mkr/kBTA<br><span class="f4-score-raw">(${p.f4_score} Mkr)</span>`
                        : `${(p.abt_budget + p.eget_kapital).toFixed(1)} Mkr`}
                </div>
            </div>
        `;
    });

    html += '</div>';
    panel.innerHTML = html;
}

function renderAssetsPanel(gs) {
    const panel = document.getElementById('assets-content');
    if (!panel) return;

    const me = gs.players.find(p => p.id === state.playerId);
    if (!me) return;

    let html = '';
    const TYPE_COLORS = {
        'BRF': '#1A4D24', 'Hyresrätt': '#4D1A1A', 'FÖRSKOLOR': '#0F3D5C',
        'LOKAL': '#7A4A10', 'KONTOR': '#321F50'
    };

    // ── Project cards ──
    const projects = me.projects || [];
    projects.forEach(p => {
        const bg = TYPE_COLORS[p.typ] || '#555';
        const ek = me.projekt_energiklass?.[p.namn] || p.energiklass || '';
        const imgUrl = projectImgUrl(p.typ, p.namn);
        html += `<div class="asset-card asset-project clickable" style="background-color:${bg}" data-detail="project" data-idx="${p.namn}">
            <img class="ac-img" src="${imgUrl}" alt="" onerror="this.style.display='none'">
            <div class="ac-overlay">
                <div class="ac-name">${truncName(p.namn, 14)}</div>
                <div class="ac-stats">BTA:${p.bta}${ek ? ' EK:'+ek : ''}</div>
            </div>
        </div>`;
    });

    // ── Moderbolagslån card ──
    const loanNet = me.abt_loans_net || 0;
    if (loanNet > 0) {
        const loanFee = me.abt_borrowing_cost || 0;
        const nLoans = Math.ceil(loanNet / 95);
        html += `<div class="asset-card clickable" style="background:#7f1d1d" data-detail="loan">
            <div class="ac-name">Lån</div>
            <div class="ac-type">${nLoans}x100</div>
            <div class="ac-stats">${loanNet} Mkr</div>
        </div>`;
    }

    // ── Suppliers (only during Phase 2 and 3) ──
    const showSuppliers = gs.phase === 'phase2_planering' || gs.phase === 'phase3_genomforande';
    if (showSuppliers) {
        const suppliers = me.pl_suppliers || {};
        for (const [namn, s] of Object.entries(suppliers)) {
            html += `<div class="asset-card clickable" style="background:#1a5276" data-detail="supplier" data-idx="${namn}">
                <div class="ac-name">${truncName(namn, 12)}</div>
                <div class="ac-type">Lev ${s.niva}</div>
                <div class="ac-stats">${s.kostnad || ''} Mkr</div>
            </div>`;
        }

        // ── Organisations ──
        const orgs = me.pl_orgs || {};
        for (const [namn, o] of Object.entries(orgs)) {
            html += `<div class="asset-card clickable" style="background:#1e4d2b" data-detail="org" data-idx="${namn}">
                <div class="ac-name">${truncName(namn, 12)}</div>
                <div class="ac-type">Org ${o.niva}</div>
                <div class="ac-stats">${o.kostnad_mkr || ''} Mkr</div>
            </div>`;
        }
    }

    // ── Staff (Phase 4) ──
    const staff = me.staff || [];
    staff.forEach(s => {
        html += `<div class="asset-card clickable" style="background:#2c3e50" data-detail="staff" data-idx="${s.namn}">
            <div class="ac-name">${truncName(s.namn, 12)}</div>
            <div class="ac-type">${s.roll}</div>
            <div class="ac-stats">${(s.specialisering || '').substring(0,6)}</div>
        </div>`;
    });

    if (!html) {
        html = '<span class="muted" style="font-size:0.8rem">Inga tillgångar ännu</span>';
    }

    panel.innerHTML = html;

    // Attach click handlers for detail modal
    panel.querySelectorAll('.asset-card.clickable').forEach(card => {
        card.addEventListener('click', () => showAssetDetail(card, me));
    });
}

function truncName(name, max) {
    return name.length > max ? name.substring(0, max - 1) + '…' : name;
}

function projectImgUrl(typ, namn) {
    return `/img/projects/${encodeURIComponent(namn)}.jpg`;
}

function showAssetDetail(card, player) {
    const type = card.dataset.detail;
    const idx = card.dataset.idx;
    const modal = document.getElementById('card-modal');
    const body = document.getElementById('card-modal-body');
    const closeBtn = document.getElementById('card-modal-close');

    let html = '';

    if (type === 'project') {
        const p = player.projects.find(pr => pr.namn === idx);
        if (!p) return;
        const ek = player.projekt_energiklass?.[p.namn] || p.energiklass || '—';
        const imgUrl = projectImgUrl(p.typ, p.namn);
        html = `
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
                <div class="detail-row"><span>Kvalitet</span><span>${p.kvalitet}</span></div>
                <div class="detail-row"><span>Hållbarhet</span><span>${p.hallbarhet}</span></div>
                <div class="detail-row"><span>Energiklass</span><span>${ek}</span></div>
                <div class="detail-row"><span>Anskaffning</span><span>${p.anskaffning} Mkr</span></div>
                <div class="detail-row"><span>Kostnad</span><span>${p.kostnad} Mkr</span></div>
            </div>
        `;
    } else if (type === 'loan') {
        const net = player.abt_loans_net || 0;
        const fee = player.abt_borrowing_cost || 0;
        const gross = net + fee;
        const nLoans = Math.ceil(net / 95);
        html = `
            <h3>Moderbolagslån</h3>
            <div class="detail-grid">
                <div class="detail-row"><span>Antal lån</span><span>${nLoans} st</span></div>
                <div class="detail-row"><span>Brutto</span><span>${nLoans * 100} Mkr</span></div>
                <div class="detail-row"><span>Avgift (5%)</span><span>${fee} Mkr</span></div>
                <div class="detail-row"><span>Netto erhållit</span><span>${net} Mkr</span></div>
                <div class="detail-row"><span>Total skuld</span><span>${gross} Mkr</span></div>
            </div>
            <p style="margin-top:12px;color:var(--text-muted);font-size:0.85rem">
                Lånet belastar slutresultatet via Real EK och TB.
            </p>
        `;
    } else if (type === 'supplier') {
        const s = player.pl_suppliers?.[idx];
        if (!s) return;
        const kompStr = Object.entries(s.kompetenser || {}).filter(([,v]) => v > 0).map(([k,v]) => `${k}: ${v}`).join(', ');
        html = `
            <h3>${idx}</h3>
            <div class="card-type">Leverantör — Nivå ${s.niva}</div>
            <div class="detail-grid">
                ${s.beskrivning ? `<div class="detail-row"><span>Beskrivning</span><span>${s.beskrivning}</span></div>` : ''}
                <div class="detail-row"><span>Kostnad</span><span>${s.kostnad} Mkr</span></div>
                <div class="detail-row"><span>Kvalitet</span><span>${s.q >= 0 ? '+' : ''}${s.q}</span></div>
                <div class="detail-row"><span>Hållbarhet</span><span>${s.h >= 0 ? '+' : ''}${s.h}</span></div>
                <div class="detail-row"><span>Tid</span><span>${s.t >= 0 ? '+' : ''}${s.t} mån</span></div>
                <div class="detail-row"><span>Erfarenhet</span><span>${s.erfarenhet >= 0 ? '+' : ''}${s.erfarenhet}</span></div>
                ${kompStr ? `<div class="detail-row"><span>Kompetenser</span><span>${kompStr}</span></div>` : ''}
            </div>
        `;
    } else if (type === 'org') {
        const o = player.pl_orgs?.[idx];
        if (!o) return;
        const kompStr = Object.entries(o.kompetenser || {}).filter(([,v]) => v > 0).map(([k,v]) => `${k}: ${v}`).join(', ');
        html = `
            <h3>${idx}</h3>
            <div class="card-type">Organisation — Nivå ${o.niva}</div>
            <div class="detail-grid">
                <div class="detail-row"><span>Kostnad</span><span>${o.kostnad_mkr} Mkr</span></div>
                <div class="detail-row"><span>Kvalitet</span><span>${o.q >= 0 ? '+' : ''}${o.q}</span></div>
                <div class="detail-row"><span>Hållbarhet</span><span>${o.h >= 0 ? '+' : ''}${o.h}</span></div>
                <div class="detail-row"><span>Tid</span><span>${o.t >= 0 ? '+' : ''}${o.t} mån</span></div>
                <div class="detail-row"><span>Erfarenhet</span><span>${o.erfarenhet >= 0 ? '+' : ''}${o.erfarenhet}</span></div>
                ${o.riskbuffert ? `<div class="detail-row"><span>Riskbuffert</span><span>+${o.riskbuffert}</span></div>` : ''}
                ${kompStr ? `<div class="detail-row"><span>Kompetenser</span><span>${kompStr}</span></div>` : ''}
            </div>
        `;
    } else if (type === 'staff') {
        const s = player.staff?.find(st => st.namn === idx);
        if (!s) return;
        html = `
            <h3>${s.namn}</h3>
            <div class="card-type">${s.roll} — ${s.specialisering || ''}</div>
            <div class="detail-grid">
                <div class="detail-row"><span>Kapacitet</span><span>${s.kapacitet} fastigheter</span></div>
                <div class="detail-row"><span>Lön</span><span>${s.lon} Mkr/kv</span></div>
                <div class="detail-row"><span>Förhandling</span><span>D${s.forhandling || '—'}</span></div>
            </div>
        `;
    }

    if (!html) return;
    body.innerHTML = html;
    modal.style.display = 'flex';
    closeBtn.onclick = () => { modal.style.display = 'none'; };
}
