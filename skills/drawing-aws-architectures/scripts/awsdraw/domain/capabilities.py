"""Plain-language roles ("capabilities") of AWS services, so anyone can read level 1 of the diagram.

Pure data: a service key maps to a capability with a title and a one-line description that
needs no AWS knowledge. Columns: 0 people, 1 entry, 2 logic, 3 data, 4 support (shown as a band).
"""

from __future__ import annotations

from dataclasses import dataclass

PEOPLE, ENTRY, LOGIC, DATA, SUPPORT = range(5)


@dataclass(frozen=True)
class Capability:
    key: str
    title: str
    does: str
    column: int


_CAPS = (
    Capability("people", "Personas usuarias", "Quienes usan el sistema desde el navegador o el celular", PEOPLE),
    Capability("delivery", "Entrega del sitio", "Hace que el sitio cargue rápido desde cualquier lugar", ENTRY),
    Capability("protection", "Protección contra ataques", "Filtra el tráfico malicioso antes de que llegue al sistema", ENTRY),
    Capability("auth", "Inicio de sesión", "Comprueba quién es cada usuario", ENTRY),
    Capability("gateway", "Puerta de entrada", "Recibe y ordena todas las solicitudes", ENTRY),
    Capability("logic", "Reglas del negocio", "Aplica las reglas del negocio y toma decisiones", LOGIC),
    Capability("workflow", "Tareas en segundo plano", "Deja trabajo pendiente para hacerlo después, sin hacer esperar al usuario", LOGIC),
    Capability("notify", "Avisos y notificaciones", "Envía correos, SMS o notificaciones push", LOGIC),
    Capability("stream", "Datos en tiempo real", "Recibe datos continuos, como sensores o eventos", LOGIC),
    Capability("ai", "Inteligencia artificial", "Genera respuestas o predicciones con modelos de IA", LOGIC),
    Capability("files", "Archivos y documentos", "Guarda imágenes, documentos y otros archivos", DATA),
    Capability("database", "Base de datos", "Guarda y consulta la información del negocio", DATA),
    Capability("cache", "Respuestas rápidas", "Recuerda datos frecuentes para responder más rápido", DATA),
    Capability("search", "Búsqueda", "Permite buscar información de forma rápida", DATA),
    Capability("analytics", "Análisis y reportes", "Convierte los datos en reportes y tableros", DATA),
    Capability("monitoring", "Monitoreo", "Vigila que todo funcione y avisa si algo falla", SUPPORT),
    Capability("audit", "Auditoría", "Registra quién hizo qué, para cumplir normas", SUPPORT),
    Capability("secrets", "Claves y accesos", "Protege contraseñas, claves y permisos", SUPPORT),
    Capability("security", "Seguridad continua", "Detecta amenazas y malas configuraciones", SUPPORT),
    Capability("backup", "Respaldos", "Guarda copias para recuperar datos", SUPPORT),
    Capability("admin", "Despliegue y administración", "Crea y mantiene la infraestructura", SUPPORT),
)
CAPABILITIES = {c.key: c for c in _CAPS}

_OF = {
    "people": ("users", "user", "client", "mobile"),
    "delivery": ("cloudfront", "route53", "amplify"),
    "protection": ("waf", "shield"),
    "auth": ("cognito",),
    "gateway": ("api_gateway", "alb", "appsync"),
    "logic": ("lambda", "ec2", "fargate", "ecs", "eks", "ecr", "app_runner", "batch", "mediaconvert", "location_service"),
    "workflow": ("sqs", "eventbridge", "step_functions", "appflow"),
    "notify": ("sns", "ses", "pinpoint"),
    "stream": ("kinesis", "msk", "firehose", "iot_core"),
    "ai": ("bedrock", "agentcore", "sagemaker", "textract", "comprehend", "transcribe", "polly", "lex", "rekognition", "personalize"),
    "files": ("s3", "efs", "ebs"),
    "database": ("aurora", "rds", "dynamodb", "redshift", "dms", "timestream", "neptune", "documentdb"),
    "cache": ("elasticache",),
    "search": ("opensearch", "kendra"),
    "analytics": ("glue", "emr", "athena", "lake_formation", "quicksight"),
    "monitoring": ("cloudwatch", "xray"),
    "audit": ("cloudtrail", "config"),
    "secrets": ("kms", "secrets_manager", "iam"),
    "security": ("guardduty", "security_hub"),
    "backup": ("backup",),
    "admin": ("systems_manager", "cloudformation"),
}
CAPABILITY_OF = {service: cap for cap, services in _OF.items() for service in services}


def of(service_key: str) -> Capability:
    return CAPABILITIES[CAPABILITY_OF[service_key]]


@dataclass(frozen=True)
class Block:
    key: str
    title: str
    does: str
    column: int


# Level 1 shows only these four blocks; capabilities are listed inside them.
BLOCKS = {b.key: b for b in (
    Block("people", "Personas usuarias", "Quienes usan el sistema desde el navegador o el celular", PEOPLE),
    Block("entry", "Entrada y seguridad", "Recibe a los usuarios, los protege y verifica quiénes son", ENTRY),
    Block("logic", "Lógica del negocio", "Procesa las solicitudes y aplica las reglas del negocio", LOGIC),
    Block("data", "Datos", "Guarda y organiza la información", DATA),
)}
_BLOCK_OF_CAP = {
    "people": "people", "delivery": "entry", "protection": "entry", "auth": "entry", "gateway": "entry",
    "logic": "logic", "workflow": "logic", "notify": "logic", "stream": "logic", "ai": "logic",
    "files": "data", "database": "data", "cache": "data", "search": "data", "analytics": "data",
}


def block_of(capability_key: str) -> Block | None:
    """None for support capabilities (monitoring, audit...), which form the bottom band."""
    key = _BLOCK_OF_CAP.get(capability_key)
    return BLOCKS[key] if key else None
