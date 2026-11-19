"""Vendor-neutral view: every service is reduced to a classic system-design building block. Pure.

Used for the first tab of the diagram, so the solution can be understood (and discussed) before
any cloud service is named. The same architecture, drawn with generic shapes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import catalog
from .models import Component


@dataclass(frozen=True)
class Kind:
    key: str
    title: str  # generic name, no vendor
    shape: str  # actor | hexagon | cloud | service | cylinder | process | model | support
    fill: str
    stroke: str


_KINDS = (
    Kind("actor", "Usuario", "actor", "#FFFFFF", "#232F3D"),
    Kind("client", "Cliente", "actor", "#FFFFFF", "#232F3D"),
    Kind("mobile", "App móvil", "actor", "#FFFFFF", "#232F3D"),
    Kind("cdn", "CDN (red de entrega)", "cloud", "#EFE8FF", "#8C4FFF"),
    Kind("dns", "DNS", "hexagon", "#EFE8FF", "#8C4FFF"),
    Kind("firewall", "Firewall web", "hexagon", "#FDE9EB", "#DD344C"),
    Kind("auth", "Autenticación", "hexagon", "#FDE9EB", "#DD344C"),
    Kind("gateway", "Puerta de entrada (API)", "hexagon", "#EFE8FF", "#8C4FFF"),
    Kind("lb", "Balanceador de carga", "hexagon", "#EFE8FF", "#8C4FFF"),
    Kind("hosting", "Hosting web", "service", "#FFF1E0", "#ED7100"),
    Kind("service", "Servicio de aplicación", "service", "#FFF1E0", "#ED7100"),
    Kind("queue", "Cola de mensajes", "process", "#FDE7F1", "#E7157B"),
    Kind("pubsub", "Notificaciones (pub/sub)", "process", "#FDE7F1", "#E7157B"),
    Kind("bus", "Bus de eventos", "process", "#FDE7F1", "#E7157B"),
    Kind("workflow", "Orquestador de flujos", "process", "#FDE7F1", "#E7157B"),
    Kind("stream", "Streaming de datos", "process", "#FDE7F1", "#E7157B"),
    Kind("agent", "Agente de IA", "model", "#DDF5F1", "#01A88D"),
    Kind("model", "Modelo de IA", "model", "#DDF5F1", "#01A88D"),
    Kind("object", "Almacenamiento de archivos", "cylinder", "#EEF5DA", "#7AA116"),
    Kind("db", "Base de datos", "cylinder", "#F7E6FA", "#C925D1"),
    Kind("warehouse", "Data warehouse", "cylinder", "#F7E6FA", "#C925D1"),
    Kind("cache", "Caché", "service", "#FDE7F1", "#E7157B"),
    Kind("search", "Motor de búsqueda", "service", "#F7E6FA", "#C925D1"),
    Kind("analytics", "Procesamiento de datos", "service", "#EFE8FF", "#8C4FFF"),
    Kind("bi", "Reportes (BI)", "service", "#EFE8FF", "#8C4FFF"),
    Kind("observability", "Monitoreo y logs", "support", "#F2F3F3", "#879196"),
    Kind("audit", "Auditoría", "support", "#F2F3F3", "#879196"),
    Kind("secrets", "Secretos y claves", "support", "#F2F3F3", "#879196"),
    Kind("security", "Detección de amenazas", "support", "#F2F3F3", "#879196"),
    Kind("backup", "Respaldos", "support", "#F2F3F3", "#879196"),
    Kind("iac", "Infraestructura como código", "support", "#F2F3F3", "#879196"),
)
KINDS = {k.key: k for k in _KINDS}

_OF = {
    "actor": ("users", "user"), "client": ("client",), "mobile": ("mobile",),
    "cdn": ("cloudfront",), "dns": ("route53",), "firewall": ("waf", "shield"), "auth": ("cognito",),
    "gateway": ("api_gateway", "appsync"), "lb": ("alb",), "hosting": ("amplify",),
    "service": ("lambda", "ec2", "fargate", "ecs", "eks", "ecr", "app_runner", "batch", "appflow"),
    "queue": ("sqs",), "pubsub": ("sns",), "bus": ("eventbridge",), "workflow": ("step_functions",),
    "stream": ("kinesis", "msk", "firehose"), "agent": ("agentcore",), "model": ("bedrock", "sagemaker"),
    "object": ("s3", "efs", "ebs"), "db": ("aurora", "rds", "dynamodb", "dms"), "warehouse": ("redshift",),
    "cache": ("elasticache",), "search": ("opensearch",),
    "analytics": ("glue", "emr", "athena", "lake_formation"), "bi": ("quicksight",),
    "observability": ("cloudwatch", "xray"), "audit": ("cloudtrail", "config"),
    "secrets": ("kms", "secrets_manager", "iam"), "security": ("guardduty", "security_hub"),
    "backup": ("backup",), "iac": ("systems_manager", "cloudformation"),
}
KIND_OF = {service: kind for kind, services in _OF.items() for service in services}


def kind_of(component: Component) -> Kind:
    return KINDS[KIND_OF[catalog.lookup(component.service).key]]


_COMMON_WORDS = {"users", "user", "client", "mobile", "config", "backup", "batch", "glue"}  # keys that are also plain words


def _vendor_names() -> set[str]:
    names = {s.label.lower() for s in catalog.SERVICES.values() if s.tier != "actors"}
    return names | {k for k in catalog.SERVICES if k not in _COMMON_WORDS and catalog.SERVICES[k].tier != "actors"}


def _mentions_vendor(text: str, vendors: set[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"(?<!\w){re.escape(v)}(?!\w)", low) for v in vendors)


def generic_label(component: Component) -> str:
    """The component's own wording without the vendor: 'Lógica del negocio (Lambda)' -> 'Lógica del negocio'.

    A label that is just a vendor name ('Aurora (SQL)') falls back to the generic block name and keeps
    a non-vendor qualifier: 'Base de datos (SQL)'.
    """
    kind = kind_of(component)
    label = (component.label or "").strip()
    vendors = _vendor_names()
    if not label or label.lower() in vendors or label.lower() in set(catalog.ALIASES):
        return kind.title
    match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", label)
    head, qualifier = (match.group(1).strip(), match.group(2).strip()) if match else (label, "")
    if not head or _mentions_vendor(head, vendors):
        head = kind.title
    if qualifier and not _mentions_vendor(qualifier, vendors):
        return f"{head} ({qualifier})"
    return head
