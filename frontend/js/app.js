/**
 * PMOPOLY - Main application
 * Handles routing, WebSocket connection, and view management.
 */

import { initLobby } from './lobby.js';
import { initGame, handleGameState, handleEvents } from './game.js';

// ── State ──
export const state = {
    playerId: null,
    roomId: null,
    playerName: '',
    isHost: false,
    ws: null,
    gameState: null,
};

// ── View Management ──
export function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const el = document.getElementById(viewId);
    if (el) el.classList.add('active');
}

// ── WebSocket ──
let wsReconnectTimer = null;
let wsIntentionalClose = false;

export function connectWs(roomId, playerId) {
    // Close existing connection if any
    if (state.ws) {
        wsIntentionalClose = true;
        state.ws.close();
        state.ws = null;
    }
    if (wsReconnectTimer) {
        clearTimeout(wsReconnectTimer);
        wsReconnectTimer = null;
    }
    wsIntentionalClose = false;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/${roomId}/${playerId}`;

    const ws = new WebSocket(url);
    state.ws = ws;

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        if (wsIntentionalClose) return;
        console.log('WebSocket disconnected, reconnecting in 3s...');
        wsReconnectTimer = setTimeout(() => {
            if (state.roomId && state.playerId) {
                connectWs(state.roomId, state.playerId);
            }
        }, 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket error', err);
    };
}

export function sendAction(action) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: 'action', ...action }));
    }
}

export function sendMessage(type, data = {}) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type, ...data }));
    }
}

// ── Message Router ──
function handleMessage(data) {
    switch (data.type) {
        case 'game_state':
            state.gameState = data.state;
            if (data.state.phase === 'lobby') {
                updateWaitingRoom(data.state);
            } else {
                showView('view-game');
                handleGameState(data.state);
            }
            break;

        case 'events':
            handleEvents(data.events);
            break;

        case 'player_connected':
            addEventLog(`${data.player_name} anslöt`);
            break;

        case 'player_disconnected':
            addEventLog(`${data.player_name} tappade anslutningen`);
            break;

        case 'chat':
            addEventLog(`${data.player_name}: ${data.message}`);
            break;

        case 'error':
            console.error('Server error:', data.message);
            addEventLog(`Fel: ${data.message}`);
            break;
    }
}

// ── Waiting Room ──
function updateWaitingRoom(gameState) {
    showView('view-waiting');
    const nameEl = document.getElementById('waiting-room-name');
    nameEl.textContent = gameState.name || 'Spelrum';

    const playersEl = document.getElementById('waiting-players');
    playersEl.innerHTML = gameState.players.map(p => `
        <div class="player-item">
            <div class="player-dot" style="background:${p.color}"></div>
            <span class="name">${p.name}</span>
            ${p.id === state.playerId ? '<span class="badge">Du</span>' : ''}
        </div>
    `).join('');

    const startBtn = document.getElementById('btn-start');
    const waitMsg = document.getElementById('waiting-msg');
    if (state.isHost) {
        startBtn.style.display = 'block';
        waitMsg.style.display = 'none';
        startBtn.onclick = () => {
            sendMessage('start_game');
            startBtn.disabled = true;
        };

        // Provspels-genvägar: hoppa direkt till Skede 2 eller Skede 3 med standardportfölj.
        let presetWrap = document.getElementById('preset-buttons');
        if (!presetWrap) {
            presetWrap = document.createElement('div');
            presetWrap.id = 'preset-buttons';
            presetWrap.style.marginTop = '12px';
            presetWrap.style.display = 'flex';
            presetWrap.style.gap = '8px';
            presetWrap.style.justifyContent = 'center';
            presetWrap.innerHTML = `
                <button id="btn-preset-s2" class="btn-secondary" style="font-size:0.85em;padding:8px 12px;">
                    ⏭ Starta i Skede 2 (provspel)
                </button>
                <button id="btn-preset-s3" class="btn-secondary" style="font-size:0.85em;padding:8px 12px;">
                    ⏭ Starta i Skede 3 (provspel)
                </button>
            `;
            startBtn.parentElement.appendChild(presetWrap);
        }
        document.getElementById('btn-preset-s2').onclick = () => {
            sendMessage('start_game_preset', { preset: 'skede_2' });
            startBtn.disabled = true;
        };
        document.getElementById('btn-preset-s3').onclick = () => {
            sendMessage('start_game_preset', { preset: 'skede_3' });
            startBtn.disabled = true;
        };
    } else {
        startBtn.style.display = 'none';
        waitMsg.style.display = 'block';
    }
}

// ── Event Log ──
export function addEventLog(text, icon = '') {
    const list = document.getElementById('event-list');
    if (!list) return;
    const entry = document.createElement('div');
    entry.className = 'event-entry';
    entry.innerHTML = `<span class="ev-icon">${icon}</span>${text}`;
    list.prepend(entry);
    // Keep max 50 entries
    while (list.children.length > 50) {
        list.removeChild(list.lastChild);
    }
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    initLobby();
    initGame();
});
