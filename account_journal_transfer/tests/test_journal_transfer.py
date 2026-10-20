from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

SOURCE_PATH = "odoo.addons.account_journal_transfer.wizard.journal_transfer_wizard.SourceDatabase"


class FakeSource:
    """Brondatabase in het geheugen, met dezelfde interface als SourceDatabase."""

    url = "https://bron.example.com"
    db = "bron"

    def __init__(self, moves, records):
        self.company = {"id": 1, "name": "Bron", "currency_id": [1, "EUR"]}
        self.moves = moves
        self.records = records

    def find_journal(self, code):
        return {"id": 1, "name": "Afsluiting", "code": code}

    def read_moves(self, journal_id, date_from, date_to, include_draft):
        return [m for m in self.moves if str(date_from) <= m["date"] <= str(date_to)]

    def read(self, model, ids, fields):
        return [self.records[model][i] for i in ids]


def line(account, debit=0.0, credit=0.0, partner=False, name=False, distribution=False):
    return {
        "id": 0, "sequence": 10, "account_id": [account, "x"], "name": name, "debit": debit, "credit": credit,
        "partner_id": [partner, "x"] if partner else False, "currency_id": [1, "EUR"],
        "amount_currency": debit - credit, "analytic_distribution": distribution, "tax_ids": [],
        "tax_line_id": False, "date_maturity": False, "display_type": "product",
    }


@tagged("post_install", "-at_install")
class TestJournalTransfer(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.currency_id = cls.env.ref("base.EUR")
        cls.journal = cls.env["account.journal"].create({"name": "Afsluiting", "code": "AFSL", "type": "general"})
        cls.account_a = cls.company_data["default_account_revenue"]
        cls.account_b = cls.company_data["default_account_payable"]
        cls.partner = cls.env["res.partner"].create({"name": "Maes NV SA", "vat": "BE0477472701"})
        cls.plan = cls.env["account.analytic.plan"].create({"name": "Projecten"})
        cls.analytic = cls.env["account.analytic.account"].create(
            {"name": "Project X", "code": "PX", "plan_id": cls.plan.id})
        cls.records = {
            "account.account": {
                11: {"id": 11, "code": cls.account_a.code, "name": "A", "account_type": "income", "reconcile": False},
                12: {"id": 12, "code": cls.account_b.code, "name": "B", "account_type": "liability_payable", "reconcile": True},
                13: {"id": 13, "code": "123ZZZ", "name": "Bestaat niet", "account_type": "expense", "reconcile": False},
            },
            "res.partner": {
                21: {"id": 21, "name": "Andere naam", "vat": "BE0477472701", "ref": False, "is_company": True, "email": False},
                22: {"id": 22, "name": "diverse leveranciers", "vat": False, "ref": False, "is_company": True, "email": False},
            },
            "account.analytic.account": {
                31: {"id": 31, "name": "Project X", "code": "PX", "plan_id": [5, "Projecten"]},
            },
            "res.currency": {1: {"id": 1, "name": "EUR"}},
        }
        cls.moves = [
            {"id": 1, "name": "AFSL/2024/12/0001", "ref": "Afsluiting 2024", "date": "2024-12-31",
             "move_type": "entry", "narration": False, "lines": [
                 line(11, debit=100.0, name="Resultaat", distribution={"31": 100.0}),
                 line(12, credit=60.0, partner=21),
                 line(12, credit=40.0, partner=22),
             ]},
            {"id": 2, "name": "AFSL/2025/01/0001", "ref": False, "date": "2025-01-01",
             "move_type": "entry", "narration": False, "lines": [
                 line(12, debit=40.0, partner=22),
                 line(11, credit=40.0),
             ]},
        ]

    def _wizard(self, moves=None, **vals):
        source = FakeSource(moves or self.moves, self.records)
        wizard = self.env["account.journal.transfer.wizard"].create({
            "source_url": source.url, "source_db": source.db, "source_login": "admin",
            "source_password": "secret", "journal_id": self.journal.id,
            "date_from": "2024-12-31", "date_to": "2025-12-31", **vals,
        })
        patcher = patch(SOURCE_PATH, return_value=source)
        patcher.start()
        self.addCleanup(patcher.stop)
        return wizard

    def _transferred(self):
        return self.env["account.move"].search([("journal_id", "=", self.journal.id)], order="date")

    def test_check_creates_nothing(self):
        wizard = self._wizard(drop_missing_partners=True, post_moves=True)
        wizard.action_check()
        self.assertTrue(wizard.can_transfer, wizard.report_html)
        self.assertIn("Controle geslaagd: 2", wizard.report_html)
        self.assertFalse(self._transferred())

    def test_transfer_and_rerun(self):
        wizard = self._wizard(drop_missing_partners=True, post_moves=True)
        wizard.action_check()
        wizard.action_transfer()
        self.assertEqual(wizard.state, "done", wizard.report_html)
        self.assertFalse(wizard.source_password)

        moves = self._transferred()
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves.mapped("state"), ["posted", "posted"])
        self.assertEqual(moves[0].ref, "AFSL/2024/12/0001 - Afsluiting 2024")
        self.assertEqual(str(moves[0].date), "2024-12-31")
        self.assertEqual(moves[1].ref, "AFSL/2025/01/0001")
        self.assertEqual(wizard.move_ids, moves)

        lines = moves[0].line_ids.sorted(lambda l: (l.debit, -l.credit))
        self.assertRecordValues(lines, [
            {"account_id": self.account_b.id, "debit": 0.0, "credit": 60.0, "partner_id": self.partner.id},
            {"account_id": self.account_b.id, "debit": 0.0, "credit": 40.0, "partner_id": False},
            {"account_id": self.account_a.id, "debit": 100.0, "credit": 0.0, "partner_id": False},
        ])
        self.assertEqual(lines[2].analytic_distribution, {str(self.analytic.id): 100.0})

        second = self._wizard(drop_missing_partners=True)
        second.action_check()
        self.assertFalse(second.can_transfer)
        self.assertIn("Alle boekingen bestaan al", second.report_html)

    def test_missing_records_block(self):
        moves = [dict(self.moves[1], lines=[line(13, debit=40.0), line(11, credit=40.0, partner=22)])]
        wizard = self._wizard(moves=moves)
        wizard.action_check()
        self.assertFalse(wizard.can_transfer)
        self.assertIn("Rekening 123ZZZ", wizard.report_html)
        self.assertIn("diverse leveranciers", wizard.report_html)
        wizard.action_transfer()
        self.assertFalse(self._transferred())

    def test_unbalanced_blocks(self):
        moves = [dict(self.moves[1], lines=[line(12, debit=40.0), line(11, credit=39.0)])]
        wizard = self._wizard(moves=moves)
        wizard.action_check()
        self.assertFalse(wizard.can_transfer)
        self.assertIn("niet in evenwicht", wizard.report_html)

    def test_lock_date_blocks(self):
        self.company.fiscalyear_lock_date = "2024-12-31"
        wizard = self._wizard(drop_missing_partners=True, post_moves=True)
        wizard.action_check()
        self.assertFalse(wizard.can_transfer)
        self.assertIn("afgesloten periode", wizard.report_html)
        self.assertNotIn("AFSL/2025/01/0001: de datum", wizard.report_html)

    def test_create_missing_records(self):
        moves = [dict(self.moves[1], lines=[line(13, debit=40.0, partner=22), line(11, credit=40.0)])]
        wizard = self._wizard(moves=moves, create_missing_accounts=True, create_missing_partners=True, post_moves=True)
        wizard.action_check()
        self.assertTrue(wizard.can_transfer, wizard.report_html)
        self.assertIn("Wordt aangemaakt bij het overzetten (2)", wizard.report_html)
        self.assertFalse(self.env["account.account"].search([("code", "=", "123ZZZ")]))

        wizard.action_transfer()
        account = self.env["account.account"].search([("code", "=", "123ZZZ")])
        partner = self.env["res.partner"].search([("name", "=", "diverse leveranciers")])
        self.assertEqual(account.account_type, "expense")
        self.assertTrue(partner.is_company)
        debit_line = self._transferred().line_ids.filtered("debit")
        self.assertEqual((debit_line.account_id, debit_line.partner_id), (account, partner))

    def test_partner_duplicates(self):
        # Een gearchiveerde dubbel en een contactpersoon met hetzelfde btw-nummer zijn geen echte dubbels.
        self.partner.copy({"active": False})
        self.env["res.partner"].create({"name": "Jan", "parent_id": self.partner.id, "type": "contact"})
        moves = [dict(self.moves[1], lines=[line(12, debit=40.0, partner=21), line(11, credit=40.0)])]
        wizard = self._wizard(moves=moves)
        wizard.action_check()
        self.assertTrue(wizard.can_transfer, wizard.report_html)

        # Twee actieve bedrijven met hetzelfde btw-nummer wel: dan tonen we welke.
        twin = self.partner.copy({"name": "Maes NV SA (dubbel)", "vat": self.partner.vat})
        wizard = self._wizard(moves=moves)
        wizard.action_check()
        self.assertFalse(wizard.can_transfer)
        self.assertIn(f"[id {twin.id}]", wizard.report_html)
