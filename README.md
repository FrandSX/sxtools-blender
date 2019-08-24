# sxtools-blender

![Early Example](/sxtools-blender.png)

### Overview
SX Tools for Blender is a work-in-progress adaptation of SX Tools for Maya. The goal of this project is to provide an artist toolbox for multi-layered vertex coloring, referencing the workflow from common 2D image editing programs. It supports driving a full PBR (physically based rendering) game material with vertex color -based data.

### Features
- Multi-layer vertex color editing
- Layer blend modes (alpha, additive, multiply)
- Color filler with noise
- Color gradient tool
- Curvature-based shading
- Vertex ambient occlusion baking
- Quick-crease tools
- Vertex-color -based material channel inputs
- Exporting vertex-colors to Unity via UV channels to drive the standard PBR material

## Installation:
- Install and enable sxtools.py through the Blender add-on interface
- SX Tools will appear in the top right corner of the 3D view

## Quick Start
- After installation, open the Misc-tab in the top right corner of the 3D View, pull the tab in from side of the screen
- Create a mesh object, select it, and press the "Set Up Object" button in SX Tools panel
- The tool will automatically generate the necessary vertex color layers and the material (Layer names Composite and Layer1-Layer7)

## The Interface
### Shading Modes
**Final** - Displays a composite of layers 1-7 in Rendered shading mode

**Debug** - Displays only the selected layer using Vertex Paint mode and Solid shading

**Alpha** - Displays the selected layer alpha in grayscale


### Visibility toggle
Toggles the visibility of the selected layer in Full shading mode

### Blend mode selection
This is similar to popular 2D paint programs:

**Alpha** - the regular transparency blend

**Add**  - creates an additive (brighter) result

**Multiply** - darkens the layer below

### The layer opacity slider
Dragging the slider changes a layer alpha value that influences the composited result. All alpha values in the layer itself are preserved.

### Layer color swatches
Displays the active layer 

### The layer list:
* Click to select layers

### Merge Up / Merge Down buttons
Merge the currently selected layer with the one above or below, respecting the blend modes of both layers. After the merge, the source layer is cleared to default values, and the resulting merged layer is set to Alpha blend mode.

### Select Layer Mask
Click to select all vertices with alpha > 0. Shift-click to invert selection.

### Clear Layer
Sets a layer to its default value (0, 0, 0, 0 for most layers). If components are selected, only clears the selected components.
Shift-clicking will clear ALL layers.

### Apply Color
Fills selected objects or components (faces, edges, verts supported). When applying noise, low values (<0.05) seem to provide tolerable results.

### Gradient Tool
Fills selected objects or components with the selected gradient. The global bbox option stretches the gradient over multiple objects. 

Modes:
* X-Axis / Y-Axis / Z-Axis - maps the gradient across the bounding volume in the selected world axis
* Luminance - remaps the brightness values of the existing layer to the tones of the gradient
* Curvature - drives the gradient tones using the convex/concave characteristics of the surface
* Normalized Curvature - provides a better use of the full range of the gradient. The normalization is done over the _entire_ selection.
* Ambient Occlusion - maps the gradient acccording to how much light they receive. When this mode is selected, additional settings are displayed: Ray Count, for adjusting the quality of the result, and Global/Local blend, for allowing other objects to shadow each other.

### Crease Edges
Allows for quick editing of edge creases, particularly useful with a subdivision and an edge split modifier.

### Channel Copy
Works around Blender's current limitation of only 8 vertex color layers by allowing artists to copy vertex color layers to UV channels, which are then used as material properties. The same UV channels are also exported to Unity, and supported in the example material. Note that the material properties Gradient 1, Gradient 2 and Overlay are not in use in the current release of the tool.


## Exporting to Unity

The package contains example shader graphs for both HDRP and LWRP renderers in Unity 2019.
Currently the export channels are set in the following way:

UV0 - Reserved for a regular texture

U1 - Currently not in use

V1 - Occlusion

U2 - Transmission

V2 - Emission

U3 - Metallic

V3 - Smoothness

UV4-UV7 - Currently not in use

Vertex colors are exported from the Composite layer. Material properties are assigned according to the list above.
Note that emission is only an 8-bit mask for base vertex color, not a full RGBA-channel.

(c) 2017-2019 Jani Kahrama / Secret Exit Ltd.


# Acknowledgments

Thanks to:

Rory Driscoll for tips on better sampling

Serge Scherbakov for tips on working with iterators

SX Tools builds on the following work:

### Vertex-to-edge curvature calculation method 
Algorithm by Stepan Jirka

http://www.stepanjirka.com/maya-api-curvature-shader/

Integrated into SX Tools under MIT license with permission from the author.
