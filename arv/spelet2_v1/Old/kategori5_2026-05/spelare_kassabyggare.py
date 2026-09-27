#!/usr/bin/env python3
"""
AI-spelare: Kassabyggare

Maximerar EK (eget kapital) framför allt:
  - Tar projekt (gratis) men minimerar alla utgifter
  - Nivå 1 leverantörer (absolut billigast)
  - Siktar på Negativt i genomförande (kräver inga kort/insats)
  - Köper ALDRIG företagskultur
  - Köper ALDRIG fastigheter
  - ALDRIG energiuppgraderingar
  - ALDRIG expansion (kostar 5 Mkr)
  - ALDRIG extra personal
  - Accepterar alla straff – sparar varje krona
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spelare_optimal import AIBrain, run_game, find_data_dir


class AIKassabyggare(AIBrain):

    # Kassabyggare: absolut minimum, bara billigaste
    SUPPORT_MAX_TOTAL = 5
    SUPPORT_EARLY_PHASES = 2   # Bara fas 1-2 (2 Mkr/st)
    SUPPORT_ABT_FLOOR = 50     # Väldigt hög reserv
    TG_TARGET = 22             # Snål – undviker negativt

    def __init__(self, data_dir=""):
        super().__init__(name="AI-Kassabyggare", data_dir=data_dir)

    def decide_yes_no(self, prompt):
        self.decision_count += 1
        ctx = self.ctx()
        p = prompt.lower()

        # Riskbuffert: ja (gratis att använda, undviker kostnader)
        if "riskbuffert" in p:
            return True

        # Ta gratis-erbjudanden
        if "ta ett projekt" in p:
            return True

        # Företagskultur: köp minimalt
        if "köp mer företagskultur" in p and "försök igen" in p:
            return self._should_retry_buy(ctx)
        if "köp företagskultur" in p:
            return self._should_buy_support(prompt, ctx)

        # Tvångsförsäljning vid negativt EK
        if "sälja en fastighet" in p:
            if self._parse_ek(ctx) < 0:
                return True
            return False

        # Allt annat som kostar pengar: NEJ
        if any(k in p for k in [
            "markanvisning", "markexpansion",
            "energiuppgraderingar",
            "köpa en fastighet",
            "anställ ytterligare",
            "byta ett projekt", "byta en leverantör",
        ]):
            return False

        if "spela igen" in p:
            return False

        return True

    def decide_int(self, prompt, min_val, max_val):
        self.decision_count += 1
        repeats = self._track_repeats(prompt)
        ctx = self.ctx()
        p = prompt.lower()

        if "välj projekt" in p:
            return 1 if min_val <= 1 else min_val

        # Multi-typ: passa
        if "val (1-2, 0 = passa)" in p:
            return 0

        # Stadshuset: ta projekt (gratis)
        if "val: " in p and max_val == 3:
            if "riskbuffert" in ctx.lower():
                return 0  # Spara alla Rb
            return 1

        # Leverantör: nivå 1 (absolut billigast)
        if "välj leverantör" in p or "välj organisation" in p:
            return self._pick_cheapest(ctx, min_val, max_val, repeats)

        # Faskort: Negativt (nivå 1) – kräver ingen insats
        if "välj nivå" in p:
            # Kassabyggare: alltid lägsta nivå (spara pengar)
            return min_val

        # Kort: spela om tvunget
        if "spela kort" in p:
            return self._pick_card(ctx, min_val, max_val)

        # Personal: billigaste
        if "anställ" in p:
            return self._pick_staff(ctx, min_val, max_val)

        # Uppgradera/sälj: aldrig
        if "uppgradera" in p:
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

    def _pick_cheapest(self, ctx, min_val, max_val, repeats):
        """Nivå 1. Fallback 2."""
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
        for target in [1, 2, 3, 4]:
            for idx, niva in valid:
                if niva == target:
                    return idx
        if repeats > 0:
            return valid[repeats % len(valid)][0]
        return valid[0][0]


if __name__ == "__main__":
    verbose = "--silent" not in sys.argv
    data_dir = find_data_dir()
    brain = AIKassabyggare(data_dir=data_dir)
    print(f"🤖 AI: Kassabyggare | 📂 {data_dir}\n{'=' * 60}\n")
    results = run_game(data_dir, brain=brain, verbose=verbose)
    print(f"\n{'=' * 60}\n🤖 RESULTAT:")
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['error']}")
        else:
            print(f"  {r['name']}: Score={r['score']:.1f} "
                  f"FV={r['fv_30']:.1f} EK={r['ek']:.1f}")

