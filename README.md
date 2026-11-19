# drawing-architectures

Colección de **Agent Skills** para generar arquitecturas cloud de alto nivel como diagramas editables. Cada skill vive en su propia carpeta dentro de `skills/` y es independiente.

| Skill | Nube | Salida | Editor | Estado |
|---|---|---|---|---|
| [`drawing-aws-architectures`](skills/drawing-aws-architectures/) | AWS | draw.io (`.drawio`, 4 niveles: system design agnóstico → visión general → servicios → detalle) | VS Code | Disponible |
| `drawing-gcp-architectures` | GCP | draw.io | VS Code | Planeada |
| `drawing-azure-architectures` | Azure | draw.io | VS Code | Planeada |

## Inicio rápido (AWS)

```bash
git clone https://github.com/LeoR22/drawing-architectures.git
cd drawing-architectures/skills/drawing-aws-architectures
python scripts/run.py plan "Portal web con login, base de datos SQL y colas" -o arq.drawio --open
```

La guía completa (instalación en VS Code, interfaz web local, formato del spec, arquitectura del código) está en [`skills/drawing-aws-architectures/README.md`](skills/drawing-aws-architectures/README.md).

## Versión web (sin instalar nada)

https://leor22.github.io/drawing-architectures/ — la misma interfaz corriendo en tu navegador (Pyodide). Detalles y cómo publicarla en la guía de la skill.

## Estructura

```
skills/
  drawing-aws-architectures/   SKILL.md, scripts/, reference/, examples/, tests/
docs/                          sitio estático (GitHub Pages), generado con scripts/build_web.py
```

Para instalar una skill en un proyecto de VS Code, ejecuta desde su carpeta:
`python scripts/run.py install --scope project --target copilot --project "<ruta del proyecto>"`.
