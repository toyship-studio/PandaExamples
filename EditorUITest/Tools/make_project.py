#!/usr/bin/env python3
"""Writes the content of EditorUITest: the worlds, the textures and the materials the UI tests of
the editor work on. The content is generated, not made by hand: change this file and run it again
(python3 Tools/make_project.py). Ids are derived from names, so they stay the same between runs
and a test may rely on what the world holds.

Two things are the editor's and are read here, not made: the sidecar of a texture (its id and
its import settings — the editor writes it when it first sees the file) and the ids of the script
fields (.Panda/scripts-manifest.json, written when the scripts are built). So after a new texture
or a change of a script class: run this file, open the project in the editor and build the
scripts (CMake panel, Scripts, Build), then run this file again.

What is there:
  Assets/world.world             the start world: a camera, a light, a sky, a crate, a group of two
                                 coins, a player with the Probe script (a field of every type)
  Assets/Levels/level1|2|10      worlds the Probe names in a list (and their natural order)
  Assets/Levels/spare.world      a world nothing names: a cook leaves it out
  Assets/Textures/*.png          three textures
  Assets/Frames/                 three numbered textures and a material: a folder to drop on a list
  Assets/Materials/*.mat         two materials
"""
import json
import os
import struct
import zlib

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(PROJECT, "Assets")
PBR_SHADER = 17  # the built-in PBR shader

TEXTURE, MATERIAL, WORLD = 1, 4, 7  # the asset types of a .pmeta sidecar
# The types of a script field: the number a world file writes, the name the script manifest writes.
INTEGER, FLOAT, ENTITY, TEXTURE_FIELD, MATERIAL_FIELD, WORLD_FIELD = 0, 1, 2, 3, 4, 5
FIELD_TYPE_NAMES = ["integer", "float", "entity", "texture", "material", "world", "font"]


def stable_id(name):
    value = zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF
    return value if value != 0 else 1


def vec3(x, y, z):
    return {"x": float(x), "y": float(y), "z": float(z)}


def vec4(x, y, z, w):
    return {"x": float(x), "y": float(y), "z": float(z), "w": float(w)}


def write_json(path, document):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(document, f, indent=4)
        f.write("\n")


def sidecar(relative, asset_type, meta=None):
    """The .pmeta of an asset: the one the editor has written is kept (its import settings are
    the editor's), a new one gets an id made of the path. Returns the asset id."""
    path = os.path.join(ASSETS, relative + ".pmeta")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)["id"]
    document = {"id": stable_id("asset:" + relative), "type": asset_type}
    if meta is not None:
        document["meta"] = meta
    write_json(path, document)
    return document["id"]


def texture(relative, pixel):
    """A 16x16 RGBA picture: `pixel(x, y)` gives the color of a pixel as (r, g, b, a) bytes."""
    size = 16
    rows = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(size)) for y in range(size))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
    path = os.path.join(ASSETS, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    # The sidecar of a texture is the editor's: None until it has seen the file.
    if not os.path.exists(path + ".pmeta"):
        return None
    with open(path + ".pmeta") as f:
        return json.load(f)["id"]


def material(relative, color):
    inputs = [
        {"name": "baseColorTexture", "type": 3, "value": 0},
        {"name": "baseColorFactor", "type": 4, "value": vec4(color[0], color[1], color[2], 1.0)},
        {"name": "metallicRoughnessTexture", "type": 3, "value": 0},
        {"name": "metallicFactor", "type": 0, "value": 0.0},
        {"name": "roughnessFactor", "type": 0, "value": 0.5},
        {"name": "normalTexture", "type": 3, "value": 0},
        {"name": "normalScale", "type": 0, "value": 1.0},
        {"name": "occlusionTexture", "type": 3, "value": 0},
        {"name": "occlusionStrength", "type": 0, "value": 0.0},
        {"name": "emissiveTexture", "type": 3, "value": 0},
        {"name": "emissiveFactor", "type": 4, "value": vec4(0, 0, 0, 1.0)},
        {"name": "alphaMode", "type": 1, "value": 0},
        {"name": "alphaCutoff", "type": 0, "value": 0.5},
        {"name": "doubleSided", "type": 1, "value": 0},
        {"name": "emissiveIntensity", "type": 0, "value": 1.0},
        {"name": "transmissionFactor", "type": 0, "value": 0.0},
    ]
    write_json(os.path.join(ASSETS, relative), {"inputs": inputs})
    return sidecar(relative, MATERIAL, {"shader": PBR_SHADER})


class World:
    """A world file: entities by name, ids made of the path of the name."""

    def __init__(self, relative):
        self.relative = relative
        self.entities = []
        self.paths = {}

    def entity(self, name, position=(0, 0, 0), parent=None, scripts=(), **components):
        path = (self.paths[parent["id"]] + "/" if parent else "") + name
        identifier = stable_id(self.relative + ":" + path)
        entity = {
            "id": identifier,
            "tagComponent": {"tag": name},
            "relationshipComponent": {"parent": parent["id"] if parent else 0, "children": []},
            "transformComponent": {"position": vec3(*position), "rotation": vec4(0, 0, 0, 1), "scale": vec3(1, 1, 1)},
        }
        entity.update(components)
        entity["scriptListComponent"] = {"scripts": list(scripts)}
        if parent:
            parent["relationshipComponent"]["children"].append(identifier)
        self.entities.append(entity)
        self.paths[identifier] = path
        return entity

    def sprite(self, name, color, **placement):
        return self.entity(name, spriteRendererComponent={
            "color": vec4(color[0], color[1], color[2], 1.0), "cols": 1, "rows": 1, "index": 0, "material": 0, "texture": 0,
        }, **placement)

    def camera(self, name="Camera", position=(0, 0, 6)):
        return self.entity(name, position=position, cameraComponent={
            "isPrimary": True,
            "camera": {"projectionType": 0, "fieldOfView": 70.0, "orthoSize": 1.0, "zNear": 0.1, "zFar": 1000.0},
        })

    def write(self):
        write_json(os.path.join(ASSETS, self.relative), {
            "lighting": {"ambientColor": vec4(1, 1, 1, 1), "ambientIntensity": 0.12},
            "entities": self.entities,
        })
        return sidecar(self.relative, WORLD)


def script(name, values):
    """A script of an entity with the values of its fields: {field: (type, value)}. The ids of the
    fields come from the manifest the editor wrote for the last script build."""
    classes = script_classes()
    declared = {field["name"]: field for field in classes[name]["scriptFields"]}
    missing = sorted(set(declared) - set(values))
    unknown = sorted(set(values) - set(declared))
    if missing or unknown:
        raise SystemExit("%s: fields without a value %s, values without a field %s" % (name, missing, unknown))
    fields = []
    for field_name, field in declared.items():
        field_type, value = values[field_name]
        if FIELD_TYPE_NAMES[field_type] != field["type"] or isinstance(value, list) != bool(field.get("list", False)):
            raise SystemExit("%s.%s: the class says type %s, list %s" % (name, field_name, field["type"], field.get("list", False)))
        fields.append({"name": field_name, "fieldId": field["fieldId"], "type": field_type, "value": value})
    return {"name": name, "scriptFields": fields}


def script_classes():
    """The script classes of the last build by name; empty — the scripts were never built."""
    path = os.path.join(PROJECT, ".Panda", "scripts-manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {entry["name"]: entry for entry in json.load(f).get("scripts", [])}


def main():
    checker = texture("Textures/checker.png", lambda x, y: (235, 235, 235, 255) if (x // 4 + y // 4) % 2 else (40, 40, 40, 255))
    texture("Textures/dots.png", lambda x, y: (250, 200, 60, 255) if (x % 4 == 1 and y % 4 == 1) else (30, 60, 110, 255))
    texture("Textures/stripes.png", lambda x, y: (220, 70, 60, 255) if (x // 2) % 2 else (250, 240, 230, 255))
    # A folder of numbered pictures next to a material: dropped on a list of textures it gives its
    # three pictures in the order of their numbers, and not the material.
    for number in (1, 2, 10):
        texture("Frames/frame%d.png" % number, lambda x, y, n=number: (20 * n % 256, 120, 200, 255) if x < 8 else (240, 240, 240, 255))
    material("Frames/tint.mat", (0.2, 0.7, 0.9))
    red = material("Materials/red.mat", (0.85, 0.2, 0.2))
    material("Materials/blue.mat", (0.2, 0.35, 0.85))

    levels = {}
    for number in (1, 2, 10):
        level = World("Levels/level%d.world" % number)
        level.camera()
        level.sprite("Flag %d" % number, (0.2, 0.8, 0.3))
        levels[number] = level.write()
    spare = World("Levels/spare.world")
    spare.camera()
    spare.write()

    if checker is None or "Probe" not in script_classes():
        raise SystemExit(
            "The pictures, the materials and the levels are written. The start world waits for the editor:\n"
            "open the project in it (it registers the new pictures), build the scripts (CMake panel, Scripts,\n"
            "Build), then run this file again."
        )

    world = World("world.world")
    world.camera()
    # Aside: the icon of a light is picked like the entity, and the middle of the picture is the crate's.
    world.entity("Sun", position=(-3, 3, 0), directionalLightComponent={"color": vec4(1, 1, 1, 1), "intensity": 1.0, "isEnabled": True})
    world.entity("Sky", cubeMapComponent={"material": 0})
    crate = world.sprite("Crate", (1.0, 0.5, 0.2))
    group = world.entity("Group", position=(0, 1.5, 0))
    coin_a = world.sprite("Coin A", (1.0, 0.85, 0.2), position=(-2, 0, 0), parent=group)
    coin_b = world.sprite("Coin B", (1.0, 0.85, 0.2), position=(2, 0, 0), parent=group)
    world.sprite("Player", (0.25, 0.5, 1.0), position=(0, -1.5, 0), scripts=[script("Probe", {
        "count": (INTEGER, 3),
        "speed": (FLOAT, 1.5),
        "target": (ENTITY, crate["id"]),
        "icon": (TEXTURE_FIELD, checker),
        "skin": (MATERIAL_FIELD, red),
        "next": (WORLD_FIELD, levels[1]),
        "numbers": (INTEGER, [1, 2, 3]),
        "levels": (WORLD_FIELD, [levels[1], levels[2]]),
        "frames": (TEXTURE_FIELD, []),
        "waypoints": (ENTITY, [coin_a["id"], coin_b["id"]]),
    })])
    world.write()
    print("EditorUITest: the content is written to", ASSETS)


if __name__ == "__main__":
    main()
