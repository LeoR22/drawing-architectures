"""Advice, in plain words, on what else the solution could include. Pure.

The diagram itself is never forced to change: these are hints inspired by the AWS Well-Architected
pillars (security, reliability, operations, performance, cost), shown next to the result.
"""

from __future__ import annotations

from . import system_design
from .models import Architecture


def suggest(arch: Architecture) -> list[str]:
    services = {c.service for c in arch.components}
    kinds = {system_design.kind_of(c).key for c in arch.components}
    out: list[str] = []
    has = lambda *s: bool(services & set(s))  # noqa: E731
    public = bool(kinds & {"cdn", "gateway", "lb", "hosting"})
    stores = kinds & {"db", "warehouse", "object"}

    if public and not kinds & {"firewall"}:
        out.append("Protección contra ataques: agrega AWS WAF (y Shield si el servicio es crítico) delante de la entrada pública.")
    if public and "auth" not in kinds:
        out.append("Identidad: si hay usuarios con cuenta, agrega Cognito para el inicio de sesión.")
    if not kinds & {"observability"}:
        out.append("Monitoreo: agrega CloudWatch (métricas, logs y alarmas) y X-Ray si hay varios servicios encadenados.")
    if stores and not has("kms"):
        out.append("Cifrado: agrega KMS para cifrar bases de datos y archivos con claves propias.")
    if stores and not has("backup"):
        out.append("Respaldos: agrega AWS Backup (o copias entre regiones) para poder recuperar los datos.")
    if "queue" in kinds:
        out.append("Colas: considera una cola de mensajes fallidos (DLQ) para no perder tareas que no se pudieron procesar.")
    if has("aurora", "rds") and not arch.multi_az:
        out.append("Alta disponibilidad: la base relacional debería ir en varias zonas de disponibilidad (multi_az).")
    if has("aurora", "rds", "dynamodb") and not has("elasticache"):
        out.append("Rendimiento: si hay mucha lectura repetida, una caché (ElastiCache) baja la latencia y el costo.")
    if kinds & {"model", "agent"}:
        out.append("IA: agrega guardrails (filtros de contenido y datos sensibles) y evaluación/observabilidad de las respuestas del modelo.")
    if not kinds & {"audit"} and (kinds & {"db"}):
        out.append("Trazabilidad: agrega CloudTrail si necesitas saber quién hizo qué (auditoría y cumplimiento).")
    if not kinds & {"secrets"} and (kinds & {"service"}):
        out.append("Secretos: guarda claves y contraseñas en Secrets Manager, no en el código.")
    return out
