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
   - [Versión web sin instalar nada (GitHub Pages)](#versión-web-sin-instalar-nada-github-pages)
6. [Formato del spec JSON](#6-formato-del-spec-json)
7. [Catálogo de servicios](#7-catálogo-de-servicios)
8. [Los 4 niveles del diagrama](#8-los-4-niveles-del-diagrama)
9. [Cómo se dibuja el diagrama](#9-cómo-se-dibuja-el-diagrama)
10. [Reglas de validación](#10-reglas-de-validación)
11. [Planificador offline vs. con IA](#11-planificador-offline-vs-con-ia)
12. [Arquitectura del código (clean architecture)](#12-arquitectura-del-código-clean-architecture)
13. [Seguridad](#13-seguridad)
14. [Pruebas](#14-pruebas)
15. [Solución de problemas](#15-solución-de-problemas)
16. [Límites y próximos pasos](#16-límites-y-próximos-pasos)

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
| `GITHUB_MODELS_TOKEN` o `ANTHROPIC_API_KEY` | Modo IA de la interfaz web (lee imágenes) | Opcional |
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
| Con IA · **GitHub Models** | `GITHUB_MODELS_TOKEN` (token de GitHub con permiso *Models: read*) | lo anterior + PNG/JPG/GIF/WebP | El caso de uso se envía a GitHub Models. No requiere pagar Anthropic |
| Con IA · Anthropic | `ANTHROPIC_API_KEY` | lo anterior + imágenes | El caso de uso se envía a la API de Anthropic (se factura aparte) |

Si falla la llamada a un modo con IA, la interfaz cae al modo offline y te avisa. Las opciones no configuradas aparecen deshabilitadas.

> **Importante:** GitHub Models es un servicio aparte de Copilot, con sus propios límites de uso por cuenta (el error 429 indica límite alcanzado). No consume la cuota de Copilot Chat. Si quieres usar exactamente tu cuota de Copilot, usa el agente de VS Code (sección 4.1) con las imágenes adjuntas.

**Crear el token de GitHub Models**
1. GitHub → Settings → Developer settings → Personal access tokens → *Fine-grained tokens* → Generate new token.
2. Concede el permiso de cuenta **Models** en modo lectura (*models: read*). No necesita acceso a repositorios.
3. Cópialo y defínelo antes de iniciar la UI.

PowerShell:
```powershell
$env:GITHUB_MODELS_TOKEN="github_pat_..."
python scripts/run.py ui --browser
```
En macOS/Linux: `export GITHUB_MODELS_TOKEN=github_pat_...`. Opcional: `GITHUB_MODELS_MODEL` (por defecto `openai/gpt-4.1`; debe aceptar imágenes). También se acepta `GITHUB_TOKEN` si tiene ese permiso.

Para Anthropic: `$env:ANTHROPIC_API_KEY="sk-ant-..."` (opcional `ANTHROPIC_MODEL`, por defecto `claude-sonnet-5-5`). Nunca subas tokens a un repositorio.

La vista previa es simplificada (cuadros de colores). El archivo `.drawio` sí trae los íconos oficiales.

### Versión web sin instalar nada (GitHub Pages)

La misma interfaz funciona **directamente en el navegador**, sin Python ni servidor: https://leor22.github.io/drawing-architectures/

Cómo funciona: la página descarga [Pyodide](https://pyodide.org) (Python compilado a WebAssembly) y ejecuta en tu navegador **el mismo código** de la skill (`awsdraw`): planificador, validación, layout y generación del `.drawio`. Tus archivos se procesan en tu equipo y no se suben a ningún servidor.

| Aspecto | Versión web | Versión local (`ui`) |
|---|---|---|
| Instalación | ninguna | Python + clonar el repo |
| Offline (texto, Word) | sí | sí |
| PDF | sí (instala `pypdf` en el navegador la primera vez, requiere conexión) | sí |
| Modos con IA | sí: pegas tu token en la página (solo en memoria de la pestaña) | sí: token por variable de entorno |
| Guardar y abrir en VS Code | no; usa **Descargar .drawio** y ábrelo en VS Code | sí |
| Primera carga | unos segundos (descarga el motor, ~10 MB, luego queda en caché) | inmediata |

Limitaciones: el navegador puede bloquear la llamada directa al proveedor de IA por CORS; si ocurre, la página lo indica y debes usar la versión local o el agente de VS Code. Anthropic permite llamadas desde el navegador con una cabecera especial que la página envía; en GitHub Models no está garantizado. Un token pegado en una página web es sensible: usa uno de permisos mínimos (*Models: read*), con vencimiento corto, y no lo compartas.

**Publicarla en tu cuenta (una sola vez):** en el repo, Settings → Pages → *Build and deployment* → Source: **Deploy from a branch** → Branch: `main` y carpeta `/docs` → Save. En un par de minutos queda en `https://<tu-usuario>.github.io/drawing-architectures/`.

**Actualizar la web tras cambiar el código:** `python skills/drawing-aws-architectures/scripts/build_web.py` y haz commit de la carpeta `docs/`. Un test falla si `docs/` quedó desactualizado.

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

### Tipos de casos de uso que entiende

El modo sin IA reconoce **familias** de soluciones y enciende lo que casi siempre necesitan (puedes combinarlas en un mismo texto). Con IA (GitHub Models o Anthropic) cualquier caso nuevo se resuelve igual, usando el catálogo de servicios.

| Familia | Palabras que activan | Qué agrega |
|---|---|---|
| **E-commerce** (tienda, marketplace, suscripciones, pagos) | tienda, carrito, checkout, pedidos, inventario, marketplace, suscripción | Login, base SQL de pedidos, archivos de productos, colas, avisos, WAF; búsqueda y caché en marketplace o alto tráfico; eventos si hay varios vendedores |
| **Agentes** de cualquier tipo | agente, MCP, chatbot, asistente, RAG, LLM | Vista de agentes en el nivel 1 + memoria + herramientas. Variantes: **soporte** (APIs de negocio), **voz** (Transcribe/Polly), **analista de datos** (consulta SQL), **multi-agente** (especialistas), **código** (entorno seguro), **automatización** (flujo de trabajo), **correo** (SES) |
| IoT / series de tiempo | sensores, IoT, telemetría | Dispositivos conectados, streaming, lago de datos, Timestream |
| Video y multimedia | video, podcast, VOD | Conversión de video, CDN, archivos |
| Documentos / OCR | factura, OCR, contrato, PDF | Lectura de documentos (Textract) + cola |
| Mapas y logística | GPS, domicilios, rastreo | Location Service |
| Redes y fraude | grafo, red social, fraude | Base de relaciones (Neptune) |
| Chat y tiempo real | chat, colaborativo, multijugador | API en tiempo real (AppSync) |
| Salud, banca, seguros | clínica, banco, fintech, seguro | Auditoría, cifrado, login, WAF |
| SaaS multi-tenant | SaaS, B2B, multi-tenant | Login, base SQL, caché |
| Marketing / recomendaciones | campaña, newsletter, recomendaciones | Pinpoint, Personalize |

## 8. Los 4 niveles del diagrama

El archivo `.drawio` trae **seis pestañas**: cuatro niveles de lo más general a lo más técnico, más el **modelo C4** (pestañas 5 y 6: *Contexto* con personas, sistema y sistemas externos; y *Contenedores* con las piezas dentro del límite del sistema y su tecnología). También salen en la interfaz con descarga PNG/SVG. La idea: entender primero el entorno de la solución, sin nombres de servicios, y bajar de nivel solo cuando haga falta.

| Nivel | Pestaña | Para quién | Qué muestra |
|---|---|---|---|
| 1 | **System design** | Todo el equipo; sirve para cualquier nube | El entorno general con bloques genéricos al estilo *system design*: figura de usuario, CDN (nube), puntos de entrada (hexágonos), servicios (rectángulos), colas (rectángulo con barras), bases de datos y archivos (cilindros) y apoyo (gris punteado). **Sin nombres de servicios** |

En la interfaz, cada diagrama (niveles 1, 2 y 3-4) tiene botones **Descargar PNG / SVG**, y hay un botón **Descargar todas las imágenes (PNG)**.

**Si la solución es de agentes**, el nivel 1 cambia a la arquitectura de referencia de un sistema agéntico (diagrama original, mismas zonas conceptuales): *Usuarios → Aplicación frontend → Entorno de ejecución del agente*, con **Memoria** (corto y largo plazo), **Herramientas** (bases de datos, APIs, servicios, archivos) conectadas por un **protocolo de comunicación (p. ej. MCP)**, el **Entorno de ejecución del modelo** (solicitud de inferencia / respuesta), el equipo de desarrollo y una banda de seguridad/observabilidad. Se activa cuando el texto menciona agente, MCP, tool use, chatbot, asistente, RAG o LLM, o cuando la arquitectura incluye un modelo generativo (Bedrock) (o con `"profile": "agents"` en el JSON; cada componente puede llevar `"role"`: `agent`, `model`, `memory_short`, `memory_long`, `tool_database`, `tool_api`, `tool_service`, `tool_files`, `frontend`, `support`).
| 2 | **Visión general** | Cualquier persona (gerencia, clientes, compañeros no técnicos) | 4 bloques: *Personas usuarias → Entrada y seguridad → Lógica del negocio → Datos*, más una franja de seguridad y operación. Flechas numeradas y una **historia paso a paso** ("Cómo explicarlo") |
| 3 | **Servicios AWS** | Producto y desarrollo | Los íconos oficiales de AWS; debajo de cada uno, su función en palabras simples |
| 4 | **Detalle técnico** | Arquitectos e ingenieros | Cajas AWS Cloud / Región / VPC, etiquetas de cada flujo y líneas punteadas para procesos asíncronos |

**Cómo usarlos en una reunión:** abre el nivel 1 para ponerse de acuerdo en *qué piezas hay y cómo se conectan*, sin discutir marcas. Luego el nivel 2 para contarlo en palabras simples (cada número está en una flecha). Si preguntan "¿con qué servicio?", pasa al nivel 3. Si preguntan por red o seguridad, al nivel 4.

**Cómo se generan:** todos salen del mismo spec. `domain/system_design.py` reduce cada servicio a un bloque clásico (por ejemplo Lambda/Fargate → "Servicio de aplicación", SQS → "Cola de mensajes", DynamoDB/Aurora → "Base de datos") y quita los nombres de proveedor de las etiquetas ("Lógica del negocio (Lambda)" → "Lógica del negocio"). `domain/capabilities.py` agrupa lo mismo en 4 bloques para el nivel 2. Como el nivel 1 no depende de AWS, es la base natural para soportar GCP y Azure más adelante. Un test verifica que ese nivel no contenga nombres de servicios.

Para reducir cruces, el layout acomoda cada componente cerca de lo que lo alimenta y dibuja como arco las flechas que saltan columnas.

## 9. Cómo se dibuja el diagrama

Esta sección describe el nivel 4 (y la base de los niveles 1 y 3). El layout es **determinista** (mismo spec → mismo dibujo) y de izquierda a derecha:

```
Actores | Edge | Aplicación | Datos | Operaciones
```

- Cada componente va a la columna de su `tier` (o la sugerida por el catálogo).
- Todo lo que no es actor va dentro de **AWS Cloud**. Los servicios regionales van dentro de la caja **Región**; los globales (CloudFront, Route 53, WAF, Shield) quedan fuera de ella si no comparten columna con servicios regionales.
- Los componentes con `vpc: true` se apilan debajo de los demás de su columna para que **una sola caja VPC** los rodee sin tocar nada más.
- Las flechas son ortogonales y draw.io las enruta al abrir el archivo; son del mismo color y trazo para que se lean bien.
- El resultado es un `mxfile` de draw.io sin comprimir, con grupos reales (al mover la caja VPC se mueven sus hijos).

## 10. Reglas de validación

| Código | Tipo | Significado |
|---|---|---|
| AWS001 | error | id de componente duplicado |
| AWS002 | error | servicio desconocido (con sugerencias) |
| AWS003 | error | un flujo apunta a un id inexistente |
| AWS004 | error | no hay componentes |
| AWS005 | aviso / error | solución grande: aviso desde 21 componentes (no bloquea; AWS no fija un límite y recomienda separar alto nivel y detalle); error solo sobre 40 |
| AWS006 | aviso | componente sin flujos (los de `ops` están exentos) |
| AWS007 | error | `tier` inválido |
| AWS008 | error | flujo de un componente a sí mismo |

Con errores no se genera archivo; con avisos sí.

## 11. Planificador offline vs. con IA

**Offline** (`domain/planner.py`): reglas por palabras clave en español e inglés. Por ejemplo, "login" activa Cognito; "relacional/SQL" activa Aurora; "colas/asíncrono" activa SQS + un worker; "contenedores/microservicios" cambia API Gateway + Lambda por ALB + Fargate dentro de una VPC; "analítica/BI" añade Glue + Athena + QuickSight; "IA/chatbot/RAG" añade Bedrock. Si no reconoce nada, genera una base serverless (API Gateway → Lambda → DynamoDB). Es instantáneo y gratis, pero es una heurística: revisa y ajusta el resultado.

**Con IA** (`adapters/llm_github.py` y `adapters/llm_anthropic.py`): el modelo solo elige servicios y flujos **del catálogo** y devuelve JSON; el dibujo sigue siendo determinista. Se valida igual que cualquier spec; si falla, se usa el planificador offline.

Cuando trabajas con un agente (Copilot/Claude Code), el propio agente actúa como "planificador" escribiendo el spec, así que no necesitas ninguna clave.

## 12. Arquitectura del código (clean architecture)

```
SKILL.md                    instrucciones para el agente
scripts/run.py              punto de entrada (funciona con python -I)
scripts/awsdraw/
  domain/                   reglas puras, sin I/O
    models.py  catalog.py  capabilities.py  system_design.py  rules.py  layout.py  overview.py  overview_layout.py  planner.py  documents.py  errors.py
  application/              casos de uso y puertos (interfaces)
    ports.py  use_cases.py  (GenerateDiagram, PlanAndGenerate, SaveDiagram, CollectRequirements)
  adapters/                 detalles externos
    drawio_renderer.py  json_spec.py  svg_preview.py  ui_response.py  fs_writer.py  vscode_opener.py
    fs_installer.py  readers.py + docx/pdf/text/image  llm_anthropic.py  web_ui.py  ui_page.html
  cli.py                    raíz de composición (terminal y servidor local)
  web_entry.py              raíz de composición del navegador (Pyodide)
scripts/build_web.py        genera docs/ (index.html + awsdraw.zip) para GitHub Pages
reference/  examples/  tests/
```

Regla de dependencia: `domain` no importa nada de `application` ni `adapters`; `application` no importa `adapters`. Un test con `ast` lo verifica, y otro comprueba que `domain` no use módulos de I/O. Para añadir otro editor o formato (Mermaid, otro IDE) se crea un adaptador nuevo sin tocar el dominio.

## 13. Seguridad

- Los archivos del usuario se tratan como **datos no confiables**: `.docx` se lee con tope de tamaño, sin extraer a disco y rechazando XML con `DOCTYPE`/`ENTITY`; las imágenes se validan por su firma; los PDF se leen con rutas absolutas.
- La interfaz escucha **solo en 127.0.0.1**, valida `Host` y `Origin` (anti DNS-rebinding/CSRF), acepta solo JSON, limita el cuerpo a 40 MB, guarda las subidas en una carpeta temporal con nombres saneados (se borra tras cada petición) y solo escribe dentro de `--output-dir`.
- El texto del caso de uso se envía al modelo como **datos**, con instrucción explícita de no obedecerlo.
- Las claves/tokens se leen de variables de entorno; nunca se guardan en disco.

## 14. Pruebas

```bash
python -m unittest discover -s tests
```

56 pruebas: catálogo contra la biblioteca real de draw.io, reglas, que los nodos no se solapen, que la caja VPC contenga solo nodos VPC, XML bien formado con ids únicos y aristas válidas, escapado de caracteres, planificador, planificadores IA (Anthropic y GitHub Models) con respuestas simuladas, servidor web (Host/Origin, subidas, guardado), instalador, regla de dependencias, que `docs/` esté al día con el código y revisión de `SKILL.md`. También hay una prueba de presupuesto de tiempo (<1 s).

## 15. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| El `.drawio` abre como texto | Falta la extensión Draw.io Integration; instálala y reabre el archivo |
| `--open` no abre nada | El comando `code` no está en el PATH (ver sección 2) |
| `error: AWS002 unknown service` | Revisa la sugerencia del mensaje o ejecuta `catalog` |
| "Images need an AI mode" | Offline no interpreta imágenes: configura `GITHUB_MODELS_TOKEN` o `ANTHROPIC_API_KEY`, o describe la imagen en texto |
| HTTP 401/403 en modo GitHub | El token no tiene el permiso *Models: read* o expiró |
| HTTP 429 | Límite de GitHub Models alcanzado: espera o usa otro modo |
| PDF escaneado sin texto | Instala poppler (`pdftoppm`) y usa modo IA, o pasa las páginas como imágenes |
| La skill no aparece en Copilot | Recarga la ventana; confirma que la carpeta está en `.github/skills/<nombre>/SKILL.md` |
| El puerto 8765 está ocupado | `python scripts/run.py ui --port 8800` |

## 16. Límites y próximos pasos

- Solo AWS y VS Code por ahora. Siguientes pasos naturales: GCP/Azure, otros IDE, subredes y AZ, exportar PNG/SVG.
- El planificador offline es heurístico; para casos complejos usa un agente o el modo IA y revisa el resultado.
- La vista previa web no usa los íconos oficiales; el `.drawio` sí.

Licencia: pendiente de definir por el autor.
