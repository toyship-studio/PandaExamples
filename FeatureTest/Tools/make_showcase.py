#!/usr/bin/env python3
"""Writes the showcase world of FeatureTest: Assets/showcase.world and the materials in
Assets/Showcase/Materials. The world is generated, not edited by hand: change this file and run
it again (python3 Tools/make_showcase.py), then Reload in the editor. Ids are derived from names,
so they stay the same between runs.

The scene is a stage for the renderer: a ground, rows of spheres that sweep roughness for a
dielectric and a metal, a shelf of typical materials, glTF models (Poly Haven, CC0), props that
show contact shadows and occlusion (a wall corner, stacked boxes, a pole, a floating slab), point
lights, the sun of the environment map.
"""
import json
import math
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdri_sun import sun_of  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(PROJECT, "Assets")
PBR_SHADER = 17  # the built-in PBR shader (StaticResources::defaultPbrShader)
ENVIRONMENT = "Environment/kloofendal_48d_partly_cloudy_puresky.hdr"

TONEMAP = os.environ.get("SHOWCASE_TONEMAP", "agx")
EXPOSURE = float(os.environ.get("SHOWCASE_EXPOSURE", "-1.4"))

CUBE, SPHERE, CAPSULE, PLANE, CYLINDER = 0, 1, 2, 3, 4


def stable_id(name):
    value = zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF
    return value if value != 0 else 1


def asset_id(relative):
    """The id of an asset the editor has registered (its .pmeta sidecar)."""
    with open(os.path.join(ASSETS, relative + ".pmeta")) as f:
        return json.load(f)["id"]


def vec3(x, y, z):
    return {"x": float(x), "y": float(y), "z": float(z)}


def vec4(x, y, z, w):
    return {"x": float(x), "y": float(y), "z": float(z), "w": float(w)}


def quat_from_axis_angle(axis, degrees):
    half = math.radians(degrees) / 2
    s = math.sin(half)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(half))


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def quat_look(direction):
    """The rotation that turns the local -Z axis along `direction` (yaw around Y, then pitch)."""
    x, y, z = direction
    length = math.sqrt(x * x + y * y + z * z)
    x, y, z = x / length, y / length, z / length
    yaw = math.degrees(math.atan2(-x, -z))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, y))))
    return quat_mul(quat_from_axis_angle((0, 1, 0), yaw), quat_from_axis_angle((1, 0, 0), pitch))


IDENTITY = (0.0, 0.0, 0.0, 1.0)


class World:
    def __init__(self):
        self.entities = []
        self.by_id = {}

    def entity(self, name, position=(0, 0, 0), rotation=IDENTITY, scale=(1, 1, 1), parent=None, **components):
        path = (parent["_path"] + "/" if parent else "") + name
        identifier = stable_id(path)
        if identifier in self.by_id:
            raise SystemExit("two entities are named " + path)
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale)
        entity = {
            "id": identifier,
            "tagComponent": {"tag": name},
            "relationshipComponent": {"parent": parent["id"] if parent else 0, "children": []},
            "transformComponent": {
                "position": vec3(*position),
                "rotation": vec4(*rotation),
                "scale": vec3(*scale),
            },
        }
        entity.update(components)
        entity["scriptListComponent"] = {"scripts": []}
        entity["_path"] = path
        if parent:
            parent["relationshipComponent"]["children"].append(identifier)
        self.entities.append(entity)
        self.by_id[identifier] = entity
        return entity

    def primitive(self, name, kind, material, **placement):
        return self.entity(name, primitiveMeshComponent={"kind": kind, "material": material}, **placement)

    def gltf(self, name, relative, parent=None, **placement):
        """A glTF asset as the editor adds it to a world: the root is the file, under it an
        entity per node, and an entity per primitive under the node that has the mesh."""
        mesh = asset_id(relative)
        with open(os.path.join(ASSETS, relative)) as f:
            data = json.load(f)
        holder = self.entity(name, parent=parent, **placement)
        root = self.entity(os.path.basename(relative), parent=holder)

        def fill(entity, node):
            transform = entity["transformComponent"]
            if "translation" in node:
                transform["position"] = vec3(*node["translation"])
            if "rotation" in node:
                transform["rotation"] = vec4(*node["rotation"])
            if "scale" in node:
                transform["scale"] = vec3(*node["scale"])
            if "matrix" in node:
                raise SystemExit(relative + ": a node with a matrix is not handled")
            if "mesh" in node:
                for index in range(len(data["meshes"][node["mesh"]]["primitives"])):
                    self.entity("primitive %d" % index, parent=entity, importedSubmeshComponent={
                        "importedMesh": mesh, "overrideMaterial": 0,
                        "submeshIndex": node["mesh"], "primitiveIndex": index,
                    })
            for child_index in node.get("children", []):
                child = data["nodes"][child_index]
                fill(self.entity(child.get("name", "node %d" % child_index), parent=entity), child)

        scene = data["scenes"][data.get("scene", 0)]
        for node_index in scene["nodes"]:
            node = data["nodes"][node_index]
            fill(self.entity(node.get("name", "node %d" % node_index), parent=root), node)
        return holder

    def write(self, relative, settings):
        document = dict(settings)
        document["entities"] = [{k: v for k, v in e.items() if k != "_path"} for e in self.entities]
        with open(os.path.join(ASSETS, relative), "w") as f:
            json.dump(document, f, indent=4)
            f.write("\n")


def material(name, color=(1, 1, 1), metallic=0.0, roughness=0.5, emissive=(0, 0, 0), emissive_intensity=1.0,
             base_color_texture=0, alpha=1.0, alpha_mode=0):
    """A PBR material of the showcase: the .mat (the inputs of the built-in PBR shader, in its
    order) and its sidecar. Returns the asset id."""
    relative = "Showcase/Materials/%s.mat" % name
    path = os.path.join(ASSETS, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    inputs = [
        {"name": "baseColorTexture", "type": 3, "value": base_color_texture},
        {"name": "baseColorFactor", "type": 4, "value": vec4(color[0], color[1], color[2], alpha)},
        {"name": "metallicRoughnessTexture", "type": 3, "value": 0},
        {"name": "metallicFactor", "type": 0, "value": float(metallic)},
        {"name": "roughnessFactor", "type": 0, "value": float(roughness)},
        {"name": "normalTexture", "type": 3, "value": 0},
        {"name": "normalScale", "type": 0, "value": 1.0},
        {"name": "occlusionTexture", "type": 3, "value": 0},
        {"name": "occlusionStrength", "type": 0, "value": 0.0},
        {"name": "emissiveTexture", "type": 3, "value": 0},
        {"name": "emissiveFactor", "type": 4, "value": vec4(emissive[0], emissive[1], emissive[2], 1.0)},
        {"name": "alphaMode", "type": 1, "value": alpha_mode},
        {"name": "alphaCutoff", "type": 0, "value": 0.5},
        {"name": "doubleSided", "type": 1, "value": 0},
        {"name": "emissiveIntensity", "type": 0, "value": float(emissive_intensity)},
    ]
    with open(path, "w") as f:
        json.dump({"inputs": inputs}, f, indent=4)
        f.write("\n")
    sidecar = path + ".pmeta"
    if os.path.exists(sidecar):
        with open(sidecar) as f:
            return json.load(f)["id"]
    identifier = stable_id("material:" + relative)
    with open(sidecar, "w") as f:
        json.dump({"id": identifier, "type": 4, "meta": {"shader": PBR_SHADER}}, f, indent=4)
        f.write("\n")
    return identifier


def main():
    world = World()
    sun = sun_of(os.path.join(ASSETS, ENVIRONMENT))
    to_sun = sun["direction"]

    # ----- the light -----
    world.entity("Sky", cubeMapComponent={"material": 0})
    world.entity(
        "Sun", position=(0, 6, 0), rotation=quat_look([-c for c in to_sun]),
        directionalLightComponent={
            "color": vec4(sun["color"][0], sun["color"][1], sun["color"][2], 1.0),
            "intensity": 12.0, "isEnabled": True, "castShadows": True,
        },
    )
    camera_position = (0.0, 2.7, 9.2)
    camera_target = (0.0, 0.75, 0.0)
    world.entity(
        "Camera", position=camera_position,
        rotation=quat_look([t - p for t, p in zip(camera_target, camera_position)]),
        cameraComponent={
            "isPrimary": True,
            "camera": {"projectionType": 0, "fieldOfView": 38.0, "orthoSize": 1.0, "zNear": 0.1, "zFar": 500.0},
            "postprocessing": 0, "postprocessingEnabled": True,
            "bloomEnabled": True, "bloomIntensity": 0.6, "bloomRadius": 1.0,
            "autoExposureEnabled": False, "autoExposureKey": 0.18, "autoExposureSpeed": 2.0,
            "autoExposureMin": 0.25, "autoExposureMax": 4.0,
            "tonemap": TONEMAP, "exposure": EXPOSURE,
        },
    )

    # ----- the stage -----
    ground = material("ground", color=(0.42, 0.42, 0.42), roughness=0.75)
    world.primitive("Ground", PLANE, ground, scale=(60, 1, 60))

    # Roughness sweeps on two steps behind the shelf: a dielectric and a metal row.
    step = material("step", color=(0.5, 0.5, 0.52), roughness=0.6)
    sweep = world.entity("Roughness Sweep", position=(0, 0, -1.0))
    world.primitive("Step 1", CUBE, step, parent=sweep, position=(0, 0.2, -0.45), scale=(7.2, 0.4, 1.9))
    world.primitive("Step 2", CUBE, step, parent=sweep, position=(0, 0.6, -0.9), scale=(7.2, 0.4, 1.0))
    count = 7
    for index in range(count):
        roughness = 0.05 + (1.0 - 0.05) * index / (count - 1)
        x = (index - (count - 1) / 2) * 0.9
        plastic = material("plastic_r%02d" % round(roughness * 100), color=(0.8, 0.08, 0.06), roughness=roughness)
        metal = material("gold_r%02d" % round(roughness * 100), color=(1.0, 0.77, 0.34), metallic=1.0,
                         roughness=roughness)
        world.primitive("Plastic %d" % index, SPHERE, plastic, parent=sweep, position=(x, 0.75, 0.05), scale=0.7)
        world.primitive("Gold %d" % index, SPHERE, metal, parent=sweep, position=(x, 1.15, -0.9), scale=0.7)

    # Typical materials.
    shelf = world.entity("Materials", position=(0, 0, 0.6))
    samples = [
        ("Chrome", material("chrome", color=(0.95, 0.95, 0.95), metallic=1.0, roughness=0.03)),
        ("Copper", material("copper", color=(0.95, 0.64, 0.54), metallic=1.0, roughness=0.3)),
        ("Brushed Steel", material("steel", color=(0.56, 0.57, 0.58), metallic=1.0, roughness=0.5)),
        ("White Ceramic", material("ceramic", color=(0.9, 0.9, 0.88), roughness=0.12)),
        ("Blue Paint", material("paint_blue", color=(0.05, 0.2, 0.75), roughness=0.3)),
        ("Black Rubber", material("rubber", color=(0.03, 0.03, 0.03), roughness=0.9)),
        ("Emissive", material("emissive", color=(0.02, 0.02, 0.02), roughness=0.4, emissive=(1.0, 0.45, 0.1),
                              emissive_intensity=12.0)),
    ]
    for index, (name, identifier) in enumerate(samples):
        x = (index - (len(samples) - 1) / 2) * 0.9
        world.primitive(name, SPHERE, identifier, parent=shelf, position=(x, 0.35, 0), scale=0.7)

    # glTF models (Poly Haven), front row.
    models = world.entity("Models", position=(0, 0, 2.6))
    world.gltf("Marble Bust", "Models/marble_bust_01/marble_bust_01.gltf", parent=models,
               position=(-2.7, 0, 0), rotation=quat_from_axis_angle((0, 1, 0), 20), scale=1.8)
    world.gltf("Camera", "Models/Camera_01/Camera_01.gltf", parent=models,
               position=(-1.4, 0, 0.5), rotation=quat_from_axis_angle((0, 1, 0), 25), scale=4.0)
    world.gltf("Brass Goblets", "Models/brass_goblets/brass_goblets.gltf", parent=models,
               position=(0.0, 0, 0.4), scale=2.5)
    world.gltf("Treasure Chest", "Models/treasure_chest/treasure_chest.gltf", parent=models,
               position=(1.4, 0, 0), rotation=quat_from_axis_angle((0, 1, 0), -25), scale=1.0)
    world.gltf("Boombox", "Models/boombox/boombox.gltf", parent=models,
               position=(2.8, 0, 0.3), rotation=quat_from_axis_angle((0, 1, 0), -20), scale=1.5)

    # Props for contact shadows and occlusion.
    wall = material("wall", color=(0.75, 0.72, 0.66), roughness=0.85)
    box = material("box", color=(0.62, 0.36, 0.2), roughness=0.6)
    props = world.entity("Props", position=(-6.3, 0, -1.2))
    world.primitive("Wall Back", CUBE, wall, parent=props, position=(0, 1.25, -1.0), scale=(4.0, 2.5, 0.2))
    world.primitive("Wall Side", CUBE, wall, parent=props, position=(-1.9, 1.25, 0.4), scale=(0.2, 2.5, 2.6))
    world.primitive("Box A", CUBE, box, parent=props, position=(-1.1, 0.4, -0.2), scale=0.8)
    world.primitive("Box B", CUBE, box, parent=props, position=(-0.25, 0.3, -0.35), scale=0.6,
                    rotation=quat_from_axis_angle((0, 1, 0), 18))
    world.primitive("Box C", CUBE, box, parent=props, position=(-1.0, 1.05, -0.25), scale=0.5,
                    rotation=quat_from_axis_angle((0, 1, 0), 33))
    world.primitive("Column", CYLINDER, wall, parent=props, position=(0.9, 0.9, 0.2), scale=(0.5, 1.8, 0.5))
    world.primitive("Capsule", CAPSULE, material("capsule", color=(0.2, 0.55, 0.3), roughness=0.45),
                    parent=props, position=(1.5, 0.5, 1.2), scale=0.5)

    shadows = world.entity("Shadow Props", position=(5.6, 0, -1.2))
    world.primitive("Pole", CYLINDER, wall, parent=shadows, position=(0, 1.5, 0), scale=(0.08, 3.0, 0.08))
    world.primitive("Slab", CUBE, box, parent=shadows, position=(1.2, 1.6, 0.4), scale=(1.4, 0.1, 1.0))
    world.primitive("Slab Leg", CYLINDER, wall, parent=shadows, position=(1.75, 0.8, 0.75), scale=(0.08, 1.6, 0.08))
    world.primitive("Low Box", CUBE, box, parent=shadows, position=(-1.0, 0.25, 0.8), scale=(0.9, 0.5, 0.9))

    # Point lights at the wall corner.
    world.entity("Warm Light", position=(-7.4, 1.2, 0.0),
                 pointLightComponent={"color": vec4(1.0, 0.55, 0.25, 1.0), "intensity": 40.0, "radius": 4.0,
                                      "isEnabled": True})
    world.entity("Cool Light", position=(-5.1, 0.6, 0.4),
                 pointLightComponent={"color": vec4(0.3, 0.55, 1.0, 1.0), "intensity": 30.0, "radius": 3.0,
                                      "isEnabled": True})

    settings = {
        "lighting": {
            "ambientColor": vec4(1, 1, 1, 1),
            "ambientIntensity": 0.0,
            "environmentMap": asset_id(ENVIRONMENT),
            "environmentIntensity": 1.5,
        },
        "graphics": {
            "shadows": {"enabled": True, "cascadeCount": 4, "tileSize": 2048, "distance": 60.0, "strength": 1.0,
                        "softness": 1.5},
            "ssao": {"enabled": True, "radius": 0.6, "intensity": 1.0},
        },
    }
    world.write("showcase.world", settings)
    print("showcase.world: %d entities, sun elevation %.1f deg" % (len(world.entities), sun["elevation"]))


main()
