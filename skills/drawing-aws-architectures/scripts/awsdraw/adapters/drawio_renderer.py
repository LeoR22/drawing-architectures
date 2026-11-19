"""Renders an Architecture as a draw.io file with four pages (tabs), from simple to detailed:

1. System design: vendor-neutral building blocks (client, CDN, service, queue, database...).
2. Visión general: four plain-language blocks + a numbered story anyone can read aloud.
3. Servicios AWS: official icons, flat, with the plain-language role under each icon.
4. Detalle técnico: Cloud / Region / VPC boxes and flow labels.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from ..domain import capabilities, overview as overview_mod, overview_layout as ovl, system_design
from ..domain.layout import Layout, Rect, skips_over
from ..domain.models import Architecture

_POINTS_ICON = (
    "points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
    "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
)
_POINTS_GROUP = (
    "points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],"
    "[0,1],[0,0.75],[0,0.5],[0,0.25]];"
)
_COMMON = "outlineConnect=0;fontColor=#232F3E;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;"
_GROUP_BASE = "sketch=0;outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=0;container=1;collapsible=0;shape=mxgraph.aws4.group;"
_GROUP_STYLES = {
    "cloud": "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#232F3E;dashed=0;",
    "region": "grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#147EBA;dashed=1;",
    "vpc": "grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#AAB7B8;dashed=0;",
}
# fill, stroke per level-1 column (people, entry, logic, data)
_BLOCK_COLORS = {0: ("#232F3D", "#232F3D", "#FFFFFF"), 1: ("#EFE8FF", "#8C4FFF", "#232F3E"), 2: ("#FFF1E0", "#ED7100", "#232F3E"), 3: ("#F7E6FA", "#C925D1", "#232F3E")}
_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#232F3E;strokeWidth=2;fontSize=11;fontColor=#232F3E;labelBackgroundColor=#ffffff;"
SERVICE_PAGE_MARGIN = (40, 110)
_SHAPES = {  # kind.shape -> (width, height, style template, label position)
    "actor": (40, 70, "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fontSize=12;fontColor=#232F3E;strokeColor={stroke};fillColor={fill};strokeWidth=2;", "below"),
    "hexagon": (130, 64, "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fixedSize=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "cloud": (130, 76, "ellipse;shape=cloud;whiteSpace=wrap;html=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "service": (130, 64, "rounded=1;whiteSpace=wrap;html=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "cylinder": (100, 78, "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=14;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "process": (130, 64, "shape=process;whiteSpace=wrap;html=1;backgroundOutline=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "model": (130, 64, "rounded=1;arcSize=30;whiteSpace=wrap;html=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=2;", "in"),
    "support": (130, 64, "rounded=1;whiteSpace=wrap;html=1;dashed=1;fontSize=12;fontColor=#232F3E;fillColor={fill};strokeColor={stroke};strokeWidth=1;", "in"),
}


def node_style(kind: str, shape: str, color: str) -> str:
    if kind == "resource":
        return f"sketch=0;{_POINTS_ICON}{_COMMON}fillColor={color};strokeColor=#ffffff;dashed=0;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{shape};"
    return f"sketch=0;{_COMMON}gradientColor=none;fillColor={color};strokeColor=none;dashed=0;pointerEvents=1;shape=mxgraph.aws4.{shape};"


def _cell(root, cid, value, style, parent="1", vertex=True, **extra):
    attrs = {"id": cid, "value": value, "style": style, "parent": parent}
    attrs["vertex" if vertex else "edge"] = "1"
    attrs.update(extra)
    return ET.SubElement(root, "mxCell", attrs)


def _geo(cell, x, y, w, h):
    ET.SubElement(cell, "mxGeometry", {"x": f"{x:g}", "y": f"{y:g}", "width": f"{w:g}", "height": f"{h:g}", "as": "geometry"})


def _page(mxfile, page_id, name, width, height):
    diagram = ET.SubElement(mxfile, "diagram", {"id": page_id, "name": name})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1200", "dy": "800", "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1", "connect": "1",
        "arrows": "1", "fold": "1", "page": "1", "pageScale": "1", "pageWidth": f"{int(width)}", "pageHeight": f"{int(height)}",
        "math": "0", "shadow": "0",
    })
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    return root


def _heading(root, title, subtitle, x, y):
    _geo(_cell(root, "title", escape(title), "text;html=1;align=left;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#232F3E;"), x, y, 900, 30)
    _geo(_cell(root, "subtitle", escape(subtitle), "text;html=1;align=left;verticalAlign=middle;fontSize=13;fontColor=#687078;"), x, y + 30, 900, 24)


def _edge(root, eid, source, target, label, style_extra, forward, same_column_down, over=False):
    style = _EDGE + style_extra
    if over:  # skips a column: arch over the top so it never crosses the boxes in between
        style += "exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
    elif forward:
        style += "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
    elif same_column_down is not None:
        style += (
            "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" if same_column_down
            else "exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
        )
    edge = _cell(root, eid, escape(label), style, vertex=False, source=source, target=target)
    ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})


def _flow_geometry(column_of, source, target):
    (c1, y1), (c2, y2) = column_of[source], column_of[target]
    return c2 > c1, (y2 > y1 if c2 == c1 else None)


class DrawioRenderer:
    def render(self, arch: Architecture, layout: Layout) -> str:
        mxfile = ET.Element("mxfile", {"host": "drawio", "agent": "drawing-aws-architectures", "version": "24.0.0"})
        ov = overview_mod.build(arch)
        self._system_design_page(mxfile, arch, layout)
        self._overview_page(mxfile, ov, ovl.compute(ov), arch.title)
        self._services_page(mxfile, arch, layout)
        self._technical_page(mxfile, arch, layout)
        ET.indent(mxfile)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(mxfile, encoding="unicode") + "\n"

    # ---- level 1: vendor-neutral system design ---------------------------------------------
    def _system_design_page(self, mxfile, arch, layout):
        xs = [n.rect.x for n in layout.nodes]
        ys = [n.rect.y for n in layout.nodes]
        dx, dy = SERVICE_PAGE_MARGIN[0] - min(xs), SERVICE_PAGE_MARGIN[1] - min(ys)
        width = max(xs) + 78 + dx + 100
        height = max(ys) + 108 + dy + 110
        root = _page(mxfile, "level-1", "1 · System design", width, height)
        _heading(root, f"Nivel 1 · System design: {arch.title}", "El entorno general de la solución con bloques genéricos, sin nombres de servicios: sirve para cualquier nube.", 40, 20)
        column_of = {}
        for n in layout.nodes:
            kind = system_design.kind_of(n.component)
            label = escape(system_design.generic_label(n.component))
            w, h, style, lab = _SHAPES[kind.shape]
            style = style.format(fill=kind.fill, stroke=kind.stroke)
            cx, cy = n.rect.x + dx + 39, n.rect.y + dy + 39
            column_of[n.component.id] = (n.column, n.rect.y)
            _geo(_cell(root, n.component.id, label, style), cx - w / 2, cy - h / 2 - (10 if kind.shape == "actor" else 0), w, h)
        self._flows(root, arch, column_of, layout)
        legend = ("<b>Cómo leerlo:</b> figura humana = quien usa el sistema · hexágono = punto de entrada o control · nube = red de entrega · "
                  "rectángulo = servicio · cilindro = datos · rectángulo con barras = cola o flujo de mensajes · gris punteado = apoyo (seguridad, monitoreo) · línea punteada = proceso asíncrono.")
        _geo(_cell(root, "legend", legend, "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=12;fontColor=#232F3E;fillColor=#FAFAFA;strokeColor=#D5DBDB;spacing=8;"), 40, height - 80, max(width - 80, 400), 60)

    # ---- level 2 -------------------------------------------------------------------------
    def _overview_page(self, mxfile, ov, lay, title):
        root = _page(mxfile, "level-2", "2 · Visión general", lay.width, lay.height)
        _heading(root, f"Nivel 2 · Visión general: {title}", "Qué hace el sistema, en palabras simples. Los números siguen la historia de abajo.", *lay.title_at)
        for box in ov.boxes:
            fill, stroke, font = _BLOCK_COLORS[box.column]
            rect = lay.boxes[box.key]
            bullets = "".join(f"<br>• {escape(i)}" for i in box.items) if box.key != "people" else ""
            aws = f"<br><font style=\"font-size:10px\" color=\"#687078\">AWS: {escape(', '.join(box.services))}</font>" if box.key != "people" else ""
            value = (f"<b style=\"font-size:15px\">{escape(box.title)}</b><br><font style=\"font-size:11px\">{escape(box.does)}</font>{bullets}{aws}")
            style = f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=2;fontColor={font};align=left;spacingLeft=12;spacingRight=8;verticalAlign=middle;fontSize=12;"
            _geo(_cell(root, f"box_{box.key}", value, style), rect.x, rect.y, rect.w, rect.h)
        columns = {b.key: b.column for b in ov.boxes}
        for link in ov.links:
            src, dst = lay.boxes[link.source], lay.boxes[link.target]
            order = {k: i for i, k in enumerate(sorted(set(columns.values())))}
            gap = order[columns[link.target]] - order[columns[link.source]]
            forward = gap > 0
            same = None if forward else (dst.y > src.y)
            _edge(root, f"link{link.step}", f"box_{link.source}", f"box_{link.target}", str(link.step),
                  "labelBackgroundColor=#ED7100;fontColor=#FFFFFF;fontStyle=1;fontSize=13;", forward, same, over=gap > 1)
        if ov.support and lay.band_label:
            _geo(_cell(root, "band_label", "Siempre activos: seguridad y operación (protegen y vigilan todo lo anterior)", "text;html=1;align=left;verticalAlign=middle;fontSize=13;fontStyle=1;fontColor=#232F3E;"), *_xywh(lay.band_label))
            for b in ov.support:
                value = f"<b>{escape(b.title)}</b><br><font style=\"font-size:11px\">{escape(b.does)}</font><br><font style=\"font-size:10px\" color=\"#687078\">AWS: {escape(', '.join(b.services))}</font>"
                style = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F2F3F3;strokeColor=#879196;dashed=1;fontColor=#232F3E;align=left;spacingLeft=10;spacingRight=6;fontSize=12;"
                _geo(_cell(root, f"chip_{b.key}", value, style), *_xywh(lay.chips[b.key]))
        lines = "".join(f"<p style=\"margin:4px 0\">{escape(line)}</p>" for line in ov.story)
        story = f"<b>Cómo explicarlo, paso a paso</b>{lines}"
        _geo(_cell(root, "story", story, "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=13;fontColor=#232F3E;fillColor=#FAFAFA;strokeColor=#D5DBDB;spacing=10;"), *_xywh(lay.story))

    # ---- level 2 -------------------------------------------------------------------------
    def _services_page(self, mxfile, arch, layout):
        xs = [n.rect.x for n in layout.nodes]
        ys = [n.rect.y for n in layout.nodes]
        dx, dy = SERVICE_PAGE_MARGIN[0] - min(xs), SERVICE_PAGE_MARGIN[1] - min(ys)
        width = max(xs) + 78 + dx + 60
        height = max(ys) + 108 + dy + 40
        root = _page(mxfile, "level-3", "3 · Servicios AWS", width, height)
        _heading(root, "Nivel 3 · Servicios de AWS", "Qué servicio hace cada parte. Debajo de cada ícono está su función en palabras simples.", 40, 20)
        column_of = {}
        for n in layout.nodes:
            column_of[n.component.id] = (n.column, n.rect.y)
            role = capabilities.of(n.service.key).title
            label = escape(n.component.label or n.service.label)
            value = f"{label}<br><font style=\"font-size:10px\" color=\"#687078\">{escape(role)}</font>"
            _geo(_cell(root, n.component.id, value, node_style(n.service.kind, n.service.shape, n.service.color)), n.rect.x + dx, n.rect.y + dy, 78, 78)
        self._flows(root, arch, column_of, layout)

    # ---- level 3 -------------------------------------------------------------------------
    def _technical_page(self, mxfile, arch, layout):
        root = _page(mxfile, "level-4", "4 · Detalle técnico", layout.width, layout.height)
        _heading(root, "Nivel 4 · Detalle técnico", f"{arch.title}. Nube, región, red privada (VPC) y flujos. Línea punteada = proceso asíncrono.", *layout.title_at)
        origins = {"1": (0, 0)}
        for g in layout.groups:
            ox, oy = origins[g.parent]
            _geo(_cell(root, g.id, escape(g.label), _GROUP_BASE + _POINTS_GROUP + _GROUP_STYLES[g.kind], parent=g.parent), g.rect.x - ox, g.rect.y - oy, g.rect.w, g.rect.h)
            origins[g.id] = (g.rect.x, g.rect.y)
        column_of = {}
        for n in layout.nodes:
            column_of[n.component.id] = (n.column, n.rect.y)
            ox, oy = origins[n.parent]
            _geo(_cell(root, n.component.id, escape(n.component.label or n.service.label), node_style(n.service.kind, n.service.shape, n.service.color), parent=n.parent), n.rect.x - ox, n.rect.y - oy, 78, 78)
        self._flows(root, arch, column_of, layout)

    @staticmethod
    def _flows(root, arch, column_of, layout):
        for i, f in enumerate(arch.flows, 1):
            forward, down = _flow_geometry(column_of, f.source, f.target)
            over = skips_over(layout.nodes, f.source, f.target)
            _edge(root, f"edge{i}", f.source, f.target, f.label, "dashed=1;" if f.is_async else "", forward, down, over=over)


def _xywh(rect: Rect):
    return rect.x, rect.y, rect.w, rect.h
