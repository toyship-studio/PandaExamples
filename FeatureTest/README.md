# FeatureTest

The showcase of the Panda renderer: one world where every capability of the engine's graphics is
on stage.

- `Assets/showcase.world` — the world. It is generated: `python3 Tools/make_showcase.py` writes it
  and the materials in `Assets/Showcase/Materials`, then Reload in the editor. Change the script,
  not the world.
- The stage: rows of spheres that sweep roughness for a dielectric and a metal, a shelf of
  typical materials, glTF models, a wall corner with stacked boxes (contact shadows, ambient
  occlusion), a pole and a floating slab (the soft edge of a shadow grows with the distance to
  the caster), point lights, the sun of the environment map (`Tools/hdri_sun.py` finds it).
- What is on: image based lighting from an HDR environment map, the PBR shader, cascaded sun
  shadows with a soft edge, screen-space ambient occlusion, HDR with bloom, the AgX tonemap,
  FXAA. The shader features of the project are in `.Panda/project.json`.
- `SHOWCASE_TONEMAP=aces python3 Tools/make_showcase.py` (`agx`, `aces`, `neutral`, `reinhard`,
  `none`) and `SHOWCASE_EXPOSURE=-1.2` regenerate the world with another look of the camera.

## Assets

The environment maps (`Assets/Environment`) and the models (`Assets/Models`) are from
[Poly Haven](https://polyhaven.com), CC0: `kloofendal_48d_partly_cloudy_puresky`,
`studio_small_09`, `belfast_sunset_puresky`; `marble_bust_01`, `Camera_01`, `brass_goblets`,
`treasure_chest`, `boombox`.
