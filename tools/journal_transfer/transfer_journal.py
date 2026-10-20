#!/usr/bin/env python3
"""Zet boekingen van een dagboek over van de ene Odoo 19-database naar de andere.

Bedoeld voor o.a. afsluitingsboekingen (bv. 31/12/2024 en 31/12/2025).

Werkwijze:
  1. Leest de boekingen (account.move van type 'entry') uit het dagboek in de
     brondatabase, gefilterd op datum(s).
  2. Zoekt in de doeldatabase het dagboek, de rekeningen (op rekeningnummer),
     partners (btw-nummer > referentie > naam) en analytische rekeningen.
  3. Standaard enkel een proefrun (rapport). Met --apply worden de boekingen
     als concept aangemaakt, met --post bovendien geboekt.

Enkel Python-standaardbibliotheek; verbinding via XML-RPC.
Zie README.md voor gebruik.
"""

import argparse
import configparser
import csv
import getpass
import os
import sys
import xmlrpc.client
from collections import defaultdict

SKIPPED_DISPLAY_TYPES = ("line_section", "line_subsection", "line_note")


class OdooConnection:
    def __init__(self, label, url, db, user, password, company=None):
        self.label = label
        self.url = url.rstrip("/")
        self.db = db
        self.password = password
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            raise SystemExit(f"[{label}] Aanmelden mislukt voor {user} op {self.url} / {db}.")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        self.context = {}
        self.company = self._resolve_company(company)
        self.context = {"allowed_company_ids": [self.company["id"]], "lang": "nl_BE"}

    def call(self, model, method, *args, **kwargs):
        if self.context and "context" not in kwargs:
            kwargs["context"] = self.context
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)

    def search_read(self, model, domain, fields, **kwargs):
        return self.call(model, "search_read", domain, fields=fields, **kwargs)

    def read(self, model, ids, fields):
        if not ids:
            return []
        return self.call(model, "read", list(ids), fields=fields)

    def _resolve_company(self, company):
        if company:
            domain = [("name", "=", company)]
            if str(company).isdigit():
                domain = [("id", "=", int(company))]
            found = self.search_read("res.company", domain, ["name", "currency_id"])
            if len(found) != 1:
                raise SystemExit(f"[{self.label}] Bedrijf '{company}' niet (eenduidig) gevonden.")
            return found[0]
        user = self.read("res.users", [self.uid], ["company_id"])[0]
        return self.read("res.company", [user["company_id"][0]], ["name", "currency_id"])[0]


def m2o_id(value):
    return value[0] if value else False


# ---------------------------------------------------------------------------
# Inlezen bron
# ---------------------------------------------------------------------------

def find_journal(conn, code):
    journals = conn.search_read(
        "account.journal",
        [("code", "=", code), ("company_id", "=", conn.company["id"])],
        ["name", "code", "type"],
    )
    if not journals:
        raise SystemExit(f"[{conn.label}] Dagboek met code '{code}' niet gevonden in {conn.company['name']}.")
    return journals[0]


def read_source_moves(conn, journal, args):
    domain = [("journal_id", "=", journal["id"])]
    domain.append(("state", "in", ["posted", "draft"] if args.include_draft else ["posted"]))
    if args.move:
        domain.append(("name", "in", args.move))
    if args.date:
        domain.append(("date", "in", args.date))
    if args.date_from:
        domain.append(("date", ">=", args.date_from))
    if args.date_to:
        domain.append(("date", "<=", args.date_to))
    if not (args.move or args.date or args.date_from or args.date_to):
        raise SystemExit("Geef minstens --date, --date-from/--date-to of --move op.")

    moves = conn.search_read(
        "account.move", domain,
        ["name", "ref", "date", "move_type", "state", "narration", "line_ids"],
        order="date, name",
    )
    line_ids = [lid for move in moves for lid in move["line_ids"]]
    lines = conn.read("account.move.line", line_ids, [
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


# ---------------------------------------------------------------------------
# Koppelen bron -> doel
# ---------------------------------------------------------------------------

class Mapper:
    def __init__(self, src, dst, args):
        self.src = src
        self.dst = dst
        self.args = args
        self.errors = []      # blokkerend
        self.warnings = []
        self.account_map = {}
        self.partner_map = {}
        self.analytic_map = {}
        self.currency_map = {}
        self.code_overrides = load_account_overrides(args.account_map)

    def error(self, msg):
        if msg not in self.errors:
            self.errors.append(msg)

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    def prepare(self, moves):
        lines = [l for m in moves for l in m["lines"]]
        self._map_accounts({m2o_id(l["account_id"]) for l in lines} - {False})
        if not self.args.no_partners:
            self._map_partners({m2o_id(l["partner_id"]) for l in lines} - {False})
        if not self.args.no_analytic:
            ids = set()
            for l in lines:
                for key in (l["analytic_distribution"] or {}):
                    ids.update(int(x) for x in str(key).split(","))
            self._map_analytic(ids)
        self._map_currencies({m2o_id(l["currency_id"]) for l in lines} - {False})

    def _map_accounts(self, src_ids):
        for acc in self.src.read("account.account", src_ids, ["code", "name"]):
            code = self.code_overrides.get(acc["code"], acc["code"])
            found = self.dst.search_read("account.account", [("code", "=", code)], ["code", "name"])
            if len(found) == 1:
                self.account_map[acc["id"]] = found[0]["id"]
            elif not found:
                self.error(f"Rekening {code} ({acc['name']}) bestaat niet in de doeldatabase.")
            else:
                self.error(f"Rekening {code} komt meerdere keren voor in de doeldatabase.")

    def _map_partners(self, src_ids):
        fields = ["name", "vat", "ref", "parent_id"]
        for partner in self.src.read("res.partner", src_ids, fields):
            found = []
            for field in ("vat", "ref"):
                if partner[field]:
                    found = self.dst.search_read("res.partner", [(field, "=", partner[field])], fields)
                    if found:
                        break
            if not found:
                found = self.dst.search_read("res.partner", [("name", "=ilike", partner["name"])], fields)
            # Bij meerdere treffers: voorkeur voor het hoofdcontact (zonder parent).
            if len(found) > 1:
                top = [p for p in found if not p["parent_id"]]
                found = top if len(top) == 1 else found
            if len(found) == 1:
                self.partner_map[partner["id"]] = found[0]["id"]
                continue
            reason = "niet gevonden" if not found else f"{len(found)} mogelijke treffers"
            msg = f"Partner '{partner['name']}' (btw {partner['vat'] or '-'}): {reason} in de doeldatabase."
            if self.args.drop_missing_partners:
                self.warn(msg + " Wordt zonder partner overgezet.")
                self.partner_map[partner["id"]] = False
            else:
                self.error(msg)

    def _map_analytic(self, src_ids):
        fields = ["name", "code", "plan_id"]
        for acc in self.src.read("account.analytic.account", src_ids, fields):
            domain = [("code", "=", acc["code"])] if acc["code"] else [("name", "=", acc["name"])]
            found = self.dst.search_read("account.analytic.account", domain, fields)
            if len(found) > 1 and acc["plan_id"]:
                found = [a for a in found if a["plan_id"] and a["plan_id"][1] == acc["plan_id"][1]]
            if len(found) == 1:
                self.analytic_map[acc["id"]] = found[0]["id"]
            else:
                reason = "niet gevonden" if not found else "niet eenduidig"
                self.error(f"Analytische rekening '{acc['code'] or acc['name']}' {reason} in de doeldatabase "
                           "(gebruik --no-analytic om analytiek weg te laten).")

    def _map_currencies(self, src_ids):
        for cur in self.src.read("res.currency", src_ids, ["name"]):
            found = self.dst.call("res.currency", "search", [("name", "=", cur["name"])],
                                  context={"active_test": False})
            if found:
                self.currency_map[cur["id"]] = found[0]
            else:
                self.error(f"Munt {cur['name']} bestaat niet in de doeldatabase.")

    def map_distribution(self, distribution):
        result = {}
        for key, pct in (distribution or {}).items():
            ids = [self.analytic_map.get(int(x)) for x in str(key).split(",")]
            if not all(ids):
                return None
            result[",".join(str(i) for i in ids)] = pct
        return result

    def build_move_vals(self, move, journal_id, source_db):
        src_currency = self.src.company["currency_id"][0]
        line_cmds = []
        for line in move["lines"]:
            if line["display_type"] in SKIPPED_DISPLAY_TYPES:
                continue
            if line["tax_ids"] or line["tax_line_id"]:
                self.warn(f"{move['name']}: btw-codes worden niet overgezet (bedragen wel).")
            vals = {
                "name": line["name"] or False,
                "account_id": self.account_map.get(m2o_id(line["account_id"])),
                "debit": line["debit"],
                "credit": line["credit"],
            }
            if line["date_maturity"]:
                vals["date_maturity"] = line["date_maturity"]
            if line["partner_id"] and not self.args.no_partners:
                vals["partner_id"] = self.partner_map.get(line["partner_id"][0], False)
            line_currency = m2o_id(line["currency_id"])
            if line_currency and line_currency != src_currency:
                vals["currency_id"] = self.currency_map.get(line_currency)
                vals["amount_currency"] = line["amount_currency"]
            if line["analytic_distribution"] and not self.args.no_analytic:
                dist = self.map_distribution(line["analytic_distribution"])
                if dist:
                    vals["analytic_distribution"] = dist
            line_cmds.append((0, 0, vals))

        ref = move["name"] + (f" - {move['ref']}" if move["ref"] else "")
        narration = f"<p>Overgezet uit database {source_db}, boeking {move['name']}.</p>"
        if move["narration"]:
            narration = move["narration"] + narration
        return {
            "move_type": "entry",
            "journal_id": journal_id,
            "date": move["date"],
            "ref": ref,
            "narration": narration,
            "line_ids": line_cmds,
        }


def load_account_overrides(path):
    if not path:
        return {}
    overrides = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(2048)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        for row in csv.reader(fh, dialect):
            if len(row) >= 2 and row[0].strip() and not row[0].strip().lower().startswith("bron"):
                overrides[row[0].strip()] = row[1].strip()
    return overrides


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------

def check_balanced(move, mapper):
    debit = round(sum(l["debit"] for l in move["lines"]), 2)
    credit = round(sum(l["credit"] for l in move["lines"]), 2)
    if abs(debit - credit) > 0.005:
        mapper.error(f"{move['name']}: niet in evenwicht (debet {debit:.2f} / credit {credit:.2f}).")
    return debit


def check_lock_dates(dst, moves, mapper):
    available = dst.call("res.company", "fields_get", attributes=["type"])
    lock_fields = [f for f in ("fiscalyear_lock_date", "hard_lock_date") if f in available]
    if not lock_fields:
        return
    company = dst.read("res.company", [dst.company["id"]], lock_fields)[0]
    for field in lock_fields:
        lock = company[field]
        if not lock:
            continue
        blocked = sorted({m["date"] for m in moves if m["date"] <= lock})
        if blocked:
            mapper.error(f"Doeldatabase is afgesloten tot {lock} ({field}); datums {', '.join(blocked)} "
                         "kunnen niet geboekt worden. Pas de afsluitdatum tijdelijk aan.")


def find_existing(dst, journal_id, vals):
    return dst.call("account.move", "search", [
        ("journal_id", "=", journal_id),
        ("date", "=", vals["date"]),
        ("ref", "=", vals["ref"]),
        ("state", "!=", "cancel"),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def connect(cfg, section, company):
    if section not in cfg:
        raise SystemExit(f"Sectie [{section}] ontbreekt in het configuratiebestand.")
    sec = cfg[section]
    env_key = f"ODOO_{section.upper()}_PASSWORD"
    password = sec.get("password") or os.environ.get(env_key)
    if not password:
        password = getpass.getpass(f"Wachtwoord / API-sleutel voor {sec['user']} op {sec['db']} ({section}): ")
    return OdooConnection(section, sec["url"], sec["db"], sec["user"], password, company or sec.get("company"))


def parse_args(argv):
    p = argparse.ArgumentParser(description="Zet boekingen van een dagboek over tussen twee Odoo 19-databases.")
    p.add_argument("--config", default="transfer.ini", help="Configuratiebestand (standaard: transfer.ini)")
    p.add_argument("--journal", required=True, help="Dagboekcode in de brondatabase, bv. MISC")
    p.add_argument("--target-journal", help="Dagboekcode in de doeldatabase (standaard gelijk aan --journal)")
    p.add_argument("--date", action="append", help="Boekingsdatum (JJJJ-MM-DD), mag herhaald worden")
    p.add_argument("--date-from", help="Vanaf datum (JJJJ-MM-DD)")
    p.add_argument("--date-to", help="Tot en met datum (JJJJ-MM-DD)")
    p.add_argument("--move", action="append", help="Specifieke boekingsnummer(s) in de bron, mag herhaald worden")
    p.add_argument("--include-draft", action="store_true", help="Ook conceptboekingen uit de bron meenemen")
    p.add_argument("--source-company", help="Bedrijf (naam of id) in de brondatabase")
    p.add_argument("--target-company", help="Bedrijf (naam of id) in de doeldatabase")
    p.add_argument("--account-map", help="CSV 'bronrekening;doelrekening' voor afwijkende rekeningnummers")
    p.add_argument("--no-partners", action="store_true", help="Partners niet overzetten")
    p.add_argument("--drop-missing-partners", action="store_true",
                   help="Onvindbare partners weglaten i.p.v. te stoppen")
    p.add_argument("--no-analytic", action="store_true", help="Analytische verdeling niet overzetten")
    p.add_argument("--apply", action="store_true", help="Boekingen effectief aanmaken (anders enkel proefrun)")
    p.add_argument("--post", action="store_true", help="Aangemaakte boekingen meteen boeken (impliceert --apply)")
    args = p.parse_args(argv)
    if args.post:
        args.apply = True
    return args


def main(argv=None):
    args = parse_args(argv)
    cfg = configparser.ConfigParser(interpolation=None)
    if not cfg.read(args.config, encoding="utf-8"):
        raise SystemExit(f"Configuratiebestand '{args.config}' niet gevonden (zie transfer.example.ini).")

    src = connect(cfg, "source", args.source_company)
    dst = connect(cfg, "target", args.target_company)
    print(f"Bron : {src.url} / {src.db} / {src.company['name']}")
    print(f"Doel : {dst.url} / {dst.db} / {dst.company['name']}")
    if src.company["currency_id"][1] != dst.company["currency_id"][1]:
        raise SystemExit("De bedrijfsmunt van bron en doel verschilt; overzetten wordt niet ondersteund.")

    src_journal = find_journal(src, args.journal)
    dst_journal = find_journal(dst, args.target_journal or args.journal)
    print(f"Dagboek: {src_journal['name']} ({src_journal['code']}) -> "
          f"{dst_journal['name']} ({dst_journal['code']})\n")

    moves = read_source_moves(src, src_journal, args)
    if not moves:
        print("Geen boekingen gevonden voor deze selectie.")
        return 0

    mapper = Mapper(src, dst, args)
    other = [m for m in moves if m["move_type"] != "entry"]
    for m in other:
        mapper.warn(f"{m['name']} is van type '{m['move_type']}' (geen diverse boeking) en wordt overgeslagen.")
    moves = [m for m in moves if m["move_type"] == "entry"]

    mapper.prepare(moves)
    check_lock_dates(dst, moves, mapper)

    plan = []
    print(f"{'Boeking':<25} {'Datum':<11} {'Lijnen':>6} {'Bedrag':>16}  Status")
    print("-" * 75)
    for move in moves:
        total = check_balanced(move, mapper)
        vals = mapper.build_move_vals(move, dst_journal["id"], src.db)
        existing = find_existing(dst, dst_journal["id"], vals)
        status = "bestaat al -> overslaan" if existing else "nieuw"
        print(f"{move['name']:<25} {move['date']:<11} {len(vals['line_ids']):>6} {total:>16,.2f}  {status}")
        if not existing:
            plan.append((move, vals))

    for w in mapper.warnings:
        print(f"WAARSCHUWING: {w}")
    if mapper.errors:
        print()
        for e in mapper.errors:
            print(f"FOUT: {e}")
        print(f"\n{len(mapper.errors)} fout(en): er wordt niets aangemaakt. Los ze op en probeer opnieuw.")
        return 1

    if not args.apply:
        print(f"\nProefrun: {len(plan)} boeking(en) zouden aangemaakt worden. Gebruik --apply om uit te voeren.")
        return 0

    created = []
    for move, vals in plan:
        new_id = dst.call("account.move", "create", [vals])[0]
        created.append(new_id)
        if args.post:
            dst.call("account.move", "action_post", [new_id])
        name = dst.read("account.move", [new_id], ["name"])[0]["name"]
        print(f"Aangemaakt: {move['name']} -> {name} (id {new_id})")

    state = "geboekt" if args.post else "als concept aangemaakt"
    print(f"\n{len(created)} boeking(en) {state} in {dst.db}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except xmlrpc.client.Fault as exc:
        sys.exit(f"Odoo-fout: {exc.faultString.strip().splitlines()[-1]}")
