"""Game engine - processes player actions and advances game state."""
import re
import random
import copy
from typing import Optional, Dict, List
from models import GamePhase, Player, Project, PlanningEventCard, roll
from room_manager import GameRoom
from economics import calc_phase1_economics, handle_abt_overflow
from config import (
    BOARD_SQUARES, EXPANSION_MIN, EXPANSION_MAX, EXPANSION_KOSTNAD,
    MAX_PROJECTS, MAX_BTA, START_Q_KRAV, START_H_KRAV,
    PLANNING_ORDER, SLOT_TO_CARD_IDS, MIN_T,
    PHASE_COST, ENERGY_CLASSES,
    YIELD_START_BOSTADER, YIELD_START_KOMMERSIELLT, LOAN_RATIO,
    BOSTADER_TYPES, KOMMERSIELLT_TYPES, PROJECT_TYPE_TO_EVENT,
    EK_FV_MODIFIER, QUARTER_NEW_PROPS, RENT_SCALE,
    ENERGY_UPGRADE_COST_PER_STEP, ENERGY_UPGRADE_D20_THRESHOLD, DICE_MAP,
    SKIP_PUZZLE_PLACEMENT, USE_F2_STAFF, SKIP_MGMT_EVENTS,
    EK_DN_MODIFIER, MV_MULTIPLIERS, EFFECTIVE_DN_ABS_MAX, YIELD_QUEUE_SIZE,
    SKEDE3_KASSA_FAKTOR, SKEDE3_DIVISOR,
)


def _staff_pool(game_data):
    """Returnera personalpool för Skede 3-anställning. Använder F2-arketyperna
    (lon=0, kapacitet=stor) om USE_F2_STAFF är satt, annars gamla F_personal."""
    if USE_F2_STAFF and getattr(game_data, 'f2_staff_objects', None):
        return game_data.f2_staff_objects
    return game_data.staff


def process_action(room: GameRoom, player_id: str, action: dict) -> dict:
    """Process a player action. Returns update dict to broadcast."""
    player = room.get_player(player_id)
    if not player:
        return {"type": "error", "message": "Okänd spelare"}

    # play_personkort kan spelas reaktivt även om det inte är spelarens tur.
    if action.get("action") == "play_personkort" and room.phase == GamePhase.PHASE4_FORVALTNING:
        return _handle_forvaltning(room, player, action)

    # Check it's this player's turn (puzzle phase allows simultaneous play)
    if room.phase != GamePhase.PUZZLE_PLACEMENT:
        if room.pending_action and room.pending_action.get("player_id") != player_id:
            return {"type": "error", "message": "Det är inte din tur"}

    action_type = action.get("action")

    # Route to phase handler
    if room.phase == GamePhase.PUZZLE_PLACEMENT:
        return _handle_puzzle(room, player, action)
    elif room.phase == GamePhase.PHASE1_MARK_TOMT:
        return _handle_mark_tomt(room, player, action)
    elif room.phase == GamePhase.PHASE1_PC_HIRE:
        return _handle_pc_hire(room, player, action)
    elif room.phase == GamePhase.PHASE1_BOARD:
        return _handle_board(room, player, action)
    elif room.phase == GamePhase.PHASE1_NAMNDBESLUT:
        return _handle_namndbeslut(room, player, action)
    elif room.phase == GamePhase.PHASE1_PLACEMENT:
        return _handle_placement(room, player, action)
    elif room.phase == GamePhase.PHASE1_EKONOMI:
        return _handle_ekonomi(room, player, action)
    elif room.phase == GamePhase.PHASE2_AC_HIRE:
        return _handle_ac_hire(room, player, action)
    elif room.phase == GamePhase.PHASE2_PLANERING:
        return _handle_planering(room, player, action)
    elif room.phase == GamePhase.PHASE3_GENOMFORANDE:
        return _handle_genomforande(room, player, action)
    elif room.phase == GamePhase.PHASE4_FORVALTNING:
        return _handle_forvaltning(room, player, action)
    else:
        return {"type": "error", "message": f"Oväntad fas: {room.phase}"}


# ═══════════════════════════════════════════
#  PHASE 1A: MARK OCH TOMT
# ═══════════════════════════════════════════

def _handle_mark_tomt(room: GameRoom, player: Player, action: dict) -> dict:
    action_type = action.get("action")

    if room.sub_state == "pick_project_type":
        typ = action.get("value")
        if typ not in room.projekt_stacks or not room.projekt_stacks[typ]:
            return {"type": "error", "message": "Ingen projekt av den typen kvar"}

        # Draw top project
        project = room.projekt_stacks[typ].pop(0)
        player.projects.append(project)
        player.q_krav += project.kvalitet
        player.h_krav += project.hallbarhet

        event = {
            "type": "project_acquired",
            "player_id": player.id,
            "player_name": player.name,
            "project": project.to_dict(),
            "text": f"{player.name} väljer {project.namn} ({project.typ})",
        }
        room.events_log.append(event)

        # Next player or advance phase
        room.next_turn()
        if room.turn_index == 0:
            # All players have picked — move to board game
            room.phase = GamePhase.PHASE1_BOARD
            room.turn_index = 0
            _setup_board_turn(room)
        else:
            room._setup_mark_tomt_action()

        return {"type": "state_update", "events": [event]}

    return {"type": "error", "message": "Okänd åtgärd"}


# ═══════════════════════════════════════════
#  PHASE 1: PC HIRE
# ═══════════════════════════════════════════

def _setup_pc_hire(room: GameRoom):
    """Set up PC hiring for current player."""
    player = room.current_player
    hired_ids = room.temp.get("pc_hired_ids", set())
    available = [pc for pc in room.game_data.pc_staff if pc["id"] not in hired_ids]
    room.sub_state = "choose_pc"
    room.pending_action = {
        "action": "choose_pc",
        "player_id": player.id,
        "available": available,
        "message": f"{player.name}, välj din Projektchef (PC).",
    }


def _handle_pc_hire(room: GameRoom, player, action: dict) -> dict:
    pc_id = action.get("value")
    hired_ids = room.temp.get("pc_hired_ids", set())
    pc = next((p for p in room.game_data.pc_staff if p["id"] == pc_id and pc_id not in hired_ids), None)
    if not pc:
        return {"type": "error", "message": "Ogiltig PC"}

    player.projektchef = dict(pc)
    hired_ids.add(pc_id)
    room.temp["pc_hired_ids"] = hired_ids

    event = {"type": "event", "text": f"{player.name} anställer {pc['namn']} som Projektchef"}
    room.events_log.append(event)

    room.next_turn()
    if room.turn_index == 0:
        # All players hired — move to mark & tomt (project selection)
        room.phase = GamePhase.PHASE1_MARK_TOMT
        room.turn_index = 0
        room._setup_mark_tomt_action()
    else:
        _setup_pc_hire(room)

    return {"type": "state_update", "events": [event]}


# ═══════════════════════════════════════════
#  PHASE 1B: BOARD GAME
# ═══════════════════════════════════════════

def _setup_board_turn(room: GameRoom):
    """Set up the current player's board turn."""
    player = room.current_player
    room.sub_state = "roll_dice"
    room.pending_action = {
        "action": "roll_dice",
        "player_id": player.id,
        "message": f"{player.name}, slå tärningen (D6)!",
    }


def _handle_board(room: GameRoom, player: Player, action: dict) -> dict:
    action_type = action.get("action")

    if room.sub_state == "roll_dice":
        result = roll("D6")
        old_pos = player.position
        new_pos = old_pos + result

        events = []

        # Check if passing start (Stadsbyggnadskontoret = pos 1)
        if new_pos > 24:
            new_pos = new_pos - 24
            player.laps += 1
            events.append({
                "type": "lap_complete",
                "player_id": player.id,
                "player_name": player.name,
                "laps": player.laps,
                "text": f"{player.name} passerar Stadsbyggnadskontoret! (Varv {player.laps})",
            })

            # Draw mark expansion piece on passing start
            if room.mark_expansion_deck:
                piece = room.mark_expansion_deck.pop(0)
                player.mark_expansion_pieces.append(piece)
                player.mark_expansions += 1
                events.append({
                    "type": "expansion",
                    "player_id": player.id,
                    "cells": piece["cell_count"],
                    "piece_id": piece["id"],
                    "text": f"{player.name} får en markexpansion ({piece['cell_count']} rutor)",
                })

        player.position = new_pos
        square = BOARD_SQUARES[new_pos - 1]

        events.insert(0, {
            "type": "dice_result",
            "player_id": player.id,
            "player_name": player.name,
            "die": "D6",
            "result": result,
            "old_position": old_pos,
            "new_position": new_pos,
            "square": square,
            "text": f"{player.name} slår {result} och landar på {square['namn']}",
        })
        room.events_log.extend(events)

        # Resolve square
        return _resolve_square(room, player, square, events)

    elif room.sub_state == "choose_project":
        return _handle_choose_project(room, player, action)

    elif room.sub_state == "card_result":
        # Player clicked OK after seeing card result
        interactive = room.temp.get("card_interactive")
        if interactive:
            room.temp["card_interactive"] = None  # clear so we don't loop
            return _setup_card_interactive(room, player, interactive)
        return _finish_board_turn(room)

    elif room.sub_state == "stadshuset_choice":
        return _handle_stadshuset(room, player, action)

    elif room.sub_state == "roll_card_d20":
        # Player clicked "Roll D20" in card modal
        card = room.temp.get("current_card")
        d20_result = roll("D20")
        # PC erfarenhet lindrar alla händelsekort i Skede 1 (samma logik som
        # AC i Skede 2-3) — Lindring/Händelsemotstand är historik som ersattes.
        pc_bonus = 0
        if player.projektchef:
            pc_bonus = player.projektchef.get("erfarenhet", 0)
            d20_result += pc_bonus
        effect = _get_card_effect(card, d20_result)
        room.temp["d20_result"] = d20_result

        events = [{
            "type": "card_result",
            "player_id": player.id,
            "card": card.to_dict(),
            "d20_result": d20_result,
            "effect": effect,
            "text": f"{player.name}: D20={d20_result}: {effect}",
        }]
        room.events_log.extend(events)

        # Apply effect (returns interactive type if player choice needed)
        interactive = _apply_card_effect(player, effect, room)
        room.temp["card_interactive"] = interactive

        # Offer reroll if bad and has riskbuffert
        is_bad = d20_result <= 10 and player.riskbuffertar > 0
        if is_bad:
            room.sub_state = "use_riskbuffert"
            room.pending_action = {
                "action": "card_reroll",
                "player_id": player.id,
                "card": card.to_dict(),
                "d20_result": d20_result,
                "effect": effect,
                "riskbuffertar": player.riskbuffertar,
                "message": f"D20: {d20_result} → {effect}. Slå om?",
            }
        else:
            room.sub_state = "card_result"
            room.pending_action = {
                "action": "card_done",
                "player_id": player.id,
                "card": card.to_dict(),
                "d20_result": d20_result,
                "effect": effect,
                "message": f"D20: {d20_result} → {effect}",
            }

        return {"type": "state_update", "events": events}

    elif room.sub_state == "use_riskbuffert":
        use = action.get("value", False)
        if use and player.riskbuffertar > 0:
            player.riskbuffertar -= 1
            # Re-roll D20
            new_roll = roll("D20")
            room.temp["d20_result"] = new_roll
            card = room.temp.get("current_card")
            effect = _get_card_effect(card, new_roll)

            events = [{
                "type": "card_result",
                "player_id": player.id,
                "card": card.to_dict(),
                "d20_result": new_roll,
                "effect": effect,
                "text": f"{player.name} använder riskbuffert! Nytt slag: {new_roll} - {effect}",
            }]
            room.events_log.extend(events)

            # Apply effect (returns interactive type if player choice needed)
            interactive = _apply_card_effect(player, effect, room)
            room.temp["card_interactive"] = interactive

            room.sub_state = "card_result"
            room.pending_action = {
                "action": "card_done",
                "player_id": player.id,
                "card": card.to_dict(),
                "d20_result": new_roll,
                "effect": effect,
                "message": f"D20: {new_roll} → {effect}",
            }
            return {"type": "state_update", "events": events}
        else:
            # Keep result — check for interactive effect from original roll
            interactive = room.temp.get("card_interactive")
            if interactive:
                return _setup_card_interactive(room, player, interactive)
            return _finish_board_turn(room)

    elif room.sub_state == "card_swap_project":
        return _handle_swap_project(room, player, action)

    elif room.sub_state == "continue":
        return _finish_board_turn(room)

    return {"type": "error", "message": f"Okänd board sub_state: {room.sub_state}"}


def _resolve_square(room: GameRoom, player: Player, square: dict, events: list) -> dict:
    typ = square.get("typ")

    if typ == "projekt":
        # Offer project types
        project_types = square.get("projekt_typer", [])
        available = []
        for pt in project_types:
            if pt in room.projekt_stacks and room.projekt_stacks[pt]:
                available.append({
                    "typ": pt,
                    "top": room.projekt_stacks[pt][0].to_dict(),
                    "count": len(room.projekt_stacks[pt]),
                })
        if available:
            room.sub_state = "choose_project"
            room.temp["available_types"] = available
            room.pending_action = {
                "action": "choose_project",
                "player_id": player.id,
                "options": available,
                "can_skip": True,
                "message": f"Välj ett projekt eller hoppa över",
            }
        else:
            return _finish_board_turn(room, events)

    elif typ in ("stjarna", "riskbuffert"):
        # "stjarna" är legacy-namnet på samma mekanik. Nya brädet (PU_spelbräde2)
        # använder "riskbuffert".
        player.riskbuffertar += 1
        events.append({
            "type": "riskbuffert",
            "player_id": player.id,
            "text": f"{player.name} får +1 riskbuffert (har nu {player.riskbuffertar})",
        })
        room.events_log.extend(events[-1:])
        return _finish_board_turn(room, events)

    elif typ == "kort":
        kort_typ = square.get("kort_typ", "dialog")
        return _draw_card(room, player, kort_typ, events)

    elif typ == "stadshuset":
        room.sub_state = "stadshuset_choice"
        room.pending_action = {
            "action": "stadshuset_choice",
            "player_id": player.id,
            "options": ["take", "return", "swap", "skip"],
            "message": "Stadshuset: Välj vad du vill göra",
        }

    elif typ == "start":
        # Stadsbyggnadskontoret - expansion handled in movement
        return _finish_board_turn(room, events)

    elif typ == "lansstyrelsen":
        player.h_krav = max(0, player.h_krav - 2)
        events.append({
            "type": "effect",
            "player_id": player.id,
            "text": f"{player.name}: Länsstyrelsen sänker hållbarhetskrav med 2 (nu {player.h_krav})",
        })
        room.events_log.extend(events[-1:])
        return _finish_board_turn(room, events)

    elif typ == "skonhetsradet":
        player.q_krav = max(0, player.q_krav - 2)
        events.append({
            "type": "effect",
            "player_id": player.id,
            "text": f"{player.name}: Skönhetsrådet sänker kvalitetskrav med 2 (nu {player.q_krav})",
        })
        room.events_log.extend(events[-1:])
        return _finish_board_turn(room, events)

    return {"type": "state_update", "events": events}


def _handle_choose_project(room: GameRoom, player: Player, action: dict) -> dict:
    value = action.get("value")
    events = []

    if value == "skip":
        events.append({"type": "event", "text": f"{player.name} hoppar över"})
        room.events_log.extend(events)
        return _finish_board_turn(room, events)

    # Find project type
    typ = value
    if typ in room.projekt_stacks and room.projekt_stacks[typ]:
        project = room.projekt_stacks[typ].pop(0)
        player.projects.append(project)
        player.q_krav += project.kvalitet
        player.h_krav += project.hallbarhet
        events.append({
            "type": "project_acquired",
            "player_id": player.id,
            "player_name": player.name,
            "project": project.to_dict(),
            "text": f"{player.name} tar {project.namn} ({project.typ})",
        })
        room.events_log.extend(events)
    else:
        events.append({"type": "event", "text": "Inga projekt kvar av den typen"})

    return _finish_board_turn(room, events)


def _setup_card_interactive(room: GameRoom, player: Player, interactive: str) -> dict:
    """After card result, set up interactive choice (take/swap project)."""
    events = []

    if interactive == "take_project":
        # Offer all project stacks
        available = []
        for typ, stack in room.projekt_stacks.items():
            if stack:
                available.append({
                    "typ": typ,
                    "top": stack[0].to_dict(),
                    "count": len(stack),
                })
        if available:
            room.sub_state = "choose_project"
            room.pending_action = {
                "action": "choose_project",
                "player_id": player.id,
                "options": available,
                "can_skip": True,
                "message": "Korteffekt: Ta ett projekt från valfri hög (eller hoppa över)",
            }
            return {"type": "state_update", "events": events}

    elif interactive == "swap_project":
        # Offer player's projects to swap
        if player.projects:
            proj_list = [
                {"id": p.id, "namn": p.namn, "typ": p.typ, "bta": p.bta,
                 "formfaktor": p.formfaktor, "anskaffning": p.anskaffning}
                for p in player.projects
                if p.typ in room.projekt_stacks and room.projekt_stacks[p.typ]
            ]
            if proj_list:
                room.sub_state = "card_swap_project"
                room.pending_action = {
                    "action": "card_swap_project",
                    "player_id": player.id,
                    "projects": proj_list,
                    "message": "Korteffekt: Byt ett projekt mot toppkortet av samma typ (eller hoppa över)",
                }
                return {"type": "state_update", "events": events}

    # No valid interactive action possible — finish turn
    return _finish_board_turn(room, events)


def _handle_swap_project(room: GameRoom, player: Player, action: dict) -> dict:
    """Handle card_swap_project action: swap a player's project for top of same type stack."""
    value = action.get("value")
    events = []

    if value == "skip":
        events.append({"type": "event", "text": f"{player.name} hoppar över byte"})
        room.events_log.extend(events)
        return _finish_board_turn(room, events)

    # Find the project to swap
    proj_to_swap = None
    for p in player.projects:
        if p.id == value:
            proj_to_swap = p
            break

    if not proj_to_swap:
        return _finish_board_turn(room, events)

    typ = proj_to_swap.typ
    if typ not in room.projekt_stacks or not room.projekt_stacks[typ]:
        events.append({"type": "event", "text": "Inga projekt kvar av den typen att byta mot"})
        return _finish_board_turn(room, events)

    # Remove old project's krav contribution
    player.q_krav = max(0, player.q_krav - proj_to_swap.kvalitet)
    player.h_krav = max(0, player.h_krav - proj_to_swap.hallbarhet)
    player.projects.remove(proj_to_swap)

    # Get new project from stack
    new_proj = room.projekt_stacks[typ].pop(0)
    player.projects.append(new_proj)
    player.q_krav += new_proj.kvalitet
    player.h_krav += new_proj.hallbarhet

    # Put old project back at bottom of stack
    room.projekt_stacks[typ].append(proj_to_swap)

    events.append({
        "type": "project_swapped",
        "player_id": player.id,
        "text": f"{player.name} byter {proj_to_swap.namn} mot {new_proj.namn}",
        "old_project": proj_to_swap.to_dict(),
        "new_project": new_proj.to_dict(),
    })
    room.events_log.extend(events)
    return _finish_board_turn(room, events)


def _draw_card(room: GameRoom, player: Player, kort_typ: str, events: list) -> dict:
    """Draw a Politik or Dialog card — show all outcomes, let player roll D20."""
    if kort_typ == "politik":
        deck = room.politik_deck
        cards = room.game_data.politik
    else:
        deck = room.dialog_deck
        cards = room.game_data.dialog

    if not deck:
        # Reshuffle
        deck.extend(range(len(cards)))
        random.shuffle(deck)

    card_idx = deck.pop(0)
    card = cards[card_idx]

    room.temp["current_card"] = card

    events.append({
        "type": "card_drawn",
        "player_id": player.id,
        "card": card.to_dict(),
        "text": f"{player.name} drar {card.typ}-kort: {card.rubrik}",
    })
    room.events_log.extend(events[-1:])

    # Wait for player to roll D20
    room.sub_state = "roll_card_d20"
    room.pending_action = {
        "action": "roll_card_d20",
        "player_id": player.id,
        "card": card.to_dict(),
        "message": "Slå D20 för att bestämma utfall",
    }

    return {"type": "state_update", "events": events}


def _get_card_effect(card, d20_result: int) -> str:
    """Get effect text for a D20 roll on a card."""
    effects = card.effects if hasattr(card, 'effects') else card.get("effects", {})
    if d20_result <= 1:
        return effects.get("1", "Ingen effekt")
    elif d20_result <= 10:
        return effects.get("2-10", "Ingen effekt")
    elif d20_result <= 15:
        return effects.get("11-15", "Ingen effekt")
    elif d20_result <= 19:
        return effects.get("16-19", "Ingen effekt")
    else:
        return effects.get("20", "Ingen effekt")


def _apply_card_effect(player: Player, effect_text: str, room: GameRoom) -> str:
    """Parse and apply effect text. Returns interactive action type or None.

    Interactive types: 'take_project', 'swap_project', 'markanvisning', None
    """
    if not effect_text or effect_text.lower() == "ingen effekt":
        return None

    text = effect_text.lower()

    # --- Interactive effects (don't apply immediately, return type) ---
    if "ta projekt" in text and "valfri" in text:
        return "take_project"
    if "byt projekt" in text:
        return "swap_project"
    if "markanvisning" in text:
        return "take_project"  # treat same as take from any stack

    # --- Immediate effects ---

    # Riskbuffert (+)
    if "riskbuffert" in text:
        m = re.search(r'[+]?\s*(\d+)\s*riskbuffert', text)
        if m:
            player.riskbuffertar += int(m.group(1))

    # Kvalitetskrav
    if "kvalitetskrav" in text:
        m_plus = re.search(r'[+]\s*(\d+)\s*kvalitetskrav', text)
        m_minus = re.search(r'[-]\s*(\d+)\s*kvalitetskrav', text)
        if m_plus:
            player.q_krav += int(m_plus.group(1))
        if m_minus:
            player.q_krav = max(0, player.q_krav - int(m_minus.group(1)))

    # Hållbarhetskrav
    if "hållbarhetskrav" in text or "hallbarhetskrav" in text:
        m_plus = re.search(r'[+]\s*(\d+)\s*h.llbarhetskrav', text)
        m_minus = re.search(r'[-]\s*(\d+)\s*h.llbarhetskrav', text)
        if m_plus:
            player.h_krav += int(m_plus.group(1))
        if m_minus:
            player.h_krav = max(0, player.h_krav - int(m_minus.group(1)))

    # Tid (- tid = bonus to build time)
    if "tid" in text:
        m = re.search(r'[-]\s*(\d+)\s*tid', text)
        if m:
            player.t_bonus += int(m.group(1))

    # Return project
    if "lämna tillbaka" in text:
        if player.projects:
            if "högst intäkt" in text or "intäkt" in text:
                proj = max(player.projects, key=lambda p: p.anskaffning)
            else:
                proj = player.projects[-1]
            player.projects.remove(proj)
            room.used_projects.append(proj.id)

    return None


def _handle_stadshuset(room: GameRoom, player: Player, action: dict) -> dict:
    choice = action.get("value")
    events = []

    if choice == "take":
        # Offer all project types
        available = []
        for typ, stack in room.projekt_stacks.items():
            if stack:
                available.append({
                    "typ": typ,
                    "top": stack[0].to_dict(),
                    "count": len(stack),
                })
        if available:
            room.sub_state = "choose_project"
            room.temp["available_types"] = available
            room.pending_action = {
                "action": "choose_project",
                "player_id": player.id,
                "options": available,
                "can_skip": True,
                "message": "Välj ett projekt från valfri typ",
            }
            return {"type": "state_update", "events": events}

    elif choice == "return":
        if player.projects:
            proj = player.projects.pop()
            room.used_projects.append(proj.id)
            events.append({
                "type": "event",
                "text": f"{player.name} lämnar tillbaka {proj.namn}",
            })

    elif choice == "swap":
        events.append({"type": "event", "text": f"{player.name} byter inte"})

    room.events_log.extend(events)
    return _finish_board_turn(room, events)


def _finish_board_turn(room: GameRoom, events: list = None) -> dict:
    """Finish current player's board turn, check game end."""
    if events is None:
        events = []

    # Check if game should end (any player completed 2 laps)
    game_over = any(p.laps >= 2 for p in room.players)

    if game_over:
        # Move to Nämndbeslut
        room.phase = GamePhase.PHASE1_NAMNDBESLUT
        room.turn_index = 0
        _setup_namndbeslut(room)
        events.append({
            "type": "phase_change",
            "phase": "phase1_namndbeslut",
            "text": "Brädspelet är slut! Dags för nämndbeslut.",
        })
    else:
        room.next_turn()
        _setup_board_turn(room)

    return {"type": "state_update", "events": events}


# ═══════════════════════════════════════════
#  PHASE 1C: NÄMNDBESLUT
# ═══════════════════════════════════════════

def _setup_namndbeslut(room: GameRoom):
    player = room.current_player
    # Find next project needing approval
    pending = [p for p in player.projects if p.namndbeslut > 1]

    if pending:
        proj = pending[0]
        room.sub_state = "namndbeslut_roll"
        room.temp["current_project"] = proj
        room.pending_action = {
            "action": "roll_namndbeslut",
            "player_id": player.id,
            "project": proj.to_dict(),
            "threshold": proj.namndbeslut,
            "message": f"Nämndbeslut för {proj.namn}: Behöver minst {proj.namndbeslut} på D20",
        }
    else:
        # This player has no pending decisions, move to next
        _advance_namndbeslut(room)


def _handle_namndbeslut(room: GameRoom, player: Player, action: dict) -> dict:
    events = []

    if room.sub_state == "namndbeslut_roll":
        result = roll("D20")
        # PC nämndbonus
        pc_namnd = 0
        if player.projektchef:
            pc_namnd = player.projektchef.get("namnd_bonus", 0)
            result += pc_namnd
        proj = room.temp.get("current_project")
        threshold = proj.namndbeslut if proj else 1
        passed = result >= threshold

        events.append({
            "type": "namndbeslut",
            "player_id": player.id,
            "project": proj.to_dict() if proj else {},
            "result": result,
            "threshold": threshold,
            "passed": passed,
            "text": f"D20={result} (behöver ≥{threshold}): {'GODKÄNT!' if passed else 'AVSLAG'}",
        })
        room.events_log.extend(events)

        if passed:
            # Project approved, continue
            _advance_namndbeslut(room)
        else:
            # Can reroll with riskbuffert?
            if player.riskbuffertar > 0:
                room.sub_state = "namndbeslut_reroll"
                room.pending_action = {
                    "action": "use_riskbuffert",
                    "player_id": player.id,
                    "riskbuffertar": player.riskbuffertar,
                    "message": f"Avslaget! Vill du använda riskbuffert för omslag? ({player.riskbuffertar} kvar)",
                }
            else:
                # Remove project
                if proj in player.projects:
                    player.projects.remove(proj)
                    room.used_projects.append(proj.id)
                    events.append({
                        "type": "event",
                        "text": f"{proj.namn} avslogs och lämnas tillbaka",
                    })
                _advance_namndbeslut(room)

        return {"type": "state_update", "events": events}

    elif room.sub_state == "namndbeslut_reroll":
        use = action.get("value", False)
        proj = room.temp.get("current_project")

        if use and player.riskbuffertar > 0:
            player.riskbuffertar -= 1
            result = roll("D20")
            threshold = proj.namndbeslut if proj else 1
            passed = result >= threshold

            events.append({
                "type": "namndbeslut",
                "player_id": player.id,
                "result": result,
                "threshold": threshold,
                "passed": passed,
                "text": f"Omslag D20={result}: {'GODKÄNT!' if passed else 'AVSLAG'}",
            })
            room.events_log.extend(events)

            if not passed:
                if proj in player.projects:
                    player.projects.remove(proj)
                    room.used_projects.append(proj.id)

        else:
            # Declined reroll - remove project
            if proj and proj in player.projects:
                player.projects.remove(proj)
                room.used_projects.append(proj.id)

        _advance_namndbeslut(room)
        return {"type": "state_update", "events": events}

    return {"type": "error", "message": "Okänd namndbeslut-åtgärd"}


def _advance_namndbeslut(room: GameRoom):
    """Move to next project or next player in namndbeslut."""
    player = room.current_player
    pending = [p for p in player.projects if p.namndbeslut > 1]

    # Mark checked projects (using temp to track)
    checked = room.temp.get("checked_projects", set())
    for p in player.projects:
        if p.namndbeslut > 1:
            checked.add(p.id)
    room.temp["checked_projects"] = checked

    # All done for this player - check next player
    room.next_turn()
    if room.turn_index == 0:
        # All players done - move to placement
        room.phase = GamePhase.PHASE1_PLACEMENT
        room.turn_index = 0
        room.temp = {}
        _setup_placement(room)
    else:
        room.temp = {}
        _setup_namndbeslut(room)


# ═══════════════════════════════════════════
#  PHASE 1D: PLACEMENT
# ═══════════════════════════════════════════

def _setup_placement(room: GameRoom):
    # No longer force return_project here — the puzzle phase handles
    # which projects fit. Players keep all projects and pay dev cost
    # for any that don't fit on the grid.
    _advance_placement(room)


def _handle_placement(room: GameRoom, player: Player, action: dict) -> dict:
    if room.sub_state == "return_project":
        project_id = action.get("value")
        proj = next((p for p in player.projects if p.id == project_id), None)
        if proj:
            player.projects.remove(proj)
            room.used_projects.append(proj.id)

        # Check again
        _setup_placement(room)
        return {"type": "state_update", "events": [{
            "type": "event",
            "text": f"{player.name} lämnar tillbaka {proj.namn if proj else 'projekt'}",
        }]}

    return {"type": "error", "message": "Okänd placement-åtgärd"}


def _advance_placement(room: GameRoom):
    room.next_turn()
    if room.turn_index == 0:
        # All done - move to economics
        room.phase = GamePhase.PHASE1_EKONOMI
        room.turn_index = 0
        _setup_ekonomi(room)
    else:
        _setup_placement(room)


# ═══════════════════════════════════════════
#  PHASE 1E: EKONOMI
# ═══════════════════════════════════════════

def _setup_ekonomi(room: GameRoom):
    """Calculate economics for all players (no player input needed)."""
    events = []
    for player in room.players:
        player_events = []
        calc_phase1_economics(player, player_events)
        for e in player_events:
            e["player_id"] = player.id
            e["player_name"] = player.name
            e["text"] = (f"{player.name}: Intäkter {e['revenue']} Mkr, "
                        f"Kostnader {e['total_cost']} Mkr, ABT = {e['net']} Mkr")
        events.extend(player_events)

    room.events_log.extend(events)

    # Offer riskbuffert investment
    room.turn_index = 0
    _setup_riskbuffert_invest(room)


def _setup_riskbuffert_invest(room: GameRoom):
    player = room.current_player
    if player.riskbuffertar > 0:
        room.sub_state = "riskbuffert_invest"
        room.pending_action = {
            "action": "riskbuffert_invest",
            "player_id": player.id,
            "riskbuffertar": player.riskbuffertar,
            "q_krav": player.q_krav,
            "h_krav": player.h_krav,
            "message": f"Du har {player.riskbuffertar} riskbuffertar. Vill du investera? (Varje sänker Q/H-krav med 1 eller T med 1 mån)",
        }
    else:
        _advance_ekonomi(room)


def _handle_ekonomi(room: GameRoom, player: Player, action: dict) -> dict:
    if room.sub_state == "riskbuffert_invest":
        investments = action.get("value", [])
        events = []

        if isinstance(investments, list):
            for inv in investments:
                if inv == "q" and player.riskbuffertar > 0:
                    player.riskbuffertar -= 1
                    player.q_krav = max(0, player.q_krav - 1)
                    events.append({"type": "event", "text": f"{player.name}: -1 kvalitetskrav (nu {player.q_krav})"})
                elif inv == "h" and player.riskbuffertar > 0:
                    player.riskbuffertar -= 1
                    player.h_krav = max(0, player.h_krav - 1)
                    events.append({"type": "event", "text": f"{player.name}: -1 hållbarhetskrav (nu {player.h_krav})"})
                elif inv == "t" and player.riskbuffertar > 0:
                    player.riskbuffertar -= 1
                    player.t_bonus += 1
                    events.append({"type": "event", "text": f"{player.name}: -1 månad byggtid"})

        room.events_log.extend(events)
        _advance_ekonomi(room)
        return {"type": "state_update", "events": events}

    elif room.sub_state == "continue":
        # Skede 1 klar — gå vidare till pussel eller direkt till Skede 2.
        room.temp = {}
        if SKIP_PUZZLE_PLACEMENT:
            return _skip_puzzle_to_phase2(room)
        _setup_puzzle_phase(room)
        return {"type": "state_update", "events": [{
            "type": "phase_change",
            "phase": "puzzle_placement",
            "text": "Skede 1 klar! Placera era projekt på kvartersplanen.",
        }]}

    return {"type": "error", "message": "Okänd ekonomi-åtgärd"}


def _advance_ekonomi(room: GameRoom):
    room.next_turn()
    if room.turn_index == 0:
        # Show summary and continue button
        room.sub_state = "continue"
        room.pending_action = {
            "action": "continue",
            "player_id": room.players[0].id,  # Host continues
            "message": "Skede 1 klar! Klicka för att gå vidare till Planering.",
        }
    else:
        _setup_riskbuffert_invest(room)


# ═══════════════════════════════════════════
#  PHASE 2: PLANERING
# ═══════════════════════════════════════════

def _setup_planering(room: GameRoom):
    """Initialize Phase 2 for all players, then start first player's first step."""
    for p in room.players:
        max_t = max((proj.tid for proj in p.projects), default=0)
        p.pl_q = 0
        p.pl_h = 0
        p.pl_t = 12 + max_t - p.t_bonus
        p.pl_kostnad = 0.0
        # Initialize empty draw/discard piles
        room.pl_draw_piles[p.id] = []
        room.pl_discard_piles[p.id] = []

    room.turn_index = 0
    room.pl_step_index = 0
    room.temp = {}
    _setup_planering_step(room)


def _setup_planering_step(room: GameRoom):
    """Set up the current planning step for the current player."""
    player = room.current_player
    step_idx = room.pl_step_index
    slot_name, slot_type = PLANNING_ORDER[step_idx]

    # Add this slot's event cards to draw pile
    draw_pile = room.pl_draw_piles[player.id]
    card_ids = SLOT_TO_CARD_IDS.get(slot_name, [])
    new_cards = []
    for cid in card_ids:
        new_cards.extend(room.game_data.planning_events.get(cid, []))
    if new_cards:
        draw_pile.extend(copy.deepcopy(new_cards))
        random.shuffle(draw_pile)

    # Determine BYA/BTA class for pricing
    if slot_type == "lev":
        all_options = room.game_data.suppliers.get(slot_name, [])
        if all_options:
            beror_av = all_options[0].beror_av
            klass = player.bya_klass if beror_av == "BYA" else player.bta_klass
        else:
            beror_av = "BTA"
            klass = player.bta_klass

        # Get min required supplier level from project requirements
        min_level = _get_min_supplier_level(room, player, slot_name)
        available = [s for s in all_options if s.niva >= min_level]

        options = []
        for s in available:
            new_q = player.pl_q + s.q
            new_h = player.pl_h + s.h
            blocked = new_q < 0 or new_h < 0
            options.append({
                **s.to_dict(klass),
                "blocked": blocked,
                "block_reason": f"Q ({player.pl_q}{s.q:+d}={new_q}) eller H ({player.pl_h}{s.h:+d}={new_h}) under 0" if blocked else "",
            })

        room.sub_state = "choose_supplier"
        room.temp["slot_name"] = slot_name
        room.temp["slot_type"] = slot_type
        room.temp["klass"] = klass
        room.temp["beror_av"] = beror_av
        room.pending_action = {
            "action": "choose_supplier",
            "player_id": player.id,
            "step": step_idx + 1,
            "total_steps": 13,
            "slot_name": slot_name,
            "slot_type": "Leverantör",
            "klass": klass,
            "beror_av": beror_av,
            "options": options,
            "min_level": min_level,
            "message": f"Steg {step_idx + 1}/13: Välj leverantör för {slot_name} ({beror_av}-klass {klass})",
        }
    else:
        # Organisation
        all_options = room.game_data.organisations.get(slot_name, [])
        options = []
        for o in all_options:
            new_q = player.pl_q + o.q
            new_h = player.pl_h + o.h
            blocked = new_q < 0 or new_h < 0
            options.append({
                **o.to_dict(),
                "blocked": blocked,
                "block_reason": f"Q ({player.pl_q}{o.q:+d}={new_q}) eller H ({player.pl_h}{o.h:+d}={new_h}) under 0" if blocked else "",
            })

        room.sub_state = "choose_org"
        room.temp["slot_name"] = slot_name
        room.temp["slot_type"] = slot_type
        room.pending_action = {
            "action": "choose_org",
            "player_id": player.id,
            "step": step_idx + 1,
            "total_steps": 13,
            "slot_name": slot_name,
            "slot_type": "Organisation",
            "options": options,
            "message": f"Steg {step_idx + 1}/13: Välj organisation för {slot_name}",
        }


def _get_min_supplier_level(room: GameRoom, player: Player, supplier_type: str) -> int:
    """Get minimum required supplier level based on player's projects."""
    reqs = room.game_data.supplier_requirements.get(supplier_type, {})
    min_level = 1
    suppliers = room.game_data.suppliers.get(supplier_type, [])
    for proj in player.projects:
        req_text = reqs.get(proj.namn, "")
        if req_text:
            for s in suppliers:
                if s.beskrivning.lower() == req_text.lower():
                    min_level = max(min_level, s.niva)
                    break
    return min_level


def _handle_planering(room: GameRoom, player: Player, action: dict) -> dict:
    action_type = action.get("action")
    events = []

    if room.sub_state == "choose_supplier":
        niva = action.get("value")
        slot_name = room.temp.get("slot_name")
        klass = room.temp.get("klass", "C")

        all_options = room.game_data.suppliers.get(slot_name, [])
        chosen = next((s for s in all_options if s.niva == niva), None)
        if not chosen:
            return {"type": "error", "message": f"Ogiltig leverantörsnivå: {niva}"}

        # Validate Q/H constraint
        new_q = player.pl_q + chosen.q
        new_h = player.pl_h + chosen.h
        if new_q < 0 or new_h < 0:
            return {"type": "error", "message": f"Kan inte välja - Q eller H går under 0"}

        # Apply
        kostnad = chosen.kostnad(klass)
        player.pl_suppliers[slot_name] = chosen
        player.pl_q += chosen.q
        player.pl_h += chosen.h
        player.pl_t = max(MIN_T, player.pl_t + chosen.t)
        player.pl_kostnad += kostnad
        player.abt_budget -= kostnad
        if player.abt_budget < 0:
            handle_abt_overflow(player)
        if hasattr(chosen, 'riskbuffert') and chosen.riskbuffert:
            player.riskbuffertar += chosen.riskbuffert

        events.append({
            "type": "supplier_chosen",
            "player_id": player.id,
            "player_name": player.name,
            "slot_name": slot_name,
            "supplier": chosen.to_dict(klass),
            "text": f"{player.name} väljer {chosen.beskrivning} (nivå {chosen.niva}) för {slot_name} - Kostnad: {kostnad} Mkr",
        })
        room.events_log.extend(events)

        # Draw planning event card
        return _draw_planning_event(room, player, events)

    elif room.sub_state == "choose_org":
        niva = action.get("value")
        slot_name = room.temp.get("slot_name")

        all_options = room.game_data.organisations.get(slot_name, [])
        chosen = next((o for o in all_options if o.niva == niva), None)
        if not chosen:
            return {"type": "error", "message": f"Ogiltig organisationsnivå: {niva}"}

        new_q = player.pl_q + chosen.q
        new_h = player.pl_h + chosen.h
        if new_q < 0 or new_h < 0:
            return {"type": "error", "message": f"Kan inte välja - Q eller H går under 0"}

        # Apply
        player.pl_orgs[slot_name] = chosen
        player.pl_q += chosen.q
        player.pl_h += chosen.h
        player.pl_t = max(MIN_T, player.pl_t + chosen.t)
        player.pl_kostnad += chosen.kostnad_mkr
        player.abt_budget -= chosen.kostnad_mkr
        if player.abt_budget < 0:
            handle_abt_overflow(player)
        if chosen.riskbuffert:
            player.riskbuffertar += chosen.riskbuffert

        events.append({
            "type": "org_chosen",
            "player_id": player.id,
            "player_name": player.name,
            "slot_name": slot_name,
            "org": chosen.to_dict(),
            "text": f"{player.name} väljer {slot_name} nivå {chosen.niva} - Kostnad: {chosen.kostnad_mkr} Mkr",
        })
        room.events_log.extend(events)

        return _draw_planning_event(room, player, events)

    elif room.sub_state == "planning_event_roll":
        return _planning_event_do_roll(room, player, events)

    elif room.sub_state == "planning_event_reroll":
        use = action.get("value", False)
        card = room.temp.get("current_event_card")
        exp = room.temp.get("current_exp", 0)

        if use and player.riskbuffertar > 0:
            player.riskbuffertar -= 1
            new_d20 = roll("D20")
            total = new_d20 + exp
            effect = card.get_effect(total)

            # Undo previous effect
            _undo_planning_effect(player, room.temp.get("applied_effect", ""))
            # Apply new effect
            _apply_planning_effect(player, effect)
            room.temp["applied_effect"] = effect

            events.append({
                "type": "planning_reroll",
                "player_id": player.id,
                "d20": new_d20,
                "exp": exp,
                "total": total,
                "effect": effect,
                "text": f"{player.name} använder riskbuffert! Nytt slag: D20={new_d20} + {exp} erfarenhet = {total} → {effect}",
            })
            room.events_log.extend(events)

        # Continue to next step
        return _advance_planering_step(room, events)

    elif room.sub_state == "planning_event_continue":
        return _advance_planering_step(room, events)

    elif room.sub_state == "planering_summary":
        # Player acknowledged summary, move to next player or Phase 3
        return _advance_planering_player(room, events)

    return {"type": "error", "message": f"Okänd planering sub_state: {room.sub_state}"}


def _draw_planning_event(room: GameRoom, player: Player, events: list) -> dict:
    """Draw and resolve a planning event card."""
    draw_pile = room.pl_draw_piles.get(player.id, [])

    if not draw_pile:
        # No cards, skip event
        return _advance_planering_step(room, events)

    card = draw_pile.pop(0)
    room.pl_discard_piles.setdefault(player.id, []).append(card)

    # Check eligibility
    if not player.card_is_eligible(card):
        events.append({
            "type": "planning_event_skip",
            "player_id": player.id,
            "card": card.to_dict(),
            "text": f"Händelsekort '{card.namn}' aktiveras inte (kräver {card.trigger}, du har {player.kvarter_trigger})",
        })
        room.events_log.extend(events[-1:])
        return _advance_planering_step(room, events)

    # Calculate experience
    exp = player.total_erfarenhet

    # Show card and ask player to roll D20
    room.sub_state = "planning_event_roll"
    room.temp["current_event_card"] = card
    room.temp["current_exp"] = exp
    room.pending_action = {
        "action": "roll_d20",
        "player_id": player.id,
        "card": card.to_dict(),
        "typ": "Händelse",
        "erfarenhet": exp,
        "riskbuffertar": player.riskbuffertar,
        "message": f"Händelsekort: {card.namn}",
    }
    return {"type": "state_update", "events": events}


def _planning_event_do_roll(room: GameRoom, player: Player, events: list) -> dict:
    """Player clicked Roll D20 for planning event."""
    card = room.temp.get("current_event_card")
    exp = room.temp.get("current_exp", 0)

    d20 = roll("D20")
    total = d20 + exp
    effect = card.get_effect(total)

    # Apply effect
    _apply_planning_effect(player, effect)

    events.append({
        "type": "dice_result",
        "player_id": player.id,
        "die": "D20",
        "result": d20,
        "text": f"{player.name} slog D20: {d20} + {exp} erfarenhet = {total}",
    })
    events.append({
        "type": "planning_event",
        "player_id": player.id,
        "player_name": player.name,
        "card": card.to_dict(),
        "d20": d20,
        "exp": exp,
        "total": total,
        "effect": effect,
        "text": f"Händelse: {card.namn} - D20={d20}+{exp}={total} → {effect}",
    })
    room.events_log.extend(events[-1:])

    # Offer reroll if bad result
    if player.riskbuffertar > 0 and total <= 5:
        room.sub_state = "planning_event_reroll"
        room.temp["applied_effect"] = effect
        room.pending_action = {
            "action": "use_riskbuffert",
            "player_id": player.id,
            "riskbuffertar": player.riskbuffertar,
            "current_effect": effect,
            "d20": d20,
            "exp": exp,
            "total": total,
            "card": card.to_dict(),
            "message": f"Effekt: {effect}. Vill du använda riskbuffert för omslag? ({player.riskbuffertar} kvar)",
        }
        return {"type": "state_update", "events": events}

    # No reroll needed/possible, continue
    room.sub_state = "planning_event_continue"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": "Klicka för att fortsätta",
    }
    return {"type": "state_update", "events": events}


def _apply_planning_effect(player: Player, effect_text: str):
    """Parse and apply a planning event effect."""
    if not effect_text or effect_text.lower() == "ingen effekt":
        return

    text = effect_text
    # Handle scaled effects (A-B // C-D)
    if "//" in text:
        parts = text.split("//")
        klass_upper = player.bta_klass.upper()
        chosen = parts[0].strip()
        for part in parts:
            ps = part.strip()
            if klass_upper in ("A", "B") and "A-B" in ps:
                chosen = ps
                break
            elif klass_upper in ("C", "D") and "C-D" in ps:
                chosen = ps
                break
        text = chosen

    # Remove label prefix
    if ":" in text:
        text = text.split(":", 1)[1].strip()

    # Parse Mkr
    for m in re.findall(r'([+-]?\d+)\s*Mkr', text):
        player.abt_budget += int(m)
        if player.abt_budget < 0:
            handle_abt_overflow(player)

    # Parse months
    for m in re.findall(r'([+-]?\d+)\s*mån', text):
        player.pl_t = max(MIN_T, player.pl_t + int(m))

    # Parse Q
    for m in re.findall(r'([+-]?\d+)\s*Q', text):
        player.pl_q += int(m)

    # Parse H
    for m in re.findall(r'([+-]?\d+)\s*H', text):
        player.pl_h += int(m)

    # Parse Riskbuffert
    for m in re.findall(r'([+-]?\d+)\s*Rb', text):
        player.riskbuffertar += int(m)


def _undo_planning_effect(player: Player, effect_text: str):
    """Reverse a previously applied planning effect (for reroll)."""
    if not effect_text or effect_text.lower() == "ingen effekt":
        return

    text = effect_text
    if "//" in text:
        parts = text.split("//")
        klass_upper = player.bta_klass.upper()
        chosen = parts[0].strip()
        for part in parts:
            ps = part.strip()
            if klass_upper in ("A", "B") and "A-B" in ps:
                chosen = ps
                break
            elif klass_upper in ("C", "D") and "C-D" in ps:
                chosen = ps
                break
        text = chosen

    if ":" in text:
        text = text.split(":", 1)[1].strip()

    for m in re.findall(r'([+-]?\d+)\s*Mkr', text):
        player.abt_budget -= int(m)
    for m in re.findall(r'([+-]?\d+)\s*mån', text):
        player.pl_t = max(MIN_T, player.pl_t - int(m))
    for m in re.findall(r'([+-]?\d+)\s*Q', text):
        player.pl_q -= int(m)
    for m in re.findall(r'([+-]?\d+)\s*H', text):
        player.pl_h -= int(m)
    for m in re.findall(r'([+-]?\d+)\s*Rb', text):
        player.riskbuffertar -= int(m)


def _advance_planering_step(room: GameRoom, events: list) -> dict:
    """Move to next planning step or show summary."""
    room.pl_step_index += 1

    if room.pl_step_index >= 13:
        # All 13 steps done for this player - show summary
        player = room.current_player
        q_ok = player.pl_q >= player.q_krav
        h_ok = player.pl_h >= player.h_krav
        t_ok = player.pl_t <= 12

        events.append({
            "type": "planning_complete",
            "player_id": player.id,
            "player_name": player.name,
            "pl_q": player.pl_q, "q_krav": player.q_krav, "q_ok": q_ok,
            "pl_h": player.pl_h, "h_krav": player.h_krav, "h_ok": h_ok,
            "pl_t": player.pl_t, "t_ok": t_ok,
            "pl_kostnad": round(player.pl_kostnad, 1),
            "abt_budget": round(player.abt_budget, 1),
            "text": f"{player.name} – Planering klar! Q:{player.pl_q}/{player.q_krav} H:{player.pl_h}/{player.h_krav} T:{player.pl_t} mån",
        })
        room.events_log.extend(events[-1:])

        room.sub_state = "planering_summary"
        room.pending_action = {
            "action": "continue",
            "player_id": player.id,
            "message": "Planering klar! Klicka för att fortsätta.",
        }
        return {"type": "state_update", "events": events}

    # Next step
    _setup_planering_step(room)
    return {"type": "state_update", "events": events}


def _advance_planering_player(room: GameRoom, events: list) -> dict:
    """Move to next player or Phase 3."""
    # Save snapshots
    player = room.current_player
    player.snap_plan_q = player.pl_q
    player.snap_plan_h = player.pl_h
    player.snap_plan_t = player.pl_t

    room.next_turn()
    if room.turn_index == 0:
        # All players done - move to Phase 3
        room.phase = GamePhase.PHASE3_GENOMFORANDE
        room.temp = {}
        _setup_genomforande(room)
        events.append({
            "type": "phase_change",
            "phase": "phase3_genomforande",
            "text": "Skede 2.1 klar! Nu börjar Genomförande.",
        })
        return {"type": "state_update", "events": events}

    # Next player's planning
    room.pl_step_index = 0
    room.temp = {}
    _setup_planering_step(room)
    events.append({
        "type": "event",
        "text": f"Nu planerar {room.current_player.name}",
    })
    return {"type": "state_update", "events": events}


# ═══════════════════════════════════════════
#  PUZZLE PLACEMENT (between Phase 2 and 3)
# ═══════════════════════════════════════════

BOSTADER_TYPER = {"BRF", "HYRESRÄTT"}


def _skip_puzzle_to_phase2(room: GameRoom) -> dict:
    """Hoppa förbi pusselplaceringen — markera alla projekt som placerade
    och gå direkt till Skede 2 (AC-anställning). Används under provspel
    enligt config.SKIP_PUZZLE_PLACEMENT."""
    events = [{
        "type": "phase_change",
        "phase": "phase2_ac_hire",
        "text": "Skede 1 klar! (Pusselspelet är inaktiverat under provspel.) Välj Arbetschef.",
    }]
    for player in room.players:
        player.placed_project_ids = [p.id for p in player.projects]
        player.puzzle_confirmed = True
        player.puzzle_placements = {}
        player.puzzle_mark_placements = {}
        player.puzzle_grid_cells = []
    room.phase = GamePhase.PHASE2_AC_HIRE
    room.turn_index = 0
    room.temp = {"ac_hired_ids": set()}
    _setup_ac_hire(room)
    return {"type": "state_update", "events": events}


# ═══════════════════════════════════════════
#  PRESETS – hoppa direkt till en senare fas med en standardportfölj.
#  Används under provspel för att slippa spela igenom tidigare faser.
# ═══════════════════════════════════════════

# Portfölj enligt skärmdump 2026-05-18: 7 projekt, totalt 7750 BTA, 371 anskaffning.
PRESET_PROJEKT_NAMN = [
    "BRF Solrosen",
    "Lokalen Löparen",
    "Förskolan Skattkistan",
    "Lokalen Rokaden",
    "Kontoret Kometbanan",
    "BRF Eldningen",
    "Hyresrätt Hamnskiftet",
]


def _find_project_by_namn(room: GameRoom, namn: str):
    """Plocka första matchande projekt ur room.projekt_stacks och returnera det."""
    for typ, stack in room.projekt_stacks.items():
        for i, proj in enumerate(stack):
            if proj.namn == namn:
                return stack.pop(i)
    return None


def _setup_preset_skede2(room: GameRoom) -> dict:
    """Hoppa direkt till Skede 2.1 (Planering) med portföljen enligt skärmdump
    'inför skede 2': 7 projekt, PC Diplomaten anställd, riskbuffertar 3,
    ABT 323 Mkr, Q-krav 15, H-krav 17."""
    events = []

    pc_diplomaten = next((pc for pc in room.game_data.pc_staff
                          if "Diplomaten" in pc.get("namn", "")), None)

    for player in room.players:
        for namn in PRESET_PROJEKT_NAMN:
            proj = _find_project_by_namn(room, namn)
            if proj:
                player.projects.append(proj)

        if pc_diplomaten:
            player.projektchef = dict(pc_diplomaten)
        elif room.game_data.pc_staff:
            player.projektchef = dict(room.game_data.pc_staff[0])

        player.has_mark_tomt = True
        player.q_krav = 15
        player.h_krav = 17
        player.riskbuffertar = 3
        player.eget_kapital = 0
        player.abt_budget = 323
        player.abt_start = 323
        player.placed_project_ids = [p.id for p in player.projects]
        player.puzzle_confirmed = True

        events.append({
            "type": "phase_change",
            "text": (f"{player.name} startar i Skede 2 med {len(player.projects)} projekt "
                     f"(ABT 323 Mkr, Q-krav 15, H-krav 17, 3 riskbuffertar)"),
        })

    room.phase = GamePhase.PHASE2_AC_HIRE
    room.turn_index = 0
    room.temp = {"ac_hired_ids": set()}
    _setup_ac_hire(room)
    events.append({
        "type": "phase_change",
        "phase": "phase2_ac_hire",
        "text": "Preset 'inför Skede 2' laddad. Välj Arbetschef för att börja planera.",
    })
    return {"type": "state_update", "events": events}


def _setup_preset_skede3(room: GameRoom) -> dict:
    """Hoppa direkt till Skede 3 (Förvaltning) med samma portfölj som Skede 2-preset
    men med Skede 2-3 redan utförda: AC anställd, Q/H/T-mål uppnådda, TB ~35 Mkr.
    Övergångsekonomin (BRF MV+10, nya lån, kreditiv återbetalt) körs i _setup_forvaltning."""
    events = []

    pc = next((p for p in room.game_data.pc_staff
               if "Diplomaten" in p.get("namn", "")),
              room.game_data.pc_staff[0] if room.game_data.pc_staff else None)
    ac = next((a for a in room.game_data.ac_staff
               if "Produktions" in a.get("namn", "")),
              room.game_data.ac_staff[0] if room.game_data.ac_staff else None)

    for player in room.players:
        for namn in PRESET_PROJEKT_NAMN:
            proj = _find_project_by_namn(room, namn)
            if proj:
                player.projects.append(proj)

        if pc:
            player.projektchef = dict(pc)
        if ac:
            player.arbetschef = dict(ac)

        player.has_mark_tomt = True
        player.q_krav = 15
        player.h_krav = 17
        player.riskbuffertar = 1
        player.snap_exec_q = 15
        player.snap_exec_h = 17
        player.snap_exec_t = 12
        player.abt_start = 371
        player.abt_remaining_before_transfer = 35
        player.abt_budget = 0
        player.eget_kapital = 35
        player.abt_loans_net = 0
        player.abt_borrowing_cost = 0
        player.placed_project_ids = [p.id for p in player.projects]
        player.puzzle_confirmed = True

        events.append({
            "type": "phase_change",
            "text": (f"{player.name} startar i Skede 3 med {len(player.projects)} projekt, "
                     f"TB 35 Mkr, mål uppnådda."),
        })

    room.phase = GamePhase.PHASE4_FORVALTNING
    room.turn_index = 0
    _setup_forvaltning(room)
    events.append({
        "type": "phase_change",
        "phase": "phase4_forvaltning",
        "text": "Preset 'inför Skede 3' laddad. Förvaltning börjar.",
    })
    return {"type": "state_update", "events": events}


def _setup_puzzle_phase(room: GameRoom):
    """Initialize puzzle placement for all players simultaneously."""
    room.phase = GamePhase.PUZZLE_PLACEMENT
    room.sub_state = "puzzle_active"
    room.pending_action = None  # No single pending — all players act

    for player in room.players:
        # Base 4×4 grid at center of 10×10 (rows 2-5, cols 2-5)
        base_cells = []
        for r in range(2, 6):
            for c in range(2, 6):
                base_cells.append([r, c])
        player.puzzle_grid_cells = base_cells
        player.puzzle_placements = {}  # project_id -> {cells, layer}
        player.puzzle_confirmed = False
        player.placed_project_ids = []
        player.puzzle_mark_placements = {}


def _all_rotations_flips(cells):
    """Generate all 8 orientations (4 rotations × 2 flips) of a shape.
    Returns list of normalized cell sets (as sorted tuple of tuples)."""
    orientations = set()

    def normalize(coords):
        min_r = min(c[0] for c in coords)
        min_c = min(c[1] for c in coords)
        normed = sorted((c[0] - min_r, c[1] - min_c) for c in coords)
        return tuple(normed)

    def rotate_90(coords):
        """Rotate 90° clockwise: (r, c) -> (c, -r)"""
        return [(c, -r) for r, c in coords]

    def flip_h(coords):
        """Flip horizontally: (r, c) -> (r, -c)"""
        return [(r, -c) for r, c in coords]

    current = [(r, c) for r, c in cells]
    for _ in range(4):
        orientations.add(normalize(current))
        orientations.add(normalize(flip_h(current)))
        current = rotate_90(current)

    return orientations


def _validate_shape(placed_cells, shape_data):
    """Check if placed_cells matches any rotation/flip of shape_data."""
    if len(placed_cells) != len(shape_data):
        return False

    def normalize(coords):
        min_r = min(c[0] for c in coords)
        min_c = min(c[1] for c in coords)
        return tuple(sorted((c[0] - min_r, c[1] - min_c) for c in coords))

    placed_norm = normalize(placed_cells)
    valid_orientations = _all_rotations_flips(shape_data)
    return placed_norm in valid_orientations


def _get_grid_neighbors(grid_cells):
    """Get all cells adjacent to the grid but not in it."""
    grid_set = {(r, c) for r, c in grid_cells}
    neighbors = set()
    for r, c in grid_set:
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (nr, nc) not in grid_set and 0 <= nr < 10 and 0 <= nc < 10:
                neighbors.add((nr, nc))
    return neighbors


def _get_ground_occupied(player, exclude_pid=None):
    """Get set of cells occupied by ground-level (non-bostäder) projects."""
    occupied = set()
    for pid, placement in player.puzzle_placements.items():
        if pid == exclude_pid:
            continue
        # Find project type
        proj = None
        for p in player.projects:
            if p.id == pid:
                proj = p
                break
        if proj and proj.typ not in BOSTADER_TYPER:
            for rc in placement["cells"]:
                occupied.add((rc[0], rc[1]))
    return occupied


def _get_all_ground_projects(player, exclude_pid=None):
    """Get set of cells covered by ANY ground-level project (for bostäder stacking)."""
    covered = set()
    for pid, placement in player.puzzle_placements.items():
        if pid == exclude_pid:
            continue
        proj = None
        for p in player.projects:
            if p.id == pid:
                proj = p
                break
        if proj and proj.typ not in BOSTADER_TYPER:
            for rc in placement["cells"]:
                covered.add((rc[0], rc[1]))
    return covered


def _handle_puzzle(room: GameRoom, player, action: dict) -> dict:
    """Handle puzzle placement actions. All players act simultaneously.
    Three layers: mark → ground projects → bostäder on top."""
    events = []
    act = action.get("action")

    if player.puzzle_confirmed:
        return {"type": "error", "message": "Du har redan bekräftat din placering"}

    # ── Place mark expansion piece (drag polyomino onto grid edge) ──
    if act == "puzzle_place_mark_expansion":
        piece_id = action.get("piece_id")
        cells = action.get("cells")  # [[r,c], ...]
        if not piece_id or not cells:
            return {"type": "error", "message": "Saknar bit/celler"}

        # Find the piece
        piece = None
        for p in player.mark_expansion_pieces:
            if p["id"] == piece_id:
                piece = p
                break
        if not piece:
            return {"type": "error", "message": "Markexpansionsbiten finns inte"}

        # Validate shape
        if not _validate_shape(cells, piece["cells"]):
            return {"type": "error", "message": "Formen matchar inte markexpansionen"}

        # All cells must be within 10×10 bounds
        for r, c in cells:
            if not (0 <= r < 10 and 0 <= c < 10):
                return {"type": "error", "message": "Utanför spelplanen"}

        # At least one cell must be adjacent to existing grid
        grid_set = {(r, c) for r, c in player.puzzle_grid_cells}
        # Remove old placement of this piece from grid if re-placing
        old_placement = player.puzzle_mark_placements.get(piece_id)
        if old_placement:
            for rc in old_placement["cells"]:
                t = (rc[0], rc[1])
                if t in grid_set:
                    grid_set.discard(t)

        adjacent = False
        for r, c in cells:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (r + dr, c + dc) in grid_set:
                    adjacent = True
                    break
            if adjacent:
                break
        if not adjacent:
            return {"type": "error", "message": "Måste vara intill rutnätet"}

        # No overlap with existing grid (except own previous placement)
        for r, c in cells:
            if (r, c) in grid_set:
                return {"type": "error", "message": "Cellen är redan mark"}

        # Remove old placement if moving
        if old_placement:
            for rc in old_placement["cells"]:
                if rc in player.puzzle_grid_cells:
                    player.puzzle_grid_cells.remove(rc)

        # Add to grid
        for r, c in cells:
            player.puzzle_grid_cells.append([r, c])
        player.puzzle_mark_placements[piece_id] = {"cells": cells}

        return {"type": "state_update", "events": events}

    # ── Remove mark expansion piece ──
    elif act == "puzzle_remove_mark_expansion":
        piece_id = action.get("piece_id")
        placement = player.puzzle_mark_placements.get(piece_id)
        if not placement:
            return {"type": "error", "message": "Biten är inte placerad"}

        # Check no project occupies these cells
        for rc in placement["cells"]:
            key = (rc[0], rc[1])
            for pid, pp in player.puzzle_placements.items():
                if list(key) in pp["cells"] or [key[0], key[1]] in pp["cells"]:
                    return {"type": "error", "message": "Kan inte ta bort — projekt ligger på marken"}

        # Remove from grid
        for rc in placement["cells"]:
            if rc in player.puzzle_grid_cells:
                player.puzzle_grid_cells.remove(rc)
            elif [rc[0], rc[1]] in player.puzzle_grid_cells:
                player.puzzle_grid_cells.remove([rc[0], rc[1]])
        del player.puzzle_mark_placements[piece_id]

        return {"type": "state_update", "events": events}

    # ── Place project ──
    elif act == "puzzle_place_project":
        project_id = action.get("project_id")
        cells = action.get("cells")  # [[r,c], ...]
        if not project_id or not cells:
            return {"type": "error", "message": "Saknar projekt/celler"}

        proj = None
        for p in player.projects:
            if p.id == project_id:
                proj = p
                break
        if not proj:
            return {"type": "error", "message": "Projektet finns inte"}

        shape_data = room.game_data.shapes.get(proj.namn)
        if not shape_data:
            return {"type": "error", "message": f"Formdata saknas för {proj.namn}"}

        if not _validate_shape(cells, shape_data):
            return {"type": "error", "message": "Formen matchar inte projektet"}

        # All cells must be on the grid (mark layer)
        grid_set = {(r, c) for r, c in player.puzzle_grid_cells}
        for r, c in cells:
            if (r, c) not in grid_set:
                return {"type": "error", "message": "Alla celler måste vara på mark"}

        is_bostad = proj.typ in BOSTADER_TYPER

        if is_bostad:
            # Bostäder must sit on top of ground projects, not on empty grid
            ground_occupied = _get_ground_occupied(player, exclude_pid=project_id)
            bostad_occupied = set()
            for pid, placement in player.puzzle_placements.items():
                if pid == project_id:
                    continue
                bp = None
                for p in player.projects:
                    if p.id == pid:
                        bp = p
                        break
                if bp and bp.typ in BOSTADER_TYPER:
                    for rc in placement["cells"]:
                        bostad_occupied.add((rc[0], rc[1]))
            for r, c in cells:
                if (r, c) not in ground_occupied:
                    return {"type": "error", "message": "Bostäder måste placeras ovanpå markplansprojekt"}
                if (r, c) in bostad_occupied:
                    return {"type": "error", "message": "Bostäder kan inte överlappa andra bostäder"}
        else:
            # Ground-level projects cannot overlap each other
            ground_occupied = _get_ground_occupied(player, exclude_pid=project_id)
            for r, c in cells:
                if (r, c) in ground_occupied:
                    return {"type": "error", "message": "Markplansprojekt kan inte överlappa varandra"}

        player.puzzle_placements[project_id] = {"cells": cells}
        return {"type": "state_update", "events": events}

    # ── Remove project ──
    elif act == "puzzle_remove_project":
        project_id = action.get("project_id")
        if project_id in player.puzzle_placements:
            # If removing a ground project, also remove any bostäder on top
            proj = None
            for p in player.projects:
                if p.id == project_id:
                    proj = p
                    break
            if proj and proj.typ not in BOSTADER_TYPER:
                removed_cells = {(rc[0], rc[1]) for rc in player.puzzle_placements[project_id]["cells"]}
                # Find bostäder that depend on these cells
                to_remove = []
                for pid, pp in player.puzzle_placements.items():
                    if pid == project_id:
                        continue
                    bp = None
                    for p in player.projects:
                        if p.id == pid:
                            bp = p
                            break
                    if bp and bp.typ in BOSTADER_TYPER:
                        # Check if any cell of this bostad sits on the removed cells
                        if any((rc[0], rc[1]) in removed_cells for rc in pp["cells"]):
                            to_remove.append(pid)
                for pid in to_remove:
                    del player.puzzle_placements[pid]

            del player.puzzle_placements[project_id]
        return {"type": "state_update", "events": events}

    # ── Confirm ──
    elif act == "puzzle_confirm":
        player.puzzle_confirmed = True
        player.placed_project_ids = list(player.puzzle_placements.keys())
        events.append({
            "type": "event",
            "text": f"{player.name} har bekräftat sin kvartersplan ({len(player.placed_project_ids)} projekt placerade)",
        })

        if all(p.puzzle_confirmed for p in room.players):
            _finalize_puzzle(room, events)

        return {"type": "state_update", "events": events}

    return {"type": "error", "message": f"Okänd pusselåtgärd: {act}"}


def _finalize_puzzle(room: GameRoom, events: list):
    """All players confirmed — remove unplaced projects, transition to Phase 2."""
    for player in room.players:
        placed_ids = set(player.placed_project_ids)
        removed = [p for p in player.projects if p.id not in placed_ids]
        player.projects = [p for p in player.projects if p.id in placed_ids]
        if removed:
            # Reduce Q/H requirements for removed projects
            for proj in removed:
                player.q_krav = max(0, player.q_krav - proj.kvalitet)
                player.h_krav = max(0, player.h_krav - proj.hallbarhet)

            # Adjust ABT: remove revenue (anskaffning) but keep dev cost (already paid)
            # Net effect: ABT -= (anskaffning - kostnad) for each removed project
            lost_revenue = sum(p.anskaffning for p in removed)
            kept_cost = sum(p.kostnad for p in removed)
            abt_reduction = lost_revenue - kept_cost
            player.abt_budget -= abt_reduction
            player.abt_start -= abt_reduction

            names = ", ".join(p.namn for p in removed)
            events.append({
                "type": "event",
                "text": f"{player.name} fick inte plats med: {names} "
                        f"(ABT -{abt_reduction} Mkr, Q-krav nu {player.q_krav}, H-krav nu {player.h_krav})",
            })

    room.phase = GamePhase.PHASE2_AC_HIRE
    room.turn_index = 0
    room.temp = {"ac_hired_ids": set()}
    _setup_ac_hire(room)
    events.append({
        "type": "phase_change",
        "phase": "phase2_ac_hire",
        "text": "Kvartersplanering klar! Välj Arbetschef innan planeringen börjar.",
    })


# ═══════════════════════════════════════════
#  PHASE 2: AC HIRE
# ═══════════════════════════════════════════

def _setup_ac_hire(room: GameRoom):
    """Set up AC hiring — kvarter med lägst ABT-kostnad väljer först (§5.4).

    Lägst ABT-kostnad = lägst kvarvarande ABT-budget i Skede 2-start.
    Ger fördel åt det fattigaste kvarteret som tröstpris.
    """
    hired_ids = room.temp.get("ac_hired_ids", set())
    # Find players who haven't picked AC yet
    candidates = [p for p in room.players if p.arbetschef is None]
    if not candidates:
        return  # All hired (caller should advance phase)
    # Sortera ASC på abt_budget — lägst budget väljer först
    candidates.sort(key=lambda p: p.abt_budget)
    player = candidates[0]

    available = [ac for ac in room.game_data.ac_staff if ac["id"] not in hired_ids]
    room.sub_state = "choose_ac"
    room.pending_action = {
        "action": "choose_ac",
        "player_id": player.id,
        "available": available,
        "message": f"{player.name}, välj din Arbetschef (AC). Lägst ABT-budget väljer först.",
    }


def _handle_ac_hire(room: GameRoom, player, action: dict) -> dict:
    ac_id = action.get("value")
    hired_ids = room.temp.get("ac_hired_ids", set())
    ac = next((a for a in room.game_data.ac_staff if a["id"] == ac_id and ac_id not in hired_ids), None)
    if not ac:
        return {"type": "error", "message": "Ogiltig AC"}

    player.arbetschef = dict(ac)
    hired_ids.add(ac_id)
    room.temp["ac_hired_ids"] = hired_ids

    # Deduct cost from ABT budget
    player.abt_budget -= ac.get("lon", 0)

    event = {"type": "event", "text": f"{player.name} anställer {ac['namn']} som Arbetschef (-{ac.get('lon', 0)} Mkr)"}
    room.events_log.append(event)

    # Alla spelare valt AC?
    if all(p.arbetschef is not None for p in room.players):
        room.phase = GamePhase.PHASE2_PLANERING
        room.temp = {}
        _setup_planering(room)
    else:
        _setup_ac_hire(room)  # Picks next lowest-ABT player

    return {"type": "state_update", "events": [event]}


# ═══════════════════════════════════════════
#  PHASE 3: GENOMFÖRANDE
# ═══════════════════════════════════════════

def _setup_genomforande(room: GameRoom):
    """Initialize Phase 3 for all players."""
    # Initialize energy classes from projects
    for p in room.players:
        p.projekt_energiklass = {proj.id: proj.energiklass for proj in p.projects}
        p.used_supplier_keys = []
        p.used_org_keys = []
        p.used_external_ids = []
        p.external_hand = []

    # Determine turn order: D6 roll, highest first
    rolls = [(roll("D6"), p) for p in room.players]
    rolls.sort(key=lambda x: -x[0])
    room.gf_turn_order = [p.id for _, p in rolls]

    # Set up shared external support deck
    ext = room.game_data.external_support
    room.extern_draw = [e.to_dict() for e in ext]
    random.shuffle(room.extern_draw)
    room.extern_discard = []

    # Start phase 1 of 8
    room.gf_fas_nr = 1
    room.temp = {}
    _setup_gf_phase(room)


def _setup_gf_phase(room: GameRoom):
    """Set up a new faskort phase (1-8). Draw one faskort, start first player."""
    fas_nr = room.gf_fas_nr
    phase_cards = room.game_data.phase_cards.get(fas_nr, [])
    if phase_cards:
        card = random.choice(phase_cards)
        room.gf_current_card = card.to_dict()
    else:
        room.gf_current_card = {"id": f"GF_{fas_nr}", "steg": fas_nr,
                                 "namn": f"Fas {fas_nr}", "beskrivning": "", "levels": []}

    # Set turn to first player in turn order
    first_pid = room.gf_turn_order[0]
    room.turn_index = next(i for i, p in enumerate(room.players) if p.id == first_pid)
    room.temp = {"gf_player_idx": 0}
    _setup_gf_player_turn(room)


def _setup_gf_player_turn(room: GameRoom):
    """Start a player's turn within a faskort phase: offer to buy external support."""
    player = room.current_player
    fas_nr = room.gf_fas_nr
    cost = PHASE_COST[fas_nr - 1]

    can_buy = player.abt_budget >= cost and len(room.extern_draw) + len(room.extern_discard) > 0

    room.gf_sub_phase = "buy_support"
    room.sub_state = "gf_buy_support"
    room.pending_action = {
        "action": "gf_buy_support",
        "player_id": player.id,
        "fas_nr": fas_nr,
        "faskort": room.gf_current_card,
        "cost": cost,
        "can_buy": can_buy,
        "abt": round(player.abt_budget, 1),
        "hand_count": len(player.external_hand),
        "deck_count": len(room.extern_draw) + len(room.extern_discard),
        "message": f"Fas {fas_nr}/8: {room.gf_current_card['namn']} – Vill du köpa externt stöd? (Kostnad: {cost} Mkr)",
    }


def _handle_genomforande(room: GameRoom, player: Player, action: dict) -> dict:
    events = []

    if room.sub_state == "gf_buy_support":
        buy = action.get("value", False)
        if buy:
            fas_nr = room.gf_fas_nr
            cost = PHASE_COST[fas_nr - 1]
            if player.abt_budget < cost:
                return {"type": "error", "message": "Inte tillräckligt med ABT"}

            # Reshuffle discard if draw pile empty
            if not room.extern_draw and room.extern_discard:
                room.extern_draw = room.extern_discard[:]
                room.extern_discard = []
                random.shuffle(room.extern_draw)

            if room.extern_draw:
                card = room.extern_draw.pop(0)
                player.external_hand.append(card)
                player.abt_budget -= cost
                if player.abt_budget < 0:
                    handle_abt_overflow(player)
                events.append({
                    "type": "external_support_bought",
                    "player_id": player.id,
                    "player_name": player.name,
                    "card": card,
                    "cost": cost,
                    "text": f"{player.name} köper externt stöd: {card['namn']} ({cost} Mkr)",
                })
                room.events_log.extend(events)
                # Offer to buy another
                _setup_gf_player_turn(room)
                return {"type": "state_update", "events": events}

        # Skip buying or can't buy - move to draw planning event
        return _gf_draw_event(room, player, events)

    elif room.sub_state == "gf_event_continue":
        # After planning event, move to resolve faskort
        return _gf_setup_resolve_faskort(room, player, events)

    elif room.sub_state == "gf_event_reroll":
        use = action.get("value", False)
        card = room.temp.get("current_event_card")
        exp = room.temp.get("current_exp", 0)

        if use and player.riskbuffertar > 0:
            player.riskbuffertar -= 1
            new_d20 = roll("D20")
            total = new_d20 + exp
            effect = card.get_effect(total)
            _undo_planning_effect(player, room.temp.get("applied_effect", ""))
            _apply_planning_effect(player, effect)
            room.temp["applied_effect"] = effect
            events.append({
                "type": "planning_reroll",
                "player_id": player.id,
                "d20": new_d20, "exp": exp, "total": total, "effect": effect,
                "text": f"{player.name} omslag: D20={new_d20}+{exp}={total} → {effect}",
            })
            room.events_log.extend(events)

        return _gf_setup_resolve_faskort(room, player, events)

    elif room.sub_state == "gf_choose_level":
        level_idx = action.get("value", 0)
        return _gf_try_play_level(room, player, level_idx, events)

    elif room.sub_state == "gf_play_cards":
        card_key = action.get("value")
        return _gf_play_competence_card(room, player, card_key, events)

    elif room.sub_state == "gf_play_done":
        # Player finished playing cards for this level - check if reqs met
        return _gf_check_level_complete(room, player, events)

    elif room.sub_state == "gf_level_fallback":
        # Player can't meet requirements, accept Negativt
        return _gf_apply_level(room, player, 0, events)

    elif room.sub_state == "gf_phase_continue":
        # Move to next player in this faskort phase
        return _gf_advance_player(room, events)

    elif room.sub_state == "gf_penalty_roll":
        # Player clicked "Roll D20" for penalty card
        return _gf_penalty_do_roll(room, player, events)

    elif room.sub_state == "gf_penalty":
        # Continue after viewing penalty card
        return _gf_penalty_next(room, player, events)

    elif room.sub_state == "gf_penalty_reroll":
        use = action.get("value", False)
        return _gf_penalty_resolve(room, player, use, events)

    elif room.sub_state == "gf_garanti_roll":
        # Player clicked "Roll D20" for garanti card
        return _gf_garanti_do_roll(room, player, events)

    elif room.sub_state == "gf_garanti":
        return _gf_garanti_next(room, player, events)

    elif room.sub_state == "gf_garanti_reroll":
        use = action.get("value", False)
        return _gf_garanti_resolve(room, player, use, events)

    elif room.sub_state == "gf_forskott":
        return _gf_forskott_continue(room, player, events)

    elif room.sub_state == "gf_summary":
        # Phase 3 complete, move to Phase 4
        room.phase = GamePhase.PHASE4_FORVALTNING
        room.temp = {}
        _setup_forvaltning(room)
        events.append({
            "type": "phase_change",
            "phase": "phase4_forvaltning",
            "text": "Skede 2.2 klar! Nu börjar Förvaltning.",
        })
        return {"type": "state_update", "events": events}

    return {"type": "error", "message": f"Okänd genomförande sub_state: {room.sub_state}"}


def _gf_draw_event(room: GameRoom, player: Player, events: list) -> dict:
    """Draw a planning event card during Phase 3."""
    draw_pile = room.pl_draw_piles.get(player.id, [])

    if not draw_pile:
        return _gf_setup_resolve_faskort(room, player, events)

    card = draw_pile.pop(0)
    room.pl_discard_piles.setdefault(player.id, []).append(card)

    if not player.card_is_eligible(card):
        events.append({
            "type": "planning_event_skip",
            "player_id": player.id,
            "card": card.to_dict(),
            "text": f"Händelsekort '{card.namn}' aktiveras inte (kräver {card.trigger})",
        })
        room.events_log.extend(events[-1:])
        return _gf_setup_resolve_faskort(room, player, events)

    exp = player.total_erfarenhet
    d20 = roll("D20")
    total = d20 + exp
    effect = card.get_effect(total)
    _apply_planning_effect(player, effect)

    events.append({
        "type": "planning_event",
        "player_id": player.id,
        "player_name": player.name,
        "card": card.to_dict(),
        "d20": d20, "exp": exp, "total": total, "effect": effect,
        "text": f"Händelse: {card.namn} – D20={d20}+{exp}={total} → {effect}",
    })
    room.events_log.extend(events[-1:])

    if player.riskbuffertar > 0 and total <= 5:
        room.sub_state = "gf_event_reroll"
        room.temp["current_event_card"] = card
        room.temp["current_exp"] = exp
        room.temp["applied_effect"] = effect
        room.pending_action = {
            "action": "use_riskbuffert",
            "player_id": player.id,
            "riskbuffertar": player.riskbuffertar,
            "current_effect": effect,
            "card": card.to_dict(),
            "message": f"Effekt: {effect}. Omslag? ({player.riskbuffertar} Rb)",
        }
        return {"type": "state_update", "events": events}

    room.sub_state = "gf_event_continue"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "effect": effect,
        "message": f"Händelse: {effect}",
    }
    return {"type": "state_update", "events": events}


def _parse_comp_req(req_text: str) -> dict:
    """Parse competence requirement like 'SAM 3, LED 2' into {SAM: 3, LED: 2}."""
    reqs = {}
    if not req_text or req_text.strip() in ("", "–", "-", "—", "— (skippa)"):
        return reqs
    for part in req_text.split(","):
        tokens = part.strip().split()
        if len(tokens) >= 2 and tokens[0] in ("STA", "KOM", "SAM", "NOG", "INN", "ABM", "LED", "PRO"):
            try:
                reqs[tokens[0]] = int(tokens[-1])
            except ValueError:
                pass
    return reqs


def _comp_req_total(reqs: dict) -> int:
    """Sum of all requirement values for display."""
    return sum(reqs.values()) if reqs else 0


def _gf_setup_resolve_faskort(room: GameRoom, player: Player, events: list) -> dict:
    """Set up faskort resolution - show available levels for player to choose."""
    faskort = room.gf_current_card
    levels = faskort.get("levels", [])

    # Determine which trigger applies to this player
    trigger = player.kvarter_trigger  # BOSTÄDER, STAPLAD, or KOMPLEX
    trigger_key = {"BOSTÄDER": "req_b", "STAPLAD": "req_s", "KOMPLEX": "req_k"}.get(trigger, "req_b")

    available_levels = []
    for i, lvl in enumerate(levels):
        req_text = lvl.get(trigger_key, "")
        reqs = _parse_comp_req(req_text)
        # Skip levels marked as "skippa"
        if req_text.strip() in ("— (skippa)", ""):
            continue
        available_levels.append({
            "index": i,
            "name": lvl["name"],
            "reqs": reqs,  # {LED: 2, SAM: 3}
            "req_text": req_text,
            "effect": lvl.get("effect", ""),
            "trigger_key": trigger_key,
        })

    # Get available competence cards
    comp_cards = player.get_available_competence_cards()

    room.sub_state = "gf_choose_level"
    room.temp["trigger_key"] = trigger_key
    room.pending_action = {
        "action": "gf_choose_level",
        "player_id": player.id,
        "faskort": faskort,
        "levels": available_levels,
        "trigger": trigger,
        "comp_cards_count": len(comp_cards),
        "message": f"Välj utfallsnivå för {faskort['namn']}",
    }
    return {"type": "state_update", "events": events}


def _gf_try_play_level(room: GameRoom, player: Player, level_idx: int, events: list) -> dict:
    """Player chose a level - set up card playing."""
    faskort = room.gf_current_card
    levels = faskort.get("levels", [])
    if level_idx < 0 or level_idx >= len(levels):
        level_idx = 0

    level = levels[level_idx]
    trigger_key = room.temp.get("trigger_key", "req_b")
    reqs = _parse_comp_req(level.get(trigger_key, ""))

    room.temp["chosen_level_idx"] = level_idx
    room.temp["chosen_level"] = level
    room.temp["reqs"] = reqs  # {LED: 2, SAM: 3}
    room.temp["fulfilled"] = {k: 0 for k in reqs}  # track per-competence
    room.temp["played_cards"] = []

    if not reqs or level.get(trigger_key, "").strip() == "—":
        # No requirement (free level), apply directly
        return _gf_apply_level(room, player, level_idx, events)

    # Need to play competence cards
    return _gf_show_card_play(room, player, events)


def _gf_show_card_play(room: GameRoom, player: Player, events: list) -> dict:
    """Show card playing interface for meeting competence requirements."""
    reqs = room.temp.get("reqs", {})
    fulfilled = room.temp.get("fulfilled", {})

    # Calculate remaining per competence
    remaining = {k: v - fulfilled.get(k, 0) for k, v in reqs.items() if fulfilled.get(k, 0) < v}
    all_met = len(remaining) == 0

    comp_cards = player.get_available_competence_cards()
    # Filter out already played this round
    played_keys = [c["key"] for c in room.temp.get("played_cards", [])]
    comp_cards = [c for c in comp_cards if c["key"] not in played_keys]

    level = room.temp.get("chosen_level", {})

    if all_met or not comp_cards:
        return _gf_check_level_complete(room, player, events)

    room.sub_state = "gf_play_cards"
    room.pending_action = {
        "action": "gf_play_cards",
        "player_id": player.id,
        "level_name": level.get("name", ""),
        "reqs": reqs,
        "fulfilled": fulfilled,
        "remaining": remaining,
        "cards": comp_cards,
        "can_finish": all_met,
        "message": "Spela kort: " + ", ".join(f"{k} {fulfilled.get(k,0)}/{v}" for k, v in reqs.items()),
    }
    return {"type": "state_update", "events": events}


def _gf_play_competence_card(room: GameRoom, player: Player, card_key: str, events: list) -> dict:
    """Player plays a competence card."""
    if card_key == "__done__":
        return _gf_check_level_complete(room, player, events)

    comp_cards = player.get_available_competence_cards()
    played_keys = [c["key"] for c in room.temp.get("played_cards", [])]
    card = next((c for c in comp_cards if c["key"] == card_key and c["key"] not in played_keys), None)
    if not card:
        return {"type": "error", "message": "Ogiltigt kort"}

    # Apply per-competence contributions
    reqs = room.temp.get("reqs", {})
    fulfilled = room.temp.get("fulfilled", {})
    komp = card.get("kompetenser", {})
    contrib_parts = []
    for k, v in komp.items():
        if k in fulfilled and v > 0:
            fulfilled[k] += v
            contrib_parts.append(f"{k}+{v}")
    room.temp["fulfilled"] = fulfilled
    room.temp.setdefault("played_cards", []).append(card)

    # Mark card as used
    if card["source"] == "supplier":
        player.used_supplier_keys.append(card["key"])
    elif card["source"] == "org":
        player.used_org_keys.append(card["key"])
    elif card["source"] == "external":
        player.used_external_ids.append(card["key"])
    elif card["source"] == "ac":
        player.ac_kompetens_used = True

    contrib_str = ", ".join(contrib_parts) if contrib_parts else "inga matchande"
    events.append({
        "type": "competence_card_played",
        "player_id": player.id,
        "card": card,
        "text": f"{player.name} spelar {card['namn']} ({contrib_str})",
    })
    room.events_log.extend(events[-1:])

    # Check if all requirements met
    remaining = {k: v - fulfilled.get(k, 0) for k, v in reqs.items() if fulfilled.get(k, 0) < v}
    if not remaining:
        return _gf_check_level_complete(room, player, events)

    return _gf_show_card_play(room, player, events)


def _gf_check_level_complete(room: GameRoom, player: Player, events: list) -> dict:
    """Check if player met the requirement for chosen level."""
    reqs = room.temp.get("reqs", {})
    fulfilled = room.temp.get("fulfilled", {})
    level_idx = room.temp.get("chosen_level_idx", 0)

    remaining = {k: v - fulfilled.get(k, 0) for k, v in reqs.items() if fulfilled.get(k, 0) < v}
    if not remaining:
        return _gf_apply_level(room, player, level_idx, events)

    # Didn't meet requirement - fall back to Negativt
    fail_str = ", ".join(f"{k} {fulfilled.get(k,0)}/{v}" for k, v in reqs.items())
    room.sub_state = "gf_level_fallback"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": f"Klarade inte kravet ({fail_str}). Faller tillbaka till Negativt.",
    }
    return {"type": "state_update", "events": events}


def _gf_apply_level(room: GameRoom, player: Player, level_idx: int, events: list) -> dict:
    """Apply the faskort level effect."""
    faskort = room.gf_current_card
    levels = faskort.get("levels", [])
    level = levels[level_idx] if level_idx < len(levels) else levels[0]
    effect = level.get("effect", "")

    if effect:
        _apply_planning_effect(player, effect)

    # Return played external support cards to discard
    for card in room.temp.get("played_cards", []):
        if card["source"] == "external":
            # Find and remove from hand, add to discard
            eid = card["key"]
            for i, h in enumerate(player.external_hand):
                if h.get("id") == eid:
                    room.extern_discard.append(player.external_hand.pop(i))
                    break

    events.append({
        "type": "faskort_resolved",
        "player_id": player.id,
        "player_name": player.name,
        "faskort": faskort["namn"],
        "level": level["name"],
        "effect": effect,
        "text": f"{player.name}: {faskort['namn']} → {level['name']}: {effect or 'Ingen effekt'}",
    })
    room.events_log.extend(events[-1:])

    room.sub_state = "gf_phase_continue"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": f"{level['name']}: {effect or 'Ingen effekt'}",
    }
    return {"type": "state_update", "events": events}


def _gf_advance_player(room: GameRoom, events: list) -> dict:
    """Move to next player in this faskort phase, or next faskort phase."""
    gf_player_idx = room.temp.get("gf_player_idx", 0) + 1

    if gf_player_idx < len(room.gf_turn_order):
        room.temp = {"gf_player_idx": gf_player_idx}
        pid = room.gf_turn_order[gf_player_idx]
        room.turn_index = next(i for i, p in enumerate(room.players) if p.id == pid)
        _setup_gf_player_turn(room)
        return {"type": "state_update", "events": events}

    # All players done this phase - advance to next faskort
    room.gf_fas_nr += 1
    if room.gf_fas_nr <= 8:
        room.temp = {}
        _setup_gf_phase(room)
        events.append({
            "type": "event",
            "text": f"Fas {room.gf_fas_nr}/8 börjar: {room.gf_current_card['namn']}",
        })
        return {"type": "state_update", "events": events}

    # All 8 phases done - move to skedesavslut (penalty cards)
    return _gf_start_penalties(room, events)


def _gf_start_penalties(room: GameRoom, events: list) -> dict:
    """Start skedesavslut - draw penalty cards based on T/Q/H shortfalls."""
    room.turn_index = 0
    room.temp = {"penalty_phase": "start", "penalty_player_idx": 0}
    return _gf_setup_penalties_for_player(room, events)


def _gf_setup_penalties_for_player(room: GameRoom, events: list) -> dict:
    """Set up penalty cards for current player."""
    idx = room.temp.get("penalty_player_idx", 0)
    if idx >= len(room.players):
        return _gf_start_garanti(room, events)

    player = room.players[idx]
    room.turn_index = idx

    # Calculate shortfalls
    t_over = max(0, player.pl_t - 12)
    q_short = max(0, player.q_krav - player.pl_q)
    h_short = max(0, player.h_krav - player.pl_h)

    # Build penalty draw list: T first, then Q, then H
    penalty_queue = []
    t_pile = room.game_data.penalty_cards.get("Tid", [])
    q_pile = room.game_data.penalty_cards.get("Kvalitet", room.game_data.penalty_cards.get("Q", []))
    h_pile = room.game_data.penalty_cards.get("Hållbarhet", room.game_data.penalty_cards.get("H",
                room.game_data.penalty_cards.get("H\xe5llbarhet", [])))

    for i in range(min(t_over, len(t_pile))):
        penalty_queue.append(("T", t_pile[i]))
    for i in range(min(q_short, len(q_pile))):
        penalty_queue.append(("Q", q_pile[i]))
    for i in range(min(h_short, len(h_pile))):
        penalty_queue.append(("H", h_pile[i]))

    room.temp["penalty_queue"] = penalty_queue
    room.temp["penalty_idx"] = 0

    if not penalty_queue:
        events.append({
            "type": "event",
            "player_id": player.id,
            "text": f"{player.name}: Inga konsekvenskort (T≤12, Q≥krav, H≥krav)",
        })
        room.temp["penalty_player_idx"] = idx + 1
        return _gf_setup_penalties_for_player(room, events)

    events.append({
        "type": "event",
        "player_id": player.id,
        "text": f"{player.name}: {len(penalty_queue)} konsekvenskort (T+{t_over}, Q-{q_short}, H-{h_short})",
    })
    room.events_log.extend(events[-1:])

    return _gf_draw_penalty(room, player, events)


def _gf_draw_penalty(room: GameRoom, player: Player, events: list) -> dict:
    """Draw a penalty card and ask player to roll D20."""
    queue = room.temp.get("penalty_queue", [])
    idx = room.temp.get("penalty_idx", 0)
    if idx >= len(queue):
        room.temp["penalty_player_idx"] = room.temp.get("penalty_player_idx", 0) + 1
        return _gf_setup_penalties_for_player(room, events)

    typ, card = queue[idx]
    room.temp["current_penalty_card"] = card
    room.temp["current_penalty_typ"] = typ

    # Show card and ask player to roll D20
    room.sub_state = "gf_penalty_roll"
    room.pending_action = {
        "action": "roll_d20",
        "player_id": player.id,
        "card": card.to_dict(),
        "typ": typ,
        "erfarenhet": player.total_erfarenhet,
        "riskbuffertar": player.riskbuffertar,
        "message": f"Konsekvenskort ({typ}): {card.namn}",
        "card_idx": idx + 1,
        "card_total": len(queue),
    }
    return {"type": "state_update", "events": events}


def _gf_penalty_do_roll(room: GameRoom, player: Player, events: list) -> dict:
    """Player clicked Roll D20 for penalty card."""
    card = room.temp.get("current_penalty_card")
    typ = room.temp.get("current_penalty_typ", "")
    d20 = roll("D20")
    exp = player.total_erfarenhet
    total = d20 + exp
    effect_text, should_downgrade = card.get_effect(total)

    room.temp["penalty_d20"] = d20
    room.temp["penalty_total"] = total
    room.temp["penalty_effect"] = effect_text
    room.temp["penalty_downgrade"] = should_downgrade

    events.append({
        "type": "dice_result",
        "player_id": player.id,
        "die": "D20",
        "result": d20,
        "text": f"{player.name} slog D20: {d20} + {exp} erfarenhet = {total}",
    })

    # Check if player can reroll (worst tier and has Rb)
    if player.riskbuffertar > 0 and total <= 8:
        room.sub_state = "gf_penalty_reroll"
        room.pending_action = {
            "action": "use_riskbuffert",
            "player_id": player.id,
            "card": card.to_dict(),
            "typ": typ,
            "d20": d20, "exp": exp, "total": total,
            "effect": effect_text,
            "riskbuffertar": player.riskbuffertar,
            "message": f"Konsekvenskort ({typ}): {card.namn} – D20={d20}+{exp}={total} → {effect_text}. Omslag?",
        }
        return {"type": "state_update", "events": events}

    # Apply directly
    return _gf_penalty_apply(room, player, card, effect_text, should_downgrade, d20, exp, total, events)


def _gf_penalty_resolve(room: GameRoom, player: Player, use_rb: bool, events: list) -> dict:
    """Resolve penalty reroll decision."""
    card = room.temp.get("current_penalty_card")
    if use_rb and player.riskbuffertar > 0:
        player.riskbuffertar -= 1
        d20 = roll("D20")
        exp = player.total_erfarenhet
        total = d20 + exp
        effect_text, should_downgrade = card.get_effect(total)
        events.append({
            "type": "penalty_reroll",
            "player_id": player.id,
            "d20": d20, "total": total, "effect": effect_text,
            "text": f"{player.name} omslag: D20={d20}+{exp}={total} → {effect_text}",
        })
    else:
        d20 = room.temp.get("penalty_d20")
        total = room.temp.get("penalty_total")
        effect_text = room.temp.get("penalty_effect")
        should_downgrade = room.temp.get("penalty_downgrade", False)

    return _gf_penalty_apply(room, player, card, effect_text, should_downgrade, d20,
                              player.total_erfarenhet, total, events)


def _gf_penalty_apply(room, player, card, effect_text, should_downgrade, d20, exp, total, events):
    """Apply a penalty card effect."""
    if effect_text and effect_text.lower() != "ingen effekt":
        _apply_planning_effect(player, effect_text)

    if should_downgrade and card.energiklass_projekt > 0:
        _downgrade_energy_class(player, card.energiklass_projekt)

    events.append({
        "type": "penalty_applied",
        "player_id": player.id,
        "player_name": player.name,
        "card": card.to_dict(),
        "d20": d20, "exp": exp, "total": total,
        "effect": effect_text,
        "text": f"Konsekvens: {card.namn} → {effect_text}",
    })
    room.events_log.extend(events[-1:])

    room.temp["penalty_idx"] = room.temp.get("penalty_idx", 0) + 1
    room.sub_state = "gf_penalty"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": f"{card.namn}: {effect_text}",
    }
    return {"type": "state_update", "events": events}


def _gf_penalty_next(room: GameRoom, player: Player, events: list) -> dict:
    """Continue to next penalty card or next player."""
    return _gf_draw_penalty(room, player, events)


def _gf_start_garanti(room: GameRoom, events: list) -> dict:
    """Start garantibesiktning for all players."""
    room.temp = {"garanti_player_idx": 0}
    events.append({"type": "event", "text": "Garantibesiktning börjar!"})
    room.events_log.extend(events[-1:])
    return _gf_setup_garanti_for_player(room, events)


def _gf_setup_garanti_for_player(room: GameRoom, events: list) -> dict:
    """Set up garanti cards for a player."""
    idx = room.temp.get("garanti_player_idx", 0)
    if idx >= len(room.players):
        return _gf_finish(room, events)

    player = room.players[idx]
    room.turn_index = idx

    # Per regelboken §7.4: 1 garantikort per draget konsekvenskort (T+Q+H) +
    # 1 per sparad leverantör på nivå 1-2. Organisationer räknas INTE här.
    low_suppliers = sum(1 for s in player.pl_suppliers.values()
                        if (s.niva if hasattr(s, 'niva') else s.get("niva", 3)) <= 2)
    q_short = max(0, player.q_krav - player.pl_q)
    h_short = max(0, player.h_krav - player.pl_h)
    t_over = max(0, player.pl_t - 12)  # T-konsekvenskort var saknat tidigare
    total_cards = low_suppliers + q_short + h_short + t_over

    # Pool all garanti cards
    all_garanti = []
    for pile in room.game_data.garanti_cards.values():
        all_garanti.extend(pile)
    random.shuffle(all_garanti)

    garanti_queue = all_garanti[:total_cards]
    room.temp["garanti_queue"] = garanti_queue
    room.temp["garanti_idx"] = 0

    if not garanti_queue:
        events.append({
            "type": "event",
            "player_id": player.id,
            "text": f"{player.name}: Inga garantikort",
        })
        room.temp["garanti_player_idx"] = idx + 1
        return _gf_setup_garanti_for_player(room, events)

    events.append({
        "type": "event",
        "player_id": player.id,
        "text": f"{player.name}: {total_cards} garantikort (lev nivå 1-2:{low_suppliers}, T+{t_over}, Q-{q_short}, H-{h_short})",
    })
    return _gf_draw_garanti(room, player, events)


def _gf_draw_garanti(room: GameRoom, player: Player, events: list) -> dict:
    """Draw a garanti card and ask player to roll D20."""
    queue = room.temp.get("garanti_queue", [])
    idx = room.temp.get("garanti_idx", 0)
    if idx >= len(queue):
        # Save ABT before transfer
        player.abt_remaining_before_transfer = player.abt_budget
        room.temp["garanti_player_idx"] = room.temp.get("garanti_player_idx", 0) + 1
        return _gf_setup_garanti_for_player(room, events)

    card = queue[idx]
    room.temp["current_garanti_card"] = card

    # Show card and ask player to roll D20
    room.sub_state = "gf_garanti_roll"
    room.pending_action = {
        "action": "roll_d20",
        "player_id": player.id,
        "card": card.to_dict(),
        "typ": "Garanti",
        "erfarenhet": player.total_erfarenhet,
        "riskbuffertar": player.riskbuffertar,
        "message": f"Garantibesiktning: {card.namn}",
        "card_idx": idx + 1,
        "card_total": len(queue),
    }
    return {"type": "state_update", "events": events}


def _gf_garanti_do_roll(room: GameRoom, player: Player, events: list) -> dict:
    """Player clicked Roll D20 for garanti card."""
    card = room.temp.get("current_garanti_card")
    d20 = roll("D20")
    exp = player.total_erfarenhet
    total = d20 + exp
    effect_text, _ = card.get_effect(total)

    room.temp["garanti_d20"] = d20
    room.temp["garanti_total"] = total
    room.temp["garanti_effect"] = effect_text

    events.append({
        "type": "dice_result",
        "player_id": player.id,
        "die": "D20",
        "result": d20,
        "text": f"{player.name} slog D20: {d20} + {exp} erfarenhet = {total}",
    })

    if player.riskbuffertar > 0 and total <= 8:
        room.sub_state = "gf_garanti_reroll"
        room.pending_action = {
            "action": "use_riskbuffert",
            "player_id": player.id,
            "card": card.to_dict(),
            "d20": d20, "exp": exp, "total": total,
            "effect": effect_text,
            "riskbuffertar": player.riskbuffertar,
            "message": f"Garanti: {card.namn} – D20={d20}+{exp}={total} → {effect_text}. Omslag?",
        }
        return {"type": "state_update", "events": events}

    return _gf_garanti_apply(room, player, card, effect_text, d20, exp, total, events)


def _gf_garanti_resolve(room: GameRoom, player: Player, use_rb: bool, events: list) -> dict:
    card = room.temp.get("current_garanti_card")
    if use_rb and player.riskbuffertar > 0:
        player.riskbuffertar -= 1
        d20 = roll("D20")
        exp = player.total_erfarenhet
        total = d20 + exp
        effect_text, _ = card.get_effect(total)
    else:
        d20 = room.temp.get("garanti_d20")
        total = room.temp.get("garanti_total")
        effect_text = room.temp.get("garanti_effect")
        exp = player.total_erfarenhet
    return _gf_garanti_apply(room, player, card, effect_text, d20, exp, total, events)


def _gf_garanti_apply(room, player, card, effect_text, d20, exp, total, events):
    if effect_text and effect_text.lower() != "ingen effekt":
        _apply_planning_effect(player, effect_text)

    events.append({
        "type": "garanti_applied",
        "player_id": player.id,
        "player_name": player.name,
        "card": card.to_dict(),
        "d20": d20, "exp": exp, "total": total,
        "effect": effect_text,
        "text": f"Garanti: {card.namn} → {effect_text}",
    })
    room.events_log.extend(events[-1:])

    room.temp["garanti_idx"] = room.temp.get("garanti_idx", 0) + 1
    room.sub_state = "gf_garanti"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": f"{card.namn}: {effect_text}",
    }
    return {"type": "state_update", "events": events}


def _gf_garanti_next(room: GameRoom, player: Player, events: list) -> dict:
    return _gf_draw_garanti(room, player, events)


def _downgrade_energy_class(player: Player, count: int):
    """Downgrade energy class for 'count' projects (highest class first)."""
    projects_with_class = []
    for proj in player.projects:
        ec = player.projekt_energiklass.get(proj.id, proj.energiklass)
        idx = ENERGY_CLASSES.index(ec) if ec in ENERGY_CLASSES else 2
        projects_with_class.append((proj, ec, idx))

    # Sort: highest class (lowest index) first, ties broken by highest marknadsvarde
    projects_with_class.sort(key=lambda x: (x[2], -x[0].marknadsvarde))

    for i in range(min(count, len(projects_with_class))):
        proj, ec, idx = projects_with_class[i]
        if idx < len(ENERGY_CLASSES) - 1:
            player.projekt_energiklass[proj.id] = ENERGY_CLASSES[idx + 1]


def _gf_finish(room: GameRoom, events: list) -> dict:
    """Finish Phase 3: ABT transfer to EK, forskott, summary."""
    # ABT to EK transfer and forskott for each player
    for player in room.players:
        player.abt_remaining_before_transfer = player.abt_budget
        # ABT remaining goes to EK
        player.eget_kapital += player.abt_budget
        player.abt_budget = 0

        # Forskott: roll rorlig_intakt for placed projects only.
        # BRF har ingen 10%-MV-bonus här – BRF säljs vid Skede 4-start för MV + 10
        # (Förvaltning 2.0, _setup_forvaltning) så bonusen skulle dubbelräknas.
        forskott_total = 0.0
        for proj in player.projects:
            if proj.id not in player.placed_project_ids:
                continue
            if proj.typ == "BRF":
                continue
            if proj.rorlig_intakt and proj.rorlig_intakt.strip():
                try:
                    r = roll(proj.rorlig_intakt)
                    forskott_total += r
                except ValueError:
                    pass

        player.eget_kapital += forskott_total

        # Save snapshot
        player.snap_exec_q = player.pl_q
        player.snap_exec_h = player.pl_h
        player.snap_exec_t = player.pl_t

        events.append({
            "type": "gf_summary",
            "player_id": player.id,
            "player_name": player.name,
            "abt_transferred": round(player.abt_remaining_before_transfer, 1),
            "forskott": round(forskott_total, 1),
            "eget_kapital": round(player.eget_kapital, 1),
            "text": f"{player.name}: ABT→EK {player.abt_remaining_before_transfer:.0f} Mkr, "
                    f"Förskott {forskott_total:.0f} Mkr, EK = {player.eget_kapital:.0f} Mkr",
        })

    room.events_log.extend(events)

    room.sub_state = "gf_summary"
    room.turn_index = 0
    room.pending_action = {
        "action": "continue",
        "player_id": room.players[0].id,
        "message": "Skede 2.2 Genomförande klar! Klicka för att gå vidare.",
    }
    return {"type": "state_update", "events": events}


def _gf_forskott_continue(room: GameRoom, player: Player, events: list) -> dict:
    """Continue after forskott display."""
    return _gf_finish(room, events)


# ═══════════════════════════════════════════
#  PHASE 4: FÖRVALTNING
# ═══════════════════════════════════════════

def _calc_fastighetsvarde(prop, yield_pct: float, energiklass: str) -> float:
    if yield_pct <= 0:
        return 0
    dn = prop.driftnetto if hasattr(prop, 'driftnetto') else prop.get("driftnetto", 0)
    annual_dn = (dn or 0) * 4
    base_fv = annual_dn / (yield_pct / 100.0)
    return base_fv * EK_FV_MODIFIER.get(energiklass, 1.0)


def _get_prop_ek(prop, player) -> str:
    namn = prop.namn if hasattr(prop, 'namn') else prop.get("namn", "")
    return player.projekt_energiklass.get(namn, getattr(prop, 'energiklass', 'C'))


def _calc_real_ek(player) -> float:
    loans_gross = player.abt_loans_net + player.abt_borrowing_cost
    return player.eget_kapital - loans_gross


def _calc_tb(player) -> float:
    """TB = abt_remaining_before_transfer - abt_loans_net - abt_borrowing_cost."""
    if player.abt_start <= 0:
        return 0.0
    abt_remaining = getattr(player, 'abt_remaining_before_transfer', player.abt_budget)
    real_remaining = abt_remaining - player.abt_loans_net
    return real_remaining - player.abt_borrowing_cost


def _prop_yield(prop, room) -> float:
    typ = prop.typ if hasattr(prop, 'typ') else prop.get("typ", "")
    # Bostäder-yield gäller hyresrätter (case-insensitive — datakällan använder "HYRESRÄTT",
    # config-listan har "Hyresrätt"). Allt annat icke-BRF räknas som kommersiellt.
    if typ.upper().startswith("HYRESR"):
        return room.f4_yield_b
    return room.f4_yield_k


# ── Förvaltning 2.0: effektiv DN, MV-tabell, risk för tvångsförsäljning ──

def _eff_dn(prop, player) -> int:
    """Effektiv DN = bas-DN + energiklass-modifier (designdoc §Fastigheter, DN).

    Cap = bas_dn × 2 (absolut max EFFECTIVE_DN_ABS_MAX). Faller tillbaka till
    int(driftnetto) om bas_dn saknas (icke-berikade projekt).
    """
    bas = prop.bas_dn if getattr(prop, 'bas_dn', None) is not None else int(prop.driftnetto or 0)
    ek = player.projekt_energiklass.get(prop.namn, prop.energiklass) if player else prop.energiklass
    eff = bas + EK_DN_MODIFIER.get(ek, 0)
    if bas > 0:
        eff = min(eff, bas * 2)
    return max(0, min(eff, EFFECTIVE_DN_ABS_MAX))


def _mv_lookup(eff_dn: int, yield_pct: float, mode: str = "normal") -> int:
    """MV-tabell uppslag. MV = effektiv DN / yield, multiplicerat med läge-faktor
    (tvång 0.7, normal 1.0, fientlig 1.2), avrundat till närmaste 5 Mkr.
    """
    if yield_pct <= 0 or eff_dn <= 0:
        return 0
    mv_raw = (eff_dn / (yield_pct / 100.0)) * MV_MULTIPLIERS.get(mode, 1.0)
    return int(round(mv_raw / 5.0) * 5)


def _margin_call_scan(room, player, events: list) -> list:
    """Sätt röd markör BARA på fastigheter där NÄSTA kvartals MV < lån.

    Vi peekar på första värdet i yield-kön och simulerar yielden efter den
    rörelsen. Då varnar vi i god tid (1 kvartal innan tvångsförsäljning) utan
    att vräka spelaren med varningar för varje liten yield-fluktuation som
    råkar tippa MV under lån just nu.
    """
    yb_next = room.f4_yield_b + (room.f4_yield_cards.get("bostader", [0])[0]
                                  if room.f4_yield_cards.get("bostader") else 0)
    yk_next = room.f4_yield_k + (room.f4_yield_cards.get("kommersiellt", [0])[0]
                                  if room.f4_yield_cards.get("kommersiellt") else 0)

    in_call = []
    new_set = set()
    for prop in player.fastigheter:
        lan = getattr(prop, 'lanebelopp', None) or 0
        if lan <= 0:
            continue
        # Använd nästa kvartals yield för bedömning, inte nuvarande.
        typ = prop.typ.upper() if hasattr(prop, 'typ') else ""
        y_next = yb_next if typ.startswith("HYRESR") else yk_next
        eff = _eff_dn(prop, player)
        mv_next = _mv_lookup(eff, y_next, "normal")
        if mv_next < lan:
            in_call.append({"namn": prop.namn, "mv_next": mv_next, "lan": lan,
                            "eff_dn": eff, "yield_next": round(y_next, 2)})
            new_set.add(prop.namn)
            events.append({
                "type": "event",
                "text": (f"⚠ {player.name}: {prop.namn} riskerar tvångsförsäljning "
                         f"nästa kvartal (MV {mv_next} < lån {lan} vid yield {y_next:.2f}%)"),
            })
    player.f4_margin_call_props = new_set
    return in_call


def _yield_queue(room, track: str) -> list:
    """Returnera de YIELD_QUEUE_SIZE närmaste yield-kortvärdena för ett spår
    (peek, utan att poppa)."""
    deck = room.f4_yield_cards.get(track, [])
    return list(deck[:YIELD_QUEUE_SIZE])


def _energy_upgrade_modifier(player) -> int:
    """Returnera total bonus till D20-slag vid energiuppgradering.

    F2-arketyper med specialeffekt på energiuppgradering:
      - 'Tekniska experten' (FC-6): +3 på alla energiuppgraderingsslag

    Senare etapp: 'Energirevisor'-personkort ger auto-success (hanteras separat).
    """
    bonus = 0
    for s in player.staff:
        namn = s.namn if hasattr(s, 'namn') else s.get("namn", "")
        if "Tekniska experten" in namn or namn.lower().startswith("tekniska"):
            bonus += 3
    return bonus


def _fc_forhandling_modifier(player) -> int:
    """Summerar f2_forh_modifier över alla FC i staben. Används som modifier
    på hyresförhandlingens netto i Q2 (Förvaltning 2.0)."""
    total = 0
    for s in player.staff:
        roll_attr = s.roll if hasattr(s, 'roll') else s.get("roll", "")
        if roll_attr != "FC":
            continue
        total += s.f2_forh_modifier if hasattr(s, 'f2_forh_modifier') else 0
    return total


def _fs_kvalitetsoptimerare_bonus(player) -> int:
    """+1 DN per kvartal om FS-2 'Per Kvalitetsoptimeraren' i staben.
    Designdoket: '+1 DN på fastighet med högst Q' — vi adderar 1 till total DN
    eftersom intäktsfasen summerar ändå."""
    if not player.fastigheter:
        return 0
    for s in player.staff:
        namn = s.namn if hasattr(s, 'namn') else s.get("namn", "")
        if "Kvalitetsoptimer" in namn:
            return 1
    return 0


def _fc_den_lugna_rantereduktion(player) -> int:
    """-1 mkr räntedrag/kvartal om FC-5 'Den lugna' i staben.
    Designdoket: '-1 mkr räntedrag på en valfri fastighet' — för enkelhet
    drar vi 1 från totalräntan istället för att kräva fastighetsval."""
    for s in player.staff:
        namn = s.namn if hasattr(s, 'namn') else s.get("namn", "")
        if "Den lugna" in namn or namn.lower().startswith("den lugna"):
            return 1
    return 0


# ── AI-motspelare: enkel default-handler ──────────────────────────────────

def ai_default_action(room, player) -> Optional[dict]:
    """Returnera ett default-val för en AI-spelare baserat på pending_action.

    Enkel strategi (passiv stand-in):
      - Hire: välj första tillgänglig FC och FS
      - Energiuppgradering: alltid skip
      - Marknad: alltid skip
      - Sell/Buy: alltid skip
      - Continue: alltid continue
    """
    pending = room.pending_action or {}
    action = pending.get("action")
    if not action:
        return None
    if action == "f4_hire":
        avail = pending.get("available", [])
        has_fc = pending.get("has_fc", False)
        has_fs = pending.get("has_fs", False)
        # Hire första saknade rollen
        for s in avail:
            roll = s.get("roll", "")
            if not has_fc and roll == "FC":
                return {"action": "f4_hire", "value": s["id"]}
            if not has_fs and roll == "FS":
                return {"action": "f4_hire", "value": s["id"]}
        # Ingen kvar att anställa – skicka None (klar)
        return {"action": "f4_hire", "value": None}
    if action == "f4_energy_upgrade":
        # Konservativ AI:
        # - Uppgradera bara om EK > 30 mkr (spara kassa)
        # - Bara en NY fastighet per kvartal (inte trampa upp samma fastighet
        #   till EK A på en runda — för dyrt och oklart strategiskt)
        # - Välj fastighet med lägst EK-klass (E/D/C/B)
        upgradeable = pending.get("upgradeable", [])
        ek_left = pending.get("eget_kapital", 0)
        already_started = {u["namn"] for u in upgradeable
                            if u.get("already_started_this_q")}
        if ek_left >= 30 and upgradeable and not already_started:
            order = {"E": 0, "D": 1, "C": 2, "B": 3}
            sortable = sorted(upgradeable, key=lambda u: order.get(u.get("ek"), 9))
            for u in sortable:
                if u.get("cost", 0) <= ek_left:
                    return {"action": "f4_energy_upgrade", "value": u["namn"]}
        return {"action": "f4_energy_upgrade", "value": None}

    if action == "f4_market":
        # Marknadsfasen: AI:n hoppar över bud/sälj. OBS: backend förväntar
        # value="skip" här, inte None (None matchar ingen gren och låser).
        return {"action": "f4_market", "value": "skip"}

    if action in ("f4_market_sell", "f4_market_buy"):
        # I sell/buy-sub-state är None = avbryt
        return {"action": action, "value": None}
    if action == "continue":
        return {"action": "continue"}
    return None


from typing import Optional  # noqa: E402


# ── F2-händelsekort: dragning per fastighet + plus/minus-tröskel ──────────

_F2_TYP_TILL_DECK = {
    "HYRESRÄTT": "HYRESRÄTT",
    "KONTOR": "KONTOR",
    "LOKAL": "LOKAL",
    "FÖRSKOLA": "FÖRSKOLA",
}


def _f2_handelse_deck_for_typ(game_data, fastighet_typ: str) -> list:
    """Returnerar lista med F2-händelsekort som passar fastighetstypen.
    Stoppkort och förköpsrätt-kort INGÅR — de dras men hamnar på handen
    (som personkort) istället för på fastigheten."""
    deck_typ = _F2_TYP_TILL_DECK.get(fastighet_typ.upper(), "HYRESRÄTT")
    return [k for k in (game_data.f2_handelsekort or [])
            if k.get("typ") == deck_typ]


def _dra_handelsekort_per_fastighet(room, player, events: list):
    """Förvaltning 2.0: vid varje kvartalsstart drar spelaren ett händelsekort
    per fastighet. Kortet placeras dolt om är_dolt eller effekt är pluskort/minuskort.
    När 3 pluskort eller 3 minuskort samlats på samma fastighet kasseras alla
    och bas-DN justeras +1/-1 permanent.
    """
    for prop in player.fastigheter:
        deck = _f2_handelse_deck_for_typ(room.game_data, prop.typ)
        if not deck:
            continue
        kort = random.choice(deck)
        effekt = kort["effekt"]
        # Placera på fastigheten
        stack = player.f4_handelse_per_prop.setdefault(prop.namn, [])

        # Direkt-effekter (synliga, permanenta)
        if effekt == "+1 dn" or effekt == "+1 DN".lower():
            prop.bas_dn = (prop.bas_dn or 0) + 1
            events.append({"type": "event",
                           "text": f"{player.name}: {prop.namn} drog '{kort['rubrik']}' → +1 DN permanent."})
            continue
        if effekt == "-1 dn" or effekt == "-1 DN".lower():
            prop.bas_dn = max(0, (prop.bas_dn or 0) - 1)
            events.append({"type": "event",
                           "text": f"{player.name}: {prop.namn} drog '{kort['rubrik']}' → −1 DN permanent."})
            continue

        # Stoppkort och förköpsrätt → till handen som reaktiva resurser.
        if effekt in ("stoppkort", "förköpsrätt"):
            HAND_CAP = 6
            if len(player.f4_personkort_hand) < HAND_CAP:
                player.f4_personkort_hand.append({
                    "id": kort["id"], "roll": "REAKT",
                    "rubrik": kort["rubrik"], "effekt": effekt,
                    "beskrivning": kort["beskrivning"],
                })
                events.append({"type": "event",
                               "text": f"{player.name}: drog reaktivt kort '{kort['rubrik']}' till handen ({effekt})."})
            continue

        # Annullera-minus: konsumera token om vi just drog ett minuskort
        if effekt == "minuskort" and player.f4_annullera_minus > 0:
            player.f4_annullera_minus -= 1
            events.append({"type": "event",
                           "text": f"{player.name}: 'Annullera minuskort' aktiverat — '{kort['rubrik']}' på {prop.namn} kasseras direkt."})
            continue

        # Plus/minus + varning/energivarning placeras (dolt) på fastigheten
        stack.append({"id": kort["id"], "rubrik": kort["rubrik"],
                      "effekt": effekt, "beskrivning": kort["beskrivning"],
                      "kalla": "händelsekort"})

        # Tröskel: 3 plus eller 3 minus → kassera och ±1 bas-DN.
        # Räkna BÅDE händelsekort OCH DD-kort på fastigheten — de delar stack
        # konceptuellt (designval: DD-kort är också plus/minus-kort).
        dd_stack = player.f4_dd_per_prop.get(prop.namn, [])
        plus_count = (sum(1 for k in stack if k["effekt"] == "pluskort")
                      + sum(1 for k in dd_stack if k.get("effekt") == "pluskort"))
        minus_count = (sum(1 for k in stack if k["effekt"] == "minuskort")
                       + sum(1 for k in dd_stack if k.get("effekt") == "minuskort"))
        if plus_count >= 3:
            # Kassera alla pluskort från BÅDE händelse- och DD-stacken
            player.f4_handelse_per_prop[prop.namn] = [k for k in stack if k["effekt"] != "pluskort"]
            player.f4_dd_per_prop[prop.namn] = [k for k in dd_stack if k.get("effekt") != "pluskort"]
            prop.bas_dn = (prop.bas_dn or 0) + 1
            events.append({"type": "event",
                           "text": f"⬆ {player.name}: {prop.namn} ackumulerade 3 pluskort (inkl. DD) → +1 bas-DN permanent."})
        elif minus_count >= 3:
            player.f4_handelse_per_prop[prop.namn] = [k for k in stack if k["effekt"] != "minuskort"]
            player.f4_dd_per_prop[prop.namn] = [k for k in dd_stack if k.get("effekt") != "minuskort"]
            prop.bas_dn = max(0, (prop.bas_dn or 0) - 1)
            events.append({"type": "event",
                           "text": f"⬇ {player.name}: {prop.namn} ackumulerade 3 minuskort (inkl. DD) → −1 bas-DN permanent."})

        # Energivarning-tröskel: 3 → -1 EK-steg (designdok)
        energi_count = sum(1 for k in stack if k["effekt"] == "energivarning")
        if energi_count >= 3:
            player.f4_handelse_per_prop[prop.namn] = [k for k in stack if k["effekt"] != "energivarning"]
            ek = player.projekt_energiklass.get(prop.namn, prop.energiklass)
            if ek in ENERGY_CLASSES:
                idx = ENERGY_CLASSES.index(ek)
                if idx < len(ENERGY_CLASSES) - 1:
                    ny_ek = ENERGY_CLASSES[idx + 1]
                    player.projekt_energiklass[prop.namn] = ny_ek
                    events.append({"type": "event",
                                   "text": f"⚠ {player.name}: {prop.namn} ackumulerade 3 energivarningar → EK {ek}→{ny_ek}."})


def _dra_dd_kort_for_prop(room, player, prop, events: list):
    """Dra ett DD-kort och lägg DOLT på fastigheten.

    Förvaltning 2.0 (uppdaterad design): DD-kort är samma typ av plus/minus-
    kort som händelsekort. Typ='Intäkt' → pluskort, Typ='Kostnad' → minuskort.
    De räknas in i samma 3-tröskel på fastigheten — vid 3 i netto avslöjas
    alla och bas-DN justeras ±1.
    Effekt_Mkr-kolumnen i CSV används inte längre direkt (kan vara kvar som
    designkommentar)."""
    deck = room.game_data.f2_dd_cards or []
    if not deck:
        return
    dd = dict(random.choice(deck))
    # Tagga DD med en plus/minus-effekt som matchar händelsekort-mekaniken.
    typ = (dd.get("typ") or "").lower()
    dd["effekt"] = "pluskort" if typ == "intäkt" else "minuskort"
    player.f4_dd_per_prop.setdefault(prop.namn, []).append(dd)
    events.append({
        "type": "event",
        "text": f"{player.name}: drog ett DD-kort dolt på {prop.namn}.",
    })


def _dra_dd_per_fastighet(room, player, events: list):
    """Vid Q0 (Skede 3-start) dras ett DD-kort dolt per fastighet (designdok)."""
    for prop in player.fastigheter:
        _dra_dd_kort_for_prop(room, player, prop, events)


def _avsloja_dolda_kort(player, prop_namn: str, events: list, anledning: str = "sålde"):
    """Avslöja alla dolda kort (DD + dolda händelsekort) på en fastighet.
    Loggar i event-listan som synligt för alla spelare."""
    dds = player.f4_dd_per_prop.pop(prop_namn, []) or []
    handelser = player.f4_handelse_per_prop.pop(prop_namn, []) or []
    if not dds and not handelser:
        return
    parts = []
    for d in dds:
        eff = d.get("effekt", "?")
        parts.append(f"DD: \"{d.get('rubrik','?')}\" ({eff})")
    for h in handelser:
        eff = h.get("effekt", "?")
        if eff in ("pluskort", "minuskort", "varning", "energivarning"):
            parts.append(f"\"{h.get('rubrik','?')}\" ({eff})")
    if parts:
        events.append({
            "type": "event",
            "text": f"🔓 {player.name} {anledning} {prop_namn} — avslöjade dolda kort: " + " · ".join(parts),
        })


def _play_personkort(room, player, kort_id: str, events: list) -> dict:
    """Spela ett personkort från handen och applicera dess effekt.

    Stödda effekter (utvidgas iterativt):
      - auto_energi: lägg en energi-garanti på fastighet med lägst EK
      - cash_plus5 / cash_plus3: +5/+3 mkr till EK
      - ranta_minus1: −1 mkr räntekostnad nästa intäktsfas
      - forh_plus2 / forh_plus3 / forh_plus2_efter: bonus på hyresförhandling
      - blockera_kons: blockera nästa konsekvenskort
      - annullera_minus: nästa minuskort som dras kasseras direkt
      - rensa_minus_3: kasta upp till 3 minuskort från fastighet med flest minus
      - halverad_uppgr: nästa energiuppgradering kostar halvt
    Andra effekter returneras som 'inte_stödd' utan att kortet konsumeras.
    """
    idx = next((i for i, k in enumerate(player.f4_personkort_hand) if k.get("id") == kort_id), -1)
    if idx < 0:
        return {"ok": False, "msg": "Hittade inte kortet i handen"}
    kort = player.f4_personkort_hand[idx]
    effekt = kort.get("effekt", "")

    def consume():
        player.f4_personkort_hand.pop(idx)

    if effekt == "auto_energi":
        # Lägg garanti-token på fastighet med lägst EK (D/E först), annars första
        target = None
        for ek in ("E", "D", "C", "B"):
            for prop in player.fastigheter:
                cur = player.projekt_energiklass.get(prop.namn, prop.energiklass)
                if cur == ek:
                    target = prop
                    break
            if target:
                break
        if not target and player.fastigheter:
            target = player.fastigheter[0]
        if target:
            player.f4_energi_garanti[target.namn] = player.f4_energi_garanti.get(target.namn, 0) + 1
            consume()
            events.append({"type": "event",
                           "text": f"{player.name} spelade '{kort['rubrik']}' → energi-garanti på {target.namn}."})
            return {"ok": True}
        return {"ok": False, "msg": "Inga fastigheter"}

    if effekt == "cash_plus5":
        player.eget_kapital += 5
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → +5 Mkr till EK."})
        return {"ok": True}

    if effekt == "cash_plus3":
        player.eget_kapital += 3
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → +3 Mkr till EK."})
        return {"ok": True}

    if effekt == "dn_plus1_perm":
        # +1 bas-DN permanent på fastighet med lägst bas-DN (för enkelhet)
        if not player.fastigheter:
            return {"ok": False, "msg": "Inga fastigheter"}
        target = min(player.fastigheter, key=lambda p: p.bas_dn or 0)
        target.bas_dn = (target.bas_dn or 0) + 1
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → +1 bas-DN permanent på {target.namn} (nu {target.bas_dn})."})
        return {"ok": True}

    if effekt == "lan_minus10":
        # Sänk lån permanent med 10 Mkr på fastighet med högst belåningsgrad
        if not player.fastigheter:
            return {"ok": False, "msg": "Inga fastigheter"}
        # Välj fastighet med högst lan/MV-kvot — utan MV använder vi lan absolut
        target = max(player.fastigheter, key=lambda p: (p.lanebelopp or 0))
        if not target.lanebelopp:
            return {"ok": False, "msg": "Ingen belånad fastighet"}
        old_lan = target.lanebelopp
        target.lanebelopp = max(0, target.lanebelopp - 10)
        # Sänk räntekostnad proportionellt (10 Mkr × 4 % / 4 = 0.1 Mkr/kv → 0)
        if (target.rantekostnad_kvartal or 0) > 0 and old_lan >= 100:
            target.rantekostnad_kvartal -= 1
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → {target.namn} lån {old_lan}→{target.lanebelopp} Mkr permanent."})
        return {"ok": True}

    if effekt in ("forh_plus2", "forh_plus2_efter"):
        # Spelas direkt i samband med hyresförhandling → +2 på slaget.
        # Effekten 'spara' tills nästa förhandling som event-sekvens, men UI-mässigt
        # förväntas spelaren spela kortet vid rätt moment.
        player.f4_forh_bonus_next += 2
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → +2 på hyresförhandling."})
        return {"ok": True}
    if effekt == "forh_plus3":
        player.f4_forh_bonus_next += 3
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → +3 på hyresförhandling."})
        return {"ok": True}

    if effekt == "blockera_kons":
        player.f4_blockera_konsekvens += 1
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → nästa konsekvenskort blockeras."})
        return {"ok": True}

    if effekt == "annullera_minus":
        player.f4_annullera_minus += 1
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → nästa minuskort kasseras direkt."})
        return {"ok": True}

    if effekt == "rensa_minus_3":
        # Hitta fastigheten med flest minuskort (händelse + DD), kasta upp till 3
        target_namn = None
        max_minus = 0
        for prop in player.fastigheter:
            h = player.f4_handelse_per_prop.get(prop.namn, [])
            d = player.f4_dd_per_prop.get(prop.namn, [])
            minus = sum(1 for k in h if k.get("effekt") == "minuskort") + \
                    sum(1 for k in d if k.get("effekt") == "minuskort")
            if minus > max_minus:
                max_minus = minus
                target_namn = prop.namn
        if not target_namn:
            return {"ok": False, "msg": "Inga minuskort att kasta"}
        rensat = 0
        new_h = []
        for k in player.f4_handelse_per_prop.get(target_namn, []):
            if k.get("effekt") == "minuskort" and rensat < 3:
                rensat += 1
                continue
            new_h.append(k)
        player.f4_handelse_per_prop[target_namn] = new_h
        new_d = []
        for k in player.f4_dd_per_prop.get(target_namn, []):
            if k.get("effekt") == "minuskort" and rensat < 3:
                rensat += 1
                continue
            new_d.append(k)
        player.f4_dd_per_prop[target_namn] = new_d
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → kastade {rensat} minuskort från {target_namn}."})
        return {"ok": True}

    if effekt == "halverad_uppgr":
        # Sätt 0.5 rabatt på room (engångs — nollställs efter nästa upgrade)
        room.f4_energy_discount = 0.5
        consume()
        events.append({"type": "event",
                       "text": f"{player.name} spelade '{kort['rubrik']}' → nästa energiuppgradering kostar halvt."})
        return {"ok": True}

    return {"ok": False, "msg": f"Effekten '{effekt}' är inte stödd än"}


def _dra_personkort(room, player, events: list, fc_n: int = 1, fs_n: int = 1):
    """Dra fc_n FC-personkort och fs_n FS-personkort till spelarens hand.
    Cap 6 i hand totalt (designdok). Vid full hand: skippa nya kort."""
    HAND_CAP = 6
    decks = [("FC", room.game_data.f2_fc_personkort or [], fc_n),
             ("FS", room.game_data.f2_fs_personkort or [], fs_n)]
    dragna = []
    for roll_name, deck, n in decks:
        for _ in range(n):
            if len(player.f4_personkort_hand) >= HAND_CAP:
                break
            if deck:
                kort = dict(random.choice(deck))
                player.f4_personkort_hand.append(kort)
                dragna.append(f"{roll_name}: {kort['rubrik']}")
    if dragna:
        events.append({
            "type": "event",
            "text": f"{player.name} drar personkort: {', '.join(dragna)}",
        })


def calc_live_score(room, player) -> dict:
    """Räkna ett 'live'-slutpoäng utifrån spelarens nuvarande tillstånd.
    Används för att visa hur poängen står just nu under Skede 3 (innan slutvärdering)."""
    from economics import calc_tg, deviation_factor, calc_deviation_n

    placed_ids = set(getattr(player, 'placed_project_ids', []) or [])
    ansk_orig = sum(p.anskaffning for p in player.projects if p.id in placed_ids)
    ansk_total = ansk_orig + player.f4_extra_anskaffning
    skede1 = ansk_total / 100.0

    skede2 = calc_tg(player) if player.abt_start > 0 else 0

    total_dn = sum(_eff_dn(prop, player) for prop in player.fastigheter)
    saljvarde = sum(_mv_lookup(_eff_dn(prop, player),
                               _prop_yield(prop, room),
                               "normal")
                    for prop in player.fastigheter)
    utestaende_lan = sum((prop.lanebelopp or 0) for prop in player.fastigheter)
    fv_obelan = saljvarde - utestaende_lan
    kassa = _calc_real_ek(player)
    skede3 = (fv_obelan + kassa * SKEDE3_KASSA_FAKTOR) / SKEDE3_DIVISOR

    rapong = skede1 + skede2 + skede3
    dev = calc_deviation_n(player)
    f_n = deviation_factor(dev["n_total"])
    score = rapong * f_n

    return {
        "skede1": round(skede1, 1),
        "skede2": round(skede2, 1),
        "skede3": round(skede3, 1),
        "rapong": round(rapong, 1),
        "f_n": round(f_n, 2),
        "score": round(score, 1),
        "ansk_total": round(ansk_total, 0),
        "fv_obelan": round(fv_obelan, 1),
        "kassa": round(kassa, 1),
        "total_dn": total_dn,
    }


def _setup_forvaltning(room: GameRoom):
    """Initialize Phase 4: remove BRF, assign properties, setup decks."""
    events = []

    room.f4_yield_b = YIELD_START_BOSTADER
    room.f4_yield_k = YIELD_START_KOMMERSIELLT
    room.f4_quarter = 0

    # Deep copy Phase 4 data
    room.f4_yield_cards = {
        "bostader": list(room.game_data.yield_cards.get("bostader", [])),
        "kommersiellt": list(room.game_data.yield_cards.get("kommersiellt", [])),
    }
    room.f4_world_events = list(room.game_data.world_events)
    random.shuffle(room.f4_world_events)
    room.f4_dd_deck = copy.deepcopy(room.game_data.dd_cards)
    random.shuffle(room.f4_dd_deck)

    # Build market pile (remaining projects, exclude BRF)
    room.f4_market_props = []
    owned_names = {p.namn for pl in room.players for p in pl.projects}
    for typ, stack in room.game_data.projects.items():
        if typ == "BRF":
            continue
        for proj in stack:
            if proj.namn not in owned_names:
                room.f4_market_props.append(copy.deepcopy(proj))
    random.shuffle(room.f4_market_props)

    # Per-player: Förvaltning 2.0 övergångsekonomi (Nya Förvaltning, designdoc 2026-05-09).
    #   Slutkassa Fas 4-start = TB + BRF-intäkt + nya lån − byggnadskreditiv
    # där TB redan ligger i EK (flyttades dit i _gf_finish som abt_remaining_before_transfer),
    # BRF säljs för MV + 10 (fast vinst, ersätter gamla MV − ansk + tärning),
    # nya lån = summan av förtryckta lånebelopp på förvaltade fastigheter,
    # kreditiv = total anskaffning för spelarens portfölj.
    room.f4_mgmt_decks = {}
    for player in room.players:
        placed_projects = [p for p in player.projects
                           if p.id in player.placed_project_ids]
        brf_projects = [p for p in placed_projects if p.typ == "BRF"]
        forvaltade = [p for p in placed_projects if p.typ != "BRF"]

        brf_intakt = sum(p.marknadsvarde + 10 for p in brf_projects)
        nya_lan = sum((p.lanebelopp or 0) for p in forvaltade)
        kreditiv = sum(p.anskaffning for p in placed_projects)

        # TB är redan inräknad i player.eget_kapital efter _gf_finish.
        # Vi loggar TB explicit för transparens, men adderar den inte igen.
        tb = player.abt_remaining_before_transfer
        slutkassa_delta = brf_intakt + nya_lan - kreditiv
        player.eget_kapital += slutkassa_delta
        player.f4_tb = tb

        if brf_projects:
            brf_details = ", ".join(f"{p.namn} (MV {p.marknadsvarde}+10)"
                                    for p in brf_projects)
            events.append({
                "type": "event",
                "text": f"{player.name} säljer BRF: {brf_details} → +{brf_intakt} Mkr",
            })
        events.append({
            "type": "economics",
            "text": (f"{player.name} övergångsekonomi: TB {tb:.0f} + BRF {brf_intakt} "
                     f"+ nya lån {nya_lan} − kreditiv {kreditiv} "
                     f"→ kassa {player.eget_kapital:.0f} Mkr"),
        })

        player.fastigheter = forvaltade
        for prop in player.fastigheter:
            if prop.namn not in player.projekt_energiklass:
                player.projekt_energiklass[prop.namn] = prop.energiklass

        # Mgmt event decks per player (deep copy, shuffled)
        decks = {}
        for typ, cards in room.game_data.mgmt_events.items():
            decks[typ] = copy.deepcopy(cards)
            random.shuffle(decks[typ])
        room.f4_mgmt_decks[player.id] = decks

        brf_count = len(player.projects) - len(player.fastigheter)
        events.append({
            "type": "phase_change",
            "text": f"{player.name}: {len(player.fastigheter)} förvaltningsfastigheter "
                    f"({brf_count} BRF sålda)",
        })

    room.f4_hired_ids = set()

    # Förvaltning 2.0 §Kvartal 0: dra händelsekort per fastighet + DD per fastighet
    # + 2 FC + 2 FS-personkort.
    for player in room.players:
        _dra_dd_per_fastighet(room, player, events)
        _dra_handelsekort_per_fastighet(room, player, events)
        _dra_personkort(room, player, events, fc_n=2, fs_n=2)

    room.events_log.extend(events)

    # Start with hiring for first player
    room.turn_index = 0
    _f4_setup_hire(room, room.players[0])


def _f4_setup_hire(room, player):
    """Setup staff hiring for a player.

    Förvaltning 2.0: Båda måste anställas — en FC OCH en FS. Inga kostnader,
    inga kapacitetstak (designdok §Personal). Varje arketyp har egenskaper
    som påverkar spelet på fastighetsnivå.
    """
    has_fc = any((s.roll if hasattr(s, 'roll') else s.get("roll", "")) == "FC"
                 for s in player.staff)
    has_fs = any((s.roll if hasattr(s, 'roll') else s.get("roll", "")) == "FS"
                 for s in player.staff)

    available = [s for s in _staff_pool(room.game_data) if s.id not in room.f4_hired_ids]

    must_hire = not has_fc or not has_fs
    msg_parts = []
    if not has_fc:
        msg_parts.append("välj en Fastighetschef (FC)")
    if not has_fs:
        msg_parts.append("välj en Fastighetsspecialist (FS)")
    msg = " och ".join(msg_parts) if msg_parts else "Personal klar"
    msg = msg.capitalize()

    room.sub_state = "f4_hire_staff"
    room.pending_action = {
        "action": "f4_hire",
        "player_id": player.id,
        "message": msg,
        "available": [s.to_dict() for s in available],
        "has_fc": has_fc,
        "has_fs": has_fs,
        "must_hire": must_hire,
    }


def _f4_advance_hire(room, events):
    """Move to next player's hiring or start Q1."""
    room.next_turn()
    if room.turn_index == 0:
        # All players hired - start Q1
        _f4_start_quarter(room, events)
    else:
        _f4_setup_hire(room, room.current_player)


def _f4_start_quarter(room, events):
    """Begin a new quarter."""
    room.f4_quarter += 1
    q = room.f4_quarter
    room.f4_no_trading = False
    room.f4_energy_discount = 1.0

    events.append({
        "type": "phase_change",
        "text": f"Kvartal {q}/4 börjar!",
    })

    # Q2+: Yield changes
    if q >= 2:
        yb_cards = room.f4_yield_cards.get("bostader", [])
        yk_cards = room.f4_yield_cards.get("kommersiellt", [])
        yb_change = yb_cards.pop(0) if yb_cards else 0
        yk_change = yk_cards.pop(0) if yk_cards else 0
        room.f4_yield_b += yb_change
        room.f4_yield_k += yk_change
        events.append({
            "type": "economics",
            "text": f"Yield: Bostäder {yb_change:+.2f}% → {room.f4_yield_b:.2f}%, "
                    f"Kommersiellt {yk_change:+.2f}% → {room.f4_yield_k:.2f}%",
        })

    # Säkerhetscheck efter yield-rörelsen (designdoc §Margin call). Sätter röd
    # markör på alla fastigheter där MV < lånebelopp.
    for player in room.players:
        _margin_call_scan(room, player, events)

    # Historik-snapshot per kvartal (yield-bana, EK + slutpoäng per spelare).
    snapshot = {
        "quarter": q,
        "yield_b": round(room.f4_yield_b, 2),
        "yield_k": round(room.f4_yield_k, 2),
        "players": [],
    }
    for p in room.players:
        live = calc_live_score(room, p)
        snapshot["players"].append({
            "id": p.id,
            "name": p.name,
            "color": p.color,
            "ek": round(p.eget_kapital, 1),
            "dn_total": live["total_dn"],
            "score": live["score"],
        })
    room.f4_history.append(snapshot)

    # Förvaltning 2.0: dra händelsekort per fastighet + 1 FC + 1 FS personkort.
    for p in room.players:
        _dra_handelsekort_per_fastighet(room, p, events)
        _dra_personkort(room, p, events, fc_n=1, fs_n=1)

    # World event
    if room.f4_world_events:
        we = room.f4_world_events.pop(0)
        _f4_resolve_world_event(room, we, events)
        room.sub_state = "f4_world_event"
        room.pending_action = {
            "action": "continue",
            "player_id": room.players[0].id,
            "message": f"Omvärldshändelse: {we.rubrik}",
            "world_event": we.to_dict(),
            "quarter": q,
            "yield_b": round(room.f4_yield_b, 2),
            "yield_k": round(room.f4_yield_k, 2),
        }
    else:
        room.turn_index = 0
        _f4_start_player_turn(room, events)


def _f4_resolve_world_event(room, event, events):
    """Apply world event effects to all players."""
    for player in room.players:
        if not player.fastigheter:
            continue
        total_effect = 0

        if event.effekt_typ in ("kostnad_alla", "intäkt_alla"):
            total_effect = event.effekt_mkr * len(player.fastigheter)
        elif event.effekt_typ in ("kostnad_kommersiellt", "kostnad_kon"):
            count = sum(1 for p in player.fastigheter if p.typ in KOMMERSIELLT_TYPES)
            total_effect = event.effekt_mkr * count
        elif event.effekt_typ == "intäkt_hr":
            count = sum(1 for p in player.fastigheter if p.typ == "HYRESRÄTT")
            total_effect = event.effekt_mkr * count
        elif event.effekt_typ == "intäkt_fsk":
            count = sum(1 for p in player.fastigheter if p.typ == "FÖRSKOLA")
            total_effect = event.effekt_mkr * count
        elif event.effekt_typ == "kostnad_per_ek":
            for prop in player.fastigheter:
                ek = _get_prop_ek(prop, player)
                if ek in (event.poverkar or ""):
                    total_effect += event.effekt_mkr
        elif event.effekt_typ == "intäkt_per_ek":
            for prop in player.fastigheter:
                ek = _get_prop_ek(prop, player)
                if ek in (event.poverkar or ""):
                    total_effect += event.effekt_mkr
        elif event.effekt_typ == "ingen_budgivning":
            room.f4_no_trading = True
        elif event.effekt_typ == "energi_rabatt":
            room.f4_energy_discount = 0.5

        if total_effect != 0:
            player.eget_kapital += total_effect
            events.append({
                "type": "economics",
                "text": f"{player.name}: {total_effect:+.1f} Mkr (omvärld)",
            })


def _f4_start_player_turn(room, events):
    """Start a player's quarter turn: collect driftnetto, pay salaries.

    Förvaltning 2.0: Summera effektiv DN över alla fastigheter (årlig), dela med 4
    för kvartalscash (avrundat nedåt). Residual hanteras med restkort (1 per 0,25 Mkr;
    autokonvertera 4→1 Mkr cash). Drar därtill räntekostnad (förtryckt per fastighet).
    """
    player = room.current_player
    q = room.f4_quarter

    # Total årlig effektiv DN (visible only — dolda kort räknas i senare etapp).
    dn_total = 0
    for prop in player.fastigheter:
        dn_total += _eff_dn(prop, player)
        dn_total += int(round(player.driftnetto_bonus.get(prop.namn, 0)))

    # FS-2 'Per Kvalitetsoptimeraren': +1 DN på fastighet med högst Q (passiv).
    fs2_bonus = _fs_kvalitetsoptimerare_bonus(player)
    dn_total += fs2_bonus

    # Kvartalscash + residual i 0,25-steg (heltal 0..3 = 0/0,25/0,5/0,75 Mkr).
    quarter_cash = dn_total // 4
    residual_steps = dn_total % 4
    player.f4_restkort += residual_steps
    auto_converted = 0
    while player.f4_restkort >= 4:
        player.f4_restkort -= 4
        quarter_cash += 1
        auto_converted += 1

    # Räntekostnad: summa förtryckta räntekostnader per kvartal från fastighetskorten.
    ranta_total = sum((prop.rantekostnad_kvartal or 0) for prop in player.fastigheter)

    # FC-5 'Den lugna': -1 mkr räntedrag/kvartal (passiv).
    rantereduktion = _fc_den_lugna_rantereduktion(player)
    ranta_total = max(0, ranta_total - rantereduktion)

    # Personkort 'ranta_minus1': konsumera ev. token från handen.
    if player.f4_ranta_reduction_next > 0:
        ranta_total = max(0, ranta_total - player.f4_ranta_reduction_next)
        player.f4_ranta_reduction_next = 0

    # Personallöner – F2-arketyperna har lon=0 (designdok: 'Inga separata kostnader').
    # Gamla F_personal-staff har fortfarande lön om USE_F2_STAFF=False.
    salary_total = 0 if USE_F2_STAFF else sum(
        s.lon if hasattr(s, 'lon') else s.get("lon", 0)
        for s in player.staff
    )

    cash_flow = quarter_cash - ranta_total - salary_total
    player.eget_kapital += cash_flow

    restkort_note = (f" (auto-konv {auto_converted} Mkr)" if auto_converted else "")
    extras = []
    if fs2_bonus:
        extras.append(f"FS-2 +{fs2_bonus} DN")
    if rantereduktion:
        extras.append(f"FC-5 −{rantereduktion} ränta")
    extra_text = (" [" + ", ".join(extras) + "]") if extras else ""
    lon_text = f", lön −{salary_total:.1f}" if salary_total > 0 else ""
    events.append({
        "type": "economics",
        "text": (f"{player.name} Q{q}: DN {dn_total} → cash {quarter_cash}"
                 f"{restkort_note}, restkort {player.f4_restkort}/3, "
                 f"ränta −{ranta_total}{lon_text} = "
                 f"{cash_flow:+.1f} Mkr (EK: {player.eget_kapital:.1f}){extra_text}"),
    })

    # Q2: rent negotiation
    if q == 2:
        hr_props = [p for p in player.fastigheter if p.typ == "HYRESRÄTT"]
        if hr_props:
            _f4_setup_rent_negotiation(room, player, hr_props, events)
            return

    # Management events (gamla mgmt_events) hoppas över när SKIP_MGMT_EVENTS är satt.
    # Nya F2_händelsekort per typ kommer in i Steg G med rätt mekanik.
    if SKIP_MGMT_EVENTS:
        _f4_after_mgmt(room, player, events)
    else:
        _f4_start_mgmt_events(room, player, events)


def _f4_setup_rent_negotiation(room, player, hr_props, events):
    """Setup rent negotiation for HR properties.

    Förvaltning 2.0: F2-FC bidrar med en platt förhandlingsmodifier (+3/+1/0/-1)
    utöver dice-rollen. Modifiern adderas till netto innan RENT_SCALE-uppslag.
    """
    # Roll dice
    hgf_roll = roll("D6")
    fa_roll = roll("D6")

    # Best FC negotiation die
    best_fc = None
    best_die = ""
    best_sides = 0
    for s in player.staff:
        s_roll = s.roll if hasattr(s, 'roll') else s.get("roll", "")
        s_forh = s.forhandling if hasattr(s, 'forhandling') else s.get("forhandling", "")
        if s_roll == "FC" and s_forh:
            sides = DICE_MAP.get(s_forh.upper(), 0)
            if sides > best_sides:
                best_sides = sides
                best_die = s_forh
                best_fc = s

    fc_roll_val = roll(best_die) if best_die else 0
    fc_name = best_fc.namn if best_fc and hasattr(best_fc, 'namn') else (
        best_fc.get("namn", "") if best_fc else "Ingen FC")

    # F2 FC förhandlings-modifier (Förh +3/+1/0/-1 från arketypen).
    fc_modifier = _fc_forhandling_modifier(player)

    # Personkort-bonus från spelade kort (forh_plus2 / forh_plus3).
    personkort_bonus = player.f4_forh_bonus_next
    player.f4_forh_bonus_next = 0

    netto = fc_roll_val + fa_roll - hgf_roll + fc_modifier + personkort_bonus
    netto_clamped = max(min(netto, 17), -4)
    hojning = RENT_SCALE.get(netto_clamped, 0)
    total = hojning * len(hr_props)

    if total > 0:
        player.eget_kapital += total

    mod_text = f" + FC-bonus({fc_modifier:+d})" if fc_modifier else ""
    events.append({
        "type": "economics",
        "text": (f"{player.name}: Hyresförhandling FC({fc_roll_val}) + FÄ({fa_roll}) "
                 f"- HGF({hgf_roll}){mod_text} = {netto} → {total:+.1f} Mkr"),
    })

    room.sub_state = "f4_rent_result"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": "Hyresförhandling",
        "hgf_roll": hgf_roll,
        "fa_roll": fa_roll,
        "fc_roll": fc_roll_val,
        "fc_name": fc_name,
        "fc_die": best_die or "Ingen",
        "fc_modifier": fc_modifier,
        "netto": netto,
        "hojning_per": round(hojning, 1),
        "hr_count": len(hr_props),
        "total": round(total, 1),
        "eget_kapital": round(player.eget_kapital, 1),
    }


def _f4_start_mgmt_events(room, player, events):
    """Process management events for each property."""
    results = []
    decks = room.f4_mgmt_decks.get(player.id, {})

    for prop in player.fastigheter:
        event_type = PROJECT_TYPE_TO_EVENT.get(prop.typ, "ALLA")
        card = None

        # Search for applicable card
        for deck_type in [event_type, "ALLA"]:
            if deck_type not in decks or not decks[deck_type]:
                continue
            deck = decks[deck_type]
            for attempt in range(len(deck)):
                candidate = deck.pop(0)
                deck.append(candidate)  # Put back at end
                if _mgmt_card_applies(candidate, player, prop):
                    card = candidate
                    break
            if card:
                break

        if card:
            # Check mitigation
            mitigator = _staff_has_mitigation(player, card.mildring_roll, card.mildring_spec)
            if mitigator:
                effect = card.mildring_effekt_mkr
                mit_name = mitigator.namn if hasattr(mitigator, 'namn') else mitigator.get("namn", "")
            else:
                effect = card.effekt_mkr
                mit_name = None

            if effect != 0:
                player.eget_kapital += effect

            results.append({
                "prop_namn": prop.namn,
                "prop_typ": prop.typ,
                "card": card.to_dict(),
                "mitigated": mit_name is not None,
                "mitigator": mit_name,
                "effect": round(effect, 1),
            })

    # Shuffle decks for next quarter
    for typ_key in decks:
        random.shuffle(decks[typ_key])

    room.sub_state = "f4_mgmt_events"
    room.pending_action = {
        "action": "continue",
        "player_id": player.id,
        "message": "Händelsekort",
        "mgmt_results": results,
        "eget_kapital": round(player.eget_kapital, 1),
        "quarter": room.f4_quarter,
    }


def _mgmt_card_applies(card, player, prop) -> bool:
    t = card.trigger.strip() if hasattr(card, 'trigger') else "Alla"
    if not t or t == "Alla":
        return True
    if t == "KOMPLEX":
        return player.kvarter_trigger == "KOMPLEX"
    if t == "STAPLAD":
        return player.kvarter_trigger in ("STAPLAD", "KOMPLEX")
    if t == "BTA_C+":
        return player.bta_klass in ("C", "D")
    if t == "EK_DEF":
        return _get_prop_ek(prop, player) in ("D", "E", "F")
    if t == "EK_ABC":
        return _get_prop_ek(prop, player) in ("A", "B", "C")
    return True


def _staff_has_mitigation(player, roll_type: str, spec: str):
    if not roll_type or not spec:
        return None
    for s in player.staff:
        s_roll = s.roll if hasattr(s, 'roll') else s.get("roll", "")
        s_spec = s.specialisering if hasattr(s, 'specialisering') else s.get("specialisering", "")
        if s_roll == roll_type and (s_spec == spec or s_spec == "Generalist"):
            return s
    return None


def _f4_after_mgmt(room, player, events):
    """After management events: energy upgrade or market."""
    q = room.f4_quarter
    if q <= 3:
        _f4_setup_energy_upgrade(room, player)
    else:
        _f4_finish_player_turn(room, events)


# Per-kvartal-limit på antal UNIKA projekt som får energiuppgraderas (spelplanen + §8.8)
# Valfritt antal steg per projekt — samma projekt kan höjas flera klasser i ett och samma kvartal.
ENERGY_UPGRADE_PROJECTS_PER_QUARTER = {1: 3, 2: 2, 3: 1, 4: 0}


def _f4_setup_energy_upgrade(room, player):
    """Let player choose energy upgrades.

    Vid moderbolagslån (§6.2): uppgraderingsstopp — visar tom lista.
    Per kvartal: Q1=3, Q2=2, Q3=1, Q4=0 unika projekt (spelplanen + §8.8).
    Samma projekt kan höjas flera steg i samma kvartal — räknas som 1.
    """
    has_loan = (player.abt_loans_net + player.abt_borrowing_cost) > 0
    q = room.f4_quarter
    quarter_limit = ENERGY_UPGRADE_PROJECTS_PER_QUARTER.get(q, 0)
    q_key = str(q)
    already_upgraded = list(player.f4_upgrades_per_quarter.get(q_key, []))
    slots_left = max(0, quarter_limit - len(already_upgraded))

    upgradeable = []
    if not has_loan and quarter_limit > 0:
        for prop in player.fastigheter:
            ek = _get_prop_ek(prop, player)
            if ek == "A":
                continue
            # Tillåt om: redan uppgraderat detta kvartal (gratis fortsättning) ELLER ledigt slot
            already_this_q = prop.namn in already_upgraded
            if not already_this_q and slots_left <= 0:
                continue  # Skip — limiten nådd och detta är inte ett påbörjat projekt
            ek_idx = ENERGY_CLASSES.index(ek) if ek in ENERGY_CLASSES else 2
            new_ek = ENERGY_CLASSES[ek_idx - 1] if ek_idx > 0 else "A"
            cost = ENERGY_UPGRADE_COST_PER_STEP * room.f4_energy_discount  # 3 Mkr/steg per §8.8
            upgradeable.append({
                "namn": prop.namn, "typ": prop.typ, "ek": ek, "new_ek": new_ek,
                "cost": round(cost, 1),
                "already_started_this_q": already_this_q,
            })

    room.sub_state = "f4_energy_upgrade"
    if has_loan:
        msg = "Energiuppgradering — blockerad pga moderbolagslån (§6.2)"
    elif quarter_limit == 0:
        msg = f"Inga energiuppgraderingar tillåtna i Kvartal {q}"
    elif slots_left == 0 and not already_upgraded:
        msg = f"Kvartal {q}: limit nådd ({quarter_limit} projekt)"
    else:
        rabatt = " (50% rabatt!)" if room.f4_energy_discount < 1 else ""
        msg = f"Energiuppgradering — Kvartal {q}: {len(already_upgraded)}/{quarter_limit} unika projekt valda{rabatt}"
    room.pending_action = {
        "action": "f4_energy_upgrade",
        "player_id": player.id,
        "upgradeable": upgradeable,
        "eget_kapital": round(player.eget_kapital, 1),
        "discount": room.f4_energy_discount,
        "has_loan": has_loan,
        "quarter_limit": quarter_limit,
        "projects_used": len(already_upgraded),
        "message": msg,
    }


def _f4_setup_market(room, player, events):
    """Setup market phase: sell then buy.

    Förvaltning 2.0: Fastigheter med risk för tvångsförsäljning (MV < lån)
    auto-säljs här innan vanlig sell/buy. Spelaren får tvångs-MV (0.7 × normal).
    """
    q = room.f4_quarter
    if q > 3 or room.f4_no_trading:
        _f4_finish_player_turn(room, events)
        return

    # Auto-tvångsförsäljning av fastigheter där MV < lån (risk-flagga satt)
    margin_call_names = set(player.f4_margin_call_props or set())
    if margin_call_names:
        sold = []
        idx_to_sell = [i for i, p in enumerate(player.fastigheter)
                        if p.namn in margin_call_names]
        # Sälj från slutet så index inte skiftar
        for i in reversed(idx_to_sell):
            prop = player.fastigheter[i]
            y = _prop_yield(prop, room)
            eff = _eff_dn(prop, player)
            mv_tvang = _mv_lookup(eff, y, "tvang")  # 0.7 × normal MV
            lan = getattr(prop, 'lanebelopp', 0) or 0
            net = mv_tvang - lan  # kan vara negativt
            player.eget_kapital += net
            player.fastigheter.pop(i)
            player.projekt_energiklass.pop(prop.namn, None)
            # Avslöja dolda kort vid tvångsauktion (designdok)
            _avsloja_dolda_kort(player, prop.namn, events, anledning="tvångsförsäljs")
            sold.append(f"{prop.namn} (MV {mv_tvang} − lån {lan} = {net:+d} Mkr)")
        # Rensa risk-markörer
        player.f4_margin_call_props = set()
        events.append({
            "type": "event",
            "text": (f"⚠ {player.name}: AUTO-TVÅNGSFÖRSÄLJNING vid marknadsfas: "
                     f"{', '.join(sold)}. EK: {player.eget_kapital:.0f} Mkr"),
        })

    real_ek = _calc_real_ek(player)
    has_loan = (player.abt_loans_net + player.abt_borrowing_cost) > 0
    forced_sell = has_loan and len(player.fastigheter) > 1

    # Draw new market properties
    new_avail = []
    for _ in range(QUARTER_NEW_PROPS.get(q, 0)):
        if room.f4_market_props:
            new_avail.append(room.f4_market_props.pop(0))
    room.temp["f4_new_avail"] = new_avail

    if forced_sell:
        _f4_setup_sell(room, player, forced=True)
    else:
        _f4_setup_sell_or_buy(room, player)


def _f4_setup_sell_or_buy(room, player):
    """Ask player if they want to sell, buy, or skip market."""
    new_avail = room.temp.get("f4_new_avail", [])
    real_ek = _calc_real_ek(player)
    has_loan = (player.abt_loans_net + player.abt_borrowing_cost) > 0

    # Build property info for selling
    sell_list = []
    for prop in player.fastigheter:
        y = _prop_yield(prop, room)
        fv = _calc_fastighetsvarde(prop, y, _get_prop_ek(prop, player))
        earn = fv * (1 - LOAN_RATIO)
        sell_list.append({
            "namn": prop.namn, "typ": prop.typ, "fv": round(fv, 1),
            "earn_30": round(earn, 1),
        })

    # Build property info for buying (blocked if player has parent company loan)
    buy_list = []
    if not has_loan:
        for prop in new_avail:
            y = _prop_yield(prop, room)
            fv = _calc_fastighetsvarde(prop, y, prop.energiklass)
            cost = fv * (1 - LOAN_RATIO)
            buy_list.append({
                "namn": prop.namn, "typ": prop.typ, "bta": prop.bta,
                "driftnetto": round(prop.driftnetto, 1), "ek": prop.energiklass,
                "fv": round(fv, 1), "cost_30": round(cost, 1),
                "can_afford": cost <= real_ek,
            })

    room.sub_state = "f4_market"
    room.pending_action = {
        "action": "f4_market",
        "player_id": player.id,
        "message": "Köpförbud — du har moderbolagslån" if has_loan else "Fastighetsmarknad",
        "sell_list": sell_list,
        "buy_list": buy_list,
        "real_ek": round(real_ek, 1),
        "can_buy": not has_loan and real_ek >= 0,
        "forced_sell": False,
        "has_loan": has_loan,
    }


def _f4_setup_sell(room, player, forced=False):
    """Setup forced or voluntary sell."""
    real_ek = _calc_real_ek(player)
    sell_list = []
    for prop in player.fastigheter:
        y = _prop_yield(prop, room)
        fv = _calc_fastighetsvarde(prop, y, _get_prop_ek(prop, player))
        earn = fv * (1 - LOAN_RATIO)
        sell_list.append({
            "namn": prop.namn, "typ": prop.typ, "fv": round(fv, 1),
            "earn_30": round(earn, 1),
        })

    room.sub_state = "f4_market_sell"
    room.pending_action = {
        "action": "f4_market_sell",
        "player_id": player.id,
        "message": "Tvångsförsäljning — du har moderbolagslån och fler än 1 fastighet!" if forced else "Sälj fastighet",
        "sell_list": sell_list,
        "real_ek": round(real_ek, 1),
        "forced": forced,
    }


def _f4_do_sell(room, player, prop_idx, events):
    """Execute a property sale. Sale proceeds go to EK.
    Förvaltning 2.0: dolda kort (DD + dolda händelsekort) avslöjas för alla."""
    prop = player.fastigheter.pop(prop_idx)
    y = _prop_yield(prop, room)
    fv = _calc_fastighetsvarde(prop, y, _get_prop_ek(prop, player))
    earn = fv * (1 - LOAN_RATIO)
    player.eget_kapital += earn
    player.projekt_energiklass.pop(prop.namn, None)

    # Avslöja dolda kort (designdok §Försäljning)
    _avsloja_dolda_kort(player, prop.namn, events, anledning="sålde")

    events.append({
        "type": "economics",
        "text": f"{player.name} sålde {prop.namn} för {earn:.1f} Mkr (EK)",
    })

    # Lös moderbolagslån direkt så fort EK har 100 Mkr (1 lån = 95 net + 5 fee = 100 gross)
    loans_repaid = 0
    while (player.abt_loans_net + player.abt_borrowing_cost) > 0 and player.eget_kapital >= 100:
        player.eget_kapital -= 100
        player.abt_loans_net = max(0, player.abt_loans_net - 95)
        player.abt_borrowing_cost = max(0, player.abt_borrowing_cost - 5)
        loans_repaid += 1
    if loans_repaid > 0:
        remaining = player.abt_loans_net + player.abt_borrowing_cost
        events.append({
            "type": "loan",
            "text": f"{loans_repaid} moderbolagslån återbetalat (-{loans_repaid * 100} Mkr från EK). Kvar: {remaining:.0f} Mkr skuld, EK: {player.eget_kapital:.1f} Mkr.",
        })


def _f4_setup_buy(room, player):
    """Setup buy phase with available market properties."""
    new_avail = room.temp.get("f4_new_avail", [])
    real_ek = _calc_real_ek(player)
    has_loan = (player.abt_loans_net + player.abt_borrowing_cost) > 0

    # Block purchases if player has parent company loan
    if has_loan:
        _f4_after_market(room, player, [])
        return

    buy_list = []
    for prop in new_avail:
        y = _prop_yield(prop, room)
        fv = _calc_fastighetsvarde(prop, y, prop.energiklass)
        cost = fv * (1 - LOAN_RATIO)
        buy_list.append({
            "namn": prop.namn, "typ": prop.typ, "bta": prop.bta,
            "driftnetto": round(prop.driftnetto, 1), "ek": prop.energiklass,
            "fv": round(fv, 1), "cost_30": round(cost, 1),
            "can_afford": cost <= real_ek,
        })

    if not buy_list or real_ek < 0:
        _f4_after_market(room, player, [])
        return

    room.sub_state = "f4_market_buy"
    room.pending_action = {
        "action": "f4_market_buy",
        "player_id": player.id,
        "message": "Köp fastighet",
        "buy_list": buy_list,
        "real_ek": round(real_ek, 1),
    }


def _f4_do_buy(room, player, prop_idx, events):
    """Execute a property purchase + DD card.

    Förvaltning 2.0: DD-kortet läggs DOLT på fastigheten (precis som vid Q0),
    inte applicerat direkt på EK. Effekten räknas som dolt DN via
    driftnetto_bonus i intäktsfasen.
    """
    new_avail = room.temp.get("f4_new_avail", [])
    prop = new_avail.pop(prop_idx)
    y = _prop_yield(prop, room)
    fv = _calc_fastighetsvarde(prop, y, prop.energiklass)
    cost = fv * (1 - LOAN_RATIO)
    player.eget_kapital -= cost
    player.fastigheter.append(prop)
    player.projekt_energiklass[prop.namn] = prop.energiklass
    # Förvaltning 2.0: Skede 1-poängen räknar all anskaffning, inklusive Skede 3-köp.
    player.f4_extra_anskaffning += prop.anskaffning

    events.append({
        "type": "economics",
        "text": f"{player.name} köpte {prop.namn} för {cost:.1f} Mkr",
    })

    # Dra DD dolt på den nyköpta fastigheten (samma logik som Q0).
    _dra_dd_kort_for_prop(room, player, prop, events)
    room.temp["f4_last_dd"] = None


def _f4_after_market(room, player, events):
    """After market: check if rehire needed, then finish turn."""
    # Return unsold market props
    new_avail = room.temp.get("f4_new_avail", [])
    for prop in new_avail:
        room.f4_market_props.append(prop)
    room.temp["f4_new_avail"] = []

    # Check if staff capacity enough
    current_cap = sum(s.kapacitet if hasattr(s, 'kapacitet') else s.get("kapacitet", 0)
                      for s in player.staff)
    if current_cap < len(player.fastigheter):
        _f4_setup_hire(room, player)
        room.sub_state = "f4_rehire"
        return

    _f4_finish_player_turn(room, events)


def _f4_finish_player_turn(room, events):
    """Move to next player or next quarter."""
    room.next_turn()
    if room.turn_index == 0:
        # All players done this quarter
        if room.f4_quarter >= 4:
            _f4_final_valuation(room, events)
        else:
            _f4_start_quarter(room, events)
    else:
        _f4_start_player_turn(room, events)


def _f4_final_valuation(room, events):
    """Räkna slutpoäng enligt Förvaltning 2.0 (kalibrerad så 'superbra' = 25 per skede).

    Skede 1 (Utveckling)  = anskaffning / 100              → 25 vid 2500 Mkr förvärv
    Skede 2 (Byggande)    = TG (procent)                    → 25 vid TG 25 %
    Skede 3 (Förvaltning) = (FV_obelånat + kassa × SKEDE3_KASSA_FAKTOR) / SKEDE3_DIVISOR
                            där FV_obelånat = säljvärde (normal MV) − utestående lån,
                            kassa = real EK (efter moderbolagslån).
    Råpoäng = S1 + S2 + S3
    Slutpoäng = Råpoäng × f(n)  där f(n) är Q/H/T-baserad straffaktor.
    """
    from economics import calc_tg, deviation_factor, calc_deviation_n

    results = []
    for player in room.players:
        # Total anskaffning: ursprungsportfölj (placerade projekt) + nya köp i Skede 3.
        ansk_orig = sum(p.anskaffning for p in player.projects
                        if p.id in player.placed_project_ids)
        ansk_total = ansk_orig + player.f4_extra_anskaffning
        skede1 = ansk_total / 100.0

        # Skede 2 — TG (saldo-%)
        skede2 = calc_tg(player)

        # Skede 3 — fastighetsvärde obelånat + kassa-vikt
        total_dn = sum(_eff_dn(prop, player) for prop in player.fastigheter)
        saljvarde = sum(_mv_lookup(_eff_dn(prop, player),
                                   _prop_yield(prop, room),
                                   "normal")
                        for prop in player.fastigheter)
        utestaende_lan = sum((prop.lanebelopp or 0) for prop in player.fastigheter)
        fv_obelan = saljvarde - utestaende_lan
        kassa = _calc_real_ek(player)
        skede3 = (fv_obelan + kassa * SKEDE3_KASSA_FAKTOR) / SKEDE3_DIVISOR

        rapong = skede1 + skede2 + skede3

        # Straffaktor från Q/H/T-avvikelse vid Skede 2-3-snapshot.
        dev = calc_deviation_n(player)
        f_n = deviation_factor(dev["n_total"])
        score = rapong * f_n

        # Behåll tidigare fält för kompatibilitet med rapporter.
        player.f4_real_ek = kassa
        player.f4_tb = _calc_tb(player)
        player.f4_fv_30 = fv_obelan  # Nu: FV obelånat (säljvärde − lån)
        player.f4_score = score
        player.f4_score_per_bta = 0  # BTA-normaliseringen är borttagen i nya formeln

        results.append({
            "name": player.name,
            "score": round(score, 1),
            "rapong": round(rapong, 1),
            "skede1": round(skede1, 1),
            "skede2": round(skede2, 1),
            "skede3": round(skede3, 1),
            "ansk_total": round(ansk_total, 0),
            "total_dn": total_dn,
            "saljvarde": saljvarde,
            "utestaende_lan": utestaende_lan,
            "fv_obelan": round(fv_obelan, 1),
            "kassa": round(kassa, 1),
            "f_n": round(f_n, 2),
            "n_total": dev["n_total"],
            "fastigheter": len(player.fastigheter),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    room.f4_final_results = results
    events.append({
        "type": "gf_summary",
        "text": (f"Slutvärdering klar! Vinnare: {results[0]['name']} "
                 f"med {results[0]['score']:.1f} poäng "
                 f"(S1 {results[0]['skede1']} + S2 {results[0]['skede2']} "
                 f"+ S3 {results[0]['skede3']}, f(n)={results[0]['f_n']})"),
        "results": results,
    })

    room.phase = GamePhase.FINISHED
    room.sub_state = "finished"
    room.pending_action = None
    room.events_log.extend(events)


def _handle_forvaltning(room: GameRoom, player: Player, action: dict) -> dict:
    """Handle all Phase 4 actions."""
    events = []
    sub = room.sub_state
    act = action.get("action")
    val = action.get("value")

    # ── Spela personkort (oberoende av pending_action) ──
    if act == "play_personkort" and val:
        result = _play_personkort(room, player, val, events)
        room.events_log.extend(events)
        if not result.get("ok"):
            return {"type": "error", "message": result.get("msg", "Kunde inte spela kortet")}
        return {"type": "state_update", "events": events}

    # ── Staff hiring ──
    if sub in ("f4_hire_staff", "f4_rehire"):
        if act == "f4_hire" and val:
            # Hire a staff member
            staff_id = val
            staff_obj = None
            for s in _staff_pool(room.game_data):
                if s.id == staff_id:
                    staff_obj = s
                    break
            if not staff_obj or staff_id in room.f4_hired_ids:
                return {"type": "error", "message": "Personal inte tillgänglig"}

            player.staff.append(staff_obj)
            room.f4_hired_ids.add(staff_id)
            events.append({
                "type": "economics",
                "text": f"{player.name} anställde {staff_obj.namn} ({staff_obj.roll})",
            })

            # Check if done hiring (F2: kräver både FC och FS, inga kostnader/kapacitetstak).
            has_fc = any((s.roll if hasattr(s, 'roll') else s.get("roll","")) == "FC"
                         for s in player.staff)
            has_fs = any((s.roll if hasattr(s, 'roll') else s.get("roll","")) == "FS"
                         for s in player.staff)
            if has_fc and has_fs:
                if sub == "f4_rehire":
                    _f4_finish_player_turn(room, events)
                else:
                    _f4_advance_hire(room, events)
            else:
                _f4_setup_hire(room, player)
                if sub == "f4_rehire":
                    room.sub_state = "f4_rehire"

        elif act == "f4_hire" and not val:
            # Done hiring (skip) - only if requirements met
            pending = room.pending_action or {}
            if pending.get("must_hire"):
                return {"type": "error", "message": "Du måste anställa mer personal!"}
            if sub == "f4_rehire":
                _f4_finish_player_turn(room, events)
            else:
                _f4_advance_hire(room, events)

        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── World event continue ──
    if sub == "f4_world_event" and act == "continue":
        room.turn_index = 0
        _f4_start_player_turn(room, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── Rent negotiation continue ──
    if sub == "f4_rent_result" and act == "continue":
        if SKIP_MGMT_EVENTS:
            _f4_after_mgmt(room, player, events)
        else:
            _f4_start_mgmt_events(room, player, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── Management events continue ──
    if sub == "f4_mgmt_events" and act == "continue":
        _f4_after_mgmt(room, player, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── Energy upgrade ──
    if sub == "f4_energy_upgrade":
        if act == "f4_energy_upgrade" and val:
            # Vid moderbolagslån: uppgraderingsstopp (§6.2)
            if (player.abt_loans_net + player.abt_borrowing_cost) > 0:
                return {"type": "error", "message": "Uppgraderingsstopp pga moderbolagslån (§6.2)"}
            # Per kvartal-limit (§8.8 + spelplanen): Q1=3, Q2=2, Q3=1, Q4=0 unika projekt
            q = room.f4_quarter
            quarter_limit = ENERGY_UPGRADE_PROJECTS_PER_QUARTER.get(q, 0)
            q_key = str(q)
            already = list(player.f4_upgrades_per_quarter.get(q_key, []))
            prop_namn = val
            if quarter_limit == 0:
                return {"type": "error", "message": f"Inga energiuppgraderingar tillåtna i Kvartal {q}"}
            if prop_namn not in already and len(already) >= quarter_limit:
                return {"type": "error",
                        "message": f"Kvartal {q}: max {quarter_limit} unika projekt får uppgraderas (du har redan valt {len(already)})"}

            # Upgrade a property
            prop = None
            for p in player.fastigheter:
                if p.namn == prop_namn:
                    prop = p
                    break
            if not prop:
                return {"type": "error", "message": "Fastighet ej hittad"}

            ek = _get_prop_ek(prop, player)
            ek_idx = ENERGY_CLASSES.index(ek) if ek in ENERGY_CLASSES else 2
            if ek_idx == 0:
                return {"type": "error", "message": f"{prop.namn} är redan EK A — kan inte uppgraderas mer."}

            new_ek = ENERGY_CLASSES[ek_idx - 1]
            cost = ENERGY_UPGRADE_COST_PER_STEP * room.f4_energy_discount  # 5 Mkr/steg per Regelhäfte §8

            # Förvaltning 2.0: D20-slag, FC/FS-modifier (Tekniska experten +3).
            # Garanti-token från tidigare misslyckande på SAMMA fastighet ger auto-success
            # (designdok: 'misslyckad uppgradering ger något — typ lyckas automatiskt nästa gång').
            garanti = player.f4_energi_garanti.get(prop_namn, 0)
            if garanti > 0:
                d20 = "AUTO"
                modifier = 0
                total = "garanti"
                success = True
                player.f4_energi_garanti[prop_namn] = garanti - 1
            else:
                d20 = roll("D20")
                modifier = _energy_upgrade_modifier(player)
                total = d20 + modifier
                success = total >= ENERGY_UPGRADE_D20_THRESHOLD

            # Spåra projekt-namnet i kvartalets set även vid fail (försök räknas som "kvartalets uppgradering").
            if prop_namn not in already:
                already.append(prop_namn)
                player.f4_upgrades_per_quarter[q_key] = already

            player.eget_kapital -= cost
            mod_text = f"+{modifier}" if isinstance(modifier, int) and modifier > 0 else ""
            if success:
                player.projekt_energiklass[prop.namn] = new_ek
                slag_text = "AUTO (garanti)" if d20 == "AUTO" else f"D20 {d20}{mod_text}={total}"
                events.append({
                    "type": "economics",
                    "text": (f"{player.name}: {prop.namn} {slag_text} "
                             f"→ uppgradering EK {ek}→{new_ek} (−{cost:.1f} Mkr)"),
                })
            else:
                # Spara garanti för nästa försök på samma fastighet
                player.f4_energi_garanti[prop_namn] = player.f4_energi_garanti.get(prop_namn, 0) + 1
                events.append({
                    "type": "economics",
                    "text": (f"{player.name}: {prop.namn} D20 {d20}{mod_text}={total} "
                             f"< {ENERGY_UPGRADE_D20_THRESHOLD} → MISSLYCKAD ({cost:.1f} Mkr förlorad), "
                             f"men nästa försök på {prop.namn} lyckas automatiskt."),
                })
            # Show upgrade options again
            _f4_setup_energy_upgrade(room, player)
        elif act == "f4_energy_upgrade" and not val:
            # Skip energy upgrade
            _f4_setup_market(room, player, events)

        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── Market phase ──
    if sub == "f4_market":
        if act == "f4_market" and val == "sell":
            _f4_setup_sell(room, player, forced=False)
        elif act == "f4_market" and val == "buy":
            _f4_setup_buy(room, player)
        elif act == "f4_market" and val == "skip":
            _f4_after_market(room, player, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    if sub == "f4_market_sell":
        if act == "f4_market_sell" and val is not None:
            idx = int(val)
            if 0 <= idx < len(player.fastigheter):
                _f4_do_sell(room, player, idx, events)
                # Check if still forced: keep selling while loan exists and >1 property
                has_loan = (player.abt_loans_net + player.abt_borrowing_cost) > 0
                if has_loan and len(player.fastigheter) > 1:
                    _f4_setup_sell(room, player, forced=True)
                else:
                    _f4_setup_buy(room, player)
            else:
                return {"type": "error", "message": "Ogiltigt val"}
        elif act == "f4_market_sell" and val is None:
            # Skip selling
            _f4_setup_buy(room, player)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    if sub == "f4_market_buy":
        if act == "f4_market_buy" and val is not None:
            idx = int(val)
            new_avail = room.temp.get("f4_new_avail", [])
            if 0 <= idx < len(new_avail):
                _f4_do_buy(room, player, idx, events)
                # Check if can buy more
                real_ek = _calc_real_ek(player)
                if real_ek >= 0 and room.temp.get("f4_new_avail"):
                    _f4_setup_buy(room, player)
                else:
                    _f4_after_market(room, player, events)
            else:
                return {"type": "error", "message": "Ogiltigt val"}
        elif act == "f4_market_buy" and val is None:
            _f4_after_market(room, player, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    # ── Generic continue ──
    if act == "continue":
        if sub == "f4_player_info":
            _f4_start_mgmt_events(room, player, events)
        else:
            _f4_finish_player_turn(room, events)
        room.events_log.extend(events)
        return {"type": "state_update", "events": events}

    return {"type": "error", "message": f"Okänd åtgärd i Skede 3: {act}/{sub}"}
