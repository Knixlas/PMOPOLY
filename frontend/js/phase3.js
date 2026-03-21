/**
 * PMOPOLY - Phase 3 (Genomförande) renderer
 */
import { sendAction } from './app.js';

export function renderPhase3Action(panel, gs, pending) {
    const action = pending.action;

    // Build player status for Phase 3
    const me = gs.players.find(p => p.id === pending.player_id);
    const statusHtml = me ? renderGfStatus(me, gs) : '';

    switch (action) {
        case 'gf_buy_support':
            renderBuySupport(panel, pending, statusHtml);
            break;
        case 'gf_choose_level':
            renderChooseLevel(panel, pending, statusHtml);
            break;
        case 'gf_play_cards':
            renderPlayCards(panel, pending, statusHtml);
            break;
        case 'roll_d20':
            renderRollD20(panel, pending, statusHtml);
            break;
        case 'use_riskbuffert':
            renderReroll(panel, pending, statusHtml);
            break;
        case 'continue':
            renderContinue(panel, pending, statusHtml);
            break;
        default:
            panel.innerHTML = statusHtml + `<h3>Fas 3: Genomförande</h3><p>${pending.message || ''}</p>`;
    }
}

function renderGfStatus(player, gs) {
    const q_ok = player.pl_q >= player.q_krav;
    const h_ok = player.pl_h >= player.h_krav;
    const t_ok = player.pl_t <= 12;
    return `
        <div class="gf-status">
            <div class="gf-stats">
                <span class="pstat ${q_ok ? 'ok' : ''}">Q: ${player.pl_q}/${player.q_krav}</span>
                <span class="pstat ${h_ok ? 'ok' : ''}">H: ${player.pl_h}/${player.h_krav}</span>
                <span class="pstat ${t_ok ? 'ok' : ''}">T: ${player.pl_t} mån</span>
                <span class="pstat">ABT: ${player.abt_budget} Mkr</span>
                <span class="pstat">Rb: ${player.riskbuffertar}</span>
                <span class="pstat">Ext: ${(player.external_hand || []).length}</span>
            </div>
        </div>
    `;
}

function renderBuySupport(panel, pending, statusHtml) {
    const faskort = pending.faskort || {};
    const cost = pending.cost;
    const canBuy = pending.can_buy;

    let html = statusHtml;
    html += `<div class="gf-faskort-header">
        <h3>Fas ${pending.fas_nr}/8: ${faskort.namn || ''}</h3>
        <p class="sub-text">${faskort.beskrivning || ''}</p>
    </div>`;

    html += `<p>Vill du köpa externt stöd (kulturkort)?</p>
             <p class="sub-text">Kostnad: ${cost} Mkr | ABT: ${pending.abt} Mkr |
             I hand: ${pending.hand_count} | Kortlek: ${pending.deck_count}</p>`;

    html += `<div class="gf-buttons">`;
    if (canBuy) {
        html += `<button class="btn btn-primary" id="gf-buy-yes">Köp externt stöd (${cost} Mkr)</button>`;
    }
    html += `<button class="btn btn-secondary" id="gf-buy-no">Hoppa över</button>`;
    html += `</div>`;

    panel.innerHTML = html;

    if (canBuy) {
        document.getElementById('gf-buy-yes').addEventListener('click', () => {
            sendAction({ action: 'gf_buy_support', value: true });
        });
    }
    document.getElementById('gf-buy-no').addEventListener('click', () => {
        sendAction({ action: 'gf_buy_support', value: false });
    });
}

function renderChooseLevel(panel, pending, statusHtml) {
    const faskort = pending.faskort || {};
    const levels = pending.levels || [];
    const trigger = pending.trigger;

    let html = statusHtml;
    html += `<div class="gf-faskort-header">
        <h3>${faskort.namn || 'Faskort'}</h3>
        <p class="sub-text">${faskort.beskrivning || ''}</p>
        <p class="sub-text">Kvartertyp: ${trigger} | ${pending.comp_cards_count} kompetenskort tillgängliga</p>
    </div>`;

    html += `<p>Välj utfallsnivå:</p>`;

    const levelColors = { 'Negativt': 'level-neg', 'Neutralt': 'level-neu', 'Positivt': 'level-pos', 'Bonus': 'level-bon' };
    levels.forEach((lvl) => {
        const reqs = lvl.reqs || {};
        const reqStr = Object.keys(reqs).length > 0
            ? Object.entries(reqs).map(([k, v]) => `${k} ${v}`).join(', ')
            : lvl.req_text || '(ingen insats krävs)';
        const levelClass = levelColors[lvl.name] || '';
        html += `
            <div class="gf-level-option ${levelClass}" data-idx="${lvl.index}">
                <div class="sup-header">
                    <span class="sup-name">${lvl.name}</span>
                    <span class="sup-cost">${reqStr}</span>
                </div>
                <div class="sup-stats">${lvl.effect || 'Ingen effekt'}</div>
            </div>
        `;
    });

    panel.innerHTML = html;

    panel.querySelectorAll('.gf-level-option').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'gf_choose_level', value: parseInt(el.dataset.idx) });
        });
    });
}

function renderPlayCards(panel, pending, statusHtml) {
    const cards = pending.cards || [];
    const reqs = pending.reqs || {};
    const fulfilled = pending.fulfilled || {};
    const remaining = pending.remaining || {};

    let html = statusHtml;
    html += `<h3>Spela kompetenskort</h3>`;
    html += `<p class="sub-text">Nivå: ${pending.level_name}</p>`;

    // Requirement summary as colored badges
    html += `<div class="comp-reqs-summary">`;
    for (const [k, v] of Object.entries(reqs)) {
        const done = fulfilled[k] || 0;
        const met = done >= v;
        const left = Math.max(0, v - done);
        html += `<div class="comp-req-badge ${met ? 'met' : 'unmet'}">
            <span class="crb-label">${k}</span>
            <span class="crb-val">${done}/${v}</span>
            ${!met ? `<span class="crb-need">behöver ${left}</span>` : `<span class="crb-check">✓</span>`}
        </div>`;
    }
    html += `</div>`;

    // Split cards into useful (has needed competence) and other
    const usefulCards = [];
    const otherCards = [];
    cards.forEach(card => {
        const komps = card.kompetenser || {};
        const hasUseful = Object.entries(komps).some(([k, v]) => v > 0 && remaining[k] && remaining[k] > 0);
        if (hasUseful) {
            usefulCards.push(card);
        } else {
            otherCards.push(card);
        }
    });

    // Show useful cards first
    if (usefulCards.length > 0) {
        html += `<p class="sub-text" style="margin-top:8px;color:var(--success)">Användbara kort (${usefulCards.length}):</p>`;
        usefulCards.forEach(card => {
            html += renderCompCard(card, remaining);
        });
    }

    // Show other cards collapsed
    if (otherCards.length > 0) {
        html += `<p class="sub-text" style="margin-top:8px;opacity:0.5">Övriga kort (${otherCards.length}):</p>`;
        otherCards.forEach(card => {
            html += renderCompCard(card, remaining);
        });
    }

    if (usefulCards.length === 0 && otherCards.length === 0) {
        html += `<p class="sub-text" style="color:var(--danger)">Inga kort kvar!</p>`;
    }

    if (pending.can_finish) {
        html += `<button class="btn btn-success" id="gf-cards-done" style="margin-top:8px">Klar - alla krav uppfyllda!</button>`;
    }
    if (Object.keys(remaining).length > 0 && usefulCards.length === 0) {
        html += `<button class="btn btn-danger" id="gf-cards-give-up" style="margin-top:8px">Ge upp (Negativt utfall)</button>`;
    } else if (Object.keys(remaining).length > 0) {
        html += `<button class="btn btn-secondary btn-small" id="gf-cards-give-up" style="margin-top:4px;opacity:0.6">Ge upp</button>`;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('.gf-comp-card').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'gf_play_cards', value: el.dataset.key });
        });
    });

    const doneBtn = document.getElementById('gf-cards-done');
    if (doneBtn) {
        doneBtn.addEventListener('click', () => {
            sendAction({ action: 'gf_play_cards', value: '__done__' });
        });
    }
    const giveUpBtn = document.getElementById('gf-cards-give-up');
    if (giveUpBtn) {
        giveUpBtn.addEventListener('click', () => {
            sendAction({ action: 'gf_play_cards', value: '__done__' });
        });
    }
}

function renderCompCard(card, remaining) {
    const kompEntries = Object.entries(card.kompetenser || {}).filter(([, v]) => v > 0);
    const kompStr = kompEntries
        .map(([k, v]) => {
            const needed = remaining[k];
            const useful = needed && needed > 0;
            return `<span class="comp-tag ${useful ? 'comp-useful' : ''}">${k}: ${v}</span>`;
        })
        .join(' ');
    const sourceLabel = card.source === 'supplier' ? 'Lev' : card.source === 'org' ? 'Org' : card.source === 'ac' ? 'AC' : 'Ext';
    return `
        <div class="supplier-option gf-comp-card" data-key="${card.key}">
            <div class="sup-header">
                <span class="sup-name">${card.namn}</span>
                <span class="sup-cost">${sourceLabel}${card.bonus ? ` +${card.bonus}` : ''}</span>
            </div>
            <div class="sup-komp">${kompStr}</div>
        </div>
    `;
}

function renderRollD20(panel, pending, statusHtml) {
    const card = pending.card || {};
    let html = statusHtml;

    html += `<div class="event-card-display">
        <div class="ec-name">${card.namn || pending.typ || 'Kort'}</div>
        <div class="ec-desc">${card.beskrivning || ''}</div>
        ${pending.card_idx ? `<div class="ec-roll">Kort ${pending.card_idx}/${pending.card_total}</div>` : ''}
        <div class="ec-effect" style="color:var(--text-muted)">Erfarenhet: +${pending.erfarenhet || 0}</div>
    </div>`;

    html += `<button class="btn btn-warning" id="gf-roll-d20" style="font-size:1.3rem;padding:16px;width:100%;margin-top:8px">
        🎲 Slå D20
    </button>`;

    panel.innerHTML = html;

    document.getElementById('gf-roll-d20').addEventListener('click', function() {
        sendAction({ action: 'roll_d20' });
        this.disabled = true;
        this.textContent = 'Slår...';
    });
}

function renderReroll(panel, pending, statusHtml) {
    const card = pending.card || {};
    let html = statusHtml;

    html += `<div class="event-card-display">
        <div class="ec-name">${card.namn || pending.typ || 'Kort'}</div>
        <div class="ec-desc">${card.beskrivning || ''}</div>
        <div class="ec-roll">D20: ${pending.d20} + ${pending.exp} erfarenhet = ${pending.total}</div>
        <div class="ec-effect">${pending.effect || pending.current_effect || ''}</div>
    </div>`;

    html += `<p>Använda riskbuffert för omslag? (${pending.riskbuffertar} kvar)</p>`;
    html += `<button class="btn btn-warning" id="gf-reroll-yes">Använd riskbuffert</button>`;
    html += `<button class="btn btn-secondary" id="gf-reroll-no">Behåll resultat</button>`;

    panel.innerHTML = html;

    document.getElementById('gf-reroll-yes').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: true });
    });
    document.getElementById('gf-reroll-no').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: false });
    });
}

function renderContinue(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<p>${pending.message || ''}</p>`;

    if (pending.effect) {
        html += `<div class="event-card-display"><div class="ec-effect">${pending.effect}</div></div>`;
    }

    html += `<button class="btn btn-primary" id="gf-continue">Fortsätt</button>`;

    panel.innerHTML = html;

    document.getElementById('gf-continue').addEventListener('click', () => {
        sendAction({ action: 'continue' });
    });
}
