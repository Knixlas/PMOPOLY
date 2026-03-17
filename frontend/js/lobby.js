/**
 * PMOPOLY - Lobby management
 */
import { state, showView, connectWs } from './app.js';

export function initLobby() {
    document.getElementById('btn-create').addEventListener('click', createRoom);
    document.getElementById('btn-refresh').addEventListener('click', refreshRooms);
    refreshRooms();
}

async function createRoom() {
    const hostName = document.getElementById('host-name').value.trim() || 'Spelare 1';
    const roomName = document.getElementById('room-name').value.trim() || 'Spelrum';

    try {
        const res = await fetch('/api/rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: roomName, host_name: hostName }),
        });
        const data = await res.json();

        state.roomId = data.room_id;
        state.playerId = data.player_id;
        state.playerName = hostName;
        state.isHost = true;

        connectWs(data.room_id, data.player_id);
        showView('view-waiting');
    } catch (err) {
        console.error('Failed to create room:', err);
        alert('Kunde inte skapa rum. Är servern igång?');
    }
}

async function refreshRooms() {
    const listEl = document.getElementById('room-list');
    try {
        const res = await fetch('/api/rooms');
        const data = await res.json();
        const rooms = data.rooms || [];

        if (rooms.length === 0) {
            listEl.innerHTML = '<p class="muted">Inga öppna rum just nu</p>';
            return;
        }

        listEl.innerHTML = rooms.map(r => `
            <div class="room-item" data-room-id="${r.room_id}">
                <div class="room-info">
                    <strong>${r.name}</strong>
                    <small>${r.players}/${r.max_players} spelare - ${r.player_names.join(', ')}</small>
                </div>
                <button class="btn btn-small btn-primary btn-join" data-room-id="${r.room_id}">
                    Gå med
                </button>
            </div>
        `).join('');

        listEl.querySelectorAll('.btn-join').forEach(btn => {
            btn.addEventListener('click', () => joinRoom(btn.dataset.roomId));
        });
    } catch (err) {
        listEl.innerHTML = '<p class="muted">Kunde inte ladda rum</p>';
    }
}

async function joinRoom(roomId) {
    const name = document.getElementById('join-name').value.trim() || 'Spelare';

    try {
        const res = await fetch(`/api/rooms/${roomId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Kunde inte gå med');
            return;
        }

        const data = await res.json();
        state.roomId = data.room_id;
        state.playerId = data.player_id;
        state.playerName = name;
        state.isHost = false;

        connectWs(data.room_id, data.player_id);
        showView('view-waiting');
    } catch (err) {
        alert('Kunde inte gå med i rummet');
    }
}
