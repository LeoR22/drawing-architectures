"""Renders a Layout as draw.io XML (uncompressed mxfile) using the AWS4 shape library."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..domain.layout import Layout, Rect
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


def node_style(kind: str, shape: str, color: str) -> str:
    if kind == "resource":
        return f"sketch=0;{_POINTS_ICON}{_COMMON}fillColor={color};strokeColor=#ffffff;dashed=0;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{shape};"
    return f"sketch=0;{_COMMON}gradientColor=none;fillColor={color};strokeColor=none;dashed=0;pointerEvents=1;shape=mxgraph.aws4.{shape};"


class DrawioRenderer:
    def render(self, arch: Architecture, layout: Layout) -> str:
        mxfile = ET.Element("mxfile", {"host": "drawio", "agent": "drawing-aws-architectures", "version": "24.0.0"})
        diagram = ET.SubElement(mxfile, "diagram", {"id": "aws-architecture", "name": arch.title[:60] or "AWS architecture"})
        model = ET.SubElement(diagram, "mxGraphModel", {
            "dx": "1200", "dy": "800", "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1",
            "connect": "1", "arrows": "1", "fold": "1", "page": "1", "pageScale": "1",
            "pageWidth": f"{int(layout.width)}", "pageHeight": f"{int(layout.height)}", "math": "0", "shadow": "0",
        })
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", {"id": "0"})
        ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

        title = ET.SubElement(root, "mxCell", {
            "id": "title", "value": arch.title, "parent": "1", "vertex": "1",
            "style": "text;html=1;align=left;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#232F3E;",
        })
        ET.SubElement(title, "mxGeometry", {"x": f"{layout.title_at[0]:g}", "y": f"{layout.title_at[1]:g}", "width": "700", "height": "30", "as": "geometry"})

        origins: dict[str, tuple[float, float]] = {"1": (0, 0)}
        for g in layout.groups:
            parent_origin = origins[g.parent]
            cell = ET.SubElement(root, "mxCell", {
                "id": g.id, "value": g.label, "parent": g.parent, "vertex": "1",
                "style": _GROUP_BASE + _POINTS_GROUP + _GROUP_STYLES[g.kind],
            })
            ET.SubElement(cell, "mxGeometry", {
                "x": f"{g.rect.x - parent_origin[0]:g}", "y": f"{g.rect.y - parent_origin[1]:g}",
                "width": f"{g.rect.w:g}", "height": f"{g.rect.h:g}", "as": "geometry",
            })
            origins[g.id] = (g.rect.x, g.rect.y)

        column_of = {}
        for n in layout.nodes:
            column_of[n.component.id] = (n.column, n.rect.y)
            parent_origin = origins[n.parent]
            cell = ET.SubElement(root, "mxCell", {
                "id": n.component.id, "value": n.component.label or n.service.label, "parent": n.parent, "vertex": "1",
                "style": node_style(n.service.kind, n.service.shape, n.service.color),
            })
            ET.SubElement(cell, "mxGeometry", {
                "x": f"{n.rect.x - parent_origin[0]:g}", "y": f"{n.rect.y - parent_origin[1]:g}",
                "width": "78", "height": "78", "as": "geometry",
            })

        for i, f in enumerate(arch.flows, 1):
            style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#232F3E;strokeWidth=2;fontSize=11;fontColor=#232F3E;labelBackgroundColor=#ffffff;"
            (c1, y1), (c2, y2) = column_of[f.source], column_of[f.target]
            if c2 > c1:
                style += "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
            elif c2 == c1:
                down = y2 > y1
                style += (
                    "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" if down
                    else "exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
                )
            if f.is_async:
                style += "dashed=1;"
            edge = ET.SubElement(root, "mxCell", {
                "id": f"edge{i}", "value": f.label, "style": style, "edge": "1", "parent": "1",
                "source": f.source, "target": f.target,
            })
            ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})

        ET.indent(mxfile)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(mxfile, encoding="unicode") + "\n"
