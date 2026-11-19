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
from awsdraw.adapters.vscode_opener import VsCodeOpener  # noqa: E402
from awsdraw.application.use_cases import CollectRequirements, GenerateDiagram, PlanAndGenerate  # noqa: E402
from awsdraw.domain import catalog, layout  # noqa: E402
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

    def test_too_many_components(self):
        comps = tuple(Component(f"c{i}", "lambda") for i in range(21))
        self.assertIn("AWS005", codes(Architecture("t", comps, ())))

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

    def test_well_formed_unique_ids_and_valid_edges(self):
        for name, res in self.render_all():
            root = ET.fromstring(res.xml.split("?>", 1)[1])
            cells = list(root.iter("mxCell"))
            ids = [c.get("id") for c in cells]
            self.assertEqual(len(ids), len(set(ids)), name)
            known = set(ids)
            for c in cells:
                if c.get("edge"):
                    self.assertIn(c.get("source"), known)
                    self.assertIn(c.get("target"), known)
                if c.get("parent"):
                    self.assertIn(c.get("parent"), known)

    def test_only_verified_icons_are_used(self):
        for name, res in self.render_all():
            used = set(re.findall(r"resIcon=mxgraph\.aws4\.([a-z0-9_]+);", res.xml))
            self.assertTrue(used <= VERIFIED, f"{name}: {used - VERIFIED}")

    def test_children_use_relative_coordinates(self):
        res = gen(json_spec.load(str(ROOT / "examples/containers-three-tier.json")))
        root = ET.fromstring(res.xml.split("?>", 1)[1])
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
        cls.server = web_ui.serve(web_ui.UiDeps(analyze, save, False), page, 0)
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
        self.assertIn(b"const AI=false", body)
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
