/**
 * PMOPOLY - Instruction texts for the tutorial system.
 * Three levels: "all" (rules + strategy), "rules" (rules only), "none" (off).
 */

export const INSTRUCTIONS = {

    phase1_mark_tomt: {
        title: "Fas 1: Välj projekttyp",
        rules:
            "Välkommen till PMOPOLY! Du är en projektutvecklare som ska bygga bostäder och lokaler.\n\n" +
            "I den här första delen väljer varje spelare vilken typ av projekt de vill satsa på: " +
            "BRF, Hyresrätt, Förskola, Lokal eller Kontor. Varje typ har olika kostnader, intäkter och krav.\n\n" +
            "Ditt mål under hela Fas 1 är att samla så bra projekt som möjligt — " +
            "de avgör din ekonomi genom resten av spelet.",
        strategy:
            "Titta på förhållandet mellan anskaffningsvärde (intäkt) och kostnad. " +
            "Projekt med lågt nämndkrav (≥-värdet) är säkrare att få igenom senare. " +
            "Blanda gärna projekttyper för att sprida risk.",
    },

    phase1_board: {
        title: "Fas 1: Brädspelet",
        rules:
            "Nu börjar brädspelet! Slå en D6 och flytta runt brädet. Du spelar 2 varv.\n\n" +
            "Ruttyper:\n" +
            "• Projekt — Ta ett nytt projekt från högen\n" +
            "• Dialog/Politik — Dra ett kort och slå D20 för utfall\n" +
            "• Stjärna — Få +1 riskbuffert\n" +
            "• Stadshuset — Ta nytt projekt, lämna tillbaka, eller skippa\n" +
            "• Länsstyrelsen — Sänker ditt hållbarhetskrav med 2\n" +
            "• Skönhetsrådet — Sänker ditt kvalitetskrav med 2\n" +
            "• Stadsbyggnadskontoret (start) — Utöka din tomtmark",
        strategy:
            "Samla riskbuffertar tidigt — de skyddar mot dåliga kortutfall och kan sänka krav senare. " +
            "Varje gång du passerar start får du 3–5 extra markrutor, " +
            "vilket ger plats för fler projekt.",
    },

    first_card: {
        title: "Kort: Dialog & Politik",
        rules:
            "Du har dragit ett kort! Kortet visar 5 möjliga utfall baserat på ett D20-slag:\n\n" +
            "• D20 = 1: Värsta utfallet (ofta förlora projekt)\n" +
            "• D20 = 2–10: Dåligt (ökade krav)\n" +
            "• D20 = 11–15: Neutralt/litet positivt\n" +
            "• D20 = 16–19: Bra (ta projekt, byt, sänk krav)\n" +
            "• D20 = 20: Bäst (bonusprojekt, markanvisning)\n\n" +
            "Om du slår ≤10 och har riskbuffertar kan du slå om!",
        strategy:
            "Riskbuffertar är värdefulla här — spara dem för att undvika de riktigt dåliga utfallen. " +
            "Dialogkort har oftast positiva effekter på höga slag, medan Politikkort " +
            "tenderar att öka dina krav.",
    },

    phase1_namndbeslut: {
        title: "Fas 1: Nämndbeslut",
        rules:
            "Varje projekt måste godkännas av nämnden! Du slår D20 för varje projekt.\n\n" +
            "• Resultatet måste vara ≥ projektets nämndkrav (visas som \"Nämnd: ≥X\")\n" +
            "• Godkänt = projektet behålls\n" +
            "• Underkänt = du kan använda en riskbuffert för att slå om\n" +
            "• Misslyckas omslaget också = projektet lämnas tillbaka\n\n" +
            "Du kan också investera riskbuffertar i att sänka kvalitets- eller hållbarhetskrav.",
        strategy:
            "Projekt med högt nämndkrav (≥15+) är riskfyllda. " +
            "Spara riskbuffertar till de viktigaste projekten. " +
            "Investera gärna överskottsbuffertar i att sänka K- och H-krav — det betalar sig i Fas 2.",
    },

    phase1_ekonomi: {
        title: "Fas 1: Ekonomi",
        rules:
            "Nu räknas ekonomin ihop automatiskt.\n\n" +
            "• Intäkter = summan av alla projekts anskaffningsvärden\n" +
            "• Kostnader = mark (15 Mkr) + expansioner + projektkostnader\n" +
            "• ABT (budget) = Intäkter − Kostnader\n\n" +
            "Om kostnaderna överstiger intäkterna behöver du ta moderbolagslån. " +
            "Varje lån på 100 Mkr ger 95 Mkr netto (5 Mkr i avgift).",
        strategy:
            "ABT är din budget för Fas 2 och 3 — allt du köper (leverantörer, organisation, extern support) " +
            "dras härifrån. Ju mer ABT du har, desto mer flexibilitet. " +
            "Undvik lån om möjligt — avgiften äter av din vinst.",
    },

    phase2_planering: {
        title: "Fas 2: Planering",
        rules:
            "Dags att planera ditt bygge! Du går igenom 13 steg i ordning.\n\n" +
            "Vid varje steg väljer du antingen en leverantör eller en organisationsresurs:\n" +
            "• Leverantörer påverkar Kvalitet (Q), Hållbarhet (H), Tid (T) och kostar pengar från ABT\n" +
            "• Organisation påverkar kompetens och projektledning\n\n" +
            "Du måste nå dina Q-krav och H-krav! Tid måste vara minst 8 månader.\n" +
            "Händelsekort kan dyka upp och ändra förutsättningarna.",
        strategy:
            "Planera bakifrån: kolla vilka Q- och H-krav du behöver uppfylla, " +
            "och välj leverantörer som ger rätt poäng till lägst kostnad. " +
            "Billigare leverantörer ger ofta lägre Q/H men sparar ABT till Fas 3.",
    },

    puzzle_placement: {
        title: "Kvartersplanering",
        rules:
            "Placera dina projektpolyominos på ditt kvarter!\n\n" +
            "Du har ett 4\u00d74 basrutnät. Varje markexpansion ger 5 extra celler runtom.\n\n" +
            "Dra projekt från inventariet till rutnätet. " +
            "Tryck R för att rotera, F för att spegelvända.\n" +
            "Bara placerade projekt genererar intäkter i Fas 3 och 4.\n\n" +
            "Alla spelare placerar samtidigt. Klicka 'Klar' när du är nöjd.",
        strategy:
            "Placera de mest lönsamma projekten först. " +
            "Använd expansionsceller strategiskt för att få plats med fler projekt.",
    },

    phase3_genomforande: {
        title: "Fas 3: Genomförande",
        rules:
            "Bygget pågår! 8 faskort spelas i ordning — varje kort representerar en byggfas.\n\n" +
            "Vid varje fas kan du köpa extern support för att minska risk. " +
            "Kostnaden ökar för varje fas (2–7 Mkr).\n\n" +
            "Faskorten kan ge positiva eller negativa effekter beroende på dina val " +
            "och hur väl du planerat.",
        strategy:
            "Extern support är dyr men kan rädda dig från katastrofala utfall i senare faser. " +
            "Spara ABT till fas 5–8 där riskerna och kostnaderna är störst.",
    },

    phase4_forvaltning: {
        title: "Fas 4: Förvaltning",
        rules:
            "Ditt bygge är klart! Nu förvaltar du dina fastigheter under 4 kvartal.\n\n" +
            "• Anställ personal — du behöver minst en förvaltare (FC)\n" +
            "• Personalens kapacitet måste täcka antal fastigheter\n" +
            "• Varje kvartal: samla driftnetto, betala löner, hantera händelser\n" +
            "• Nya fastigheter dyker upp på marknaden (3, 2, 1, 0 per kvartal)\n\n" +
            "Slutpoäng = Fastighetsvärde × 30% + Eget kapital + Totalbalans",
        strategy:
            "Anställ rätt personal tidigt — underbemanning ger sämre förvaltning. " +
            "Energiklass påverkar värdering (A = +10%, F = -15%). " +
            "Köp undervärderade fastigheter om du har kapital.",
    },
};
