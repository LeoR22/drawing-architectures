# drawing-aws-architectures

Agent Skill que convierte los **requisitos de un proyecto** (texto, PDF, Word o una imagen del caso de uso) en una **arquitectura AWS de alto nivel** dibujada en **draw.io**, lista para abrir y editar en **VS Code**. Objetivo: tenerla en **1 a 3 minutos**.

- Solo **AWS** (por ahora).
- Solo **VS Code** como editor objetivo (por ahora). El `.drawio` también se abre en https://app.diagrams.net.
- Alto nivel: entre 6 y 14 componentes, con íconos oficiales de AWS. No incluye subredes, zonas de disponibilidad, grupos de seguridad ni dimensionamiento.
- Solo usa la biblioteca estándar de Python 3.10+ (no hay que instalar paquetes).

> Para revisiones profundas (resiliencia, ADR, evaluación, GCP/Azure) existe la skill hermana `designing-cloud-architectures`.

---

## Índice

1. [¿Qué es una Agent Skill?](#1-qué-es-una-agent-skill)
2. [Requisitos](#2-requisitos)
3. [Instalación paso a paso en VS Code](#3-instalación-paso-a-paso-en-vs-code)
4. [Formas de usarla](#4-formas-de-usarla)
5. [Interfaz web local](#5-interfaz-web-local)
6. [Formato del spec JSON](#6-formato-del-spec-json)
7. [Catálogo de servicios](#7-catálogo-de-servicios)
8. [Cómo se dibuja el diagrama](#8-cómo-se-dibuja-el-diagrama)
9. [Reglas de validación](#9-reglas-de-validación)
10. [Planificador offline vs. con IA](#10-planificador-offline-vs-con-ia)
11. [Arquitectura del código (clean architecture)](#11-arquitectura-del-código-clean-architecture)
12. [Seguridad](#12-seguridad)
13. [Pruebas](#13-pruebas)
14. [Solución de problemas](#14-solución-de-problemas)
15. [Límites y próximos pasos](#15-límites-y-próximos-pasos)

---

## 1. ¿Qué es una Agent Skill?

Una skill es una carpeta con un archivo `SKILL.md` (instrucciones para el agente de IA) y scripts opcionales. El agente (GitHub Copilot en VS Code, Claude Code, etc.) lee solo el nombre y la descripción al inicio, y carga el resto únicamente cuando tu petición coincide. Así no gasta contexto en vano.

Esta skill le enseña al agente un flujo corto: leer requisitos → escribir un spec JSON → ejecutar el generador → abrir el `.drawio`.

## 2. Requisitos

| Qué | Para qué | Obligatorio |
|---|---|---|
| Python 3.10 o superior | Ejecutar los scripts | Sí |
| VS Code | Editor objetivo | Sí |
| Extensión **Draw.io Integration** (`hediet.vscode-drawio`) | Ver y editar `.drawio` dentro de VS Code (incluye draw.io sin conexión) | Sí |
| Comando `code` en el PATH | Opción `--open` y botón "Abrir en VS Code" | Recomendado |
| Agente con soporte de skills (Copilot agent mode, Claude Code) | Usarla en lenguaje natural | Opcional |
| `ANTHROPIC_API_KEY` | Modo IA de la interfaz web (lee imágenes) | Opcional |
| `pdftotext`/`pdftoppm` (poppler) o `pip install pypdf` | Leer PDF (texto / escaneados) | Opcional |

Comando `code` en Windows/macOS: Paleta de comandos (`Ctrl+Shift+P`) → **Shell Command: Install 'code' command in PATH** (en Windows suele quedar instalado por defecto).

## 3. Instalación paso a paso en VS Code

1. **Clona el repo**
   ```bash
   git clone https://github.com/LeoR22/drawing-architectures.git
   cd drawing-architectures/skills/drawing-aws-architectures
   ```
2. **Instala la extensión** de draw.io: abre VS Code → pestaña Extensiones → busca **Draw.io Integration** (autor Henning Dieterichs) → Instalar. O desde terminal: `code --install-extension hediet.vscode-drawio`.
3. **Instala la skill** en tu proyecto (desde la carpeta de este repo, apuntando a tu proyecto):
   ```bash
   python scripts/run.py install --scope project --target copilot --project "C:\ruta\a\tu\proyecto"
   ```
   Esto copia la skill a `tu-proyecto/.github/skills/drawing-aws-architectures/` y añade la extensión a `.vscode/extensions.json` como recomendada.

   Opciones:
   | Opción | Valores | Efecto |
   |---|---|---|
   | `--scope` | `project` (por defecto), `user` | `project`: solo ese proyecto. `user`: disponible en todos tus proyectos |
   | `--target` | `copilot`, `claude`, `agents` | Carpeta de destino: `.github/skills`, `.claude/skills` o `.agents/skills` (las tres las lee VS Code). Con `--scope user` usa `~/.copilot/skills`, `~/.claude/skills` o `~/.agents/skills` |
   | `--project` | ruta | Proyecto de destino (por defecto, la carpeta actual) |

4. **Reinicia/recarga VS Code** (`Developer: Reload Window`) para que el agente detecte la skill.
5. **Pruébala** en el chat del agente:
   > Diseña una arquitectura AWS de alto nivel para un portal web con login, base de datos relacional, colas para correos y archivos subidos por los usuarios.

   El agente escribirá `architecture.json`, ejecutará el generador y abrirá `architecture.drawio`.

## 4. Formas de usarla

### 4.1 Con un agente (lenguaje natural)
Pide la arquitectura. Si adjuntas un PDF o Word, el agente extrae el texto con `plan -f`; las imágenes las interpreta el propio agente.

### 4.2 Directo desde la terminal, sin agente

```bash
# A) Desde texto: planificador offline por palabras clave (instantáneo)
python scripts/run.py plan "Portal web con login, base de datos SQL, cache, colas y archivos" -o arq.drawio --open

# B) Desde archivos (PDF, .docx, .txt, .md)
python scripts/run.py plan -f requisitos.pdf caso.docx -o arq.drawio --open

# C) Desde un spec JSON escrito por ti o por el agente
python scripts/run.py generate examples/serverless-web.json -o arq.drawio --open

# Utilidades
python scripts/run.py validate mi-spec.json     # valida sin escribir nada
python scripts/run.py catalog                   # lista los servicios disponibles
```

`--open` abre el resultado en VS Code (si `code` no está en el PATH, imprime el comando a ejecutar).

## 5. Interfaz web local

Para quien prefiere una pantalla en vez de la terminal:

```bash
python scripts/run.py ui --browser
```

Abre `http://127.0.0.1:8765/`. Allí puedes:

1. Escribir el caso de uso y/o **subir** PDF, Word, `.txt`/`.md` o imágenes.
2. Elegir el modo (**Offline** o **Con IA**).
3. Pulsar **Generar arquitectura**: ves una vista previa, la lista de componentes y avisos.
4. **Descargar .drawio** o **Guardar y abrir en VS Code** (guarda en la carpeta `diagrams/`).

Opciones: `--port 8765`, `--output-dir diagrams`, `--browser`.

| Modo | Necesita | Lee | Privacidad |
|---|---|---|---|
| Offline | nada | texto, PDF, Word | Nada sale de tu equipo |
| Con IA | `ANTHROPIC_API_KEY` | lo anterior + PNG/JPG/GIF/WebP | El caso de uso se envía a la API de Anthropic. Si la llamada falla, cae al modo offline |

Definir la clave en Windows PowerShell antes de iniciar la UI:
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
python scripts/run.py ui --browser
```
En macOS/Linux: `export ANTHROPIC_API_KEY=sk-ant-...`. Opcional: `ANTHROPIC_MODEL` para cambiar el modelo (por defecto `claude-sonnet-5-5`).

La vista previa es simplificada (cuadros de colores). El archivo `.drawio` sí trae los íconos oficiales.

## 6. Formato del spec JSON

```json
{
  "title": "Aplicación web serverless",
  "region": "us-east-1",
  "multi_az": false,
  "components": [
    {"id": "users", "service": "users", "label": "Usuarios"},
    {"id": "api",   "service": "api_gateway"},
    {"id": "fn",    "service": "lambda", "label": "Lógica de negocio"},
    {"id": "db",    "service": "dynamodb"}
  ],
  "flows": [
    {"from": "users", "to": "api", "label": "HTTPS"},
    {"from": "api",   "to": "fn"},
    {"from": "fn",    "to": "db", "label": "lectura/escritura"}
  ]
}
```

| Campo | Descripción |
|---|---|
| `title` | Título del diagrama |
| `region` | Texto de la caja Región (por defecto `us-east-1`) |
| `multi_az` | Si es `true`, la caja VPC dice "(Multi-AZ)" |
| `components[].id` | Identificador único |
| `components[].service` | Clave del catálogo o alias (`apigw`, `dynamo`, `redis`, `k8s`…) |
| `components[].label` | Texto bajo el ícono (opcional; usa el nombre del servicio) |
| `components[].tier` | Columna: `actors`, `edge`, `app`, `data`, `ops` (opcional; el catálogo ya sugiere una) |
| `components[].vpc` | `true` = se dibuja dentro de la caja VPC (contenedores, cachés, SQL) |
| `flows[].from/to` | ids de origen y destino |
| `flows[].label` | Texto sobre la flecha |
| `flows[].async` | `true` = flecha punteada (colas, eventos, notificaciones) |

Ejemplos listos en `examples/`: `serverless-web.json`, `containers-three-tier.json`, `event-driven-analytics.json`. Patrones y reglas rápidas de elección en `reference/patterns.md`.

## 7. Catálogo de servicios

Ejecuta `python scripts/run.py catalog` para verlo completo. Resumen por columna:

- **actors**: users, user, client, mobile
- **edge**: cloudfront, route53, waf, shield, cognito, api_gateway, appsync, alb, amplify
- **app**: lambda, ec2, fargate, ecs, eks, ecr, app_runner, batch, step_functions, sqs, sns, eventbridge, appflow, kinesis, firehose, msk, glue, emr, sagemaker, bedrock
- **data**: s3, efs, ebs, aurora, rds, dynamodb, elasticache, redshift, opensearch, dms, athena, lake_formation, quicksight
- **ops**: iam, kms, secrets_manager, guardduty, security_hub, cloudwatch, cloudtrail, config, systems_manager, cloudformation, xray, backup

Cada entrada apunta a un ícono de la biblioteca **oficial** `Sidebar-AWS4.js` de draw.io. Un test comprueba que todos existan (fixture en `tests/fixtures/aws4-icons.txt`), así no salen cuadros vacíos. Si pides un servicio desconocido, el error sugiere los más parecidos (por ejemplo `dynamodbb` → `dynamodb`).

## 8. Cómo se dibuja el diagrama

El layout es **determinista** (mismo spec → mismo dibujo) y de izquierda a derecha:

```
Actores | Edge | Aplicación | Datos | Operaciones
```

- Cada componente va a la columna de su `tier` (o la sugerida por el catálogo).
- Todo lo que no es actor va dentro de **AWS Cloud**. Los servicios regionales van dentro de la caja **Región**; los globales (CloudFront, Route 53, WAF, Shield) quedan fuera de ella si no comparten columna con servicios regionales.
- Los componentes con `vpc: true` se apilan debajo de los demás de su columna para que **una sola caja VPC** los rodee sin tocar nada más.
- Las flechas son ortogonales y draw.io las enruta al abrir el archivo; son del mismo color y trazo para que se lean bien.
- El resultado es un `mxfile` de draw.io sin comprimir, con grupos reales (al mover la caja VPC se mueven sus hijos).

## 9. Reglas de validación

| Código | Tipo | Significado |
|---|---|---|
| AWS001 | error | id de componente duplicado |
| AWS002 | error | servicio desconocido (con sugerencias) |
| AWS003 | error | un flujo apunta a un id inexistente |
| AWS004 | error | no hay componentes |
| AWS005 | error / aviso | demasiados componentes (>20 error, >16 aviso); agrupa servicios |
| AWS006 | aviso | componente sin flujos (los de `ops` están exentos) |
| AWS007 | error | `tier` inválido |
| AWS008 | error | flujo de un componente a sí mismo |

Con errores no se genera archivo; con avisos sí.

## 10. Planificador offline vs. con IA

**Offline** (`domain/planner.py`): reglas por palabras clave en español e inglés. Por ejemplo, "login" activa Cognito; "relacional/SQL" activa Aurora; "colas/asíncrono" activa SQS + un worker; "contenedores/microservicios" cambia API Gateway + Lambda por ALB + Fargate dentro de una VPC; "analítica/BI" añade Glue + Athena + QuickSight; "IA/chatbot/RAG" añade Bedrock. Si no reconoce nada, genera una base serverless (API Gateway → Lambda → DynamoDB). Es instantáneo y gratis, pero es una heurística: revisa y ajusta el resultado.

**Con IA** (`adapters/llm_anthropic.py`): el modelo solo elige servicios y flujos **del catálogo** y devuelve JSON; el dibujo sigue siendo determinista. Se valida igual que cualquier spec; si falla, se usa el planificador offline.

Cuando trabajas con un agente (Copilot/Claude Code), el propio agente actúa como "planificador" escribiendo el spec, así que no necesitas la API key.

## 11. Arquitectura del código (clean architecture)

```
SKILL.md                    instrucciones para el agente
scripts/run.py              punto de entrada (funciona con python -I)
scripts/awsdraw/
  domain/                   reglas puras, sin I/O
    models.py  catalog.py  rules.py  layout.py  planner.py  documents.py  errors.py
  application/              casos de uso y puertos (interfaces)
    ports.py  use_cases.py  (GenerateDiagram, PlanAndGenerate, SaveDiagram, CollectRequirements)
  adapters/                 detalles externos
    drawio_renderer.py  json_spec.py  svg_preview.py  fs_writer.py  vscode_opener.py
    fs_installer.py  readers.py + docx/pdf/text/image  llm_anthropic.py  web_ui.py  ui_page.html
  cli.py                    raíz de composición: único lugar que conecta adaptadores con casos de uso
reference/  examples/  tests/
```

Regla de dependencia: `domain` no importa nada de `application` ni `adapters`; `application` no importa `adapters`. Un test con `ast` lo verifica, y otro comprueba que `domain` no use módulos de I/O. Para añadir otro editor o formato (Mermaid, otro IDE) se crea un adaptador nuevo sin tocar el dominio.

## 12. Seguridad

- Los archivos del usuario se tratan como **datos no confiables**: `.docx` se lee con tope de tamaño, sin extraer a disco y rechazando XML con `DOCTYPE`/`ENTITY`; las imágenes se validan por su firma; los PDF se leen con rutas absolutas.
- La interfaz escucha **solo en 127.0.0.1**, valida `Host` y `Origin` (anti DNS-rebinding/CSRF), acepta solo JSON, limita el cuerpo a 40 MB, guarda las subidas en una carpeta temporal con nombres saneados (se borra tras cada petición) y solo escribe dentro de `--output-dir`.
- El texto del caso de uso se envía al modelo como **datos**, con instrucción explícita de no obedecerlo.
- La clave de API se lee de la variable de entorno; nunca se guarda en disco.

## 13. Pruebas

```bash
python -m unittest discover -s tests
```

41 pruebas: catálogo contra la biblioteca real de draw.io, reglas, que los nodos no se solapen, que la caja VPC contenga solo nodos VPC, XML bien formado con ids únicos y aristas válidas, escapado de caracteres, planificador, planificador IA con respuesta simulada, servidor web (Host/Origin, subidas, guardado), instalador, regla de dependencias y revisión de `SKILL.md`. También hay una prueba de presupuesto de tiempo (<1 s).

## 14. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| El `.drawio` abre como texto | Falta la extensión Draw.io Integration; instálala y reabre el archivo |
| `--open` no abre nada | El comando `code` no está en el PATH (ver sección 2) |
| `error: AWS002 unknown service` | Revisa la sugerencia del mensaje o ejecuta `catalog` |
| "Images need the AI mode" | Offline no interpreta imágenes: usa modo IA o describe la imagen en texto |
| PDF escaneado sin texto | Instala poppler (`pdftoppm`) y usa modo IA, o pasa las páginas como imágenes |
| La skill no aparece en Copilot | Recarga la ventana; confirma que la carpeta está en `.github/skills/<nombre>/SKILL.md` |
| El puerto 8765 está ocupado | `python scripts/run.py ui --port 8800` |

## 15. Límites y próximos pasos

- Solo AWS y VS Code por ahora. Siguientes pasos naturales: GCP/Azure, otros IDE, subredes y AZ, exportar PNG/SVG.
- El planificador offline es heurístico; para casos complejos usa un agente o el modo IA y revisa el resultado.
- La vista previa web no usa los íconos oficiales; el `.drawio` sí.

Licencia: pendiente de definir por el autor.
