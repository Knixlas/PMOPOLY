# Stödbilder för manuella moment

Bilder som visas i player-vyn under "manuella" steg (sätt upp bräde,
placera projekt, etc.) — efter att prompt-modalen stängts.

## Filnamn-konvention

Filnamnen i `data/companion_texts.json` (fältet `image`) mappas direkt
till PNG-filer i denna mapp. Inga prefix, ingen sökväg — bara filnamn.

## Lista över bilder som referensras

Steg → filnamn (skapa dem i denna ordning för att täcka manuella moment):

| Steg-ID | Filnamn | Vad bilden visar |
|---|---|---|
| `setup_skede1` | `Spelbrade_Skede1_Setup_Klart.png` | PU-bräde med tärningar, T=12, Q=H=6 |
| `placement` | `Spelbrade_Skede1_Placering_Exempel.png` | Exempel på giltig pussellösning på 4×4-grid |
| `transition_skede2` | `Spelbrade_Skede2_1_Setup.png` | Skede 2-bräde uppdukat, planeringsplattor |
| `transition_skede3` | `Spelbrade_Skede2_2_Setup.png` | Genomförande-bräde, byggfaser uppmärkta |
| `f4_forbered` | `Spelbrade_Skede3_Setup.png` | Förvaltnings-bräde med kvartalspositioner |

## Var ligger originalen?

Niklas har originalen på `OneDrive\SPELET 2\Bilder\Spelbräde\`.
Sync till denna mapp via `sync_csv.sh` (eller manuellt copy).

## Saknad bild

Om en PNG saknas visar appen en placeholder-ruta med filnamnet — så
det är uppenbart vilken som ska skapas. Ingen krasch.
