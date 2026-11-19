import ast
import base64
import json
import re
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from awsdraw.adapters import json_spec, svg_preview, web_ui  # noqa: E402
from awsdraw.adapters.drawio_renderer import DrawioRenderer  # noqa: E402
from awsdraw.adapters.fs_installer import EXTENSION_ID, FsInstaller  # noqa: E402
from awsdraw.adapters.llm_anthropic import AnthropicPlanner  # noqa: E402
from awsdraw.adapters.llm_github import GithubModelsPlanner  # noqa: E402
from awsdraw.adapters.vscode_opener import VsCodeOpener  # noqa: E402
from awsdraw.application.use_cases import CollectRequirements, GenerateDiagram, PlanAndGenerate  # noqa: E402
from awsdraw.domain import agents, agents_layout, c4, capabilities, catalog, layout, overview, system_design  # noqa: E402
from awsdraw.domain.errors import SpecError  # noqa: E402
from awsdraw.domain.models import Architecture, Component, Flow, Requirements  # noqa: E402
from awsdraw.domain.planner import RulePlanner  # noqa: E402
from awsdraw.domain.rules import validate  # noqa: E402

VERIFIED = {ln.split("\t")[0] for ln in (ROOT / "tests/fixtures/aws4-icons.txt").read_text().splitlines() if ln and not ln.startswith("#")}


def gen(arch):
    return GenerateDiagram(DrawioRenderer())(arch)


def codes(arch):
    return {f.code for f in validate(arch)}


class CatalogTests(unittest.TestCase):
    def test_every_resource_icon_exists_in_drawio_library(self):
        missing = [s.key for s in catalog.SERVICES.values() if s.kind == "resource" and s.shape not in VERIFIED]
        self.assertEqual(missing, [])

    def test_aliases_point_to_real_services(self):
        self.assertEqual([a for a, k in catalog.ALIASES.items() if k not in catalog.SERVICES], [])

    def test_lookup_and_suggestions(self):
        self.assertEqual(catalog.lookup("API-Gateway").key, "api_gateway")
        self.assertIn("dynamodb", catalog.suggestions("dynamodbb"))


class CapabilityTests(unittest.TestCase):
    def test_every_service_has_a_plain_language_capability(self):
        self.assertEqual([k for k in catalog.SERVICES if k not in capabilities.CAPABILITY_OF], [])
        self.assertEqual([c for c in capabilities.CAPABILITY_OF.values() if c not in capabilities.CAPABILITIES], [])

    def test_blocks_cover_all_non_support_capabilities(self):
        for cap in capabilities.CAPABILITIES.values():
            self.assertEqual(capabilities.block_of(cap.key) is None, cap.column == capabilities.SUPPORT, cap.key)

    def test_overview_merges_and_orders_story_left_to_right(self):
        arch = json_spec.load(str(ROOT / "examples/containers-three-tier.json"))
        ov = overview.build(arch)
        cols = {b.key: b.column for b in ov.boxes}
        pairs = [(cols[l.source], cols[l.target]) for l in ov.links]
        self.assertEqual(pairs, sorted(pairs))
        self.assertTrue(any(b.key == "monitoring" for b in ov.support))


class SystemDesignTests(unittest.TestCase):
    def test_every_service_maps_to_a_generic_kind(self):
        self.assertEqual([k for k in catalog.SERVICES if k not in system_design.KIND_OF], [])
        self.assertEqual([k for k in system_design.KIND_OF.values() if k not in system_design.KINDS], [])

    def test_labels_are_vendor_neutral(self):
        vendors = {s.label.lower() for s in catalog.SERVICES.values() if s.tier != "actors"}
        for name, res in RendererTests().render_all():
            page = list(ET.fromstring(res.xml.split("?>", 1)[1]).iter("diagram"))[0]
            text = " ".join((c.get("value") or "") for c in page.iter("mxCell") if c.get("vertex") and c.get("id") not in ("title", "subtitle", "legend")).lower()
            self.assertFalse([v for v in vendors if re.search(rf"(?<!\w){re.escape(v)}(?!\w)", text)], f"{name}: vendor name in system design page")

    def test_generic_label_strips_vendor_parentheses(self):
        from awsdraw.domain.models import Component
        self.assertEqual(system_design.generic_label(Component("a", "lambda", "Lógica del negocio (Lambda)")), "Lógica del negocio")
        self.assertEqual(system_design.generic_label(Component("a", "cloudfront", "CloudFront")), "CDN (red de entrega)")
        self.assertEqual(system_design.generic_label(Component("a", "dynamodb", "")), "Base de datos")
        self.assertEqual(system_design.generic_label(Component("a", "aurora", "Aurora (SQL)")), "Base de datos (SQL)")
        self.assertEqual(system_design.generic_label(Component("a", "s3", "Uploads (S3)")), "Uploads")

    def test_same_column_feeders_are_adjacent_and_skip_arcs_avoid_boxes(self):
        arch = RulePlanner().plan(Requirements("web con login, sql, colas, correo"))
        lay = layout.compute(arch)
        rows = {n.component.id: (n.column, n.rect.y) for n in lay.nodes}
        self.assertLess(rows["queue"][1] - rows["compute"][1], 2 * layout.ROW_H)
        for f in arch.flows:
            if layout.skips_over(lay.nodes, f.source, f.target):
                self.assertGreaterEqual(rows[f.target][0] - rows[f.source][0], 2)


class AgentProfileTests(unittest.TestCase):
    TEXT = "Un agente de soporte con MCP que consulta documentos (RAG) y un sitio web"

    def setUp(self):
        self.arch = RulePlanner().plan(Requirements(self.TEXT, ()))

    def test_planner_detects_agents_and_general_stays_general(self):
        self.assertEqual(self.arch.profile, "agents")
        self.assertTrue(agents.is_agentic(self.arch))
        self.assertFalse(agents.is_agentic(RulePlanner().plan(Requirements("Tienda web con pagos", ()))))

    def test_classification_covers_zones(self):
        zones = agents.classify(self.arch).zones
        for role in ("agent", "model", "memory_short", "memory_long", "tool_service"):
            self.assertTrue(zones[role], role)

    def test_every_component_lands_in_exactly_one_zone(self):
        zones = agents.classify(self.arch).zones
        placed = [c.id for cs in zones.values() for c in cs]
        self.assertEqual(sorted(placed), sorted(c.id for c in self.arch.components))

    def test_agent_inferred_when_not_declared(self):
        arch = Architecture("x", (Component("u", "users"), Component("c", "lambda"), Component("m", "bedrock")), (Flow("c", "m"),), profile="agents")
        self.assertEqual([c.id for c in agents.classify(arch).zones["agent"]], ["c"])

    def test_layout_has_no_overlapping_items_and_page_one_is_agentic(self):
        lay = agents_layout.compute(agents.classify(self.arch))
        rs = [i.rect for i in lay.items]
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                self.assertFalse(a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h)
        xml = DrawioRenderer().render(self.arch, layout.compute(self.arch))
        first = ET.fromstring(xml).find("diagram")
        self.assertIn("agentes", first.get("name") + ET.tostring(first, encoding="unicode"))
        self.assertIn("Entorno de ejecución del agente", xml)

    def test_agent_page_is_vendor_neutral(self):
        lay = agents_layout.compute(agents.classify(self.arch))
        text = " ".join(i.label + i.note for i in lay.items).lower()
        for word in ("bedrock", "lambda", "dynamodb", "opensearch", "fargate"):
            self.assertNotIn(word, text)

    def test_json_spec_roundtrip_role_and_profile(self):
        spec = {"title": "t", "profile": "agents", "components": [{"id": "a", "service": "lambda", "role": "agent"}], "flows": []}
        arch = json_spec.parse(spec)
        self.assertEqual((arch.profile, arch.components[0].role), ("agents", "agent"))


class C4Tests(unittest.TestCase):
    def setUp(self):
        self.arch = RulePlanner().plan(Requirements("Tienda web con login, notificaciones por correo y cola de tareas", ()))
        self.lay = layout.compute(self.arch)

    def test_context_has_person_system_and_external(self):
        v = c4.context(self.arch)
        types = [b.type for b in v.boxes]
        self.assertIn(c4.PERSON, types)
        self.assertEqual(types.count(c4.SYSTEM), 1)
        self.assertIn(c4.EXTERNAL, types)
        ids = {b.id for b in v.boxes}
        self.assertTrue(all(r.source in ids and r.target in ids for r in v.rels))

    def test_containers_inside_boundary_and_no_support(self):
        v = c4.containers(self.arch, self.lay)
        self.assertNotIn("monitor", {b.id for b in v.boxes})
        _, r = v.boundary
        for b in v.boxes:
            if b.type != c4.PERSON:
                self.assertTrue(r.x <= b.rect.x and b.rect.x + b.rect.w <= r.x + r.w and r.y <= b.rect.y and b.rect.y + b.rect.h <= r.y + r.h)
        ids = {b.id for b in v.boxes}
        self.assertTrue(all(rel.source in ids and rel.target in ids for rel in v.rels))

    def test_drawio_has_six_tabs_with_c4_last(self):
        names = [d.get("name") for d in ET.fromstring(DrawioRenderer().render(self.arch, self.lay)).findall("diagram")]
        self.assertEqual(len(names), 6)
        self.assertTrue(names[4].startswith("5 · C4") and names[5].startswith("6 · C4"))

    def test_svg_previews(self):
        for v in (c4.context(self.arch), c4.containers(self.arch, self.lay)):
            ET.fromstring(svg_preview.render_c4(v))


class UseCaseFamilyTests(unittest.TestCase):
    """Any kind of use case must produce a valid, renderable architecture (all 6 tabs)."""

    CASES = {
        "Tienda en línea de ropa con carrito, pagos y recomendaciones": ("cognito", "aurora", "personalize"),
        "Marketplace multi-vendedor con pedidos e inventario": ("eventbridge", "opensearch"),
        "Suscripciones SaaS B2B multi-tenant": ("cognito", "aurora"),
        "Agente de soporte al cliente con RAG y acceso a pedidos": ("bedrock", "opensearch"),
        "Sistema multi-agente supervisor con agentes especialistas": ("bedrock",),
        "Agente de voz para call center": ("transcribe", "polly"),
        "Agente analista de datos text-to-sql": ("athena",),
        "Agente de código con sandbox y pull requests": ("fargate",),
        "Agente de correo que automatiza respuestas": ("ses", "step_functions"),
        "Plataforma IoT de sensores con series de tiempo y dashboards": ("iot_core", "timestream"),
        "Plataforma de video bajo demanda": ("mediaconvert", "cloudfront"),
        "Digitalización de facturas con OCR": ("textract",),
        "App de domicilios con rastreo GPS y mapa": ("location_service",),
        "Red social con grafo de amigos": ("neptune",),
        "Historia clínica de pacientes con auditoría": ("cloudtrail", "kms"),
        "Chat en tiempo real colaborativo": ("appsync",),
    }

    def test_families_get_their_services_and_render(self):
        for text, expected in self.CASES.items():
            with self.subTest(text):
                arch = RulePlanner().plan(Requirements(text, ()))
                services = {c.service for c in arch.components}
                for svc in expected:
                    self.assertIn(svc, services)
                self.assertEqual([f.code for f in validate(arch) if f.severity == "error"], [])
                xml = DrawioRenderer().render(arch, layout.compute(arch))
                self.assertEqual(len(ET.fromstring(xml).findall("diagram")), 6)

    def test_agent_flavours_are_agentic_and_shop_is_not(self):
        for text in self.CASES:
            self.assertEqual(agents.is_agentic(RulePlanner().plan(Requirements(text, ()))), text.startswith(("Agente", "Sistema multi-agente")), text)


class RuleTests(unittest.TestCase):
    def base(self, **kw):
        return Architecture("t", (Component("a", "users"), Component("b", "lambda")), (Flow("a", "b"),), **kw)

    def test_valid(self):
        self.assertEqual(codes(self.base()), set())

    def test_errors(self):
        arch = Architecture("t", (Component("a", "users"), Component("a", "nope"), Component("c", "s3", tier="x")), (Flow("a", "zzz"), Flow("a", "a")))
        self.assertTrue({"AWS001", "AWS002", "AWS003", "AWS007", "AWS008"} <= codes(arch))

    def test_unknown_service_suggests(self):
        msg = [f.message for f in validate(Architecture("t", (Component("a", "dynamodbb"),), ()))][0]
        self.assertIn("dynamodb", msg)

    def test_many_components_only_warn_until_the_sanity_cap(self):
        comps = tuple(Component(f"c{i}", "lambda") for i in range(25))
        findings = [f for f in validate(Architecture("t", comps, ())) if f.code == "AWS005"]
        self.assertEqual([f.severity for f in findings], ["warning"])
        huge = tuple(Component(f"c{i}", "lambda") for i in range(41))
        self.assertEqual([f.severity for f in validate(Architecture("t", huge, ())) if f.code == "AWS005"], ["error"])

    def test_suggestions_name_what_is_missing(self):
        from awsdraw.domain import suggestions
        arch = Architecture("t", (Component("u", "users"), Component("cdn", "cloudfront"), Component("api", "api_gateway"), Component("fn", "lambda"), Component("db", "aurora")), (Flow("u", "cdn"), Flow("cdn", "api"), Flow("api", "fn"), Flow("fn", "db")))
        text = " ".join(suggestions.suggest(arch))
        for word in ("WAF", "CloudWatch", "KMS", "Backup", "multi_az"):
            self.assertIn(word, text)
        full = RulePlanner().plan(Requirements("Tienda web con pagos, login y monitoreo", ()))
        self.assertNotIn("Cognito", " ".join(suggestions.suggest(full)))

    def test_orphan_warning_but_ops_exempt(self):
        arch = Architecture("t", (Component("a", "users"), Component("b", "lambda"), Component("c", "s3"), Component("m", "cloudwatch")), (Flow("a", "b"),))
        found = [f.message for f in validate(arch) if f.code == "AWS006"]
        self.assertEqual(len(found), 1)
        self.assertIn("'c'", found[0])

    def test_generate_refuses_invalid(self):
        with self.assertRaises(SpecError):
            gen(Architecture("t", (Component("a", "nope"),), ()))


def overlap(a, b):
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


class LayoutTests(unittest.TestCase):
    def layouts(self):
        for f in sorted((ROOT / "examples").glob("*.json")):
            yield f.name, json_spec.load(str(f))
        yield "planner", RulePlanner().plan(Requirements("web con login, sql, cache, colas, archivos, waf, contenedores, correo"))

    def test_nodes_never_overlap(self):
        for name, arch in self.layouts():
            nodes = layout.compute(arch).nodes
            for i, a in enumerate(nodes):
                for b in nodes[i + 1:]:
                    self.assertFalse(overlap(a.rect, b.rect), f"{name}: {a.component.id} overlaps {b.component.id}")

    def test_vpc_box_contains_only_vpc_nodes(self):
        for name, arch in self.layouts():
            lay = layout.compute(arch)
            vpc = next((g for g in lay.groups if g.id == "vpc"), None)
            for n in lay.nodes:
                inside = vpc is not None and overlap(vpc.rect, n.rect)
                self.assertEqual(inside, n.component.vpc, f"{name}: {n.component.id}")

    def test_groups_nest_and_actors_stay_outside_cloud(self):
        for name, arch in self.layouts():
            lay = layout.compute(arch)
            g = {x.id: x.rect for x in lay.groups}
            def inside(a, b):
                return a.x >= b.x and a.y >= b.y and a.x + a.w <= b.x + b.w and a.y + a.h <= b.y + b.h
            if "region" in g:
                self.assertTrue(inside(g["region"], g["cloud"]), name)
            if "vpc" in g:
                self.assertTrue(inside(g["vpc"], g["region"]), name)
            for n in lay.nodes:
                if n.parent == "1":
                    self.assertFalse(overlap(n.rect, g["cloud"]), f"{name}: actor inside cloud")
                else:
                    self.assertTrue(inside(n.rect, g["cloud"]), f"{name}: {n.component.id} outside cloud")
            for rect in g.values():
                self.assertGreaterEqual(min(rect.x, rect.y), 0)


class RendererTests(unittest.TestCase):
    def render_all(self):
        for f in sorted((ROOT / "examples").glob("*.json")):
            yield f.name, gen(json_spec.load(str(f)))

    def test_four_pages_each_well_formed_with_valid_edges(self):
        for name, res in self.render_all():
            root = ET.fromstring(res.xml.split("?>", 1)[1])
            pages = list(root.iter("diagram"))
            self.assertEqual([d.get("name")[:1] for d in pages], ["1", "2", "3", "4", "5", "6"], name)
            for page in pages:
                cells = list(page.iter("mxCell"))
                ids = [c.get("id") for c in cells]
                self.assertEqual(len(ids), len(set(ids)), f"{name}/{page.get('name')}")
                known = set(ids)
                for c in cells:
                    if c.get("edge"):
                        self.assertIn(c.get("source"), known)
                        self.assertIn(c.get("target"), known)
                    if c.get("parent"):
                        self.assertIn(c.get("parent"), known)

    def test_level_one_is_simple_and_has_a_story(self):
        for name, res in self.render_all():
            ov = overview.build(res.architecture)
            self.assertLessEqual(len(ov.boxes), 4, name)
            self.assertGreaterEqual(len(ov.story), 1, name)
            self.assertEqual([l.step for l in ov.links], list(range(1, len(ov.links) + 1)))
            page = list(ET.fromstring(res.xml.split("?>", 1)[1]).iter("diagram"))[1]
            self.assertIn("story", {c.get("id") for c in page.iter("mxCell")})

    def test_level_two_shows_plain_role_under_each_icon(self):
        res = gen(json_spec.load(str(ROOT / "examples/serverless-web.json")))
        page = list(ET.fromstring(res.xml.split("?>", 1)[1]).iter("diagram"))[2]
        db = next(c for c in page.iter("mxCell") if c.get("id") == "db")
        self.assertIn("Base de datos", db.get("value"))

    def test_only_verified_icons_are_used(self):
        for name, res in self.render_all():
            used = set(re.findall(r"resIcon=mxgraph\.aws4\.([a-z0-9_]+);", res.xml))
            self.assertTrue(used <= VERIFIED, f"{name}: {used - VERIFIED}")

    def test_children_use_relative_coordinates(self):
        res = gen(json_spec.load(str(ROOT / "examples/containers-three-tier.json")))
        root = list(ET.fromstring(res.xml.split("?>", 1)[1]).iter("diagram"))[3]  # level 4 uses groups
        cells = {c.get("id"): c for c in root.iter("mxCell")}
        absolute = {n.component.id: n.rect for n in res.layout.nodes}
        groups = {g.id: g.rect for g in res.layout.groups}
        for cid, rect in absolute.items():
            cell = cells[cid]
            geo = cell.find("mxGeometry")
            px, py = (groups[cell.get("parent")].x, groups[cell.get("parent")].y) if cell.get("parent") in groups else (0, 0)
            self.assertAlmostEqual(float(geo.get("x")) + px, rect.x)
            self.assertAlmostEqual(float(geo.get("y")) + py, rect.y)

    def test_labels_are_escaped(self):
        arch = Architecture('A & <B> "q"', (Component("a", "users", "<script>"), Component("b", "lambda")), (Flow("a", "b", "x & y"),))
        res = gen(arch)
        ET.fromstring(res.xml.split("?>", 1)[1])
        self.assertNotIn("<script>", res.xml)

    def test_async_flow_is_dashed(self):
        res = gen(json_spec.load(str(ROOT / "examples/event-driven-analytics.json")))
        self.assertIn("dashed=1", res.xml)

    def test_preview_svg_is_well_formed(self):
        res = gen(json_spec.load(str(ROOT / "examples/serverless-web.json")))
        ET.fromstring(svg_preview.render(res.architecture, res.layout))


class PlannerTests(unittest.TestCase):
    def services(self, text):
        return {c.service for c in RulePlanner().plan(Requirements(text)).components}

    def test_keywords_spanish_and_english(self):
        s = self.services("Portal web con login, base de datos relacional, cache y colas de correo, archivos e imágenes")
        self.assertTrue({"cloudfront", "cognito", "aurora", "elasticache", "sqs", "sns", "s3"} <= s)
        s = self.services("Mobile app with real-time streaming, a data lake and dashboards, plus a chatbot using RAG")
        self.assertTrue({"mobile", "kinesis", "glue", "athena", "quicksight", "bedrock"} <= s)

    def test_containers_use_alb_fargate(self):
        s = self.services("microservicios en contenedores con base de datos sql")
        self.assertTrue({"alb", "fargate", "aurora"} <= s)

    def test_static_site_has_no_backend(self):
        s = self.services("sitio web estático de marketing")
        self.assertNotIn("lambda", s)
        self.assertTrue({"cloudfront", "s3"} <= s)

    def test_unrecognised_text_gets_serverless_baseline(self):
        self.assertIn("api_gateway", self.services("lorem ipsum"))

    def test_every_plan_validates_and_renders(self):
        prompts = [
            "web con login, sql, cache, colas, archivos, waf, contenedores, correo, auditoría, secretos",
            "iot sensores telemetría tiempo real con analítica y alertas por sms",
            "ia generativa y búsqueda con orquestación de workflow y eventos",
            "multi-region global api para móvil",
        ]
        for p in prompts:
            res = gen(RulePlanner().plan(Requirements(p)))
            self.assertFalse([f for f in res.findings if f.severity == "error"], p)
            self.assertLessEqual(len(res.architecture.components), 20, p)

    def test_fallback_used_when_primary_planner_fails(self):
        class Broken:
            def plan(self, req):
                raise SpecError("boom")
        res = PlanAndGenerate(Broken(), GenerateDiagram(DrawioRenderer()), fallback=RulePlanner())(Requirements("web con login"))
        self.assertTrue(res.xml)

    def test_performance_budget(self):
        started = time.perf_counter()
        gen(RulePlanner().plan(Requirements("web con login, sql, cache, colas, archivos, waf, contenedores, correo")))
        self.assertLess(time.perf_counter() - started, 1.0)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class LlmPlannerTests(unittest.TestCase):
    def test_parses_model_json_and_sends_images(self):
        sent = {}
        spec = {"title": "T", "components": [{"id": "a", "service": "users"}, {"id": "b", "service": "lambda"}], "flows": [{"from": "a", "to": "b"}]}

        def opener(request, timeout):
            sent["body"] = json.loads(request.data)
            sent["key"] = request.headers.get("X-api-key")
            return FakeResponse({"content": [{"type": "text", "text": "```json\n" + json.dumps(spec) + "\n```"}]})

        planner = AnthropicPlanner(api_key="k", opener=opener)
        arch = planner.plan(Requirements("uc", (("x.png", b"\x89PNG\r\n\x1a\n0000"),)))
        self.assertEqual([c.id for c in arch.components], ["a", "b"])
        self.assertEqual(sent["key"], "k")
        kinds = [b["type"] for b in sent["body"]["messages"][0]["content"]]
        self.assertEqual(kinds, ["image", "text"])
        self.assertIn("lambda", sent["body"]["system"])

    def test_http_error_and_garbage_become_spec_errors(self):
        def http_error(request, timeout):
            raise urllib.error.HTTPError("u", 401, "no", {}, None)

        with self.assertRaises(SpecError):
            AnthropicPlanner(api_key="k", opener=http_error).plan(Requirements("x"))
        with self.assertRaises(SpecError):
            AnthropicPlanner(api_key="k", opener=lambda r, timeout: FakeResponse({"content": [{"type": "text", "text": "no json"}]})).plan(Requirements("x"))
        with self.assertRaises(SpecError):
            AnthropicPlanner(api_key="").plan(Requirements("x"))


class GithubPlannerTests(unittest.TestCase):
    SPEC = {"title": "G", "components": [{"id": "a", "service": "users"}, {"id": "b", "service": "s3"}], "flows": [{"from": "a", "to": "b"}]}

    def test_request_shape_and_parsing(self):
        sent = {}

        def opener(request, timeout):
            sent["url"] = request.full_url
            sent["auth"] = request.headers.get("Authorization")
            sent["body"] = json.loads(request.data)
            return FakeResponse({"choices": [{"message": {"content": json.dumps(self.SPEC)}}]})

        arch = GithubModelsPlanner(token="tok", opener=opener).plan(Requirements("uc", (("x.png", b"\x89PNG\r\n\x1a\n0000"),)))
        self.assertEqual([c.id for c in arch.components], ["a", "b"])
        self.assertEqual(sent["url"], "https://models.github.ai/inference/chat/completions")
        self.assertEqual(sent["auth"], "Bearer tok")
        user = sent["body"]["messages"][1]["content"]
        self.assertEqual([p["type"] for p in user], ["image_url", "text"])
        self.assertTrue(user[0]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(sent["body"]["messages"][0]["role"], "system")

    def test_errors_become_spec_errors(self):
        def limited(request, timeout):
            raise urllib.error.HTTPError("u", 429, "slow", {}, None)

        with self.assertRaisesRegex(SpecError, "rate limit"):
            GithubModelsPlanner(token="t", opener=limited).plan(Requirements("x"))
        with self.assertRaises(SpecError):
            GithubModelsPlanner(token="t", opener=lambda r, timeout: FakeResponse({"oops": 1})).plan(Requirements("x"))
        with self.assertRaises(SpecError):
            GithubModelsPlanner(token="").plan(Requirements("x"))


class CollectTests(unittest.TestCase):
    def test_collects_text_and_requires_something(self):
        from awsdraw.adapters.readers import read_document

        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "uc.md"
            f.write_text("API con colas")
            req, warnings = CollectRequirements(read_document)("login", [str(f)])
            self.assertIn("login", req.text)
            self.assertIn("API con colas", req.text)
            with self.assertRaises(SpecError):
                CollectRequirements(read_document)("  ", [])
            with self.assertRaises(SpecError):
                read_document(str(Path(tmp) / "x.exe"))


class WebUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        saved = {}

        def analyze(text, paths, mode):
            from awsdraw.adapters.readers import read_document

            req, w = CollectRequirements(read_document)(text, paths)
            res = PlanAndGenerate(RulePlanner(), GenerateDiagram(DrawioRenderer()))(Requirements(req.text))
            return {"title": res.architecture.title, "planner": "offline", "filename": "x.drawio", "xml": res.xml, "svg": "<svg/>", "components": [], "warnings": w}

        def save(xml, filename):
            if "<mxfile" not in xml:
                raise SpecError("Nothing valid to save")
            p = Path(cls.tmp.name) / web_ui._safe_name(filename, "a.drawio")
            p.write_text(xml)
            return str(p), False

        page = (ROOT / "scripts/awsdraw/adapters/ui_page.html").read_text(encoding="utf-8")
        cls.server = web_ui.serve(web_ui.UiDeps(analyze, save, []), page, 0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, path, body=None, headers=None, host=None):
        h = {"Content-Type": "application/json", "Host": host or f"127.0.0.1:{self.port}"}
        h.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(), headers=h, method="GET" if body is None else "POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_serves_page_bound_to_loopback(self):
        status, body = self.call("/")
        self.assertEqual(status, 200)
        self.assertIn(b"const PROV=[]", body)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_generate_from_text_and_file(self):
        data = base64.b64encode("Necesito una API con colas".encode()).decode()
        status, body = self.call("/api/generate", {"text": "web con login", "files": [{"name": "../../uc.txt", "data": data}]})
        self.assertEqual(status, 200)
        self.assertIn("<mxfile", json.loads(body)["xml"])

    def test_rejects_bad_input(self):
        self.assertEqual(self.call("/api/generate", {"text": "", "files": []})[0], 400)
        bad = base64.b64encode(b"MZ").decode()
        self.assertEqual(self.call("/api/generate", {"text": "x", "files": [{"name": "a.exe", "data": bad}]})[0], 400)
        self.assertEqual(self.call("/api/generate", {"text": "x", "files": [{"name": "a.txt", "data": "***"}]})[0], 400)

    def test_blocks_foreign_host_origin_and_non_json(self):
        self.assertEqual(self.call("/", host="evil.example")[0], 403)
        self.assertEqual(self.call("/api/generate", {"text": "x"}, {"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.call("/api/generate", {"text": "x"}, {"Content-Type": "text/plain"})[0], 415)

    def test_save_sanitises_filename_and_validates_xml(self):
        status, _ = self.call("/api/save", {"xml": "junk", "filename": "a.drawio"})
        self.assertEqual(status, 400)
        status, body = self.call("/api/save", {"xml": "<?xml?><mxfile/>", "filename": "../../etc/passwd.drawio"})
        self.assertEqual(status, 200)
        self.assertEqual(Path(json.loads(body)["path"]).parent, Path(self.tmp.name))


class InstallerTests(unittest.TestCase):
    def test_project_install_copies_skill_and_recommends_extension(self):
        with TemporaryDirectory() as proj:
            dest = FsInstaller().install(ROOT, "drawing-aws-architectures", "project", "copilot", proj)
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertTrue((dest / "scripts/run.py").is_file())
            self.assertFalse((dest / "tests").exists())
            recs = json.loads((Path(proj) / ".vscode/extensions.json").read_text())["recommendations"]
            self.assertIn(EXTENSION_ID, recs)
            FsInstaller().install(ROOT, "drawing-aws-architectures", "project", "copilot", proj)  # idempotent
            self.assertEqual(json.loads((Path(proj) / ".vscode/extensions.json").read_text())["recommendations"].count(EXTENSION_ID), 1)

    def test_existing_recommendations_are_kept(self):
        with TemporaryDirectory() as proj:
            ext = Path(proj) / ".vscode/extensions.json"
            ext.parent.mkdir()
            ext.write_text(json.dumps({"recommendations": ["ms-python.python"]}))
            FsInstaller().install(ROOT, "drawing-aws-architectures", "project", "claude", proj)
            self.assertEqual(json.loads(ext.read_text())["recommendations"], ["ms-python.python", EXTENSION_ID])

    def test_unknown_target(self):
        with self.assertRaises(SpecError):
            FsInstaller().install(ROOT, "x", "project", "nope", ".")


class OpenerTests(unittest.TestCase):
    def test_opener(self):
        calls = []
        self.assertTrue(VsCodeOpener(which=lambda n: "/usr/bin/code", run=lambda *a, **k: calls.append(a)).open("f.drawio"))
        self.assertEqual(calls[0][0][0], "/usr/bin/code")
        self.assertFalse(VsCodeOpener(which=lambda n: None).open("f.drawio"))


class ArchitectureTests(unittest.TestCase):
    PKG = ROOT / "scripts/awsdraw"

    def imports(self, layer):
        found = set()
        for path in (self.PKG / layer).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    found.add(("." * node.level + (node.module or ""), path.name))
        return found

    def test_dependency_rule(self):
        for mod, f in self.imports("domain"):
            self.assertFalse(mod.startswith("..") and ("application" in mod or "adapters" in mod), f"domain/{f} imports {mod}")
        for mod, f in self.imports("application"):
            self.assertFalse("adapters" in mod, f"application/{f} imports {mod}")

    def test_domain_has_no_io_imports(self):
        banned = {"os", "subprocess", "socket", "urllib", "http", "pathlib", "json", "shutil"}
        for path in (self.PKG / "domain").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else []
                self.assertFalse(banned & set(names), f"{path.name} imports {banned & set(names)}")


class WebBuildTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_web
        self.build = build_web

    def test_zip_has_engine_and_no_os_bound_modules(self):
        import io
        import zipfile
        names = zipfile.ZipFile(io.BytesIO(self.build.package_zip())).namelist()
        self.assertIn("awsdraw/web_entry.py", names)
        self.assertIn("awsdraw/__init__.py", names)
        for banned in ("cli.py", "web_ui.py", "fs_installer.py", "llm_github.py", "llm_anthropic.py", "vscode_opener.py"):
            self.assertFalse([n for n in names if n.endswith(banned)], banned)

    def test_zip_is_deterministic(self):
        self.assertEqual(self.build.package_zip(), self.build.package_zip())

    def test_page_is_in_web_mode_without_placeholders(self):
        html = self.build.page_html()
        self.assertIn("const PROV=null", html)
        self.assertNotIn("__PROVIDERS__", html)
        self.assertNotIn("__PYODIDE_VERSION__", html)
        self.assertIn(f"pyodide/v{self.build.PYODIDE_VERSION}/full/pyodide.js", html)

    def test_published_docs_are_up_to_date(self):
        docs = ROOT.parents[1] / "docs"
        if not docs.is_dir():
            self.skipTest("docs/ not present (skill used outside the repository)")
        self.assertEqual((docs / "awsdraw.zip").read_bytes(), self.build.package_zip(), "run: python scripts/build_web.py")
        self.assertEqual((docs / "index.html").read_text(encoding="utf-8"), self.build.page_html(), "run: python scripts/build_web.py")


class SkillLintTests(unittest.TestCase):
    def test_skill_md(self):
        text = (ROOT / "SKILL.md").read_text()
        self.assertLess(len(text.splitlines()), 500)
        meta = dict(re.findall(r"^(\w+):\s*(.+)$", text.split("---")[1], re.M))
        self.assertEqual(meta["name"], "drawing-aws-architectures")
        self.assertRegex(meta["name"], r"^[a-z0-9-]{1,64}$")
        self.assertLessEqual(len(meta["description"]), 1024)
        self.assertNotRegex(meta["description"], r"<|>")
        for needle in ("1-3 minutes", "draw.io", "VS Code", "AWS"):
            self.assertIn(needle, text)

    def test_every_reference_in_skill_md_exists(self):
        text = (ROOT / "SKILL.md").read_text()
        for rel in set(re.findall(r"\]\(([^)#]+)\)", text)):
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
