/**
 * PMOPOLY - Phase 2 (Planering) action rendering
 */
import { sendAction } from './app.js';
import { showPreview, previewSupplier, previewOrg } from './components.js';

export function renderPhase2Action(panel, gs, pending) {
    const action = pending.action;

    // Always show planning status header
    const me = gs.players.find(p => p.id === pending.player_id);
    let statusHtml = '';
    if (me) {
        statusHtml = renderPlanningStatus(me, pending);
    }

    switch (action) {
        case 'choose_supplier': renderChooseSupplier(panel, pending, statusHtml); break;
        case 'choose_org': renderChooseOrg(panel, pending, statusHtml); break;
        case 'roll_d20': renderPlanningRollD20(panel, pending, statusHtml); break;
        case 'use_riskbuffert': renderPlanningReroll(panel, pending, statusHtml); break;
        case 'continue': renderPlanningContinue(panel, pending, statusHtml); break;
        case 'choose_ac': renderChooseAC(panel, pending); break;
        default: panel.innerHTML = statusHtml + `<p>${pending.message || 'Väntar...'}</p>`;
    }
}

function renderPlanningStatus(player, pending) {
    const step = pending.step || 0;
    const totalSteps = pending.total_steps || 13;
    const pct = step > 0 ? ((step - 1) / totalSteps * 100) : 0;

    const qOk = player.pl_q >= player.q_krav ? ' ok' : '';
    const hOk = player.pl_h >= player.h_krav ? ' ok' : '';
    const tOk = player.pl_t <= 12 ? ' ok' : '';

    // Build chosen suppliers/orgs summary
    const chosen = [];
    if (player.pl_suppliers) {
        for (const [k, v] of Object.entries(player.pl_suppliers)) {
            chosen.push(`${k}: niv ${v.niva}`);
        }
    }
    if (player.pl_orgs) {
        for (const [k, v] of Object.entries(player.pl_orgs)) {
            chosen.push(`${k}: niv ${v.niva}`);
        }
    }

    return `
        <div class="planning-status">
            <div class="planning-progress">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:${pct}%"></div>
                </div>
                <span class="progress-text">Steg ${step}/${totalSteps}</span>
            </div>
            <div class="planning-stats">
                <div class="pstat${qOk}"><b>Q:</b> ${player.pl_q}/${player.q_krav}</div>
                <div class="pstat${hOk}"><b>H:</b> ${player.pl_h}/${player.h_krav}</div>
                <div class="pstat${tOk}"><b>T:</b> ${player.pl_t} mån</div>
                <div class="pstat"><b>ABT:</b> ${player.abt_budget} Mkr</div>
                <div class="pstat"><b>Rb:</b> ${player.riskbuffertar}</div>
                <div class="pstat"><b>Erf:</b> ${player.total_erfarenhet}</div>
            </div>
            ${chosen.length > 0 ? `<div class="planning-chosen">${chosen.join(' | ')}</div>` : ''}
        </div>
    `;
}

function renderChooseSupplier(panel, pending, statusHtml) {
    const options = pending.options || [];
    const klass = pending.klass || 'C';
    const beror = pending.beror_av || 'BTA';

    let html = statusHtml;
    html += `<h3>${pending.slot_name}</h3>`;
    html += `<p class="sub-text">Leverantör (${beror}-klass ${klass})${pending.min_level > 1 ? ` — Miniminivå: ${pending.min_level}` : ''}</p>`;

    for (const opt of options) {
        const kostnad = opt.kostnad || 0;
        const blocked = opt.blocked;
        const kompStr = Object.entries(opt.kompetenser || {}).filter(([k, v]) => v > 0).map(([k, v]) => `${k}:${v}`).join(' ');
        html += `
            <div class="supplier-option action-btn${blocked ? ' blocked' : ''}" data-niva="${opt.niva}">
                <div class="sup-header">
                    <span class="sup-name">Nivå ${opt.niva}: ${opt.beskrivning}</span>
                    <span class="sup-cost">${kostnad} Mkr</span>
                </div>
                <div class="sup-stats">
                    Q:${opt.q >= 0 ? '+' : ''}${opt.q}
                    H:${opt.h >= 0 ? '+' : ''}${opt.h}
                    T:${opt.t >= 0 ? '+' : ''}${opt.t}
                    Erf:${opt.erfarenhet >= 0 ? '+' : ''}${opt.erfarenhet}
                </div>
                ${kompStr ? `<div class="sup-komp">${kompStr}</div>` : ''}
                ${blocked ? `<div class="sup-blocked">${opt.block_reason}</div>` : ''}
            </div>
        `;
    }

    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn:not(.blocked)').forEach(btn => {
        btn.addEventListener('click', () => {
            const opt = options.find(o => o.niva === parseInt(btn.dataset.niva));
            if (opt) {
                showPreview(previewSupplier(opt), () => {
                    sendAction({ action: 'choose_supplier', value: parseInt(btn.dataset.niva) });
                });
            }
        });
    });
}

function renderChooseOrg(panel, pending, statusHtml) {
    const options = pending.options || [];

    let html = statusHtml;
    html += `<h3>${pending.slot_name}</h3>`;
    html += `<p class="sub-text">Organisation</p>`;

    for (const opt of options) {
        const blocked = opt.blocked;
        const kompStr = Object.entries(opt.kompetenser || {}).filter(([k, v]) => v > 0).map(([k, v]) => `${k}:${v}`).join(' ');
        html += `
            <div class="supplier-option action-btn${blocked ? ' blocked' : ''}" data-niva="${opt.niva}">
                <div class="sup-header">
                    <span class="sup-name">Nivå ${opt.niva}</span>
                    <span class="sup-cost">${opt.kostnad_mkr} Mkr</span>
                </div>
                <div class="sup-stats">
                    Q:${opt.q >= 0 ? '+' : ''}${opt.q}
                    H:${opt.h >= 0 ? '+' : ''}${opt.h}
                    T:${opt.t >= 0 ? '+' : ''}${opt.t}
                    Erf:${opt.erfarenhet >= 0 ? '+' : ''}${opt.erfarenhet}
                    ${opt.riskbuffert ? `Rb:+${opt.riskbuffert}` : ''}
                </div>
                ${kompStr ? `<div class="sup-komp">${kompStr}</div>` : ''}
                ${blocked ? `<div class="sup-blocked">${opt.block_reason}</div>` : ''}
            </div>
        `;
    }

    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn:not(.blocked)').forEach(btn => {
        btn.addEventListener('click', () => {
            const opt = options.find(o => o.niva === parseInt(btn.dataset.niva));
            if (opt) {
                showPreview(previewOrg(opt), () => {
                    sendAction({ action: 'choose_org', value: parseInt(btn.dataset.niva) });
                });
            }
        });
    });
}

function renderPlanningRollD20(panel, pending, statusHtml) {
    const card = pending.card || {};
    panel.innerHTML = statusHtml + `
        <h3>Händelsekort</h3>
        <div class="event-card-display">
            <div class="ec-name">${card.namn || 'Händelse'}</div>
            <div class="ec-desc">${card.beskrivning || ''}</div>
            <div class="ec-effect" style="color:var(--text-muted)">Erfarenhet: +${pending.erfarenhet || 0}</div>
        </div>
        <button class="btn btn-warning" id="btn-roll-d20" style="font-size:1.3rem;padding:16px;width:100%;margin-top:8px">
            🎲 Slå D20
        </button>
    `;
    document.getElementById('btn-roll-d20').addEventListener('click', function() {
        sendAction({ action: 'roll_d20' });
        this.disabled = true;
        this.textContent = 'Slår...';
    });
}

function renderPlanningReroll(panel, pending, statusHtml) {
    const card = pending.card || {};
    panel.innerHTML = statusHtml + `
        <h3>Händelsekort</h3>
        <div class="event-card-display">
            <div class="ec-name">${card.namn || 'Händelse'}</div>
            <div class="ec-desc">${card.beskrivning || ''}</div>
            <div class="ec-roll">D20: ${pending.d20} + ${pending.exp} erfarenhet = ${pending.total}</div>
            <div class="ec-effect">${pending.current_effect}</div>
        </div>
        <p>Du har <strong>${pending.riskbuffertar}</strong> riskbuffertar kvar.</p>
        <button class="btn btn-warning" id="btn-use-rb">Använd riskbuffert (slå om)</button>
        <button class="btn btn-secondary" id="btn-keep">Behåll resultatet</button>
    `;
    document.getElementById('btn-use-rb').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: true });
    });
    document.getElementById('btn-keep').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: false });
    });
}

function renderPlanningContinue(panel, pending, statusHtml) {
    panel.innerHTML = statusHtml + `
        <p>${pending.message}</p>
        <button class="btn btn-primary" id="btn-continue">Fortsätt</button>
    `;
    document.getElementById('btn-continue').addEventListener('click', () => {
        sendAction({ action: 'continue' });
    });
}

function renderChooseAC(panel, pending) {
    let html = `<h3>Välj Arbetschef (AC)</h3><p>${pending.message}</p>`;
    const options = pending.available || [];
    for (const ac of options) {
        const komp = ac.kompetenser ? Object.entries(ac.kompetenser).map(([k,v]) => `${k}:${v}`).join(', ') : 'ingen';
        html += `
            <div class="project-option action-btn" data-id="${ac.id}">
                <div class="proj-name">${ac.namn}</div>
                <div class="proj-type">${ac.specialisering}</div>
                <div class="proj-stats">
                    Erfarenhet: +${ac.erfarenhet || 0}<br>
                    Kompetens: ${komp}<br>
                    Kostnad: ${ac.lon} Mkr (dras från ABT)
                </div>
                <div class="proj-desc">${ac.not_text || ''}</div>
            </div>`;
    }
    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            sendAction({ action: 'choose_ac', value: btn.dataset.id });
        });
    });
}
