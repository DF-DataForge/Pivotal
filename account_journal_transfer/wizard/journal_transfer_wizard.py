import logging
import xmlrpc.client
from collections import defaultdict

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "account_journal_transfer."
REMEMBERED_FIELDS = ("source_url", "source_db", "source_login", "source_company", "source_journal_code")
SKIPPED_DISPLAY_TYPES = ("line_section", "line_subsection", "line_note")
XMLRPC_TIMEOUT = 120


class _TimeoutTransport(xmlrpc.client.Transport):
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = XMLRPC_TIMEOUT
        return conn


class _TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = XMLRPC_TIMEOUT
        return conn


class _DryRun(Exception):
    """Wordt opgegooid om een proefaanmaak terug te draaien."""


class SourceDatabase:
    """Leestoegang tot de brondatabase via XML-RPC."""

    def __init__(self, url, db, login, password, company=None):
        self.url = url.rstrip("/")
        transport = _TimeoutSafeTransport() if self.url.startswith("https") else _TimeoutTransport()
        self.db = db
        self.password = password
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", transport=transport, allow_none=True)
            self.uid = common.authenticate(db, login, password, {})
        except (OSError, xmlrpc.client.Error) as exc:
            raise UserError(f"Geen verbinding met de brondatabase {self.url}: {exc}") from exc
        if not self.uid:
            raise UserError(f"Aanmelden op de brondatabase mislukt voor {login} ({self.url} / {db}).")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", transport=transport, allow_none=True)
        self.context = {}
        self.company = self._resolve_company(company)
        self.context = {"allowed_company_ids": [self.company["id"]]}

    def call(self, model, method, *args, **kwargs):
        kwargs.setdefault("context", self.context)
        try:
            return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)
        except xmlrpc.client.Fault as exc:
            message = exc.faultString.strip().splitlines()[-1]
            raise UserError(f"Fout in de brondatabase ({model}.{method}): {message}") from exc
        except (OSError, xmlrpc.client.Error) as exc:
            raise UserError(f"Verbinding met de brondatabase verbroken: {exc}") from exc

    def search_read(self, model, domain, fields, **kwargs):
        return self.call(model, "search_read", domain, fields=fields, **kwargs)

    def read(self, model, ids, fields):
        return self.call(model, "read", list(ids), fields=fields) if ids else []

    def _resolve_company(self, company):
        fields = ["name", "currency_id"]
        if company:
            domain = [("id", "=", int(company))] if str(company).isdigit() else [("name", "=", company)]
            found = self.search_read("res.company", domain, fields)
            if len(found) != 1:
                raise UserError(f"Bedrijf '{company}' niet (eenduidig) gevonden in de brondatabase.")
            return found[0]
        user = self.read("res.users", [self.uid], ["company_id"])[0]
        return self.read("res.company", [user["company_id"][0]], fields)[0]

    def find_journal(self, code):
        journals = self.search_read(
            "account.journal",
            [("code", "=", code), ("company_id", "=", self.company["id"])],
            ["name", "code"],
        )
        if not journals:
            raise UserError(f"Dagboek met code '{code}' niet gevonden in de brondatabase ({self.company['name']}).")
        return journals[0]

    def read_moves(self, journal_id, date_from, date_to, include_draft):
        domain = [
            ("journal_id", "=", journal_id),
            ("state", "in", ["posted", "draft"] if include_draft else ["posted"]),
            ("date", ">=", fields.Date.to_string(date_from)),
            ("date", "<=", fields.Date.to_string(date_to)),
        ]
        moves = self.search_read(
            "account.move", domain, ["name", "ref", "date", "move_type", "narration", "line_ids"],
            order="date, name",
        )
        line_ids = [line_id for move in moves for line_id in move["line_ids"]]
        lines = self.read("account.move.line", line_ids, [
            "move_id", "sequence", "account_id", "name", "debit", "credit", "partner_id",
            "currency_id", "amount_currency", "analytic_distribution", "tax_ids",
            "tax_line_id", "date_maturity", "display_type",
        ])
        lines_by_move = defaultdict(list)
        for line in lines:
            lines_by_move[line["move_id"][0]].append(line)
        for move in moves:
            move["lines"] = sorted(lines_by_move[move["id"]], key=lambda l: (l["sequence"], l["id"]))
        return moves


def _m2o_id(value):
    return value[0] if value else False


class AccountJournalTransferWizard(models.TransientModel):
    _name = "account.journal.transfer.wizard"
    _description = "Dagboek overzetten uit een andere database"

    state = fields.Selection(
        [("config", "Instellingen"), ("checked", "Gecontroleerd"), ("done", "Overgezet")],
        default="config",
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    source_url = fields.Char("URL brondatabase", required=True, help="Bv. https://oude-database.odoo.com")
    source_db = fields.Char("Naam brondatabase", required=True)
    source_login = fields.Char("Gebruiker", required=True)
    source_password = fields.Char("Wachtwoord / API-sleutel", help="Wordt niet bewaard.")
    source_company = fields.Char("Bedrijf in bron", help="Enkel nodig als de brondatabase meerdere bedrijven heeft.")
    source_journal_code = fields.Char("Dagboekcode in bron", required=True, default="AFSL")

    journal_id = fields.Many2one(
        "account.journal", "Doeldagboek", required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    date_from = fields.Date("Vanaf", required=True)
    date_to = fields.Date("Tot en met", required=True)

    include_draft = fields.Boolean("Ook conceptboekingen uit de bron")
    transfer_partners = fields.Boolean("Partners overzetten", default=True)
    drop_missing_partners = fields.Boolean(
        "Onvindbare partners weglaten",
        help="Lijnen met een partner die hier niet gevonden wordt, worden zonder partner overgezet "
             "in plaats van de overzetting te blokkeren.",
    )
    create_missing_partners = fields.Boolean(
        "Ontbrekende partners aanmaken",
        help="Partners die hier niet gevonden worden, worden aangemaakt met naam, btw-nummer, "
             "referentie en e-mail uit de bron.",
    )
    create_missing_accounts = fields.Boolean(
        "Ontbrekende rekeningen aanmaken",
        help="Rekeningen die hier niet bestaan, worden aangemaakt met nummer, naam en type uit de bron.",
    )
    transfer_analytic = fields.Boolean("Analytische verdeling overzetten", default=True)
    post_moves = fields.Boolean("Boekingen meteen boeken", help="Anders worden ze als concept aangemaakt.")

    report_html = fields.Html("Rapport", readonly=True, sanitize=False)
    can_transfer = fields.Boolean(readonly=True)
    move_ids = fields.Many2many("account.move", string="Aangemaakte boekingen", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        params = self.env["ir.config_parameter"].sudo()
        for name in REMEMBERED_FIELDS:
            value = params.get_param(PARAM_PREFIX + name)
            if value and name in fields_list:
                res[name] = value
        if "journal_id" in fields_list and not res.get("journal_id"):
            code = res.get("source_journal_code") or "AFSL"
            journal = self.env["account.journal"].search(
                [("code", "=", code), ("type", "=", "general"), ("company_id", "=", self.env.company.id)], limit=1)
            res["journal_id"] = journal.id
        return res

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError("De begindatum moet voor de einddatum liggen.")

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------

    def action_check(self):
        self.ensure_one()
        self._remember_settings()
        result = self._run(apply=False)
        self.write({
            "state": "checked",
            "report_html": self._render_report(result),
            "can_transfer": not result["errors"] and bool(result["todo"]),
        })
        return self._reopen()

    def action_transfer(self):
        self.ensure_one()
        result = self._run(apply=True)
        if result["errors"]:
            self.write({"state": "checked", "report_html": self._render_report(result), "can_transfer": False})
            return self._reopen()
        self.write({
            "state": "done",
            "report_html": self._render_report(result),
            "can_transfer": False,
            "move_ids": [(6, 0, result["created"].ids)],
            "source_password": False,
        })
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.write({"state": "config", "report_html": False, "can_transfer": False})
        return self._reopen()

    def action_open_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Overgezette boekingen",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.move_ids.ids)],
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "name": "Dagboek overzetten",
        }

    def _remember_settings(self):
        params = self.env["ir.config_parameter"].sudo()
        for name in REMEMBERED_FIELDS:
            params.set_param(PARAM_PREFIX + name, self[name] or "")

    # ------------------------------------------------------------------
    # Kern
    # ------------------------------------------------------------------

    def _run(self, apply):
        if not self.source_password:
            raise UserError("Vul het wachtwoord of de API-sleutel van de brondatabase in.")
        source = SourceDatabase(self.source_url, self.source_db, self.source_login,
                                self.source_password, self.source_company)
        company = self.company_id
        if source.company["currency_id"][1] != company.currency_id.name:
            raise UserError("De bedrijfsmunt van de brondatabase verschilt van deze database.")
        if self.journal_id.company_id != company:
            raise UserError("Het doeldagboek hoort niet bij het actieve bedrijf.")
        source_journal = source.find_journal(self.source_journal_code)
        moves = source.read_moves(source_journal["id"], self.date_from, self.date_to, self.include_draft)

        result = {
            "source": source, "source_journal": source_journal,
            "rows": [], "todo": [], "errors": [], "warnings": [], "info": [],
            "created": self.env["account.move"],
        }
        mapping = _Mapping(self, source, result)
        for move in moves:
            if move["move_type"] != "entry":
                mapping.warn(f"{move['name']} is geen diverse boeking (type {move['move_type']}) en wordt overgeslagen.")
        moves = [m for m in moves if m["move_type"] == "entry"]

        # Ook bij de controle alles echt aanmaken (rekeningen, partners, boekingen), maar in een
        # savepoint dat wordt teruggedraaid: zo komen alle validaties van Odoo zelf al aan het licht.
        try:
            with self.env.cr.savepoint():
                mapping.prepare(moves)
                self._plan_moves(moves, mapping, result)
                if not result["errors"]:
                    result["created"] = self._create_moves(result)
                if not apply or result["errors"]:
                    raise _DryRun()
        except _DryRun:
            self.env.invalidate_all()
            result["created"] = self.env["account.move"]
        return result

    def _plan_moves(self, moves, mapping, result):
        for move in moves:
            vals = mapping.move_vals(move)
            total = self._check_balanced(move, mapping)
            self._check_lock_date(move, mapping)
            existing = self.env["account.move"].search([
                ("journal_id", "=", self.journal_id.id),
                ("date", "=", move["date"]),
                ("ref", "=", vals["ref"]),
                ("state", "!=", "cancel"),
            ], limit=1)
            row = {"name": move["name"], "date": move["date"], "lines": len(vals["line_ids"]),
                   "total": total, "existing": existing.name}
            result["rows"].append(row)
            if not existing:
                result["todo"].append((move, vals, row))

    def _create_moves(self, result):
        created = self.env["account.move"]
        for move, vals, row in result["todo"]:
            try:
                with self.env.cr.savepoint():
                    new_move = self.env["account.move"].with_company(self.company_id).create(vals)
                    if self.post_moves:
                        new_move.action_post()
                    self.env.flush_all()
                    if new_move.date != fields.Date.to_date(move["date"]):
                        raise UserError(f"Odoo verschoof de datum naar {new_move.date} (afsluitdatum?).")
            except (UserError, ValidationError) as exc:
                self.env.invalidate_all()
                result["errors"].append(f"{move['name']}: {exc.args[0] if exc.args else exc}")
                continue
            row["new_name"] = new_move.name
            created |= new_move
        return created

    def _check_balanced(self, move, mapping):
        rounding = self.company_id.currency_id.rounding
        debit = sum(line["debit"] for line in move["lines"])
        credit = sum(line["credit"] for line in move["lines"])
        if float_compare(debit, credit, precision_rounding=rounding):
            mapping.error(f"{move['name']}: niet in evenwicht (debet {debit:.2f} / credit {credit:.2f}).")
        return debit

    def _check_lock_date(self, move, mapping):
        date = fields.Date.to_date(move["date"])
        violated = self.company_id._get_violated_lock_dates(date, False, self.journal_id)
        if violated:
            lock_date = violated[-1][0]
            mapping.error(f"{move['name']}: de datum {date} valt in een afgesloten periode "
                          f"(afsluitdatum {lock_date}). Pas de afsluitdatums tijdelijk aan.")

    # ------------------------------------------------------------------
    # Rapport
    # ------------------------------------------------------------------

    def _render_report(self, result):
        source = result["source"]
        html = Markup(
            "<p>Bron: <b>{}</b> / {} / {} — dagboek <b>{}</b> ({})</p>"
        ).format(source.url, source.db, source.company["name"],
                 result["source_journal"]["name"], result["source_journal"]["code"])
        applied = bool(result["created"])
        sections = (
            ("danger", "Op te lossen", result["errors"]),
            ("warning", "Waarschuwingen", result["warnings"]),
            ("info", "Aangemaakt" if applied else "Wordt aangemaakt bij het overzetten", result["info"]),
        )
        for level, title, messages in sections:
            if messages:
                items = Markup().join(Markup("<li>{}</li>").format(m) for m in messages)
                html += Markup('<div class="alert alert-{} py-2"><b>{} ({})</b><ul class="mb-0">{}</ul></div>').format(
                    level, title, len(messages), items)

        if not result["rows"]:
            return html + Markup("<p>Geen boekingen gevonden voor deze selectie.</p>")

        body = Markup()
        for row in result["rows"]:
            if row["existing"]:
                status = Markup("<span class='text-muted'>bestaat al ({})</span>").format(row["existing"])
            elif row.get("new_name"):
                status = Markup("<span class='text-success'>aangemaakt: {}</span>").format(row["new_name"])
            else:
                status = escape("nieuw")
            body += Markup(
                "<tr><td>{}</td><td>{}</td><td class='text-end'>{}</td><td class='text-end'>{}</td><td>{}</td></tr>"
            ).format(row["name"], row["date"], row["lines"], f"{row['total']:,.2f}", status)
        html += Markup(
            "<table class='table table-sm'><thead><tr><th>Boeking in bron</th><th>Datum</th>"
            "<th class='text-end'>Lijnen</th><th class='text-end'>Bedrag</th><th>Status</th></tr></thead>"
            "<tbody>{}</tbody></table>"
        ).format(body)

        todo = len(result["todo"])
        if result["errors"]:
            summary = f"{len(result['errors'])} probleem/problemen: er wordt niets overgezet."
        elif result["created"]:
            state = "geboekt" if self.post_moves else "als concept aangemaakt"
            summary = f"{len(result['created'])} boeking(en) {state}."
        elif todo:
            summary = f"Controle geslaagd: {todo} boeking(en) kunnen overgezet worden."
        else:
            summary = "Alle boekingen bestaan al in deze database."
        return html + Markup("<p><b>{}</b></p>").format(summary)


class _Mapping:
    """Koppelt records uit de brondatabase aan records in deze database."""

    def __init__(self, wizard, source, result):
        self.wizard = wizard
        self.env = wizard.env
        self.company = wizard.company_id
        self.source = source
        self.result = result
        self.accounts = {}
        self.partners = {}
        self.analytic = {}
        self.currencies = {}

    def error(self, message):
        if message not in self.result["errors"]:
            self.result["errors"].append(message)

    def warn(self, message):
        if message not in self.result["warnings"]:
            self.result["warnings"].append(message)

    def info(self, message):
        self.result["info"].append(message)

    def _create(self, model, vals, label):
        """Maakt een record aan; een validatiefout wordt een melding in plaats van een crash."""
        try:
            with self.env.cr.savepoint():
                record = self.env[model].with_company(self.company).create(vals)
                self.env.flush_all()
        except (UserError, ValidationError) as exc:
            self.env.invalidate_all()
            self.error(f"{label} kon niet aangemaakt worden: {exc.args[0] if exc.args else exc}")
            return False
        self.info(label)
        return record

    def _domain(self, model):
        return Domain(self.env[model]._check_company_domain(self.company))

    def prepare(self, moves):
        lines = [line for move in moves for line in move["lines"]]
        self._map_accounts({_m2o_id(l["account_id"]) for l in lines} - {False})
        if self.wizard.transfer_partners:
            self._map_partners({_m2o_id(l["partner_id"]) for l in lines} - {False})
        if self.wizard.transfer_analytic:
            ids = set()
            for line in lines:
                for key in line["analytic_distribution"] or {}:
                    ids.update(int(x) for x in str(key).split(","))
            self._map_analytic(ids)
        self._map_currencies({_m2o_id(l["currency_id"]) for l in lines} - {False})

    def _map_accounts(self, source_ids):
        Account = self.env["account.account"].with_company(self.company)
        fields = ["code", "name", "account_type", "reconcile"]
        for account in sorted(self.source.read("account.account", source_ids, fields), key=lambda a: a["code"]):
            found = Account.search(self._domain("account.account") & Domain("code", "=", account["code"]))
            if len(found) == 1:
                self.accounts[account["id"]] = found.id
            elif not found and self.wizard.create_missing_accounts:
                new = self._create("account.account", {
                    "code": account["code"], "name": account["name"],
                    "account_type": account["account_type"], "reconcile": account["reconcile"],
                }, f"Rekening {account['code']} ({account['name']})")
                self.accounts[account["id"]] = new.id if new else False
            elif not found:
                self.error(f"Rekening {account['code']} ({account['name']}) bestaat niet in deze database.")
            else:
                self.error(f"Rekening {account['code']} komt meerdere keren voor in deze database.")

    def _map_partners(self, source_ids):
        fields = ["name", "vat", "ref", "is_company", "email"]
        source_partners = self.source.read("res.partner", source_ids, fields)
        for partner in sorted(source_partners, key=lambda p: (p["name"] or "").lower()):
            found = self._find_partner(partner)
            if len(found) == 1:
                self.partners[partner["id"]] = found.id
                continue
            if not found and self.wizard.create_missing_partners:
                new = self._create("res.partner", {
                    "name": partner["name"], "vat": partner["vat"] or False, "ref": partner["ref"] or False,
                    "is_company": partner["is_company"], "email": partner["email"] or False,
                }, f"Partner '{partner['name']}'" + (f" (btw {partner['vat']})" if partner["vat"] else ""))
                self.partners[partner["id"]] = new.id if new else False
                continue
            if found:
                candidates = ", ".join(f"{p.display_name} [id {p.id}]" for p in found[:5])
                reason = f"{len(found)} mogelijke treffers: {candidates}. Voeg deze contacten samen"
            else:
                reason = "niet gevonden in deze database"
            message = f"Partner '{partner['name']}' (btw {partner['vat'] or '-'}): {reason}."
            if self.wizard.drop_missing_partners:
                self.warn(message + " Wordt zonder partner overgezet.")
                self.partners[partner["id"]] = False
            else:
                self.error(message)

    def _find_partner(self, partner):
        Partner = self.env["res.partner"]
        domain = self._domain("res.partner")
        criteria = [(field, "=", partner[field]) for field in ("vat", "ref") if partner[field]]
        criteria.append(("name", "=ilike", partner["name"]))
        for criterion in criteria:
            # Eerst bij de actieve contacten zoeken, pas daarna bij de gearchiveerde.
            found = Partner.search(domain & Domain(*criterion)) \
                or Partner.with_context(active_test=False).search(domain & Domain(*criterion))
            if found:
                break
        if len(found) > 1:
            # Contactpersonen en adressen van hetzelfde bedrijf: neem het bedrijf zelf.
            commercial = found.commercial_partner_id
            if len(commercial) == 1:
                return commercial
            top = found.filtered(lambda p: not p.parent_id)
            if len(top) == 1:
                return top
        return found

    def _map_analytic(self, source_ids):
        Analytic = self.env["account.analytic.account"].with_context(active_test=False)
        domain = self._domain("account.analytic.account")
        for account in self.source.read("account.analytic.account", source_ids, ["name", "code", "plan_id"]):
            key = ("code", account["code"]) if account["code"] else ("name", account["name"])
            found = Analytic.search(domain & Domain(key[0], "=", key[1]))
            if len(found) > 1 and account["plan_id"]:
                found = found.filtered(lambda a: a.plan_id.name == account["plan_id"][1])
            if len(found) == 1:
                self.analytic[account["id"]] = found.id
            else:
                reason = "niet gevonden" if not found else "niet eenduidig"
                self.error(f"Analytische rekening '{key[1]}' {reason} in deze database "
                           "(of vink 'Analytische verdeling overzetten' uit).")

    def _map_currencies(self, source_ids):
        Currency = self.env["res.currency"].with_context(active_test=False)
        for currency in self.source.read("res.currency", source_ids, ["name"]):
            found = Currency.search([("name", "=", currency["name"])], limit=1)
            if found:
                self.currencies[currency["id"]] = found.id
            else:
                self.error(f"Munt {currency['name']} bestaat niet in deze database.")

    def _distribution(self, distribution):
        result = {}
        for key, percentage in (distribution or {}).items():
            ids = [self.analytic.get(int(x)) for x in str(key).split(",")]
            if not all(ids):
                return False
            result[",".join(str(i) for i in ids)] = percentage
        return result

    def move_vals(self, move):
        source_currency = self.source.company["currency_id"][0]
        rounding = self.company.currency_id.rounding
        commands = []
        for line in move["lines"]:
            if line["display_type"] in SKIPPED_DISPLAY_TYPES:
                continue
            if float_is_zero(line["debit"], precision_rounding=rounding) \
                    and float_is_zero(line["credit"], precision_rounding=rounding) \
                    and float_is_zero(line["amount_currency"], precision_rounding=rounding):
                continue
            if line["tax_ids"] or line["tax_line_id"]:
                self.warn(f"{move['name']}: btw-codes worden niet overgezet (bedragen wel).")
            vals = {
                "name": line["name"] or False,
                "account_id": self.accounts.get(_m2o_id(line["account_id"])),
                "debit": line["debit"],
                "credit": line["credit"],
            }
            if line["date_maturity"]:
                vals["date_maturity"] = line["date_maturity"]
            if line["partner_id"] and self.wizard.transfer_partners:
                vals["partner_id"] = self.partners.get(line["partner_id"][0], False)
            line_currency = _m2o_id(line["currency_id"])
            if line_currency and line_currency != source_currency:
                vals["currency_id"] = self.currencies.get(line_currency)
                vals["amount_currency"] = line["amount_currency"]
            if line["analytic_distribution"] and self.wizard.transfer_analytic:
                distribution = self._distribution(line["analytic_distribution"])
                if distribution:
                    vals["analytic_distribution"] = distribution
            commands.append((0, 0, vals))

        ref = move["name"] + (f" - {move['ref']}" if move["ref"] else "")
        narration = Markup("<p>Overgezet uit database {}, boeking {}.</p>").format(self.source.db, move["name"])
        if move["narration"]:
            narration = Markup(move["narration"]) + narration
        return {
            "move_type": "entry",
            "journal_id": self.wizard.journal_id.id,
            "date": move["date"],
            "ref": ref,
            "narration": narration,
            "line_ids": commands,
        }
