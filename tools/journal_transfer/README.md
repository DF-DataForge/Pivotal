# Dagboek overzetten tussen twee Odoo 19-databases

Het script `transfer_journal.py` kopieert de diverse boekingen van één dagboek (bv. het
afsluitdagboek **AFSL**) van een brondatabase naar een doeldatabase via XML-RPC.
Je hebt enkel Python 3.10 of hoger nodig, zonder extra pakketten.

## Voorbereiding

1. Kopieer `transfer.example.ini` naar `transfer.ini` en vul URL, database en gebruiker
   van bron en doel in.
2. Maak in de **doeldatabase** het dagboek aan (zelfde code, bv. `AFSL`, type *Diversen*),
   of geef een andere code mee met `--target-journal`.
3. Controleer de **afsluitdatums** in de doeldatabase (Boekhouding > Configuratie >
   Instellingen > Afsluitdatums). Als 2024 en/of 2025 vergrendeld zijn, stopt het script
   met een melding.

## Gebruik

Eerst een proefrun. Die schrijft niets weg en toont welke boekingen aangemaakt zouden worden
en welke rekeningen of partners ontbreken:

```bash
python3 transfer_journal.py --journal AFSL --date-from 2024-12-31 --date-to 2025-12-31
```

Is alles in orde, dan maak je de boekingen aan als **concept**, zodat je ze in Odoo nog
kunt nakijken:

```bash
python3 transfer_journal.py --journal AFSL --date-from 2024-12-31 --date-to 2025-12-31 --apply
```

Of je maakt ze aan en boekt ze meteen met `--post`.

### Nuttige opties

| Optie | Betekenis |
|---|---|
| `--date 2024-12-31 --date 2025-12-31` | Enkel op deze datums (in plaats van een bereik) |
| `--move AFSL/2024/12/0001` | Enkel deze boeking(en), mag herhaald worden |
| `--target-journal CODE` | Andere dagboekcode in de doeldatabase |
| `--drop-missing-partners` | Partners die niet gevonden worden weglaten in plaats van te stoppen |
| `--no-partners` / `--no-analytic` | Partners of analytiek helemaal niet overzetten |
| `--account-map rekeningen.csv` | Afwijkende rekeningnummers, CSV met `bron;doel` per regel |
| `--include-draft` | Ook conceptboekingen uit de bron meenemen |
| `--source-company` / `--target-company` | Bedrijf kiezen bij meerdere bedrijven |

## Wat wordt overgezet

- Per boeking: datum, lijnen (rekening, omschrijving, debet, credit, vervaldatum,
  vreemde munt), partner en analytische verdeling.
- **Rekeningen** worden gezocht op rekeningnummer, **partners** op btw-nummer, dan
  referentie en tenslotte exacte naam.
- De doeldatabase geeft een eigen nummer (AFSL/...). De **referentie** van de nieuwe boeking
  bevat het oorspronkelijke nummer, bv. `AFSL/2024/12/0001`, en de interne notitie vermeldt
  de brondatabase.
- Het script controleert of elke boeking in evenwicht is.
- Opnieuw draaien is veilig. Boekingen met dezelfde referentie, datum en hetzelfde dagboek
  in de doeldatabase worden overgeslagen.

## Wat níet wordt overgezet

- **Afpuntingen** (matching #): lijnen op 440000 en 444000 komen open in de doeldatabase
  terecht en moeten daar desgewenst opnieuw afgepunt worden.
- **Btw-codes** op lijnen. De bedragen gaan wel mee, maar zonder btw-roosters.
  Bij afsluitingsboekingen is dat normaal niet relevant. Het script waarschuwt als het
  toch voorkomt.
- Facturen en creditnota's (andere boekingstypes) worden overgeslagen.

Tip: test eerst op een kopie (staging/duplicaat) van de doeldatabase.
