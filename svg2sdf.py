#!/usr/bin/python3

import xml.etree.ElementTree as ET
import argparse
import os
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape


unit_magnitude = {"m": 1, "dm": 0.1, "cm": 0.01, "mm": 0.001, "inch": 0.0254}
number_with_units_re = re.compile(r"([0-9]+)(m|dm|cm|mm)")

tmppath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

env = Environment(
    loader=FileSystemLoader(tmppath),
    autoescape=select_autoescape(["xml"])
)


def default_output_filename(path):
    filename = os.path.splitext(os.path.basename(path))[0]
    return filename + ".sdf"


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
    mx = sum(x for x,_ in path_coord)/len(path_coord)
    my = sum(y for _,y in path_coord)/len(path_coord)
    path_coord = [(x-mx, y-my) for x, y in path_coord]
    # path_coord = [(x-mx, my-y) for x, y in path_coord]
    # path_coord.reverse()
    path_coord.append(path_coord[0])
    return path_coord

def main(svg, output=None):
    output = output or default_output_filename(svg)
    assert os.path.isfile(svg)
    tree = ET.parse(svg)
    root = tree.getroot()
    width = get_length_as_number(root.attrib["width"])
    height = get_length_as_number(root.attrib["height"])
    view_box = [float(n) for n in root.attrib["viewBox"].split()]
    ns = {"default": "http://www.w3.org/2000/svg"}
    path = get_path_as_coordinates(
            root.find("default:g/default:path", namespaces=ns).attrib["d"],
            view_box, width, height)
    tmp = env.get_template("sdftemplate.sdf")
    out = tmp.render({"path": path, "height": 0.02})
    print(out)
    # print(width)
    # print(height)
    # print(view_box)
    # print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", help="SVG file with a simple shape")
    parser.add_argument("-o", "--output", help="Output file")
    args = parser.parse_args()
    main(args.svg, output=args.output)

