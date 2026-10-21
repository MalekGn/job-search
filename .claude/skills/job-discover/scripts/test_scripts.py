#!/usr/bin/env python3
"""Offline tests for the job-discover scripts. Run: python3 -m unittest test_scripts (from scripts/)."""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ats  # noqa: E402
import common  # noqa: E402
import config  # noqa: E402
import discover  # noqa: E402
import merge  # noqa: E402
import regions  # noqa: E402
import tracker  # noqa: E402
import verify_links  # noqa: E402
from ats import recruitee, teamtailor  # noqa: E402
from sources import companies, france_travail, free_work  # noqa: E402

TODAY = common.today_local()


def search_params(**kw) -> common.SearchParams:
    return common.SearchParams(**{"keywords": ["java"], "since": TODAY - datetime.timedelta(days=30), **kw})


class CommonTest(unittest.TestCase):
    def test_published_on_or_after_handles_dates_and_datetimes(self):
        self.assertTrue(common.published_on_or_after(TODAY.isoformat(), TODAY))
        self.assertTrue(common.published_on_or_after(common.local_midnight(TODAY).isoformat(), TODAY))
        late_yesterday = common.local_midnight(TODAY) - datetime.timedelta(minutes=1)
        self.assertFalse(common.published_on_or_after(late_yesterday.isoformat(), TODAY))
        self.assertFalse(common.published_on_or_after("", TODAY))

    def test_retries_server_errors_but_not_404(self):
        calls = []

        def flaky(req, timeout):
            calls.append(1)
            if len(calls) < 3:
                raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, None)
            return mock.MagicMock(**{"__enter__.return_value.getcode.return_value": 200,
                                     "__enter__.return_value.read.return_value": b'{"ok": 1}',
                                     "__enter__.return_value.headers": {}})
        with mock.patch.object(common.urllib.request, "urlopen", flaky), mock.patch.object(common.time, "sleep"):
            self.assertEqual(common.http_get_json("https://x"), (200, {"ok": 1}))
        self.assertEqual(len(calls), 3)

        def not_found(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        calls.clear()
        with mock.patch.object(common.urllib.request, "urlopen", not_found):
            self.assertEqual(common.http_get_json("https://x"), (404, None))
        self.assertEqual(len(calls), 1)

    def test_merge_by_id_accumulates_keywords_and_nearby(self):
        a = common.posting(company="A", title="T", url="u", source="s", source_job_id="1")
        merged = common.merge_by_id([("java", a), ("ged", a | {"nearby": True})])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["matched_keywords"], ["java", "ged"])
        self.assertTrue(merged[0]["nearby"])


class ConfigTest(unittest.TestCase):
    def test_project_copy_is_created_once_and_wins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            created = config.ensure_project_config(root)
            self.assertEqual(len(created), 3)
            self.assertEqual(config.ensure_project_config(root), [])
            path = root / "config" / "sources.json"
            path.write_text(json.dumps({"sources": [{"id": "custom"}]}))
            self.assertEqual(config.load_config("sources.json", root)["sources"][0]["id"], "custom")

    def test_default_config_references_existing_modules(self):
        cfg = config.load_config("sources.json", Path("/nonexistent"))
        scripts = Path(__file__).resolve().parent
        for s in cfg["sources"]:
            if s["type"] == "script":
                self.assertTrue((scripts / "sources" / f"{s['id']}.py").exists(), s["id"])
            else:
                self.assertTrue(s.get("queries"), s["id"])
        for name in config.load_config("ats.json", Path("/nonexistent"))["probe_order"]:
            self.assertTrue((scripts / "ats" / f"{name}.py").exists(), name)


class SelectionTest(unittest.TestCase):
    SOURCES = [
        {"id": "it_fr", "active": True, "countries": ["FR"], "domains": ["it"], "contracts": ["freelance"]},
        {"id": "all", "active": True, "countries": ["*"], "domains": ["*"], "contracts": ["permanent", "freelance"]},
        {"id": "off", "active": False, "countries": ["*"], "domains": ["*"], "contracts": ["permanent"]},
    ]

    def ids(self, country="", domain="", contracts=(), sources=None):
        args = mock.Mock(country=country, domain=domain, contracts=list(contracts), sources=sources)
        return [s["id"] for s in discover.select(self.SOURCES, args)]

    def test_filters_by_activity_country_domain_and_contract(self):
        self.assertEqual(self.ids(), ["it_fr", "all"])
        self.assertEqual(self.ids(country="BE"), ["all"])
        self.assertEqual(self.ids(domain="health"), ["all"])
        self.assertEqual(self.ids(contracts=["permanent"]), ["all"])
        self.assertEqual(self.ids(sources=["it_fr"]), ["it_fr"])


class CompaniesTest(unittest.TestCase):
    def setUp(self):
        self.inc = companies.build_pattern(["java", "tech lead", "alfresco"])
        self.exc = companies.build_pattern(["stage", "alternance"])

    def job(self, title, departments=()):
        return {"title": title, "departments": list(departments)}

    def test_title_filter(self):
        self.assertTrue(companies.matches(self.job("Développeur Java Senior"), self.inc, self.exc))
        self.assertTrue(companies.matches(self.job("Tech-Lead Backend"), self.inc, self.exc))
        self.assertTrue(companies.matches(self.job("Ingénieur GED", ["Alfresco"]), self.inc, self.exc))
        self.assertFalse(companies.matches(self.job("JavaScript Developer"), self.inc, self.exc))
        self.assertFalse(companies.matches(self.job("Stage développeur Java"), self.inc, self.exc))

    def run_search(self, company_list, fetchers):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "output").mkdir()
            path = root / "output" / "companies.json"
            path.write_text(json.dumps({"companies": company_list}))
            with mock.patch.object(companies.ats, "load", lambda names: fetchers):
                result = companies.search(search_params(project_root=root))
            return result, json.loads(path.read_text())

    def empty_fetchers(self):
        return {name: (lambda b: []) for name in ("greenhouse", "lever", "recruitee")}

    def test_probe_finds_ats_and_caches_mapping(self):
        fetchers = self.empty_fetchers()
        fetchers["recruitee"] = lambda b: [ats.job(title="Java Engineer", url="https://x/1", location="Paris",
                                                   departments=[], updated_at=TODAY.isoformat(), source="recruitee")]
        result, cfg = self.run_search([{"slug": "acme", "display": "Acme", "ats": None}], fetchers)
        self.assertEqual([r["company"] for r in result["roles"]], ["Acme"])
        self.assertEqual((cfg["companies"][0]["ats"], cfg["companies"][0]["confidence"]), ("recruitee", "probe_verified"))

    def test_unknown_company_switches_to_web_and_is_skipped_next_time(self):
        result, cfg = self.run_search([{"slug": "bigco", "ats": None}], self.empty_fetchers())
        self.assertEqual(cfg["companies"][0]["ats"], "web")
        self.assertEqual(result["web_companies"][0]["slug"], "bigco")
        result2, _ = self.run_search(cfg["companies"], self.empty_fetchers())
        self.assertEqual(result2["companies_polled"], 0)

    def test_broken_mapped_ats_is_kept_with_warning(self):
        result, cfg = self.run_search([{"slug": "acme", "ats": "lever"}], self.empty_fetchers())
        self.assertEqual(cfg["companies"][0]["ats"], "lever")
        self.assertEqual(len(result["warnings"]), 1)

    def test_missing_company_file_is_a_warning(self):
        with tempfile.TemporaryDirectory() as d:
            result = companies.search(search_params(project_root=Path(d)))
        self.assertIn("No followed companies", result["warnings"][0])


class AtsAdapterTest(unittest.TestCase):
    def test_date_parsers(self):
        self.assertEqual(recruitee._date("2026-10-15 09:31:36 UTC"), "2026-10-15T09:31:36+00:00")
        self.assertTrue(teamtailor._rfc822_to_iso("Wed, 14 Oct 2026 14:33:33 +0200").startswith("2026-10-14T14:33:33"))


PUBLIC_PAGE = """
<ul class="result-list list-unstyled" id="page_0-19">
<li data-id-offre="7092816" class="result"><a href="/offres/recherche/detail/7092816">
<h2 class="t4 media-heading"><span class="media-heading-title">Pilote GED Alfresco - Freelance (H/F)</span></h2>
<p translate="no" class="subtext"> Collective.work - <span>75 - Paris</span></p>
<p class="description">Taux journalier (TJM): 524&euro; maximum</p>
<p class="date"> Publié il y a 3 jours </p>
<div class="media-right"><p class="contrat">Profession libérale<span class="type-contrat">Non renseigné</span></p></div>
</a></li>
<li data-id-offre="200ABCD" class="result"><a href="/offres/recherche/detail/200ABCD">
<span class="media-heading-title">Développeur Java</span>
<p translate="no" class="subtext"> <span>95 - Cergy</span></p>
<p class="date"> Publié aujourd'hui </p>
<p class="contrat">CDI<span class="type-contrat">Temps plein</span></p>
</a></li>
</ul>"""


class FranceTravailTest(unittest.TestCase):
    def no_keys(self):
        return mock.patch.dict(os.environ, {"FT_CLIENT_ID": "", "FT_CLIENT_SECRET": ""})

    def test_parse_public_page(self):
        a, b = france_travail.parse_public_page(PUBLIC_PAGE)
        self.assertEqual((a["company"], a["location"], a["contracts"]), ("Collective.work", "75 - Paris", ["freelance"]))
        self.assertEqual(a["published_at"], (TODAY - datetime.timedelta(days=3)).isoformat())
        self.assertIn("524€", a["description"])
        self.assertEqual(a["url"], "https://candidat.francetravail.fr/offres/recherche/detail/7092816")
        self.assertEqual((b["company"], b["contracts"], b["published_at"]),
                         ("(not disclosed)", ["permanent"], TODAY.isoformat()))

    def test_window_covers_cutoff(self):
        self.assertEqual(france_travail.window_for(TODAY), 1)
        self.assertEqual(france_travail.window_for(TODAY - datetime.timedelta(days=5)), 7)
        self.assertEqual(france_travail.window_for(TODAY - datetime.timedelta(days=90)), 31)

    def test_without_keys_uses_public_site_and_filters_dates_and_contracts(self):
        fake = lambda kw, dep, w, c, p, warn: france_travail.parse_public_page(PUBLIC_PAGE)  # noqa: E731
        with self.no_keys(), mock.patch.object(france_travail, "search_public", fake):
            today_only = france_travail.search(search_params(since=TODAY))
            freelance = france_travail.search(search_params(keywords=["alfresco", "ged"], contracts=["freelance"]))
        self.assertEqual(today_only["mode"], "public")
        self.assertIn("public site", today_only["warnings"][0])
        self.assertEqual([r["source_job_id"] for r in today_only["roles"]], ["200ABCD"])
        self.assertEqual([r["source_job_id"] for r in freelance["roles"]], ["7092816"])
        self.assertEqual(freelance["roles"][0]["matched_keywords"], ["alfresco", "ged"])

    def test_base_department_is_searched_separately_and_flagged(self):
        searched = []

        def fake(kw, dep, w, cutoff, p, warn):
            searched.append(dep)
            return france_travail.parse_public_page(PUBLIC_PAGE)[1:] if dep == "95" else []
        with self.no_keys(), mock.patch.object(france_travail, "search_public", fake):
            r = france_travail.search(search_params(base={"department": "95"}))
        self.assertEqual(searched, [None, "95"])
        self.assertTrue(r["roles"][0]["nearby"])

    def test_public_search_stops_at_cutoff_and_warns_on_page_cap(self):
        def page(n, label):
            return "".join(f'<li data-id-offre="{n}{i}" class="result"><p class="date"> {label} </p></li>'
                           for i in range(france_travail.PAGE_SIZE))
        pages = iter([page("A", "Publié aujourd'hui"), page("B", "Publié il y a 20 jours")])
        with mock.patch.object(france_travail, "fetch_public", lambda params: next(pages)):
            warnings = []
            out = france_travail.search_public("java", None, 1, TODAY, 5, warnings)
        self.assertEqual(len(out), 2 * france_travail.PAGE_SIZE)  # 2nd page is older: stop
        self.assertEqual(warnings, [])
        with mock.patch.object(france_travail, "fetch_public", lambda params: page("C", "Publié aujourd'hui")), \
                mock.patch.object(france_travail.time, "sleep"):
            warnings = []
            france_travail.search_public("java", None, 1, TODAY, 2, warnings)
            self.assertIn("exceeds 300 results (page cap)", warnings[0])
            warnings = []
            france_travail.search_public("java", None, 1, TODAY, 99, warnings)
            self.assertIn("exceeds 750 results (site limit)", warnings[0])

    def test_failed_keywords_are_reported(self):
        def fake(kw, dep, w, cutoff, p, warnings):
            if kw == "tech lead":
                warnings.append(f"France Travail (public site): error for \"{kw}\"  (HTTP 500)")
                return []
            return france_travail.parse_public_page(PUBLIC_PAGE)
        with self.no_keys(), mock.patch.object(france_travail, "search_public", fake):
            r = france_travail.search(search_params(keywords=["java", "tech lead"]))
        self.assertEqual(r["failed_keywords"], ["tech lead"])
        self.assertTrue(r["roles"])

    def test_normalize_api_falls_back_to_detail_url(self):
        o = {"id": "123ABC", "intitule": "Développeur Java", "typeContrat": "LIB",
             "lieuTravail": {"libelle": "95 - Cergy"}, "entreprise": {}}
        n = france_travail.normalize_api(o)
        self.assertTrue(n["url"].endswith("/123ABC"))
        self.assertEqual((n["location"], n["contracts"]), ("95 - Cergy", ["freelance"]))


class FreeWorkTest(unittest.TestCase):
    def posting(self, id_, contracts, published, **kw):
        return {"id": id_, "slug": f"offre-{id_}", "title": f"Offre {id_}", "status": "published",
                "contracts": contracts, "publishedAt": published, "createdAt": published,
                "job": {"slug": "developpeur-java"}, "company": {"name": "ACME"},
                "location": {"label": "Paris, France"}, **kw}

    def fake_api(self, pages_by_keyword):
        def fake(url, **kw):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            return 200, {"hydra:member": pages_by_keyword.get(q["searchKeywords"], []), "hydra:view": {}}
        return fake

    def run_fw(self, api, **kw):
        with mock.patch.object(free_work, "http_get_json", self.fake_api(api)):
            return free_work.search(search_params(**kw))

    def test_merges_keywords_and_filters_old_expired_and_internships(self):
        now = datetime.datetime.now().astimezone()
        recent = (now - datetime.timedelta(days=2)).isoformat()
        old = (now - datetime.timedelta(days=90)).isoformat()
        past = (now - datetime.timedelta(days=1)).isoformat()
        api = {
            "java": [self.posting(1, ["contractor"], recent, dailySalary="500-600 €"),
                     self.posting(2, ["permanent"], old),
                     self.posting(3, ["internship"], recent),
                     self.posting(4, ["contractor"], recent, expiredAt=past)],
            "alfresco": [self.posting(1, ["contractor"], recent, dailySalary="500-600 €")],
        }
        r = self.run_fw(api, keywords=["java", "alfresco"])
        self.assertEqual([x["source_job_id"] for x in r["roles"]], ["1"])
        role = r["roles"][0]
        self.assertEqual((role["matched_keywords"], role["contracts"], role["daily_rate"]),
                         (["java", "alfresco"], ["freelance"], "500-600 €"))
        self.assertEqual(role["url"], "https://www.free-work.com/fr/tech-it/job-mission/developpeur-java/offre-1")

    def test_since_today_and_republished(self):
        now = datetime.datetime.now().astimezone()
        today = now.replace(hour=0, minute=5).isoformat()
        yesterday = (now - datetime.timedelta(days=1)).replace(hour=23, minute=59).isoformat()
        old = (now - datetime.timedelta(days=2)).isoformat()
        api = {"java": [self.posting(1, ["contractor"], today, createdAt=old),
                        self.posting(2, ["contractor"], today),
                        self.posting(3, ["contractor"], yesterday)]}
        r = self.run_fw(api, since=TODAY)
        self.assertEqual({x["source_job_id"]: x["republished"] for x in r["roles"]}, {"1": True, "2": False})
        self.assertEqual(r["roles"][0]["source_job_id"], "2")  # genuinely new postings first

    def test_contract_filter(self):
        now = datetime.datetime.now().astimezone().isoformat()
        api = {"java": [self.posting(1, ["contractor"], now), self.posting(2, ["permanent"], now)]}
        self.assertEqual([x["source_job_id"] for x in self.run_fw(api, contracts=["permanent"])["roles"]], ["2"])

    def test_failed_keywords_are_reported(self):
        def fake(url, **kw):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            return (500, None) if q["searchKeywords"] == "kafka" else (200, {"hydra:member": [], "hydra:view": {}})
        with mock.patch.object(free_work, "http_get_json", fake):
            r = free_work.search(search_params(keywords=["java", "kafka"]))
        self.assertEqual(r["failed_keywords"], ["kafka"])

    def test_excerpt_strips_html(self):
        self.assertEqual(free_work.excerpt("<p>Java &amp; <b>Spring</b></p>"), "Java & Spring")


class TrackerTest(unittest.TestCase):
    def test_url_normalization(self):
        self.assertEqual(tracker.normalize_url("https://Free-Work.com/mission/123/?utm_source=x&id=4"),
                         "https://free-work.com/mission/123?id=4")

    def test_add_dedupes_on_normalized_url(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tracker.csv"
            row = {"company": "A", "role": "Java", "contract": "permanent", "url": "https://a.fr/job/1"}
            self.assertTrue(tracker.add(path, row))
            self.assertFalse(tracker.add(path, dict(row, url="https://a.fr/job/1/?utm_medium=mail")))
            self.assertEqual(len(tracker.read_rows(path)), 1)

    def test_set_status_updates_matching_row_only(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tracker.csv"
            tracker.add(path, {"company": "A", "url": "https://a.fr/job/1", "status": "to review"})
            tracker.add(path, {"company": "B", "url": "https://b.fr/job/2", "status": "to review"})
            self.assertTrue(tracker.set_status(path, "https://a.fr/job/1/?utm_source=x", "applied", "sent CV"))
            self.assertFalse(tracker.set_status(path, "https://c.fr/job/3", "applied"))
            rows = tracker.read_rows(path)
            self.assertEqual([(r["status"], r["notes"]) for r in rows], [("applied", "sent CV"), ("to review", "")])


class RunLogTest(unittest.TestCase):
    PERIODS = {"default_period_days": 7, "widen_below": 3, "widen_to_days": 14}

    def test_since_last_uses_previous_run_or_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "runs.csv"
            since, note = discover.resolve_since("last", self.PERIODS, log)
            self.assertEqual(since, TODAY - datetime.timedelta(days=6))
            self.assertIn("No previous run", note)
            discover.log_run(log, {"date": "2026-10-01T09:00:00+02:00", "since": "2026-09-01"})
            discover.log_run(log, {"date": "2026-10-12T18:30:00+02:00", "since": "2026-10-01"})
            self.assertEqual(discover.resolve_since("last", self.PERIODS, log)[0], datetime.date(2026, 10, 12))
            self.assertEqual(discover.resolve_since("2026-10-15", self.PERIODS, log), (datetime.date(2026, 10, 15), ""))

    def test_keyword_sources_restricts_a_keyword_to_some_sources(self):
        restrict = discover.parse_keyword_sources(["Activiti=free_work", "GED = free_work, france_travail"])
        self.assertEqual(restrict, {"Activiti": {"free_work"}, "GED": {"free_work", "france_travail"}})
        kws = ["Java", "Activiti", "GED"]
        self.assertEqual(discover.keywords_for("france_travail", kws, restrict), ["Java", "GED"])
        self.assertEqual(discover.keywords_for("free_work", kws, restrict), kws)
        with self.assertRaises(ValueError):
            discover.parse_keyword_sources(["Activiti"])

    def test_rerun_suffix_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.assertEqual(discover.run_suffix(d, ["free_work", "france_travail"]), "")
            (d / "_raw_france_travail.json").write_text("{}")
            self.assertEqual(discover.run_suffix(d, ["france_travail"]), "-2")
            self.assertEqual(discover.run_suffix(d, ["free_work"]), "")  # another source: no clash
            (d / "_summary.json").write_text("{}")
            self.assertEqual(discover.run_suffix(d, ["free_work"]), "-2")

    def test_default_and_widen_come_from_config(self):
        self.assertEqual(discover.resolve_since("default", self.PERIODS)[0], TODAY - datetime.timedelta(days=6))
        self.assertEqual(discover.resolve_since("widen", self.PERIODS)[0], TODAY - datetime.timedelta(days=13))
        custom = dict(self.PERIODS, default_period_days=1)
        self.assertEqual(discover.resolve_since("default", custom)[0], TODAY)
        defaults = config.load_config("search.json", Path("/nonexistent"))
        self.assertFalse(defaults["confirmed"])


class MergeTest(unittest.TestCase):
    def write_raw(self, d: Path, source: str, roles: list[dict], **extra) -> None:
        (d / f"_raw_{source}.json").write_text(json.dumps({"source": source, "since": "2026-10-01",
                                                           "roles": roles, **extra}))

    def role(self, url, source, **kw):
        return common.posting(company=kw.pop("company", "ACME"), title=kw.pop("title", "Java Developer"), url=url,
                              source=source, published_at=kw.pop("published_at", "2026-10-10"), **kw)

    def test_dedupes_marks_seen_and_presorts(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            track = d / "tracker.csv"
            tracker.add(track, {"company": "Old", "url": "https://old.fr/1", "status": "applied"})
            self.write_raw(d, "free_work", [
                self.role("https://fw.fr/1", "free_work", title="Java Developer", matched_keywords=["java"],
                          pay="600 €"),
                self.role("https://fw.fr/2", "free_work", title="Java Engineer", matched_keywords=["java", "spring"],
                          republished=True),
                self.role("https://fw.fr/3", "free_work", title="Java Lead", matched_keywords=["java"],
                          published_at="2026-10-12"),
                self.role("https://old.fr/1", "free_work", matched_keywords=["java"]),
            ], warnings=["Free-Work: something"])
            self.write_raw(d, "web", [
                self.role("https://fw.fr/1/?utm_source=google", "web", matched_keywords=["spring"]),
                self.role("https://wttj.fr/9", "web", published_at=""),
            ])
            r = merge.merge(d, track, top=2)
        self.assertEqual(r["counts"]["total"], 5)
        self.assertEqual([c["url"] for c in r["candidates"]], ["https://fw.fr/1", "https://fw.fr/3"])
        self.assertEqual(r["candidates"][0]["matched_keywords"], ["java", "spring"])  # merged with the web copy
        self.assertEqual(r["candidates"][0]["pay"], "600 €")                         # script version kept
        self.assertEqual([o["url"] for o in r["others"]], ["https://fw.fr/2"])         # republished goes last
        self.assertEqual(r["already_seen"][0]["status"], "applied")
        self.assertEqual(r["unknown_date"][0]["url"], "https://wttj.fr/9")
        self.assertEqual(r["warnings"], ["Free-Work: something"])

    def test_ranking_prefers_title_matches_nearby_and_groups_series(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            series = [self.role(f"https://ft.fr/s{i}", "france_travail", company="(not disclosed)",
                                title="Tech Lead Java (H/F)", matched_keywords=["tech lead", "lead java", "tech lead java"])
                      for i in range(5)]
            self.write_raw(d, "france_travail", series + [
                self.role("https://ft.fr/near", "france_travail", company="Scalian", title="Développeur Java Senior",
                          location="95 - Cergy", matched_keywords=["java"]),
                self.role("https://ft.fr/neighbour", "france_travail", company="Safran", title="Développeur Java",
                          location="78 - Magny-les-Hameaux", matched_keywords=["java"]),
                self.role("https://ft.fr/text-only", "france_travail", company="Acme", title="Ingénieur logiciel",
                          location="13 - Marseille", matched_keywords=["java", "spring", "kafka"]),
            ])
            r = merge.merge(d, d / "tracker.csv", top=3, near=["78"], home=["95", "Cergy"], country="FR")
        urls = [c["url"] for c in r["candidates"]]
        self.assertEqual(urls[0], "https://ft.fr/s0")                       # 3 title words, counted once each
        self.assertEqual(r["candidates"][0]["same_title"], [f"https://ft.fr/s{i}" for i in range(1, 5)])
        self.assertEqual(set(urls[1:]), {"https://ft.fr/near", "https://ft.fr/neighbour"})  # nearby via --near
        self.assertTrue(all(c["nearby"] for c in r["candidates"][1:]))
        self.assertEqual([o["url"] for o in r["others"]], ["https://ft.fr/text-only"])  # keywords only in the text

    def test_rerun_files_are_added_up_and_widened_postings_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.write_raw(d, "france_travail", [self.role("https://ft.fr/1", "france_travail", title="Java Dev")])
            (d / "_raw_france_travail-2.json").write_text(json.dumps({"source": "france_travail", "since": "2026-09-20",
                "roles": [self.role("https://ft.fr/2", "france_travail", title="Java Lead", published_at="2026-09-25"),
                          self.role("https://ft.fr/1", "france_travail", title="Java Dev")]}))
            r = merge.merge(d, d / "tracker.csv", top=10)
        self.assertEqual(r["postings_by_source"], {"france_travail": 3})
        self.assertEqual(r["since"], "2026-10-01")
        flags = {c["url"]: c.get("outside_period", False) for c in r["candidates"]}
        self.assertEqual(flags, {"https://ft.fr/1": False, "https://ft.fr/2": True})

    def test_generic_words_count_less_and_home_postings_are_kept(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            filler = [self.role(f"https://x.fr/{i}", "france_travail", company=f"Co{i}", title=f"Développeur Java {i}",
                                location="69 - Lyon", matched_keywords=["développeur java"]) for i in range(30)]
            self.write_raw(d, "france_travail", filler + [
                self.role("https://x.fr/leader", "france_travail", company="Safran", title="Leader technique Java",
                          location="31 - Toulouse", matched_keywords=["leader technique", "développeur java"]),
                self.role("https://x.fr/home", "france_travail", company="Scalian", title="Développeur Java",
                          location="95 - Cergy", matched_keywords=["développeur java"]),
            ])
            r = merge.merge(d, d / "tracker.csv", top=1, home=["95"], country="FR")
        self.assertEqual([c["url"] for c in r["candidates"]], ["https://x.fr/leader", "https://x.fr/home"])
        self.assertTrue(r["candidates"][1]["home"])
        self.assertEqual(r["candidates"][1]["region"], "Île-de-France")
        self.assertEqual(r["new_by_region"]["Auvergne-Rhône-Alpes"], 30)

    def test_ambiguous_keyword_is_flagged_per_source_and_its_noise_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            noise = [self.role(f"https://ft.fr/n{i}", "france_travail", company=f"Co{i}", title=f"Animateur d'activités {i}",
                               matched_keywords=["Activiti"]) for i in range(25)]
            kafka = [self.role(f"https://ft.fr/k{i}", "france_travail", company=f"K{i}", title=f"Développeur {i}",
                               description="Java, Kafka" if i % 3 == 0 else "Java", matched_keywords=["Kafka"])
                     for i in range(30)]  # a third contain it: low share, but a real keyword
            self.write_raw(d, "france_travail", noise + kafka + [
                self.role("https://ft.fr/both", "france_travail", company="B", title="Développeur Java",
                          matched_keywords=["Activiti", "Java"]),
                self.role("https://ft.fr/real", "france_travail", company="R", title="Ingénieur BPM",
                          description="Workflows Activiti et Camunda", matched_keywords=["Activiti"]),
            ])
            self.write_raw(d, "free_work", [self.role("https://fw.fr/a", "free_work", title="Dev Activiti",
                                                      matched_keywords=["Activiti"])])
            r = merge.merge(d, d / "tracker.csv", top=100)
        self.assertEqual([(f["keyword"], f["source"], f["dropped"]) for f in r["ambiguous_keywords"]],
                         [("Activiti", "france_travail", 25)])
        self.assertEqual(r["counts"]["dropped_ambiguous"], 25)
        urls = {o["url"] for o in r["candidates"] + r["others"]}
        self.assertTrue({"https://ft.fr/both", "https://ft.fr/real", "https://fw.fr/a", "https://ft.fr/k0"} <= urls)
        self.assertFalse(any(u.startswith("https://ft.fr/n") for u in urls))

    def test_flags_near_identical_titles(self):
        candidates = [{"url": "a", "title": "Développeur Java Spring (H/F)"},
                      {"url": "b", "title": "Développeur Java/Spring - F/H"},
                      {"url": "c", "title": "Chef de projet GED"}]
        self.assertEqual(merge.possible_duplicates(candidates), [["a", "b"]])


class RegionsTest(unittest.TestCase):
    def test_region_from_department_code_name_or_remote(self):
        self.assertEqual(regions.region_of("78 - Magny-les-Hameaux", country="FR"), "Île-de-France")
        self.assertEqual(regions.region_of("2A - Ajaccio", country="FR"), "Corse")
        self.assertEqual(regions.region_of("Nice, Provence-Alpes-Côte d'Azur, France", country="FR"),
                         "Provence-Alpes-Côte d'Azur")
        self.assertEqual(regions.region_of("Paris, France"), "Île-de-France")
        self.assertEqual(regions.region_of("France", remote="full", country="FR"), regions.REMOTE)
        self.assertEqual(regions.region_of("", country="FR"), regions.UNKNOWN)


class VerifyLinksTest(unittest.TestCase):
    def test_flags_links_missing_from_run_data(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "_raw_free_work.json").write_text(json.dumps({"roles": [{"url": "https://fw.fr/1"}]}))
            track = d / "tracker.csv"
            tracker.add(track, {"company": "Old", "url": "https://old.fr/1"})
            report = ("[A](https://fw.fr/1/?utm_source=x) [B](https://old.fr/1) "
                      "[C](https://invented.fr/42) <https://francetravail.io>")
            self.assertEqual(verify_links.unknown_links(report, d, track, []),
                             ["https://invented.fr/42", "https://francetravail.io"])
            self.assertEqual(verify_links.unknown_links(report, d, track, ["https://francetravail.io"]),
                             ["https://invented.fr/42"])


if __name__ == "__main__":
    unittest.main()
