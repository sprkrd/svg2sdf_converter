#!/usr/bin/python3

import xml.etree.ElementTree as ET
import argparse
import os
import re
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape


unit_magnitude = {"m": 1, "dm": 0.1, "cm": 0.01, "mm": 0.001, "inch": 0.0254}
number_with_units_re = re.compile(r"([0-9]+)(m|dm|cm|mm)")

scrpath = os.path.dirname(os.path.realpath(__file__))
tmppath = os.path.join(scrpath, "templates")

env = Environment(
    loader=FileSystemLoader(tmppath),
    autoescape=select_autoescape(["xml"])
)


colors = {}


with open(os.path.join(scrpath, "xkcd_colors.txt"), "r") as f:
    for line in f:
        if line[0] != "#":
            name, html_color = line.split("\t")[:2]
            name = name.replace(" ", "_")
            r = int(html_color[1:3], 16)/255
            g = int(html_color[3:5], 16)/255
            b = int(html_color[5:7], 16)/255
            colors[name] = (r, g, b)


def inertia_moments(path, height, mass):
    xmin = min(x for x,_ in path)
    xmax = max(x for x,_ in path)
    ymin = min(y for _,y in path)
    ymax = max(y for _,y in path)
    width = xmax - xmin
    depth = ymax - ymin
    inertia = {
        "ixx": mass * (depth**2 + height**2) / 12,
        "ixy": 0.0,
        "ixz": 0.0,
        "iyy": mass * (width**2 + height**2) / 12,
        "iyz": 0.0,
        "izz": mass * (width**2 + depth**2) / 12,
    }
    return inertia


def get_length_as_number(length):
    match = number_with_units_re.match(length)
    number = float(match.group(1))
    unit = match.group(2)
    return number * unit_magnitude[unit]


def get_path_as_coordinates(path_str, view_box=None, width=1, height=1):
    view_box = view_box or [0, 0, 1, 1]
    sx = width/(view_box[2] - view_box[0])
    sy = height/(view_box[3] - view_box[1])
    path_rel = [tuple(float(n) for n in t.split(","))
                for t in path_str[2:-2].split(" ")]
    # return path_rel
    path_coord = [(path_rel[0][0]*sx, path_rel[0][1]*sy)]
    for dx, dy in path_rel[1:]:
        x, y = path_coord[-1]
        path_coord.append((x + dx*sx, y + dy*sy))
    mx = (max(x for x,_ in path_coord) + min(x for x,_ in path_coord))/2
    my = (max(y for _,y in path_coord) + min(y for _,y in path_coord))/2
    # mx = sum(x for x,_ in path_coord)/len(path_coord)
    # my = sum(y for _,y in path_coord)/len(path_coord)
    # path_coord = [(x-mx, y-my) for x, y in path_coord]
    path_coord = [(x-mx, my-y) for x, y in path_coord]
    # path_coord.reverse()
    # path_coord.append(path_coord[0])
    return path_coord


def main(svg, mass=1.0, thickness=0.01, color="grey", out=None):
    assert os.path.isfile(svg)
    name = os.path.splitext(os.path.basename(svg))[0]
    tree = ET.parse(svg)
    root = tree.getroot()
    width = get_length_as_number(root.attrib["width"])
    height = get_length_as_number(root.attrib["height"])
    view_box = [float(n) for n in root.attrib["viewBox"].split()]
    ns = {"default": "http://www.w3.org/2000/svg"}
    path = get_path_as_coordinates(
            root.find("default:g/default:path", namespaces=ns).attrib["d"],
            view_box, width, height)
    inertia = inertia_moments(path, mass, height)
    tmp_sdf = env.get_template("model.sdf")
    tmp_config = env.get_template("model.config")
    ambient = tuple(map(lambda x: 0.1*x, colors[color]))
    diffuse = colors[color]
    context = {
        "path": path,
        "thickness": thickness,
        "mass": mass,
        "name": name,
        "inertia": inertia,
        "ambient": ambient,
        "diffuse": diffuse,
    }
    if out is None: out = os.path.join(".", name)
    out_sdf = os.path.join(out, "model.sdf")
    out_config = os.path.join(out, "model.config")
    if not os.path.isdir(out):
        os.makedirs(out)
    sdf = tmp_sdf.render(context)
    config = tmp_config.render(context)
    with open(out_sdf, "w") as f:
        f.write(sdf)
        print("Written SDF to " + out_sdf)
    with open(out_config, "w") as f:
        f.write(config)
        print("Written config to " + out_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", help="SVG file with a simple shape")
    parser.add_argument("-m", "--mass", help="Mass of the object", type=float,
                        default=1.0)
    parser.add_argument("-t", "--thickness", help="Thickness of the extrusion",
                        type=float, default=0.01)
    parser.add_argument("-c", "--color", help="Color of the object (XKCD id)",
                        default="grey")
    parser.add_argument("-o", "--out", help="Output directory")
    args = parser.parse_args()
    main(args.svg, mass=args.mass, thickness=args.thickness,
         color=args.color, out=args.out)

