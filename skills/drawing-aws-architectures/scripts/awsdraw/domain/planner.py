"""Offline rule-based planner: requirements text -> Architecture. Pure, deterministic, instant.

It is intentionally simple: keyword rules (Spanish + English) switch services on, then a
fixed wiring turns them into a request path. An LLM planner (adapters/llm_anthropic.py)
can replace it for richer interpretation.
"""

from __future__ import annotations

from dataclasses import replace

import re
import unicodedata

from .models import Architecture, Component, Flow, Requirements


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


class RulePlanner:
    def plan(self, req: Requirements) -> Architecture:
        t = _fold(req.text)
        title = self._title(req.text)

        web = _has(t, r"\bweb\b", r"sitio", r"portal", r"frontend", r"front-end", r"pagina", r"spa\b", r"website", r"landing")
        mobile = _has(t, r"movil", r"mobile", r"\bapp\b", r"android", r"ios")
        containers = _has(t, r"contenedor", r"container", r"docker", r"kubernetes", r"\beks\b", r"\becs\b", r"fargate", r"microservici", r"microservice")
        relational = _has(t, r"relacional", r"\bsql\b", r"postgres", r"mysql", r"transaccion", r"transaction", r"erp", r"facturacion", r"billing")
        nosql = _has(t, r"nosql", r"dynamo", r"clave.valor", r"key.value")
        streaming = _has(t, r"streaming", r"tiempo real", r"real.time", r"kafka", r"\biot\b", r"telemetr", r"sensor")
        analytics = _has(t, r"analitic", r"analytic", r"data lake", r"datalake", r"\bbi\b", r"reporte", r"dashboard", r"business intelligence", r"big data")
        genai = _has(t, r"\bia\b", r"\bai\b", r"genai", r"llm", r"chatbot", r"\brag\b", r"generativ", r"bedrock", r"asistente")
        agent = _has(t, r"\bagente", r"\bagent", r"agentic", r"agentico", r"\bmcp\b", r"multi.?agente", r"multi.?agent", r"herramientas del agente", r"tool.?use", r"function calling")
        ml = _has(t, r"machine learning", r"\bml\b", r"modelo predictiv", r"entrenar", r"sagemaker")
        genai = genai or agent
        files = _has(t, r"archivo", r"\bfile", r"imagen", r"image", r"upload", r"subir", r"documento", r"almacen", r"storage", r"video", r"adjunto")
        queue = _has(t, r"cola\b", r"colas", r"queue", r"asincron", r"async", r"mensajer", r"background", r"segundo plano", r"batch")
        notify = _has(t, r"notificacion", r"notification", r"email", r"correo", r"\bsms\b", r"push", r"alerta")
        events = _has(t, r"evento", r"event.driven", r"event-driven", r"eventbridge")
        workflow = _has(t, r"orquest", r"workflow", r"flujo de trabajo", r"saga", r"aprobacion")
        auth = _has(t, r"login", r"autentic", r"authent", r"usuarios registrados", r"sso", r"\bauth\b", r"registro de usuario", r"oauth", r"jwt")
        cache = _has(t, r"cache", r"redis", r"baja latencia", r"low latency", r"alto trafico", r"high traffic", r"millones")
        search = _has(t, r"busqueda", r"search", r"opensearch", r"elasticsearch")
        security = _has(t, r"waf", r"ataque", r"attack", r"ddos", r"seguridad", r"security", r"pci", r"bancari", r"banking", r"finanz", r"financ")
        audit = _has(t, r"auditor", r"audit", r"cumplimiento", r"compliance", r"trazabilidad")
        monitor = _has(t, r"monitor", r"observab", r"logs?\b", r"metric", r"alarma")
        domain = _has(t, r"dominio", r"domain", r"dns", r"route ?53")
        secrets = _has(t, r"secreto", r"secret", r"credencial", r"credential", r"api key")
        global_users = _has(t, r"global", r"multi.?region", r"internacional", r"worldwide", r"latencia global")

        comps: list[Component] = []
        flows: list[Flow] = []
        add = lambda cid, svc, label="", **kw: comps.append(Component(cid, svc, label or cid, **kw))  # noqa: E731
        link = lambda a, b, label="", **kw: flows.append(Flow(a, b, label, **kw))  # noqa: E731

        actor = "users" if (web or not mobile) else "mobile"
        add("actor", actor, "Usuarios móviles" if actor == "mobile" else "Usuarios")
        entry_from = "actor"

        if domain:
            add("dns", "route53", "Route 53")
            link("actor", "dns", "DNS")
            entry_from = "dns"
        if web or global_users:
            add("cdn", "cloudfront", "CloudFront")
            link(entry_from, "cdn", "HTTPS")
            entry_from = "cdn"
            if security:
                add("waf", "waf", "AWS WAF")
                link("cdn", "waf", "filtra")
                entry_from = "waf"
            if web:
                add("site", "s3", "Sitio web (S3)")
                link("cdn", "site", "archivos del sitio")
        elif security:
            add("waf", "waf", "AWS WAF")
            link(entry_from, "waf", "filtra")
            entry_from = "waf"

        needs_backend = bool(mobile or containers or auth or relational or nosql or queue or genai or ml or files or not web)
        backend = None
        if needs_backend:
            if containers:
                add("lb", "alb", "Balanceador de carga")
                add("compute", "fargate", "Contenedores (Fargate)", vpc=True)
                link(entry_from, "lb", "HTTPS")
                link("lb", "compute")
                backend = "compute"
                if auth:
                    add("auth", "cognito", "Cognito")
                    link("compute", "auth", "valida identidad")
            else:
                add("api", "api_gateway", "API Gateway")
                add("compute", "lambda", "Lógica del negocio (Lambda)")
                link(entry_from, "api", "REST/HTTPS")
                link("api", "compute")
                backend = "compute"
                if auth:
                    add("auth", "cognito", "Cognito")
                    link("api", "auth", "valida identidad")
        elif auth:
            add("auth", "cognito", "Cognito")
            link("actor", "auth", "inicia sesión")

        if backend:
            if relational:
                add("db", "aurora", "Base de datos SQL (Aurora)", vpc=containers)
                link(backend, "db", "SQL")
            elif nosql or not (analytics or streaming):
                add("db", "dynamodb", "Base de datos (DynamoDB)")
                link(backend, "db", "lee y escribe")
            if cache:
                add("cache", "elasticache", "Caché (ElastiCache)", vpc=True)
                link(backend, "cache", "caché")
            if files:
                add("files", "s3", "Archivos (S3)")
                link(backend, "files", "archivos")
            if queue:
                add("queue", "sqs", "Cola de tareas (SQS)")
                add("worker", "lambda", "Procesador en segundo plano (Lambda)")
                link(backend, "queue", "encola", is_async=True)
                link("queue", "worker", is_async=True)
            if workflow:
                add("flow", "step_functions", "Flujo de trabajo (Step Functions)")
                link(backend, "flow", "coordina")
            if events:
                add("bus", "eventbridge", "Eventos (EventBridge)")
                link(backend, "bus", "eventos", is_async=True)
            if notify:
                add("notify", "sns", "Notificaciones (SNS)")
                link("worker" if queue else backend, "notify", "avisa", is_async=True)
            if search:
                add("search", "opensearch", "Búsqueda (OpenSearch)")
                link(backend, "search", "busca")
            if genai:
                add("llm", "bedrock", "IA generativa (Bedrock)")
                link(backend, "llm", "consulta")
            if agent:
                add("tools", "lambda", "Herramientas del agente (MCP)")
                link(backend, "tools", "usa herramientas")
                add("memory", "dynamodb", "Memoria de la conversación (DynamoDB)", role="memory_short")
                link(backend, "memory", "recuerda")
                if search or _has(t, r"\brag\b", r"conocimiento", r"knowledge", r"documento", r"memoria de largo"):
                    add("knowledge", "opensearch", "Conocimiento (OpenSearch)", role="memory_long")
                    link(backend, "knowledge", "consulta")
            if ml:
                add("ml", "sagemaker", "Modelo de ML (SageMaker)")
                link(backend, "ml", "predice")

        if streaming:
            add("stream", "kinesis", "Datos en tiempo real (Kinesis)")
            add("lake", "s3", "Data lake (S3)")
            link("actor", "stream", "eventos")
            link("stream", "lake", "entrega", is_async=True)
        if analytics:
            source = next((c.id for c in comps if c.id in ("lake", "files", "db")), None)
            if source is None:
                add("lake", "s3", "Data lake (S3)")
                source = "lake"
            add("etl", "glue", "Preparación de datos (Glue)")
            add("query", "athena", "Consultas SQL (Athena)")
            add("bi", "quicksight", "Dashboards (QuickSight)")
            link(source, "etl", "prepara datos")
            link("etl", "query")
            link("query", "bi", "dashboards")

        if monitor or len(comps) > 3:
            add("monitor", "cloudwatch", "Monitoreo (CloudWatch)")
        if audit:
            add("audit", "cloudtrail", "Auditoría (CloudTrail)")
        if security or auth or relational:
            add("kms", "kms", "Cifrado (KMS)")
        if secrets:
            add("secrets", "secrets_manager", "Secretos (Secrets Manager)")

        if agent:
            comps = [replace(c, role="agent") if c.id == backend else c for c in comps]

        if len(comps) <= 1:  # nothing recognisable: give a sensible serverless baseline
            return RulePlanner._baseline(title)
        return Architecture(title, tuple(comps), tuple(flows), multi_az=containers or relational, profile="agents" if agent else None)

    @staticmethod
    def _title(text: str) -> str:
        first = next((ln.strip(" #-*\t") for ln in text.splitlines() if ln.strip()), "")
        return (first[:70] + "…") if len(first) > 70 else (first or "AWS high-level architecture")

    @staticmethod
    def _baseline(title: str) -> Architecture:
        comps = (
            Component("actor", "users", "Users"),
            Component("api", "api_gateway", "API Gateway"),
            Component("compute", "lambda", "Lambda"),
            Component("db", "dynamodb", "DynamoDB"),
            Component("monitor", "cloudwatch", "CloudWatch"),
        )
        flows = (Flow("actor", "api", "HTTPS"), Flow("api", "compute"), Flow("compute", "db", "read/write"))
        return Architecture(title, comps, flows)
