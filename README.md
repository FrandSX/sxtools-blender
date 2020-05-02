# sxtools-blender
NOTE: This readme is partially out of date. Please visit the new [Documentation Site](https://www.notion.so/SX-Tools-for-Blender-Documentation-9ad98e239f224624bf98246822a671a6)

## For Game Developers
SX Tools is a lightweight content pipeline for vertex-colored assets that drive PBR (Physically Based Rendering) materials in a game. This tool ships with baseline shader networks for Unreal and Unity.

![Asset Pipeline](/images/sxtools-magic.png)

## For 3D Artists
SX Tools is a multi-layer vertex coloring toolbox, referencing a workflow from common 2D image editing programs.

## Highlights
For game artists, UV-channels are presented as grayscale layers. Regular paint operations like gradients, color fills and even occlusion baking can be performed directly to UVs like they were vertex color layers. The toolbox comes with a custom material that displays all edits in the viewport in realtime.

The artist can therefore apply per-vertex occlusion/metallic/smoothness/transmission/emission directly on the model, and tweak the results interactively.

### Features
- Multi-layer vertex color editing
- Layer blend modes (alpha, additive, multiply, overlay)
- Color filler with optional noise
- Color gradient tool with optional noise
- Curvature-based shading
- Vertex ambient occlusion baking
- Mesh thickness baking
- Luminance-based tone-mapping
- Master Palette Tool for quickly replacing the color scheme of object/objects
- PBR Material Library
- Quick-crease tools
- Modifier automations
- Material channel editing via UV channel values (subsurface scattering, occlusion, metallic, roughness)
- Exporting vertex-colors to Unity via UV channels to drive the standard PBR material

## Installation:
- Download the zip file, uncompress it, then install and enable sxtools.py through the Blender add-on interface
- Point the library folder in SX Tools prefs to the unzipped folder
- SX Tools will appear in the top right corner of the 3D view
- Open the Misc-tab in the top right corner of the 3D View, pull the tab in from side of the screen

## Getting Started:

Now would be a good time to visit the new [Documentation Site](https://www.notion.so/SX-Tools-for-Blender-Documentation-9ad98e239f224624bf98246822a671a6)

![Step One](/images/sxtools-01.png)
1) Point SX Tools to the folder where the zip was uncompressed. This also contains example palettes, PBR materials and gradient presets.

![Step Two](/images/sxtools-02.png)

2) Create and select a mesh object.

3) Enable the layers and channels you wish to work on. *These settings are scene-specific.*

4) Alpha and RGBA overlays are for very specific needs in game projects, it is recommended not to enable them unless necessary. The Layer View refers to Alpha Overlays as Gradient1 and Gradient2.

5) Choose "Erase Existing UV Sets" if you are creating a new mesh object. If you are working with an object with existing UV data, uncheck this option and SX Tools will attempt to preserve existing UV sets if there are enough slots available for the selected options.

6) Click on *Set Up Object*. SX Tools will now generate the needed layers, UV sets, variables and a custom material

![Step Three](/images/sxtools-03.png)

7) The default view of SX Tools is now active. Think of your favorite 2D paint tool. Click on layers, apply colors to objects or components, get familiar with the gradient tool.

![Step Four](/images/sxtools-04.png)

8) After some familiarization, you'll be able to create rapid color variants of your game assets in no time.

NOTE: Relative paths may cause issues with export paths in SX Tool. Setting "Save&Load -> Relative Paths" to disabled is recommended.


## Exporting to Game Engines

![Pipeline Overview](/images/sxtools-pipeline.png)

The basic flow for using SX Tools in game development is as follows:
1) Model your assets as low-poly control cages for subdivision
2) Define the categories needed for your objects in your game
3) Set up project in SX Tools, enable the needed features
4) Assign objects to categories
5) Color the objects according to category-specific layer definitions
6) Batch-process the objects for export, leave as much work for automation as possible. Take a look at the existing batch functions and adapt to your project needs.
7) Export to your game engine as FBX
8) Run the assets using a the provided custom material (or make your own)

The package contains simple example shader graphs for Unreal4, and both HDRP and LWRP renderers in Unity 2019. Dynamic palette changes in the game engine are not facilitated by the example shader graphs, but they do fully support driving PBR material channels with UV data.

Currently the export channels are set in the following way:

Channel | Function
---------|-------------
UV0 | Reserved for a regular texturing
U1 | Layer coverage masks for dynamic palettes
V1 | Ambient Occlusion
U2 | Transmission
V2 | Emission
U3 | Metallic
V3 | Smoothness
U4 | Alpha Overlay 1, an alpha mask channel
V4 | Alpha Overlay 2, an alpha mask channel
UV5/UV6 | RGBA Overlay, an optional additional color layer 
UV7 | Currently not in use

Vertex colors are exported from the Composite/VertexColor0 layer. Material properties are assigned according to the list above.
Note that emission is only an 8-bit mask for base vertex color, not a full RGBA-channel.

(c) 2017-2020 Jani Kahrama / Secret Exit Ltd.


# Acknowledgments

Thanks to:

Rory Driscoll for tips on better sampling

Serge Scherbakov for tips on working with iterators
 
Jason Summers for sRGB conversion formulas


SX Tools builds on the following work:

### Vertex-to-edge curvature calculation method 
Algorithm by Stepan Jirka

http://www.stepanjirka.com/maya-api-curvature-shader/

Integrated into SX Tools under MIT license with permission from the author.
