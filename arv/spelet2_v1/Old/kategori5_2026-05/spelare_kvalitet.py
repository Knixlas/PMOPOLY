#!/usr/bin/env python3
"""
AI-spelare: Kvalitet

Få projekt, hög kvalitet:
  - Tar projekt från enkelrutor, passar multi-typ
  - Nivå 4 leverantörer (bäst kvalitet → mindre garanti-straff)
  - Siktar på Positivt i genomförande
  - Köper företagskultur om ABT > 20
  - Köper fastigheter bara om EK > 80 (selektivt)
  - Energiuppgraderar alltid (höjer FV/BTA)
  - Skippar expansion (mindre tomt = färre projekt = fokus)
  - Minimal personal
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spelare_optimal import AIBrain, run_game, find_data_dir


class AIKvalitet(AIBrain):

    # Kvalitet: investerar mer i kompetens, köper genom hela spelet
    SUPPORT_MAX_TOTAL = 12
    SUPPORT_EARLY_PHASES = 4   # Köper genom tidiga faser
    SUPPORT_ABT_FLOOR = 25
    TG_TARGET = 22             # Investerar men skyddar marginal

    def __init__(self, data_dir=""):
        super().__init__(name="AI-Kvalitet", data_dir=data_dir)

    def _rb_spend(self, ctx):
        """Kvalitet: all Rb on Q (quality obsessed)."""
        return 1

    def decide_yes_no(self, prompt):
        self.decision_count += 1
        ctx = self.ctx()
        p = prompt.lower()

        if "riskbuffert" in p:
            return True
        if "ta ett projekt" in p:
            return True
        if "spela igen" in p:
            return False
        if "byta ett projekt" in p or "byta en leverantör" in p:
            return False
        if "sälja en fastighet" in p:
            if self._parse_ek(ctx) < 0:
                return True  # Tvångsförsäljning
            return False

        # Skippa expansion – håll tomten liten
        if "markanvisning" in p or "markexpansion" in p:
            return False

        # Företagskultur: smart inköp
        if "köp mer företagskultur" in p and "försök igen" in p:
            return self._should_retry_buy(ctx)
        if "köp företagskultur" in p:
            return self._should_buy_support(prompt, ctx)

        # Energi: alltid (höjer FV-multiplikatorn)
        if "energiuppgraderingar" in p:
            self._upgrade_count = 0
            return True

        # Köpa fastighet: bara om EK > 80
        if "köpa en fastighet" in p:
            return self._parse_ek(ctx) > 80

        # Anställ ytterligare: nej
        if "anställ ytterligare" in p:
            return False

        return True

    def decide_int(self, prompt, min_val, max_val):
        self.decision_count += 1
        repeats = self._track_repeats(prompt)
        ctx = self.ctx()
        p = prompt.lower()

        if "välj projekt" in p:
            return 1 if min_val <= 1 else min_val

        # Multi-typ: passa (fokusera på färre projekt)
        if "val (1-2, 0 = passa)" in p:
            return 0

        if "val: " in p and max_val == 3:
            if "riskbuffert" in ctx.lower():
                return self._rb_spend(ctx)
            return 1

        # Leverantör: nivå 4, men backa vid TG-tryck
        if "välj leverantör" in p or "välj organisation" in p:
            tg = self._parse_tg(ctx)
            if tg <= self.TG_TARGET + 3:
                return self._pick_with_rotation(ctx, min_val, max_val, repeats)
            return self._pick_top(ctx, min_val, max_val, repeats)

        # Faskort: Positivt, men backa vid TG-tryck
        if "välj nivå" in p:
            # Kvalitet: siktar högt, använder strategisk bedömning
            choice = self._choose_faskort_level(ctx, min_val, max_val)
            # Kvalitet: försöker alltid minst Neutralt
            return max(choice, min(2, max_val))

        if "spela kort" in p:
            return self._pick_card(ctx, min_val, max_val)
        if "anställ" in p:
            return self._pick_staff(ctx, min_val, max_val)

        # Energi: uppgradera allt
        if "uppgradera" in p:
            self._upgrade_count += 1
            if self._upgrade_count > 4:
                self._upgrade_count = 0
                return 0
            ek = self._parse_ek(ctx)
            if ek > 5 and max_val >= 1:
                return 1
            self._upgrade_count = 0
            return 0

        if "sälj" in p:
            return 0
        if "välj" in p and min_val >= 1:
            return 1
        if "antal spelare" in p:
            return 1
        if "lämnar du tillbaka" in p or "byta" in p:
            return 0 if min_val == 0 else 1

        return max(min_val, (min_val + max_val) // 2)

    def _pick_top(self, ctx, min_val, max_val, repeats):
        """Nivå 4, fallback 3."""
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
    brain = AIKvalitet(data_dir=data_dir)
    print(f"🤖 AI: Kvalitet | 📂 {data_dir}\n{'=' * 60}\n")
    results = run_game(data_dir, brain=brain, verbose=verbose)
    print(f"\n{'=' * 60}\n🤖 RESULTAT:")
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['error']}")
        else:
            print(f"  {r['name']}: Score={r['score']:.1f} "
                  f"FV={r['fv_30']:.1f} EK={r['ek']:.1f}")

