# sxtools-blender

![Example Situation](/images/sxtools-blender.png)

### Overview

## For Game Developers
SX Tools is a lightweight content pipeline for vertex-colored assets that drive PBR (Physically Based Rendering) materials in a game. This tool ships with baseline shader networks for Unreal and Unity.

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
- SX Tools will appear in the top right corner of the 3D view
- Open the Misc-tab in the top right corner of the 3D View, pull the tab in from side of the screen

## Getting Started:

![Step One](/images/sxtools-01.png)
1) Point SX Tools to the folder where the zip was uncompressed. This also contains example palettes, PBR materials and gradient presets.

![Step Two](/images/sxtools-02.png)

2) Create and select a mesh object.

3) Enable the layers and channels you wish to work on. *These settings are scene-specific.*

4) Alpha and RGBA overlays are for very specific needs in game projects, it is recommended not to enable them unless necessary.

5) Choose "Erase Existing UV Sets" if you are creating a new mesh object. If you are working with an object with existing UV data, uncheck this option and SX Tools will attempt to preserve existing UV sets if there are enough slots available for the selected options.

6) Click on *Set Up Object*. SX Tools will now generate the needed layers, UV sets, variables and a custom material

![Step Three](/images/sxtools-03.png)

7) The default view of SX Tools is now active. Think of your favorite 2D paint tool. Click on layers, apply colors to objects or components, get familiar with the gradient tool.

![Step Four](/images/sxtools-04.png)

8) After some familiarization, you'll be able to create rapid color variants of your game assets in no time.

## The Interface
### Shading Modes

Shading Mode | Function
------------ | -------------
**Full** | Displays a composite of layers 1-7 in Rendered shading mode
**Debug** | Displays only the selected layer with alpha as black
**Alpha** | Displays the selected layer alpha in grayscale


### Visibility toggle
Toggles the visibility of the selected layer in Full shading mode

### Blend mode selection
This is similar to popular 2D paint programs:

Blend Mode | Function
------------ | -------------
**Alpha** | The regular transparency blend
**Add**  | Creates an additive (brighter) result
**Multiply** | Darkens the layer below
**Overlay** | Lightens and darkens the layer below

### The layer opacity slider
Dragging the slider changes a layer alpha value that influences the composited result. All alpha values in the layer itself are preserved.

### Layer color swatches
Displays prominent colors from the selected objects

### The layer list:
* The eye-icon indicates if the layer is hidden or visible
* Click to select layers
* For game developers: object categories can be defined that rename the layers as needed

### Brightness slider
Allows you to fine-tune the brightness of the selected objects or components

### Merge Up / Merge Down buttons
Merge the currently selected layer with the one above or below, respecting the blend modes of both layers. After the merge, the source layer is cleared to default values, and the resulting merged layer is set to Alpha blend mode. Merging is not permitted with material channels.

### Copy / Paste buttons
Allows any layer to be copied and pasted. Grayscale layers (material channels) are expanded to RGB values upon pasting, and if a color layer is pasted on a material channel, the luminance of the color is used for grayscale. 
* Shift-clicking on paste swaps the source and the target layers.
* Alt-clicking merges the copied layer with the target according to the alpha and blendmode

### Select Layer Mask
Click to select all vertices with alpha > 0. Shift-click to invert selection. With material channels, picks any vertex that is not black.

### Clear Layer
Sets a layer to its default value (0, 0, 0, 0 for most layers). If components are selected, only clears the selected components.
Shift-clicking will clear ALL layers.

### Apply Color
Fills selected objects or components (faces, edges, verts supported).
* Overwrite Alpha option can be unchecked to respect current alpha mask and only replace existing color values
* Optional color or monochrome noise can be added

### Gradient Tool
Fills selected objects or components with the selected gradient. The global bbox option stretches the gradient over multiple objects. 

Gradient Mode | Function
------------ | -------------
**X/Y/Z-Axis** | Maps the gradient across the bounding volume in the selected world axis
**Directional** | Works like a directional light that maps the surface brightness to the gradient
**Luminance** | Remaps the brightness values of the existing layer to the tones of the gradient
**Curvature** | Drives the gradient tones using the convex/concave characteristics of the surface
**Normalized Curvature** | Provides a better use of the full range of the gradient. The normalization is done over the _entire_ selection.
**Ambient Occlusion** | Maps the gradient acccording to how much light they receive. When this mode is selected, additional settings are displayed: Ray Count, for adjusting the quality of the result, and Global/Local blend, for allowing other objects to shadow each other.
**Thickness** | Maps the gradient according to mesh thickness. The quality of the calculation can be improved by increasing the ray count.

### Master Palettes
Clicking Apply will replace colors in layers 1-5 with the colors of the palette while retaining alpha channels.

### PBR Materials
Clicking Apply on a material will fill the current layer with the material color, and fill the Metallic and Smoothness/Roughness UV channels with the respective values.

### Creasing
Allows for quick editing of edge creases, particularly useful with a subdivision and an edge split modifier. Shift-click on any of the crease buttons to select the edges of respective crease level.

### Modifiers
Contains settings for SX Tools default modifier stack. Max creases can be selected to be Smooth/Sharp/Beveled, with the default being Beveled. Currently beveling is applied after subdivision, but this is likely to change.

Other functions include quick optoins to hide/show modifiers, or add/remove the entire stack.


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

(c) 2017-2019 Jani Kahrama / Secret Exit Ltd.


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
