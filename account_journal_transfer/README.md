# Dagboek overzetten (Odoo 19)

Wizard om de diverse boekingen van één dagboek, bv. het afsluitdagboek **AFSL**, uit een
andere Odoo-database op te halen en in de huidige database aan te maken. De andere database
wordt alleen gelezen, via XML-RPC.

## Installeren

1. Zorg dat de branch met deze module op de server staat (bv. Cloudpepper: branch `staging`).
2. Ga naar *Apps*, kies *App-lijst bijwerken* en installeer **Dagboek overzetten**.
3. Je vindt de wizard onder *Boekhouding > Boekhouding > Afsluiting > Dagboek overzetten*.
   Hij is alleen zichtbaar voor de groep *Boekhouding / Beheerder*.

## Gebruik

1. Vul de brondatabase in: URL, databasenaam, gebruiker en wachtwoord of API-sleutel.
   Het wachtwoord wordt niet bewaard; URL, database, gebruiker en dagboekcode wel.
2. Kies het doeldagboek en de periode, bv. 31/12/2024 tot en met 31/12/2025.
3. **Controleren**: de boekingen worden proefondervindelijk aangemaakt en weer teruggedraaid.
   Je ziet welke boekingen nieuw zijn of al bestaan, en wat ontbreekt.
4. **Overzetten**: de boekingen worden aangemaakt, en geboekt als *Boekingen meteen boeken*
   aangevinkt is.

Koppelingen: rekeningen op rekeningnummer, partners op btw-nummer, dan referentie, dan naam,
en analytische rekeningen op code of naam. Zolang er iets ontbreekt, wordt niets overgezet.
Afsluitdatums worden gecontroleerd; Odoo mag de datum van een boeking nooit stilzwijgend
verschuiven. Een nieuwe boeking krijgt als referentie het nummer uit de bron, zodat een
tweede run ze herkent en overslaat.

Niet overgezet: afpuntingen, btw-codes op lijnen, en facturen of creditnota's.
