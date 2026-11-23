#!/usr/bin/env python3
"""
AI-spelare: Aggressiv

Maxar allt:
  - Tar alla projekt, expanderar alltid
  - Nivå 4 leverantörer (dyrast, bäst)
  - Siktar på Positivt/Bonus i genomförande
  - Köper alltid företagskultur
  - Köper fastigheter aggressivt i förvaltning
  - Energiuppgraderar allt
  - Använder riskbuffertar
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spelare_optimal import AIBrain, run_game, find_data_dir


class AIAggressiv(AIBrain):

    # Aggressiv: skippar tidigt, panikköper sent (dyrt!)
    SUPPORT_MAX_TOTAL = 10
    SUPPORT_EARLY_PHASES = 0   # Köper INGA tidigt
    SUPPORT_ABT_FLOOR = 20
    TG_TARGET = 20             # Pushar men respekterar gräns

    def __init__(self, data_dir=""):
        super().__init__(name="AI-Aggressiv", data_dir=data_dir)

    def _should_buy_support(self, prompt, ctx):
        """Aggressiv: skippar fas 1-4, panikköper fas 5-8."""
        abt = self._parse_abt(ctx)
        fas_nr = self._parse_fas_nr(ctx)

        if self._total_support_bought >= self.SUPPORT_MAX_TOTAL:
            return False
        if abt < self.SUPPORT_ABT_FLOOR:
            return False
        if not self._tg_ok_for_spending(ctx, planned_cost=fas_nr + 1):
            return False

        # Fas 1-4: skip (tror vi klarar det)
        if fas_nr <= 4:
            return False

        # Fas 5+: panikköp!
        self._total_support_bought += 1
        return True

    def _rb_spend(self, ctx):
        """Aggressiv: spend ALL Rb, cycle Q/H/T."""
        self._rb_round += 1
        r = self._rb_round % 3
        return 1 if r == 1 else 2 if r == 2 else 3

    def decide_yes_no(self, prompt):
        self.decision_count += 1
        ctx = self.ctx()
        p = prompt.lower()

        # Alltid nej
        if "spela igen" in p:
            return False
        if "byta ett projekt" in p or "byta en leverantör" in p:
            return False
        if "sälja en fastighet" in p:
            if self._parse_ek(ctx) < 0:
                return True  # Tvångsförsäljning
            return False

        # Alltid ja – fullt ös
        if "riskbuffert" in p:
            return True
        if any(k in p for k in ["markanvisning", "markexpansion"]):
            return True
        if "ta ett projekt" in p:
            return True
        if "köp mer företagskultur" in p and "försök igen" in p:
            return self._should_retry_buy(self.ctx())
        if "köp företagskultur" in p:
            return self._should_buy_support(prompt, self.ctx())
        if "energiuppgraderingar" in p:
            return True  # Alltid uppgradera
        if "köpa en fastighet" in p:
            return self._parse_ek(ctx) > 0  # Köp om EK > 0
        if "anställ ytterligare" in p:
            return True  # Mer personal

        return True

    def decide_int(self, prompt, min_val, max_val):
        self.decision_count += 1
        repeats = self._track_repeats(prompt)
        ctx = self.ctx()
        p = prompt.lower()

        if "välj projekt" in p:
            return 1 if min_val <= 1 else min_val
        if "val (1-2, 0 = passa)" in p:
            return 1  # Ta alltid
        if "val: " in p and max_val == 3:
            if "riskbuffert" in ctx.lower():
                return self._rb_spend(ctx)
            return 1  # Stadshuset → ta projekt

        # Leverantör: nivå 4 (bäst), men backa vid TG-tryck
        if "välj leverantör" in p or "välj organisation" in p:
            tg = self._parse_tg(ctx)
            if tg <= self.TG_TARGET + 3:
                return self._pick_with_rotation(ctx, min_val, max_val, repeats)
            return self._pick_best(ctx, min_val, max_val, repeats)

        # Faskort: strategiskt nivåval (aggressiv siktar högt)
        if "välj nivå" in p:
            choice = self._choose_faskort_level(ctx, min_val, max_val)
            # Aggressiv: bump up one level if possible
            return min(choice + 1, max_val) if choice < max_val else choice

        if "spela kort" in p:
            return self._pick_card(ctx, min_val, max_val)
        if "anställ" in p:
            return self._pick_staff(ctx, min_val, max_val)

        # Energi: uppgradera allt (max 3 per omgång)
        if "uppgradera" in p:
            self._upgrade_count += 1
            if self._upgrade_count > 3:
                self._upgrade_count = 0
                return 0
            return min(1, max_val) if max_val >= 1 else 0

        if "sälj" in p:
            return 0
        if "välj" in p and min_val >= 1:
            return 1
        if "antal spelare" in p:
            return 1
        if "lämnar du tillbaka" in p or "byta" in p:
            return 0 if min_val == 0 else 1

        return max(min_val, (min_val + max_val) // 2)

    def _pick_best(self, ctx, min_val, max_val, repeats):
        """Välj nivå 4. Fallback 3, 2, 1."""
        lines = ctx.split("\n")
        valid = []
        for line in lines:
            m = re.match(r'\s+(\d+)\.\s+Nivå\s+(\d+):', line)
            if m and "⛔" not in line:
                idx = int(m.group(1))
                niva = int(m.group(2))
                if min_val <= idx <= max_val:
                    valid.append((idx, niva))
        if not valid:
            choice = min_val + (repeats % (max_val - min_val + 1))
            return min(max(choice, min_val), max_val)
        for target in [4, 3, 2, 1]:
            for idx, niva in valid:
                if niva == target:
                    return idx
        if repeats > 0:
            return valid[repeats % len(valid)][0]
        return valid[-1][0]


if __name__ == "__main__":
    verbose = "--silent" not in sys.argv
    data_dir = find_data_dir()
    brain = AIAggressiv(data_dir=data_dir)
    print(f"🤖 AI: Aggressiv | 📂 {data_dir}\n{'=' * 60}\n")
    results = run_game(data_dir, brain=brain, verbose=verbose)
    print(f"\n{'=' * 60}\n🤖 RESULTAT:")
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['error']}")
        else:
            print(f"  {r['name']}: Score={r['score']:.1f} "
                  f"FV={r['fv_30']:.1f} EK={r['ek']:.1f}")

