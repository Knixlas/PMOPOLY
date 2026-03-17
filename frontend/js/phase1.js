/**
 * PMOPOLY - Phase 1 action rendering
 * Uses addEventListener instead of inline onclick for ES module compatibility.
 */
import { sendAction } from './app.js';
import { updateCardResult, showPreview, previewProject } from './components.js';

export function renderPhase1Action(panel, gs, pending) {
    const action = pending.action;

    switch (action) {
        case 'pick_project_type': renderPickProjectType(panel, pending); break;
        case 'roll_dice': renderRollDice(panel, pending); break;
        case 'choose_project': renderChooseProject(panel, pending); break;
        case 'continue': renderContinue(panel, pending); break;
        case 'roll_card_d20': renderRollCardD20(panel, pending); break;
        case 'card_reroll': renderCardReroll(panel, pending); break;
        case 'card_done': renderCardDone(panel, pending); break;
        case 'use_riskbuffert': renderUseRiskbuffert(panel, pending); break;
        case 'stadshuset_choice': renderStadshuset(panel, pending); break;
        case 'roll_namndbeslut': renderNamndbeslut(panel, pending); break;
        case 'return_project': renderReturnProject(panel, pending); break;
        case 'riskbuffert_invest': renderRiskbuffertInvest(panel, pending, gs); break;
        case 'card_swap_project': renderCardSwapProject(panel, pending); break;
        default: panel.innerHTML = `<p>${pending.message || 'Väntar...'}</p>`;
    }
}

function renderPickProjectType(panel, pending) {
    let html = `<h3>Välj projekttyp</h3><p>${pending.message}</p>`;
    for (const typ of pending.options) {
        html += `<button class="btn btn-primary action-btn" data-typ="${typ}">${typ}</button>`;
    }
    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            sendAction({ action: 'pick_project_type', value: btn.dataset.typ });
        });
    });
}

function renderRollDice(panel, pending) {
    panel.innerHTML = `
        <h3>Slå tärning</h3>
        <p>${pending.message}</p>
        <button class="btn btn-warning" id="btn-roll" style="font-size:1.3rem;padding:16px">
            🎲 Slå D6
        </button>
    `;
    document.getElementById('btn-roll').addEventListener('click', function() {
        sendAction({ action: 'roll_dice' });
        this.disabled = true;
        this.textContent = 'Slår...';
    });
}

function renderChooseProject(panel, pending) {
    let html = `<h3>Välj projekt</h3><p>${pending.message}</p>`;
    const options = pending.options || [];
    for (const opt of options) {
        const p = opt.top;
        html += `
            <div class="project-option action-btn" data-typ="${opt.typ}">
                <div class="proj-name">${p.namn} (${p.typ})</div>
                <div class="proj-stats">
                    BTA: ${p.bta} kvm | Kostnad: ${p.kostnad} Mkr |
                    Anskaff: ${p.anskaffning} Mkr<br>
                    Q:${p.kvalitet} H:${p.hallbarhet} T:${p.tid} |
                    Form: ${p.formfaktor} | Nämnd: ≥${p.namndbeslut}
                </div>
            </div>
        `;
    }
    if (pending.can_skip) {
        html += `<button class="btn btn-secondary action-btn" data-typ="skip">Hoppa över</button>`;
    }
    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.typ === 'skip') {
                sendAction({ action: 'choose_project', value: 'skip' });
                return;
            }
            const opt = options.find(o => o.typ === btn.dataset.typ);
            if (opt) {
                showPreview(previewProject(opt), () => {
                    sendAction({ action: 'choose_project', value: btn.dataset.typ });
                });
            }
        });
    });
}

function renderContinue(panel, pending) {
    panel.innerHTML = `
        <h3>Fortsätt</h3>
        <p>${pending.message}</p>
        <button class="btn btn-primary" id="btn-continue">Fortsätt</button>
    `;
    document.getElementById('btn-continue').addEventListener('click', () => {
        sendAction({ action: 'continue' });
    });
}

function renderRollCardD20(panel, pending) {
    panel.innerHTML = `
        <h3>Slå D20</h3>
        <p>${pending.message}</p>
        <button class="btn btn-warning" id="btn-roll-card" style="font-size:1.3rem;padding:16px">
            🎲 Slå D20
        </button>
    `;
    document.getElementById('btn-roll-card').addEventListener('click', function() {
        sendAction({ action: 'roll_card_d20' });
        this.disabled = true;
        this.textContent = 'Slår...';
    });
}

function renderCardReroll(panel, pending) {
    // Card modal already shows reroll buttons via updateCardResult
    // Show summary in action panel as backup
    panel.innerHTML = `
        <h3>Riskbuffert?</h3>
        <p>D20: ${pending.d20_result} → ${pending.effect}</p>
        <p>Du har <strong>${pending.riskbuffertar}</strong> riskbuffertar.</p>
        <p class="muted">Välj i kortfönstret eller här:</p>
        <button class="btn btn-warning" id="btn-use-rb">Slå om</button>
        <button class="btn btn-secondary" id="btn-keep">Behåll</button>
    `;
    // Also update the card modal
    updateCardResult(pending.d20_result, pending.effect, pending.riskbuffertar, sendAction);

    document.getElementById('btn-use-rb').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: true });
    });
    document.getElementById('btn-keep').addEventListener('click', () => {
        sendAction({ action: 'use_riskbuffert', value: false });
    });
}

function renderCardDone(panel, pending) {
    // Card modal shows OK button, but also show in action panel
    updateCardResult(pending.d20_result, pending.effect, 0, sendAction);
    panel.innerHTML = `
        <h3>Fortsätt</h3>
        <p>D20: ${pending.d20_result} → ${pending.effect}</p>
        <button class="btn btn-primary" id="btn-continue">OK</button>
    `;
    document.getElementById('btn-continue').addEventListener('click', () => {
        document.getElementById('card-modal').style.display = 'none';
        sendAction({ action: 'continue' });
    });
}

function renderUseRiskbuffert(panel, pending) {
    panel.innerHTML = `
        <h3>Riskbuffert</h3>
        <p>${pending.message}</p>
        <p>Du har <strong>${pending.riskbuffertar}</strong> riskbuffertar kvar.</p>
        ${pending.current_effect ? `<p>Nuvarande effekt: <em>${pending.current_effect}</em></p>` : ''}
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

function renderStadshuset(panel, pending) {
    panel.innerHTML = `
        <h3>Stadshuset</h3>
        <p>Välj vad du vill göra:</p>
        <button class="btn btn-success action-btn" data-val="take">Ta ett nytt projekt</button>
        <button class="btn btn-danger action-btn" data-val="return">Lämna tillbaka ett projekt</button>
        <button class="btn btn-secondary action-btn" data-val="skip">Gör ingenting</button>
    `;
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            sendAction({ action: 'stadshuset_choice', value: btn.dataset.val });
        });
    });
}

function renderNamndbeslut(panel, pending) {
    const p = pending.project || {};
    panel.innerHTML = `
        <h3>Nämndbeslut</h3>
        <div class="project-option" style="cursor:default">
            <div class="proj-name">${p.namn || 'Projekt'}</div>
            <div class="proj-stats">Behöver ≥${pending.threshold} på D20</div>
        </div>
        <button class="btn btn-warning" id="btn-roll-namnd" style="font-size:1.2rem;padding:14px">
            🎲 Slå D20
        </button>
    `;
    document.getElementById('btn-roll-namnd').addEventListener('click', function() {
        sendAction({ action: 'roll_namndbeslut' });
        this.disabled = true;
    });
}

function renderReturnProject(panel, pending) {
    let html = `<h3>Lämna tillbaka projekt</h3><p>${pending.message}</p>`;
    for (const p of (pending.projects || [])) {
        html += `
            <div class="project-option action-btn" data-id="${p.id}">
                <div class="proj-name">${p.namn} (${p.typ})</div>
                <div class="proj-stats">BTA: ${p.bta} | Form: ${p.formfaktor} | Anskaff: ${p.anskaffning} Mkr</div>
            </div>
        `;
    }
    panel.innerHTML = html;
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            sendAction({ action: 'return_project', value: btn.dataset.id });
        });
    });
}

function renderRiskbuffertInvest(panel, pending, gs) {
    const investments = [];
    panel.innerHTML = `
        <h3>Investera riskbuffertar</h3>
        <p>Du har <strong>${pending.riskbuffertar}</strong> riskbuffertar.
           Varje sänker ett krav med 1.</p>
        <p>Q-krav: ${pending.q_krav} | H-krav: ${pending.h_krav}</p>
        <div id="rb-selections" style="margin-bottom:8px;color:var(--accent)"></div>
        <button class="btn btn-success rb-btn" data-type="q">-1 Kvalitetskrav</button>
        <button class="btn btn-success rb-btn" data-type="h">-1 Hållbarhetskrav</button>
        <button class="btn btn-success rb-btn" data-type="t">-1 Månad byggtid</button>
        <div style="margin-top:12px">
            <button class="btn btn-primary" id="btn-rb-done">Klar</button>
            <button class="btn btn-secondary" id="btn-rb-skip">Hoppa över</button>
        </div>
    `;
    panel.querySelectorAll('.rb-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            investments.push(btn.dataset.type);
            document.getElementById('rb-selections').textContent = `Valda: ${investments.join(', ')}`;
        });
    });
    document.getElementById('btn-rb-done').addEventListener('click', () => {
        sendAction({ action: 'riskbuffert_invest', value: investments });
    });
    document.getElementById('btn-rb-skip').addEventListener('click', () => {
        sendAction({ action: 'riskbuffert_invest', value: [] });
    });
}

function renderCardSwapProject(panel, pending) {
    let html = `<h3>Byt projekt</h3><p>${pending.message}</p>`;
    for (const p of (pending.projects || [])) {
        html += `
            <div class="project-option action-btn" data-id="${p.id}">
                <div class="proj-name">${p.namn} (${p.typ})</div>
                <div class="proj-stats">BTA: ${p.bta} | Form: ${p.formfaktor} | Anskaff: ${p.anskaffning} Mkr</div>
            </div>
        `;
    }
    html += `<button class="btn btn-secondary action-btn" data-id="skip">Hoppa över</button>`;
    panel.innerHTML = html;
    const projects = pending.projects || [];
    panel.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.id === 'skip') {
                sendAction({ action: 'card_swap_project', value: 'skip' });
                return;
            }
            const p = projects.find(pr => pr.id === btn.dataset.id);
            if (p) {
                showPreview(previewProject(p), () => {
                    sendAction({ action: 'card_swap_project', value: btn.dataset.id });
                });
            }
        });
    });
}
