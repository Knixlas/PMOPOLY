/**
 * PMOPOLY - Phase 4 (Förvaltning) renderer
 */
import { sendAction } from './app.js';
import { showPreview, previewStaff, previewMarketBuy } from './components.js';

export function renderPhase4Action(panel, gs, pending) {
    const action = pending.action;
    const me = gs.players.find(p => p.id === pending.player_id);
    const statusHtml = me ? renderF4Status(me, gs) : '';

    switch (action) {
        case 'f4_hire':
            renderHireStaff(panel, pending, statusHtml);
            break;
        case 'f4_energy_upgrade':
            renderEnergyUpgrade(panel, pending, statusHtml);
            break;
        case 'f4_market':
            renderMarket(panel, pending, statusHtml);
            break;
        case 'f4_market_sell':
            renderMarketSell(panel, pending, statusHtml);
            break;
        case 'f4_market_buy':
            renderMarketBuy(panel, pending, statusHtml);
            break;
        case 'continue':
            renderContinue(panel, pending, statusHtml, gs);
            break;
        default:
            panel.innerHTML = statusHtml + `<h3>Fas 4</h3><p>${pending.message || ''}</p>`;
    }
}

function renderF4Status(player, gs) {
    const staffCost = (player.staff || []).reduce((s, st) => s + (st.lon || 0), 0);
    const staffCap = (player.staff || []).reduce((s, st) => s + (st.kapacitet || 0), 0);
    return `
        <div class="gf-status">
            <div class="gf-stats">
                <span class="pstat">Fast: ${(player.fastigheter || []).length}</span>
                <span class="pstat">EK: ${player.eget_kapital} Mkr</span>
                <span class="pstat">Personal: ${(player.staff || []).length} (kap ${staffCap})</span>
                <span class="pstat">Lön: ${staffCost.toFixed(1)}/kv</span>
            </div>
        </div>
    `;
}

function renderHireStaff(panel, pending, statusHtml) {
    const available = pending.available || [];
    const mustHire = pending.must_hire;

    let html = statusHtml;
    html += `<h3>Anställ personal</h3>`;
    html += `<div class="planning-status">
        <div class="progress-text">Kapacitet: ${pending.current_cap}/${pending.required} fastigheter
        ${!pending.has_fc ? ' | <strong style="color:var(--danger)">Behöver FC!</strong>' : ''}
        | Lönekostnad: ${(pending.staff_cost || 0).toFixed(1)} Mkr/kv</div>
    </div>`;

    if (available.length === 0) {
        html += `<p class="muted">Ingen personal tillgänglig.</p>`;
    } else {
        available.forEach(s => {
            html += `
                <div class="supplier-option f4-staff-card" data-id="${s.id}">
                    <div class="sup-header">
                        <span class="sup-name">[${s.roll}] ${s.namn}</span>
                        <span class="sup-cost">Lön: ${(s.lon || 0).toFixed(1)} Mkr/kv</span>
                    </div>
                    <div class="sup-stats">${s.specialisering} | Kap: ${s.kapacitet}
                    ${s.forhandling ? ` | Förh: ${s.forhandling}` : ''}</div>
                </div>
            `;
        });
    }

    if (!mustHire) {
        html += `<button class="btn btn-secondary" id="f4-hire-done">Klar</button>`;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('.f4-staff-card').forEach(el => {
        el.addEventListener('click', () => {
            const s = available.find(st => st.id === el.dataset.id);
            if (s) {
                showPreview(previewStaff(s), () => {
                    sendAction({ action: 'f4_hire', value: el.dataset.id });
                });
            }
        });
    });

    const doneBtn = document.getElementById('f4-hire-done');
    if (doneBtn) {
        doneBtn.addEventListener('click', () => {
            sendAction({ action: 'f4_hire', value: null });
        });
    }
}

function renderEnergyUpgrade(panel, pending, statusHtml) {
    const upgradeable = pending.upgradeable || [];
    let html = statusHtml;
    html += `<h3>${pending.message || 'Energiuppgradering'}</h3>`;
    html += `<p class="sub-text">EK: ${pending.eget_kapital} Mkr</p>`;

    if (upgradeable.length === 0) {
        html += `<p class="muted">Alla fastigheter har redan energiklass A!</p>`;
    } else {
        upgradeable.forEach(u => {
            const canAfford = u.cost <= pending.eget_kapital;
            html += `
                <div class="supplier-option ${!canAfford ? 'blocked' : ''}" data-namn="${u.namn}">
                    <div class="sup-header">
                        <span class="sup-name">${u.namn} (${u.typ})</span>
                        <span class="sup-cost">${u.ek} → ${u.new_ek} | ${u.cost} Mkr</span>
                    </div>
                    ${!canAfford ? '<div class="sup-blocked">Inte råd</div>' : ''}
                </div>
            `;
        });
    }

    html += `<button class="btn btn-secondary" id="f4-energy-skip">Hoppa över</button>`;
    panel.innerHTML = html;

    panel.querySelectorAll('.supplier-option:not(.blocked)').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'f4_energy_upgrade', value: el.dataset.namn });
        });
    });

    document.getElementById('f4-energy-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_energy_upgrade', value: null });
    });
}

function renderMarket(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>Fastighetsmarknad</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    const buyList = pending.buy_list || [];
    if (buyList.length > 0) {
        html += `<h4>Till salu:</h4>`;
        buyList.forEach(b => {
            html += `<div class="f4-market-info">
                ${b.namn} (${b.typ}) BTA:${b.bta} | DN:${b.driftnetto}/kv | EK:${b.ek} |
                Pris: ${b.cost_30} Mkr ${!b.can_afford ? '⛔' : ''}
            </div>`;
        });
    }

    html += `<div class="gf-buttons">`;
    if (pending.sell_list && pending.sell_list.length > 1) {
        html += `<button class="btn btn-warning" id="f4-market-sell">Sälj</button>`;
    }
    if (pending.can_buy && buyList.some(b => b.can_afford)) {
        html += `<button class="btn btn-primary" id="f4-market-buy">Köp</button>`;
    }
    html += `<button class="btn btn-secondary" id="f4-market-skip">Hoppa över</button>`;
    html += `</div>`;

    panel.innerHTML = html;

    const sellBtn = document.getElementById('f4-market-sell');
    if (sellBtn) sellBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'sell' });
    });
    const buyBtn = document.getElementById('f4-market-buy');
    if (buyBtn) buyBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'buy' });
    });
    document.getElementById('f4-market-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_market', value: 'skip' });
    });
}

function renderMarketSell(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>${pending.message}</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    (pending.sell_list || []).forEach((s, i) => {
        html += `
            <div class="supplier-option" data-idx="${i}">
                <div class="sup-header">
                    <span class="sup-name">${s.namn} (${s.typ})</span>
                    <span class="sup-cost">FV: ${s.fv} | Du får: ${s.earn_30} Mkr</span>
                </div>
            </div>
        `;
    });

    if (!pending.forced) {
        html += `<button class="btn btn-secondary" id="f4-sell-skip">Avbryt</button>`;
    }

    panel.innerHTML = html;

    panel.querySelectorAll('.supplier-option').forEach(el => {
        el.addEventListener('click', () => {
            sendAction({ action: 'f4_market_sell', value: parseInt(el.dataset.idx) });
        });
    });

    const skipBtn = document.getElementById('f4-sell-skip');
    if (skipBtn) skipBtn.addEventListener('click', () => {
        sendAction({ action: 'f4_market_sell', value: null });
    });
}

function renderMarketBuy(panel, pending, statusHtml) {
    let html = statusHtml;
    html += `<h3>Köp fastighet</h3>`;
    html += `<p class="sub-text">Verkligt EK: ${pending.real_ek} Mkr</p>`;

    (pending.buy_list || []).forEach((b, i) => {
        html += `
            <div class="supplier-option ${!b.can_afford ? 'blocked' : ''}" data-idx="${i}">
                <div class="sup-header">
                    <span class="sup-name">${b.namn} (${b.typ})</span>
                    <span class="sup-cost">Pris: ${b.cost_30} Mkr</span>
                </div>
                <div class="sup-stats">BTA:${b.bta} | DN:${b.driftnetto}/kv | EK:${b.ek} | FV:${b.fv}</div>
                ${!b.can_afford ? '<div class="sup-blocked">Inte råd</div>' : ''}
            </div>
        `;
    });

    html += `<button class="btn btn-secondary" id="f4-buy-skip">Avbryt</button>`;
    panel.innerHTML = html;

    const buyList = pending.buy_list || [];
    panel.querySelectorAll('.supplier-option:not(.blocked)').forEach(el => {
        el.addEventListener('click', () => {
            const b = buyList[parseInt(el.dataset.idx)];
            if (b) {
                showPreview(previewMarketBuy(b), () => {
                    sendAction({ action: 'f4_market_buy', value: parseInt(el.dataset.idx) });
                });
            }
        });
    });

    document.getElementById('f4-buy-skip').addEventListener('click', () => {
        sendAction({ action: 'f4_market_buy', value: null });
    });
}

function renderContinue(panel, pending, statusHtml, gs) {
    let html = statusHtml;
    const sub = gs.sub_state || '';

    if (sub === 'f4_world_event' && pending.world_event) {
        const we = pending.world_event;
        html += `<div class="event-card-display">
            <div class="ec-name">🌍 ${we.rubrik}</div>
            <div class="ec-desc">${we.beskrivning}</div>
            <div class="ec-effect">${we.effekt_typ}: ${we.effekt_mkr} Mkr | Påverkar: ${we.poverkar}</div>
        </div>`;
        html += `<p class="sub-text">Q${pending.quarter} | Yield B: ${pending.yield_b}% K: ${pending.yield_k}%</p>`;
    } else if (sub === 'f4_rent_result') {
        html += `<div class="event-card-display">
            <div class="ec-name">Hyresförhandling</div>
            <div class="ec-roll">
                FC ${pending.fc_name} (${pending.fc_die}): ${pending.fc_roll} +
                FÄ: ${pending.fa_roll} −
                HGF: ${pending.hgf_roll} = <strong>${pending.netto}</strong>
            </div>
            <div class="ec-effect">Höjning: ${pending.hojning_per} Mkr × ${pending.hr_count} HR = ${pending.total} Mkr</div>
        </div>`;
    } else if (sub === 'f4_mgmt_events') {
        const results = pending.mgmt_results || [];
        if (results.length > 0) {
            html += `<h3>Händelsekort</h3>`;
            results.forEach(r => {
                const card = r.card || {};
                html += `<div class="f4-mgmt-result ${r.effect >= 0 ? 'positive' : 'negative'}">
                    <strong>${r.prop_namn}:</strong> ${card.rubrik || 'Inga kort'}
                    ${r.mitigated ? ` <em>(mildrad av ${r.mitigator})</em>` : ''}
                    <span class="f4-effect">${r.effect >= 0 ? '+' : ''}${r.effect} Mkr</span>
                </div>`;
            });
            html += `<p class="sub-text">EK: ${pending.eget_kapital} Mkr</p>`;
        } else {
            html += `<p class="muted">Inga händelsekort detta kvartal.</p>`;
        }
    } else {
        html += `<p>${pending.message || ''}</p>`;
        if (pending.effect) {
            html += `<div class="event-card-display"><div class="ec-effect">${pending.effect}</div></div>`;
        }
    }

    html += `<button class="btn btn-primary" id="f4-continue">Fortsätt</button>`;
    panel.innerHTML = html;

    document.getElementById('f4-continue').addEventListener('click', () => {
        sendAction({ action: 'continue' });
    });
}
