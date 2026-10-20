{
    "name": "Dagboek overzetten",
    "summary": "Boekingen van een dagboek overnemen uit een andere Odoo-database",
    "description": """
Wizard om de diverse boekingen van één dagboek (bv. het afsluitdagboek AFSL)
via XML-RPC op te halen uit een andere Odoo-database en hier aan te maken.
Rekeningen worden gekoppeld op rekeningnummer, partners op btw-nummer,
referentie of naam, en analytische rekeningen op code of naam.
""",
    "category": "Accounting/Accounting",
    "version": "19.0.1.0.0",
    "author": "DataForge",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/journal_transfer_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
