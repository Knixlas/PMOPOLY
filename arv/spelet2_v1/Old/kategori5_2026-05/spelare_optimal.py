#!/usr/bin/env python3
"""
AI-spelare för Husbyggspelet.

Monkey-patchar input-funktionerna och fattar beslut baserat på
output-kontext. Har inbyggt skydd mot oändliga loopar.

Användning:
  python3 ai_spelare.py           # Verbose
  python3 ai_spelare.py --silent  # Tyst
"""

import sys
import os
import io
import re
import builtins

# ═══════════════════════════════════════════════════════
#  AI BRAIN
# ═══════════════════════════════════════════════════════

class AIBrain:

    # ── Support buying config (override per strategy) ──
    SUPPORT_MAX_TOTAL = 15     # EK-based logic is primary limiter, this is safety cap
    SUPPORT_EARLY_PHASES = 3   # Legacy (unused by new logic)
    SUPPORT_ABT_FLOOR = 30     # Legacy (unused by new logic)
    TG_TARGET = 22             # Händelser dränerar ~15% → slutar på ~5-7%

    def __init__(self, name="AI-Optimal", data_dir=""):
        self.name = name
        self.data_dir = data_dir
        self.output_lines: list[str] = []
        self.decision_count = 0
        self._upgrade_count = 0
        # Loop protection
        self._last_prompt = ""
        self._repeat_count = 0
        # Support buying tracking
        self._total_support_bought = 0
        self._bought_this_phase = 0
        self._current_fas = 0

    def reset(self):
        self.output_lines.clear()
        self.decision_count = 0
        self._upgrade_count = 0
        self._last_prompt = ""
        self._repeat_count = 0
        self._total_support_bought = 0
        self._bought_this_phase = 0
        self._current_fas = 0
        self._total_support_bought = 0

    def ctx(self, n=40):
        return "\n".join(self.output_lines[-n:])

    def _track_repeats(self, prompt: str) -> int:
        """Räknar hur många gånger samma prompt upprepas i rad."""
        key = prompt.strip()[:40]
        if key == self._last_prompt:
            self._repeat_count += 1
        else:
            self._last_prompt = key
            self._repeat_count = 0
        return self._repeat_count

    def _parse_ek(self, ctx):
        matches = re.findall(r'EK:\s*([-\d.,]+)', ctx)
        return float(matches[-1].replace(",", ".")) if matches else 0

    def _parse_abt(self, ctx):
        matches = re.findall(r'ABT[^:]*:\s*([\d.,]+)', ctx)
        return float(matches[-1].replace(",", ".")) if matches else 0

    def _parse_tg(self, ctx):
        """Parse current TG% from context. Returns remaining ABT as % of start."""
        m = re.search(r'TG:\s*([-\d]+)%', ctx)
        return int(m.group(1)) if m else 50  # Default: assume healthy

    def _parse_abt_start(self, ctx):
        """Parse ABT start value from context."""
        m = re.search(r'start:\s*([\d.,]+)', ctx)
        return float(m.group(1).replace(",", ".")) if m else 0

    def _tg_ok_for_spending(self, ctx, planned_cost=0):
        """Check if TG margin allows additional spending."""
        tg = self._parse_tg(ctx)  # Now reads real TG (incl overflow)
        # If already at or below target, don't spend
        if tg <= self.TG_TARGET:
            return False
        # Check if planned cost would push below target
        if planned_cost > 0:
            abt_start = self._parse_abt_start(ctx)
            if abt_start > 0:
                cost_impact = (planned_cost / abt_start) * 100
                if tg - cost_impact < self.TG_TARGET:
                    return False
        return True

    def _parse_qh_margin(self, ctx):
        """Parse Q and H margin above krav from context."""
        q_match = re.search(r'Q:\s*(\d+)\s*\(krav:\s*(\d+)\)', ctx)
        h_match = re.search(r'H:\s*(\d+)\s*\(krav:\s*(\d+)\)', ctx)
        q_margin = (int(q_match.group(1)) - int(q_match.group(2))) if q_match else 0
        h_margin = (int(h_match.group(1)) - int(h_match.group(2))) if h_match else 0
        return q_margin, h_margin

    def _parse_fas_nr(self, ctx):
        """Parse current phase number from context."""
        m = re.search(r'FAS\s+(\d+)/8', ctx)
        return int(m.group(1)) if m else 1

    def _should_buy_support(self, prompt, ctx):
        """EK-baserat köpbeslut: bedöm antal i förhållande till EK.
        
        Spelaren köper kulturkort INNAN faskort dras (blind).
        Strategi: Säkra ett rimligt lager, men gå aldrig under EK 15 Mkr.
        Anpassa antal efter fas (dyrare senare) och tillgängligt EK.
        """
        ek = self._parse_ek(ctx)
        fas_nr = self._parse_fas_nr(ctx)
        
        # Reset per-phase counter when phase changes
        if fas_nr != self._current_fas:
            self._current_fas = fas_nr
            self._bought_this_phase = 0
        
        # ── HÅRD STOPP ──
        # EK-golv: Bör ej gå under 15 Mkr
        if ek < 15:
            return False
        
        # Totalt tak
        if self._total_support_bought >= self.SUPPORT_MAX_TOTAL:
            return False
        
        # ── EK-BASERAD BEDÖMNING ──
        # Mer EK = fler kort per fas, billiga faser = fler kort
        phase_cost = [2, 2, 3, 3, 4, 5, 6, 7][fas_nr - 1] if fas_nr <= 8 else 5
        
        # Hur många kort har vi råd med utan att krascha EK?
        ek_after = ek  # ABT-kostnad, men vid overflow → EK-påverkan
        
        if ek > 60:
            max_this_phase = 3 if fas_nr <= 4 else 2
        elif ek > 30:
            max_this_phase = 2 if fas_nr <= 5 else 1
        elif ek > 15:
            max_this_phase = 1
        else:
            return False
        
        # Sena faser (dyra) → färre kort
        if phase_cost >= 5 and max_this_phase > 1:
            max_this_phase -= 1
        
        if self._bought_this_phase >= max_this_phase:
            return False
        
        self._bought_this_phase += 1
        self._total_support_bought += 1
        return True

    def _parse_t_margin(self, ctx):
        """Parse T (tid) och returnera marginal till mål (12 mån)."""
        m = re.search(r'T:\s*(\d+)\s*mån', ctx)
        current_t = int(m.group(1)) if m else 12
        return 12 - current_t  # Positivt = utrymme, negativt = redan över

    def _count_available_cards(self, ctx):
        """Räkna tillgängliga kompetenskort (oanvända lev + org + kultur på hand)."""
        lev_m = re.search(r'Lev\s*(\d+)/(\d+)', ctx)
        org_m = re.search(r'Org\s*(\d+)/(\d+)', ctx)
        ext_m = re.search(r'Kultur på hand:\s*(\d+)', ctx)
        
        unused_lev = (int(lev_m.group(2)) - int(lev_m.group(1))) if lev_m else 0
        unused_org = (int(org_m.group(2)) - int(org_m.group(1))) if org_m else 0
        ext_hand = int(ext_m.group(1)) if ext_m else 0
        
        return unused_lev, unused_org, ext_hand

    def _parse_faskort_levels(self, ctx):
        """Parse faskort-nivåer från kontexten.
        
        Returns list of (idx, name, reqs_dict, total_req, effect_text)
        """
        levels = []
        lines = ctx.split("\n")
        for line in lines:
            m = re.match(r'\s+(\d+)\.\s+\[(\w+)\]\s+Krav:\s*(.+?)\s*→\s*Effekt:\s*(.+)', line)
            if m:
                idx = int(m.group(1))
                name = m.group(2)
                req_text = m.group(3).strip()
                effect = m.group(4).strip()
                
                # Parse kompetenskrav
                reqs = {}
                for comp_m in re.finditer(r'(LED|KOM|SAM|PRO|ABM)\s+(\d+)', req_text):
                    reqs[comp_m.group(1)] = int(comp_m.group(2))
                
                total_req = sum(reqs.values())
                levels.append((idx, name, reqs, total_req, effect))
        
        return levels

    def _choose_faskort_level(self, ctx, min_val, max_val):
        """Välj faskort-nivå strategiskt.
        
        Logik:
        1. Parse tillgängliga nivåer och deras krav
        2. Räkna tillgängliga kompetenskort  
        3. Välj högsta nåbara nivån
        4. Om budget tight → kan backa på tid (Negativt) om T-utrymme finns
        5. Annars: Neutralt som minsta mål
        """
        levels = self._parse_faskort_levels(ctx)
        if not levels:
            return min_val
        
        # Tillgängliga kort
        unused_lev, unused_org, ext_hand = self._count_available_cards(ctx)
        total_cards = unused_lev + unused_org + ext_hand
        
        # Fas och marginaler
        fas_nr = self._parse_fas_nr(ctx)
        t_margin = self._parse_t_margin(ctx)
        ek = self._parse_ek(ctx)
        tg = self._parse_tg(ctx)
        
        # Hur mycket kompetens kan vi troligen producera?
        # Lev/org ger ~2-3 poäng relevanta, kulturkort ~1.5
        estimated_kompetens = (unused_lev + unused_org) * 2.5 + ext_hand * 1.5
        
        # Spara kort för framtida faser: ju fler faser kvar, desto mer reservera
        phases_left = 8 - fas_nr
        reserve_factor = phases_left * 0.5  # Spara ~0.5 kort per kvarvarande fas
        usable_kompetens = max(0, estimated_kompetens - reserve_factor)
        
        # Utvärdera varje nivå, uppifrån och ner
        best_choice = min_val  # Default: Negativt
        
        for idx, name, reqs, total_req, effect in reversed(levels):
            if idx < min_val or idx > max_val:
                continue
            
            if name == "Negativt":
                continue  # Prova bättre alternativ först
            
            # Inga krav → ta den direkt
            if total_req == 0:
                best_choice = idx
                break
            
            # Kan vi nå detta krav med tillgängliga kort?
            if total_req <= usable_kompetens:
                best_choice = idx
                break
        
        # Om vi bara kan nå Negativt, kolla om T-marginal finns
        if best_choice == min_val and len(levels) >= 2:
            neg_effect = levels[0][4] if levels else ""
            neut_reqs = levels[1][3] if len(levels) > 1 else 999
            
            # Om Neutralt bara kräver lite kompetens, försök ändå
            if neut_reqs <= total_cards * 2:
                best_choice = min(2, max_val)  # Sikta på Neutralt
            elif t_margin >= 2:
                # Vi har tid-utrymme → acceptera Negativt (ofta T-kostnad)
                best_choice = min_val
            else:
                # Ingen tid-marginal → försök Neutralt ändå (kompetens viktigare)
                if neut_reqs <= total_cards * 3:
                    best_choice = min(2, max_val)
        
        return best_choice

    def _should_retry_buy(self, ctx):
        """Köp mer kulturkort och försök igen?
        
        Ja om: gap till krav är rimligt (1-2 kort kan täcka)
        och EK > 15 Mkr.
        """
        ek = self._parse_ek(ctx)
        if ek < 15:
            return False
        
        # Parse remaining requirements from context
        remaining_m = re.search(r'Kvar att uppfylla:\s*(.+)', ctx)
        if remaining_m:
            reqs = re.findall(r'(\w+)\s+(\d+)', remaining_m.group(1))
            total_gap = sum(int(v) for _, v in reqs)
            # Kulturkort ger ~1.5 relevant kompetens i snitt
            # Om gapet är ≤ 3-4 → värt att försöka med 1-2 kort
            if total_gap <= 4:
                self._total_support_bought += 1
                return True
        
        return False

    # ── Ja/Nej ──

    def decide_yes_no(self, prompt):
        self.decision_count += 1
        ctx = self.ctx()
        p = prompt.lower()

        if any(k in p for k in ["markanvisning", "markexpansion"]):
            return True
        if "ta ett projekt från valfri hög" in p:
            return True
        if "riskbuffert" in p:
            return True
        if "byta ett projekt" in p:
            return False
        if "byta en leverantör" in p:
            return False
        if "spela igen" in p:
            return False
        if "sälja en fastighet" in p:
            # Tvångsförsäljning vid negativt EK – alltid ja
            if self._parse_ek(ctx) < 0:
                return True
            return False

        if "köp mer företagskultur" in p and "försök igen" in p:
            return self._should_retry_buy(ctx)
        if "köp företagskultur" in p:
            return self._should_buy_support(prompt, ctx)

        if "energiuppgraderingar" in p:
            self._upgrade_count = 0
            return self._parse_ek(ctx) > 20

        if "köpa en fastighet" in p:
            # Köp bara om god EK och det finns råd
            ek = self._parse_ek(ctx)
            if ek < 50:
                return False
            # Kolla om det finns minst en fastighet vi har råd med
            if "EJ RÅD" in ctx and "Pris:" in ctx:
                # Räkna fastigheter med/utan "EJ RÅD"
                lines = [l for l in ctx.split("\n") if "Pris:" in l]
                affordable = [l for l in lines if "EJ RÅD" not in l]
                return len(affordable) > 0
            return True

        if "anställ ytterligare" in p:
            return self._parse_ek(ctx) > 5

        return True

    # ── Heltal ──

    def decide_int(self, prompt, min_val, max_val):
        self.decision_count += 1
        repeats = self._track_repeats(prompt)
        ctx = self.ctx()
        p = prompt.lower()

        # ── Riskbuffert-investering (efter PU) ──
        if "val: " in p and max_val == 3 and "riskbuffert" in ctx.lower():
            return self._rb_spend(ctx)

        # ── Projekt ──
        if "välj projekt" in p:
            return 1 if min_val <= 1 else min_val
        if "val (1-2, 0 = passa)" in p:
            return 1
        if "val: " in p and max_val == 3:
            return 1

        # ── Leverantör/org – med loop-skydd ──
        if "välj leverantör" in p or "välj organisation" in p:
            return self._pick_with_rotation(ctx, min_val, max_val, repeats)

        # ── Faskort – strategiskt nivåval ──
        if "välj nivå" in p:
            return self._choose_faskort_level(ctx, min_val, max_val)

        # ── Kompetenskort ──
        if "spela kort" in p:
            return self._pick_card(ctx, min_val, max_val)

        # ── Personal ──
        if "anställ" in p:
            return self._pick_staff(ctx, min_val, max_val)

        # ── Energi ──
        if "uppgradera" in p:
            return self._pick_upgrade(ctx, min_val, max_val)

        # ── Sälj ──
        if "sälj" in p:
            if min_val >= 1:
                # Tvångsförsäljning – sälj minsta (billigaste) fastigheten
                # Parsea fastighetslistan och välj den med lägst FV
                return self._pick_sell(ctx, min_val, max_val)
            return 0  # Frivilligt → avbryt

        # ── Köp fastighet ──
        if "välj" in p and min_val >= 1:
            return 1

        # ── Övrigt ──
        if "antal spelare" in p:
            return 1
        if "lämnar du tillbaka" in p or "byta" in p:
            return 0 if min_val == 0 else 1

        return max(min_val, (min_val + max_val) // 2)

    def _pick_with_rotation(self, ctx, min_val, max_val, repeats):
        """Välj leverantör/org: Smart nivå 2-3 med Q/H-medvetenhet.
        
        Strategi:
        - Mål: nå 1-3 steg ÖVER krav (marginal för genomförande)
        - Konsekvenskorten är tunga → värt att investera för att undvika dem
        - Föredra nivå 2-3 (kostnadseffektivt utan överkonsumtion)
        - Välj den som bäst adresserar svagaste dimensionen
        """
        lines = ctx.split("\n")
        
        # Parse current Q/H margins
        q_margin, h_margin = self._parse_qh_margin(ctx)
        weakest = "Q" if q_margin <= h_margin else "H"
        min_margin = min(q_margin, h_margin)
        
        # Parse available options: index, niva, Q-bidrag, H-bidrag
        options = []
        for line in lines:
            m = re.match(r'\s+(\d+)\.\s+Nivå\s+(\d+)', line)
            if m and "⛔" not in line:
                idx = int(m.group(1))
                niva = int(m.group(2))
                if min_val <= idx <= max_val:
                    # Parse Q/H contributions from display
                    qm = re.search(r'Q:\s*([+-]?\d+)', line)
                    hm = re.search(r'H:\s*([+-]?\d+)', line)
                    q_contrib = int(qm.group(1)) if qm else 0
                    h_contrib = int(hm.group(1)) if hm else 0
                    options.append((idx, niva, q_contrib, h_contrib))
        
        # Remove duplicates, keep last
        seen = {}
        for opt in options:
            seen[opt[0]] = opt
        options = list(seen.values())
        
        if not options:
            choice = min_val + (repeats % (max_val - min_val + 1))
            return min(max(choice, min_val), max_val)
        
        if repeats > 0:
            # Previous blocked – try next
            rotated = options[repeats % len(options)]
            return rotated[0]
        
        # Score each option
        best_idx = options[0][0]
        best_score = -999
        
        # TG awareness: if budget is tight, prefer cheaper options
        tg = self._parse_tg(ctx)
        tg_pressure = max(0, (self.TG_TARGET + 5) - tg)  # 0 = fine, higher = tighter
        
        for idx, niva, q_c, h_c in options:
            score = 0.0
            
            # Prefer level 2-3, but shift down when TG is tight
            if tg_pressure > 5:
                # Budget very tight – prefer cheapest
                level_pref = {1: 10, 2: 6, 3: 2, 4: -5}
            elif tg_pressure > 0:
                # Budget somewhat tight – prefer level 2
                level_pref = {1: 5, 2: 10, 3: 6, 4: 0}
            else:
                # Budget healthy – prefer level 2-3
                level_pref = {1: 2, 2: 10, 3: 8, 4: 3}
            score += level_pref.get(niva, 0)
            
            # Reward contribution to weakest dimension
            new_q_margin = q_margin + q_c
            new_h_margin = h_margin + h_c
            new_min = min(new_q_margin, new_h_margin)
            
            # Big bonus for lifting weakest above 0 (avoid konsekvenskort!)
            if min_margin < 0 and new_min >= 0:
                score += 20
            elif min_margin < 1 and new_min >= 1:
                score += 15
            elif min_margin < 3 and new_min >= 3:
                score += 10
            
            # Reward getting closer to target margin (1-3 above krav)
            TARGET_MARGIN = 2
            q_gap = max(0, TARGET_MARGIN - new_q_margin)
            h_gap = max(0, TARGET_MARGIN - new_h_margin)
            score -= (q_gap + h_gap) * 3  # Penalize remaining gap
            
            # But penalize OVER-investing (>4 above krav = waste)
            if new_q_margin > 4:
                score -= (new_q_margin - 4) * 2
            if new_h_margin > 4:
                score -= (new_h_margin - 4) * 2
            
            # Bonus for experience (helps with event cards)
            # Parse experience from line
            for line in lines:
                if f"  {idx}." in line:
                    em = re.search(r'Erf:\s*\+?(\d+)', line)
                    if em:
                        score += int(em.group(1)) * 0.5
                    break
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx

    _rb_round = 0  # Tracks which Rb we're spending

    def _rb_spend(self, ctx):
        """Decide how to spend riskbuffertar. Smart: target weakest dimension.
        1=Q, 2=H, 3=T, 0=spara. Keep 2 for genomförande."""
        import re
        m = re.search(r'Rb kvar:\s*(\d+)', ctx)
        rb_left = int(m.group(1)) if m else 1
        if rb_left <= 2:
            return 0  # Spara för genomförande
        
        # Spend on weakest dimension
        q_margin, h_margin = self._parse_qh_margin(ctx)
        
        # T: check if time is critical
        t_match = re.search(r'T:\s*(\d+)\s*mån', ctx)
        t_val = int(t_match.group(1)) if t_match else 10
        
        # If any dimension is below krav, fix it (avoid konsekvenskort!)
        if q_margin < 0:
            return 1  # Q
        if h_margin < 0:
            return 2  # H
        if t_val > 14:
            return 3  # T - time critical
        
        # Otherwise boost weakest towards target margin
        if q_margin <= h_margin:
            return 1  # Q
        return 2  # H

    def _pick_card(self, ctx, min_val, max_val):
        if max_val == 0:
            return 0
        lines = ctx.split("\n")
        best_idx, best_score = 1, 0
        for line in lines:
            m = re.match(r'\s+(\d+)\.\s+.*uppfyller\s+\{(.+)\}', line)
            if m:
                idx = int(m.group(1))
                vals = re.findall(r"'(\w+)':\s*(\d+)", m.group(2))
                score = sum(int(v) for _, v in vals)
                if score > best_score and idx <= max_val:
                    best_score = score
                    best_idx = idx
        return min(best_idx, max_val)

    def _pick_staff(self, ctx, min_val, max_val):
        lines = ctx.split("\n")
        cheapest_idx, cheapest_cost = min_val, 999
        for line in lines:
            m = re.match(r'\s+(\d+)\.\s+\[(\w+)\].*Lön:\s*([\d.,]+)', line)
            if m:
                idx = int(m.group(1))
                cost = float(m.group(3).replace(",", "."))
                if cost < cheapest_cost and idx <= max_val:
                    cheapest_cost = cost
                    cheapest_idx = idx
        return cheapest_idx

    def _pick_upgrade(self, ctx, min_val, max_val):
        self._upgrade_count += 1
        if self._upgrade_count > 2:
            self._upgrade_count = 0
            return 0
        ek = self._parse_ek(ctx)
        lines = ctx.split("\n")
        cheapest_idx, cheapest_cost = 0, 999
        for line in lines[-15:]:
            m = re.match(r'\s+(\d+)\.\s+.*Kostnad:\s*([\d.,]+)', line)
            if m:
                idx = int(m.group(1))
                cost = float(m.group(2).replace(",", "."))
                if idx <= max_val and cost < cheapest_cost:
                    cheapest_cost = cost
                    cheapest_idx = idx
        if cheapest_idx > 0 and cheapest_cost < ek * 0.2:
            return cheapest_idx
        self._upgrade_count = 0
        return 0

    def _pick_sell(self, ctx, min_val, max_val):
        """Välj fastighet att sälja – sälj den med lägst FV (minst värdefull)."""
        lines = ctx.split("\n")
        lowest_fv_idx = min_val
        lowest_fv = float('inf')
        for line in lines[-20:]:
            m = re.match(r'\s+(\d+)\.\s+.*FV:\s*([\d.,]+)', line)
            if m:
                idx = int(m.group(1))
                fv = float(m.group(2).replace(",", "."))
                if min_val <= idx <= max_val and fv < lowest_fv:
                    lowest_fv = fv
                    lowest_fv_idx = idx
        return lowest_fv_idx


# ═══════════════════════════════════════════════════════
#  OUTPUT CAPTURE + PATCHING
# ═══════════════════════════════════════════════════════

class OutputCapture(io.TextIOBase):
    def __init__(self, brain, real_stdout, verbose):
        self.brain = brain
        self.real_stdout = real_stdout
        self.verbose = verbose

    def write(self, text):
        if text.strip():
            self.brain.output_lines.append(text.rstrip())
            if len(self.brain.output_lines) > 300:
                self.brain.output_lines = self.brain.output_lines[-150:]
        if self.verbose:
            return self.real_stdout.write(text)
        return len(text)

    def flush(self):
        if self.verbose:
            self.real_stdout.flush()


_original_input = builtins.input


def patch_game(brain, verbose=True):
    """Monkey-patchar husbyggspelet med AI-beslut."""
    import husbyggspelet as h
    real_stdout = sys.stdout
    sys.stdout = OutputCapture(brain, real_stdout, verbose)

    def ai_int(prompt, mn, mx):
        val = brain.decide_int(prompt, mn, mx)
        if verbose:
            real_stdout.write(f"{prompt}{val}\n")
        return val

    def ai_yn(prompt):
        val = brain.decide_yes_no(prompt)
        if verbose:
            real_stdout.write(f"{prompt}{'ja' if val else 'nej'}\n")
        return val

    def ai_raw(prompt=""):
        p = prompt.lower()
        if "namn" in p and "spelare" in p:
            return brain.name
        if "sökväg" in p or "mappen" in p:
            return brain.data_dir
        return ""

    h.input_int = ai_int
    h.input_yes_no = ai_yn
    h.pause = lambda: None
    builtins.input = ai_raw

    return real_stdout


def unpatch(real_stdout):
    sys.stdout = real_stdout
    builtins.input = _original_input


# ═══════════════════════════════════════════════════════
#  RESULTATEXTRAKTION
# ═══════════════════════════════════════════════════════

def extract_results(game, brain_output):
    import husbyggspelet as h
    results = []
    if not game or not game.players:
        return results

    # Parsa slutliga yields från output
    yield_b = h.YIELD_START_BOSTADER
    yield_k = h.YIELD_START_KOMMERSIELLT
    for line in reversed(brain_output):
        if "Bostäder:" in line and "nu " in line:
            m = re.search(r'nu\s+([\d.,]+)%', line)
            if m:
                yield_b = float(m.group(1).replace(",", "."))
                break
    for line in reversed(brain_output):
        if "Kommersiellt:" in line and "nu " in line:
            m = re.search(r'nu\s+([\d.,]+)%', line)
            if m:
                yield_k = float(m.group(1).replace(",", "."))
                break

    for player in game.players:
        total_fv = 0
        total_bta = 0
        for prop in player.fastigheter:
            y = yield_b if prop.typ in h.BOSTADER_TYPES else yield_k
            ek_class = h.get_prop_ek(prop, player)
            fv = h.calc_fastighetsvarde(prop, y, ek_class)  # Already includes energiklassfaktor
            total_fv += fv
            total_bta += prop.bta

        # ABT-ekonomi (inkl. lånekostnader)
        abt_start = getattr(player, 'abt_start', 0)
        # Use pre-transfer remaining (before ABT→EK transfer zeroes it)
        abt_remaining = getattr(player, 'abt_remaining_before_transfer',
                                getattr(player, 'abt_budget', 0))
        abt_loans_net = getattr(player, 'abt_loans_net', 0)
        abt_borrow_cost = getattr(player, 'abt_borrowing_cost', 0)
        abt_t = abt_start                                         # Tillgänglig (original)
        real_remaining = abt_remaining - abt_loans_net
        abt_k = abt_start - real_remaining + abt_borrow_cost      # Faktisk kostnad inkl avgifter
        tb = abt_t - abt_k                                        # Täckningsbidrag
        tg = (tb / abt_t * 100) if abt_t > 0 else 0              # Täckningsgrad %

        # EK justerat för moderbolagslån
        ek_raw = player.eget_kapital
        loans_gross = abt_loans_net + abt_borrow_cost  # N × 100 Mkr
        ek = ek_raw - loans_gross                       # Verkligt EK efter skulder

        # ── SCORE = (FV×30% + EK + TB) × straffaktor f(n) ──
        # FV×30% = din ägarandel (70% är belånat), redan energiklassjusterat
        # EK     = verkligt eget kapital (negativt slår fullt)
        # TB     = täckningsbidrag (budgetdisciplin)
        # f(n)   = Q/H/T-avvikelse-multiplikator vid Skede 2:s slut (tabell)
        fv_30 = total_fv * (1 - h.LOAN_RATIO)
        score_raw = fv_30 + ek + tb
        n_avvikelse = h.qht_penalty_n(player)
        penalty = h.qht_penalty_factor(n_avvikelse)
        score = score_raw * penalty

        fv_bta = (fv_30 / total_bta * 1000) if total_bta > 0 else 0

        results.append({
            "name": player.name,
            "fv": total_fv,
            "fv_30": fv_30,
            "ek": ek,                    # Verkligt EK (efter lån)
            "ek_raw": ek_raw,            # EK före lånejustering
            "loans_gross": loans_gross,  # Totala moderbolagslån
            "bta": total_bta,
            "fv_bta_tkr": fv_bta,
            "score_raw": score_raw,
            "score": score,
            "qht_avvikelse": n_avvikelse,
            "penalty_factor": penalty,
            "n_fast": len(player.fastigheter),
            "n_proj": len(player.projects),
            "proj_bta": player.total_bta,
            "abt_t": abt_t,
            "abt_k": abt_k,
            "tb": tb,
            "tg": tg,
            "borrow_cost": abt_borrow_cost,
            "plan_q": getattr(player, 'snap_plan_q', 0),
            "plan_h": getattr(player, 'snap_plan_h', 0),
            "plan_t": getattr(player, 'snap_plan_t', 0),
            "plan_qk": getattr(player, 'q_krav', 0),
            "plan_hk": getattr(player, 'h_krav', 0),
            "exec_q": getattr(player, 'snap_exec_q', 0),
            "exec_h": getattr(player, 'snap_exec_h', 0),
            "exec_t": getattr(player, 'snap_exec_t', 0),
        })
    return results


# ═══════════════════════════════════════════════════════
#  KÖR ETT SPEL
# ═══════════════════════════════════════════════════════

def run_game(data_dir, brain=None, verbose=True):
    """Kör en omgång. Returnerar resultat-lista."""
    import importlib

    # VIKTIGT: Rensa cached modul helt innan reload
    if "husbyggspelet" in sys.modules:
        del sys.modules["husbyggspelet"]
    import husbyggspelet as h

    if brain is None:
        brain = AIBrain(name="AI-Optimal", data_dir=data_dir)
    else:
        brain.data_dir = data_dir
        brain.reset()

    real_stdout = patch_game(brain, verbose)

    try:
        game = h.main()
        return extract_results(game, brain.output_lines)
    except Exception as e:
        real_stdout.write(f"\n⚠ {e}\n")
        import traceback
        traceback.print_exc(file=real_stdout)
        return [{"name": brain.name, "error": str(e)}]
    finally:
        unpatch(real_stdout)


# ═══════════════════════════════════════════════════════
#  FIND DATA DIR
# ═══════════════════════════════════════════════════════

def find_data_dir():
    candidates = [
        os.environ.get("HUSBYGG_DATA", ""),
        os.path.dirname(os.path.abspath(__file__)),  # Script's own folder first
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata"),
        os.path.join(os.path.expanduser("~"), "OneDrive",
                     "Husbyggspelet", "Speldata"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            tf = os.path.join(c, "1. Projektutveckling", "PU_projekt.csv")
            if os.path.isfile(tf):
                return c
    return candidates[1]


if __name__ == "__main__":
    verbose = "--silent" not in sys.argv
    data_dir = find_data_dir()
    print(f"🤖 AI: Optimal | 📂 {data_dir}\n{'=' * 60}\n")
    results = run_game(data_dir, verbose=verbose)
    print(f"\n{'=' * 60}\n🤖 RESULTAT:")
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['error']}")
        else:
            print(f"  {r['name']}: Score={r['score']:.1f} "
                  f"FV30={r['fv_30']:.0f} EK={r['ek']:.0f} TB={r['tb']:+.0f} "
                  f"Fast={r['n_fast']} BTA={r['bta']}")

