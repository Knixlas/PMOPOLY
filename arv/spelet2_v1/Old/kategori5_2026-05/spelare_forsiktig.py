#!/usr/bin/env python3
"""
AI-spelare: Försiktig

Konservativ strategi som skyddar EK:
  - Tar projekt men skippar multi-typ-rutor (passar)
  - Väljer billiga leverantörer (nivå 2)
  - Siktar på Neutralt i genomförande
  - Köper ALDRIG företagskultur
  - Köper ALDRIG fastigheter i förvaltning
  - Gör ALDRIG energiuppgraderingar
  - Skippar markexpansioner (kostar 5 Mkr)
  - Använder riskbuffertar (undviker negativa utfall)
  - Anställer bara minimum personal
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spelare_optimal import AIBrain, run_game, find_data_dir


class AIForsiktig(AIBrain):
    """Försiktig spelare som minimerar utgifter och skyddar EK."""

    # Försiktig: köper ~10 tidiga billiga kort som försäkring
    SUPPORT_MAX_TOTAL = 8
    SUPPORT_EARLY_PHASES = 3   # Bara fas 1-3 (allra billigast)
    SUPPORT_ABT_FLOOR = 40     # Hög reserv – vill inte riskera
    TG_TARGET = 25             # Extra försiktig – god marginal

    def __init__(self, data_dir=""):
        super().__init__(name="AI-Försiktig", data_dir=data_dir)

    def _rb_spend(self, ctx):
        """Försiktig: spend ALL Rb on Q/H, never save."""
        self._rb_round += 1
        return 1 if self._rb_round % 2 == 1 else 2

    # ── Ja/Nej ──

    def decide_yes_no(self, prompt):
        self.decision_count += 1
        ctx = self.ctx()
        p = prompt.lower()

        # Riskbuffert: alltid ja (undvik negativa utfall)
        if "riskbuffert" in p:
            return True

        # Företagskultur: smart – köp lagom
        if "köp mer företagskultur" in p and "försök igen" in p:
            return self._should_retry_buy(ctx)
        if "köp företagskultur" in p:
            return self._should_buy_support(prompt, ctx)

        # Tvångsförsäljning vid negativt EK
        if "sälja en fastighet" in p:
            if self._parse_ek(ctx) < 0:
                return True
            return False

        # Köpa: aldrig (spara)
        if "köpa en fastighet" in p:
            return False

        # Alltid nej – spara pengar
        if any(k in p for k in [
            "markanvisning", "markexpansion",
            "energiuppgraderingar",
            "byta ett projekt",
            "byta en leverantör",
            "spela igen",
        ]):
            return False

        # Ta projekt från valfri hög: ja (gratis)
        if "ta ett projekt från valfri hög" in p:
            return True

        # Anställ ytterligare: nej (minimum personal)
        if "anställ ytterligare" in p:
            return False

        return True

    # ── Heltal ──

    def decide_int(self, prompt, min_val, max_val):
        self.decision_count += 1
        repeats = self._track_repeats(prompt)
        ctx = self.ctx()
        p = prompt.lower()

        # Projektval: ta alltid (gratis)
        if "välj projekt" in p:
            return 1 if min_val <= 1 else min_val

        # Multi-typ-rutor: passa (0) – tar inga risker
        if "val (1-2, 0 = passa)" in p:
            return 0

        # Stadshuset: ta projekt (gratis)
        if "val: " in p and max_val == 3:
            if "riskbuffert" in ctx.lower():
                return self._rb_spend(ctx)
            return 1

        # Leverantör/org: välj nivå 2 (billig men ok)
        if "välj leverantör" in p or "välj organisation" in p:
            return self._pick_cheap(ctx, min_val, max_val, repeats)

        # Faskort: Billigast möjligt, bara nivå 2 om mycket god TG
        if "välj nivå" in p:
            # Försiktig: strategiskt val men aldrig högre än Neutralt
            choice = self._choose_faskort_level(ctx, min_val, max_val)
            return min(choice, 2) if max_val >= 2 else min_val

        # Kompetenskort: spela bästa
        if "spela kort" in p:
            return self._pick_card(ctx, min_val, max_val)

        # Personal: billigaste
        if "anställ" in p:
            return self._pick_staff(ctx, min_val, max_val)

        # Uppgradera: aldrig
        if "uppgradera" in p:
            return 0

        # Sälj: aldrig
        if "sälj" in p:
            return 0

        # Köp fastighet: aldrig (men om tvingad, välj 1)
        if "välj" in p and min_val >= 1:
            return 1

        if "antal spelare" in p:
            return 1
        if "lämnar du tillbaka" in p or "byta" in p:
            return 0 if min_val == 0 else 1

        return max(min_val, (min_val + max_val) // 2)

    def _pick_cheap(self, ctx, min_val, max_val, repeats):
        """Välj nivå 2 (billig). Fallback till 1 om 2 blockerad."""
        import re
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

        # Föredra nivå 2, sedan 1, sedan 3
        for target in [2, 1, 3, 4]:
            for idx, niva in valid:
                if niva == target:
                    return idx

        if repeats > 0:
            return valid[repeats % len(valid)][0]
        return valid[0][0]


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    verbose = "--silent" not in sys.argv
    data_dir = find_data_dir()
    brain = AIForsiktig(data_dir=data_dir)
    print(f"🤖 AI: Försiktig | 📂 {data_dir}\n{'=' * 60}\n")
    results = run_game(data_dir, brain=brain, verbose=verbose)
    print(f"\n{'=' * 60}\n🤖 RESULTAT:")
    for r in results:
        if "error" in r:
            print(f"  ⚠ {r['error']}")
        else:
            print(f"  {r['name']}: Score={r['score']:.1f} "
                  f"FV={r['fv_30']:.1f} EK={r['ek']:.1f} "
                  f"Fast={r['n_fast']} BTA={r['bta']}")

