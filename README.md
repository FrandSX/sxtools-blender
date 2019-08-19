# sxtools-blender

![Early Example](/sxtools-blender.png)

### Overview
SX Tools for Blender is a work-in-progress adaptation of SX Tools for Maya. The goal of this project is to provide an artist toolbox for multi-layered vertex coloring, referencing the workflow from common 2D image editing programs.

### Features
- Multi-layer vertex color editing
- Layer blend modes (alpha, additive, multiply)
- Color filler with noise
- Color gradient tool
- Vertex ambient occlusion baking

Installation:
- Install and enable sxtools.py through the Blender add-on interface
- SX Tools will appear in the top right corner of the 3D view
- The tool will automatically generate vertex color layers and the necessary material

## The Interface
### Shading Modes
**Final** - Displays a composite of layers 1-7 in Rendered shading mode

**Debug** - Displays only the selected layer using Vertex Paint mode and Solid shading

**Alpha** - Not yet implemented


### Visibility toggle
Toggles the visibility of the selected layer in Full shading mode

### Blend mode selection
This is similar to popular 2D paint programs:

**Alpha** - the regular transparency blend

**Add**  - creates an additive (brighter) result

**Multiply** - darkens the layer below

### The layer opacity slider
Dragging the slider changes a layer alpha value that influences the composited result. All alpha values in the layer itself are preserved.


### The layer list:
* Click to select layers

### Merge Up / Merge Down buttons
Merge the currently selected layer with the one above or below, respecting the blend modes of both layers. After the merge, the source layer is cleared to default values, and the resulting merged layer is set to Alpha blend mode.

### Select Layer Mask
Not yet implemented.

### Clear Layer
Sets a layer to its default value (0, 0, 0, 0 for most layers). If components are selected, only clears the selected components.
Shift-clicking will clear ALL layers.

### Apply Color
Fills selected objects or components (faces, edges, verts supported). When applying noise, low values (<0.05) seem to provide tolerable results.

### Gradient Tool
Fills selected objects or components with a gradient across the selected axis.

### Ambient Occlusion
A simple occlusion baking tool with selectable ray count. Supports blending between object/local and scene/global occlusion results.

