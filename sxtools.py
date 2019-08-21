bl_info = {
    "name": "SX Tools",
    "author": "Jani Kahrama / Secret Exit Ltd.",
    "version": (0, 0, 85),
    "blender": (2, 80, 0),
    "location": "View3D",
    "description": "Multi-layer vertex paint tool",
    "category": "Development",
}

import bpy
import time
import random
import math
import bmesh
from collections import defaultdict
from mathutils import Vector


# ------------------------------------------------------------------------
#    Globals
# ------------------------------------------------------------------------
class SXTOOLS_sxglobals(object):
    def __init__(self):
        self.refreshInProgress = False
        self.refArray = [
            'layer1', 'layer2', 'layer3', 'layer4',
            'layer5', 'layer6', 'layer7']
        self.refLayerArray = [
            'layer1', 'layer2', 'layer3', 'layer4',
            'layer5', 'layer6', 'layer7', 'composite']
        self.refColorArray = [
            [0.5, 0.5, 0.5, 1.0], [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
        self.refChannelArray = [
            ('textureU', 'textureV'),
            ('palettemasks', 'occlusion'),
            ('transmission', 'emission'),
            ('metallic', 'smoothness'),
            ('gradient1', 'gradient2'),
            ('overlayR', 'overlayG'),
            ('overlayB', 'overlayA'),
            ('unused', 'unused') ]
        self.refChannels = {
            'textureU': 0, 'textureV': 0,
            'palettemasks': 0, 'occlusion': 1,
            'metallic': 0, 'smoothness': 0,
            'transmission': 0, 'emission': 0,
            'gradient1': 0, 'gradient2': 0,
            'overlayR': 0, 'overlayG': 0,
            'overlayB': 0, 'overlayA': 0,
            'unused': 0}
        # Brush tools may leave low alpha values that break
        # palettemasks, alphaTolerance can be used to fix this
        self.alphaTolerance = 1.0

    def __del__(self):
        print('SX Tools: Exiting sxglobals')

# ------------------------------------------------------------------------
#    Scene Setup
# ------------------------------------------------------------------------
class SXTOOLS_setup(object):
    def __init__(self):
        return None

    def setupGeometry(self):
        objects = bpy.context.view_layer.objects.selected
        for obj in objects:
            mesh = obj.data

            if not 'layer1' in mesh.vertex_colors.keys():
                for vcol in mesh.vertex_colors:
                    mesh.vertex_colors.remove(vcol)

            for layer in sxglobals.refLayerArray:
                if not layer in mesh.vertex_colors.keys():
                    mesh.vertex_colors.new(name=layer)
                    tools.clearLayers([obj, ], layer)

            if len(mesh.uv_layers.keys()) < 8:
                for i in range(len(mesh.uv_layers.keys()), (9 - len(mesh.uv_layers.keys()))):
                    uValue = sxglobals.refChannels[sxglobals.refChannelArray[i][0]]
                    vValue = sxglobals.refChannels[sxglobals.refChannelArray[i][1]]
                    uvmap = mesh.uv_layers.new()
                    for poly in obj.data.polygons:
                        for idx in poly.loop_indices:
                            mesh.uv_layers[uvmap.name].data[idx].uv = [uValue, vValue]

            #for i in range(5):
            #    if not 'CreaseSet'+str(i) in obj.vertex_groups.keys():
            #        obj.vertex_groups.new(name = 'CreaseSet'+str(i))

        self.createSXMaterial()

    def createSXMaterial(self):
        if 'SXMaterial' not in bpy.data.materials.keys():
            sxmaterial = bpy.data.materials.new(name = 'SXMaterial')
            sxmaterial.use_nodes = True
            sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [0.0, 0.0, 0.0, 1.0]
            sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = [0.0, 0.0, 0.0, 1.0]
            sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0
            sxmaterial.node_tree.nodes['Principled BSDF'].location = (300, 200)

            sxmaterial.node_tree.nodes['Material Output'].location = (600, 200)

            # Gradient tool color ramp
            sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')
            sxmaterial.node_tree.nodes['ColorRamp'].location = (-900, 200)

            # Vertex color source
            sxmaterial.node_tree.nodes.new(type='ShaderNodeAttribute')
            sxmaterial.node_tree.nodes['Attribute'].attribute_name = 'composite'
            sxmaterial.node_tree.nodes['Attribute'].location = (-600, 200)

            # Occlusion source
            sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            sxmaterial.node_tree.nodes['UV Map'].uv_map = 'UVMap.001'
            sxmaterial.node_tree.nodes['UV Map'].location = (-600, 0)

            # Metallic and roughness source
            sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            sxmaterial.node_tree.nodes['UV Map.001'].uv_map = 'UVMap.003'
            sxmaterial.node_tree.nodes['UV Map.001'].location = (-600, -200)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            sxmaterial.node_tree.nodes['Separate XYZ'].location = (-300, 0)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            sxmaterial.node_tree.nodes['Separate XYZ.001'].location = (-300, -200)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeInvert')
            sxmaterial.node_tree.nodes['Invert'].location = (0, -200)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeMixRGB')
            sxmaterial.node_tree.nodes["Mix"].inputs[0].default_value = 1
            sxmaterial.node_tree.nodes["Mix"].blend_type = 'MULTIPLY'
            sxmaterial.node_tree.nodes['Mix'].location = (0, 200)

            # Node connections
            # Vertex color to mixer
            output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Mix'].inputs['Color1']
            sxmaterial.node_tree.links.new(input, output)

            # Split occlusion from UV1
            output = sxmaterial.node_tree.nodes['UV Map'].outputs['UV']
            input = sxmaterial.node_tree.nodes['Separate XYZ'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

            # Occlusion to mixer
            output = sxmaterial.node_tree.nodes['Separate XYZ'].outputs['Y']
            input = sxmaterial.node_tree.nodes['Mix'].inputs['Color2']
            sxmaterial.node_tree.links.new(input, output)

            # Mixer out to base color
            output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color']
            sxmaterial.node_tree.links.new(input, output)

            # Split metallic and smoothness
            output = sxmaterial.node_tree.nodes['UV Map.001'].outputs['UV']
            input = sxmaterial.node_tree.nodes['Separate XYZ.001'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

            # X to metallic
            output = sxmaterial.node_tree.nodes['Separate XYZ.001'].outputs['X']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Metallic']
            sxmaterial.node_tree.links.new(input, output)

            # Invert smoothness to roughness (inverse used by Unity)
            output = sxmaterial.node_tree.nodes['Separate XYZ.001'].outputs['Y']
            input = sxmaterial.node_tree.nodes['Invert'].inputs['Color']
            sxmaterial.node_tree.links.new(input, output)

            # Y to roughness
            output = sxmaterial.node_tree.nodes['Invert'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Roughness']
            sxmaterial.node_tree.links.new(input, output)

        objects = bpy.context.view_layer.objects.selected
        for obj in objects:
            obj.active_material = bpy.data.materials['SXMaterial']

    def __del__(self):
        print('SX Tools: Exiting setup')


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------
class SXTOOLS_tools(object):
    def __init__(self):
        return None

    def clearLayers(self, objects, targetlayer = None):
        for obj in objects:
            if targetlayer is None:
                print('SX Tools: Clearing all layers')
                for i, layer in enumerate(sxglobals.refLayerArray):
                    color = sxglobals.refColorArray[i]
                    self.applyColor([obj, ], layer, color, True, 0.0)
                    setattr(obj.sxtools, layer+'Alpha', 1.0)
                    setattr(obj.sxtools, layer+'Visibility', True)
                    setattr(obj.sxtools, layer+'BlendMode', 'ALPHA')
            else:
                color = sxglobals.refColorArray[sxglobals.refLayerArray.index(targetlayer)]
                self.applyColor([obj, ], targetlayer, color, True, 0.0)
                setattr(obj.sxtools, targetlayer+'Alpha', 1.0)
                setattr(obj.sxtools, targetlayer+'Visibility', True)
                setattr(obj.sxtools, targetlayer+'BlendMode', 'ALPHA')

    def calculateBoundingBox(self, vertDict):
        xmin = None
        xmax = None
        ymin = None
        ymax = None
        zmin = None
        zmax = None

        for i, (vert, fvPos) in enumerate(vertDict.items()):
            fvPos = (fvPos[0][0], fvPos[0][1], fvPos[0][2])
            # first vert
            if i == 0:
                if not xmin:
                    xmin = fvPos[0]
                if not xmax:
                    xmax = fvPos[0]
                if not ymin:
                    ymin = fvPos[1]
                if not ymax:
                    ymax = fvPos[1]
                if not zmin:
                    zmin = fvPos[2]
                if not zmax:
                    zmax = fvPos[2]
            else:
                if fvPos[0] < xmin:
                    xmin = fvPos[0]
                elif fvPos[0] > xmax:
                    xmax = fvPos[0]

                if fvPos[1] < ymin:
                    ymin = fvPos[1]
                elif fvPos[1] > ymax:
                    ymax = fvPos[1]

                if fvPos[2] < zmin:
                    zmin = fvPos[2]
                elif fvPos[2] > zmax:
                    zmax = fvPos[2]

        return ((xmin,xmax), (ymin,ymax), (zmin,zmax))

    def selectionHandler(self, object):
        mesh = object.data
        objSel = False
        faceSel = False
        vertSel = False

        vertLoopDict = defaultdict(list)
        vertPosDict = defaultdict(list)

        # If components selected, apply to selection
        if (True in [poly.select for poly in mesh.polygons]):
            objSel = False
            faceSel = True
            vertSel = False
        elif (True in [vertex.select for vertex in mesh.vertices]):
            objSel = False
            faceSel = False
            vertSel = True
        else:
            # Apply to entire object
            objSel = True
            faceSel = False
            vertSel = False

        if objSel or faceSel:
            for poly in mesh.polygons:
                if poly.select or objSel:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        vertLoopDict[vert_idx].append(loop_idx)
                        vertPosDict[vert_idx] = (mesh.vertices[vert_idx].co, mesh.vertices[vert_idx].normal)
        else:
            for poly in mesh.polygons:
                for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                    if mesh.vertices[vert_idx].select:
                        vertLoopDict[vert_idx].append(loop_idx)
                        vertPosDict[vert_idx] = (mesh.vertices[vert_idx].co, mesh.vertices[vert_idx].normal)

        return (vertLoopDict, vertPosDict, objSel, faceSel, vertSel)

    def applyColor(self, objects, layer, color, overwrite, noise = 0.0, mono = False):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objects:
            vertexColors = obj.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            
            dicts = self.selectionHandler(obj)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]

            if noise == 0.0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if overwrite:
                            vertexColors[loop_idx].color = color
                        else:
                            if vertexColors[loop_idx].color[3] > 0.0:
                                vertexColors[loop_idx].color[0] = color[0]
                                vertexColors[loop_idx].color[1] = color[1]
                                vertexColors[loop_idx].color[2] = color[2]
                            else:
                                vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
            else:
                for vert_idx, loop_indices in vertLoopDict.items():
                    noiseColor = [color[0], color[1], color[2], 1.0][:]
                    if mono:
                        monoNoise = random.uniform(-noise, noise)
                        for i in range(3):
                            noiseColor[i] += monoNoise
                    else:
                        for i in range(3):
                            noiseColor[i] += random.uniform(-noiseColor[i]*noise, noiseColor[i]*noise)
                    for loop_idx in loop_indices:
                        if overwrite:
                            vertexColors[loop_idx].color = noiseColor
                        else:
                            if vertexColors[loop_idx].color[3] > 0.0:
                                vertexColors[loop_idx].color[0] = noiseColor[0]
                                vertexColors[loop_idx].color[1] = noiseColor[1]
                                vertexColors[loop_idx].color[2] = noiseColor[2]
                            else:
                                vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]

        bpy.ops.object.mode_set(mode = mode) 

    def applyRamp(self, objects, layer, ramp, rampmode, overwrite, mergebbx = True, noise = 0.0):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        if mergebbx:
            bbx_x = []
            bbx_y = []
            bbx_z = []
            for obj in objects:
                corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                for corner in corners:
                    bbx_x.append(corner[0])
                    bbx_y.append(corner[1])
                    bbx_z.append(corner[2])
            xmin, xmax = min(bbx_x), max(bbx_x)
            ymin, ymax = min(bbx_y), max(bbx_y)
            zmin, zmax = min(bbx_z), max(bbx_z)

        for obj in objects:
            vertexColors = obj.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            mat = obj.matrix_world
            
            dicts = self.selectionHandler(obj)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]
            
            if not mergebbx:
                bbx = self.calculateBoundingBox(vertPosDict)
                xmin, xmax = bbx[0][0], bbx[0][1]
                ymin, ymax = bbx[1][0], bbx[1][1]
                zmin, zmax = bbx[2][0], bbx[2][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                for loop_idx in loop_indices:
                    ratioRaw = None
                    ratio = None

                    if mergebbx:
                        fvPos = mat @ vertPosDict[vert_idx][0]
                    else:
                        fvPos = vertPosDict[vert_idx][0]
                    if rampmode == 'X':
                        xdiv = float(xmax - xmin)
                        if xdiv == 0:
                            xdiv = 1.0
                        ratioRaw = ((fvPos[0] - xmin) / xdiv)
                    elif rampmode == 'Y':
                        ydiv = float(ymax - ymin)
                        if ydiv == 0:
                            ydiv = 1.0
                        ratioRaw = ((fvPos[1] - ymin) / ydiv)
                    elif rampmode == 'Z':
                        zdiv = float(zmax - zmin)
                        if zdiv == 0:
                            zdiv = 1.0
                        ratioRaw = ((fvPos[2] - zmin) / zdiv)

                    ratio = max(min(ratioRaw, 1), 0)
                    if overwrite:
                        vertexColors[loop_idx].color = ramp.color_ramp.evaluate(ratio)
                    else:
                        if vertexColors[loop_idx].color[3] > 0.0:
                            vertexColors[loop_idx].color[0] = ramp.color_ramp.evaluate(ratio)[0]
                            vertexColors[loop_idx].color[1] = ramp.color_ramp.evaluate(ratio)[1]
                            vertexColors[loop_idx].color[2] = ramp.color_ramp.evaluate(ratio)[2]
                            vertexColors[loop_idx].color[3] = ramp.color_ramp.evaluate(ratio)[3]
                        else:
                            vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]

        bpy.ops.object.mode_set(mode = mode)

    def selectMask(self, objects, layer, inverse):
        mode = objects[0].mode

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode = 'OBJECT', toggle=False)

        for obj in objects:
            vertexColors = obj.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            
            dicts = self.selectionHandler(obj)
            vertLoopDict = dicts[0]

            selList = []
            for vert_idx, loop_indices in vertLoopDict.items():
                for loop_idx in loop_indices:
                    if inverse:
                        if vertexColors[loop_idx].color[3] == 0.0:
                            obj.data.vertices[vert_idx].select = True
                    else:
                        if vertexColors[loop_idx].color[3] > 0.0:
                            obj.data.vertices[vert_idx].select = True

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    def compositeLayers(self, objects):
        #then = time.time()
        shadingmode = bpy.context.scene.sxtools.shadingmode
        idx = bpy.context.active_object.sxtools.selectedlayer
        layer = sxglobals.refLayerArray[idx]

        if shadingmode == 'FULL':
            self.blendLayers(objects, sxglobals.refArray, 'composite', 'composite')
        else:
            self.blendDebug(objects, layer, shadingmode)
        #now = time.time()
        #print("Compositing duration: ", now-then, " seconds")

    def blendDebug(self, objects, layer, shadingmode):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objects:
            vertexColors = obj.data.vertex_colors
            resultLayer = vertexColors['composite'].data
            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    if shadingmode == 'DEBUG':
                        top = [
                            vertexColors[layer].data[idx].color[0],
                            vertexColors[layer].data[idx].color[1],
                            vertexColors[layer].data[idx].color[2],
                            vertexColors[layer].data[idx].color[3]][:]
                    elif shadingmode == 'ALPHA':
                        top = [
                            vertexColors[layer].data[idx].color[3],
                            vertexColors[layer].data[idx].color[3],
                            vertexColors[layer].data[idx].color[3],
                            vertexColors[layer].data[idx].color[3]][:]
                    resultLayer[idx].color = top[:]

        bpy.ops.object.mode_set(mode = mode)

    def blendLayers(self, objects, topLayerArray, baseLayerName, resultLayerName):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objects:
            vertexColors = obj.data.vertex_colors
            resultLayer = vertexColors[resultLayerName].data
            baseLayer = vertexColors[baseLayerName].data

            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    if baseLayerName == 'composite':
                        base = [0.0, 0.0, 0.0, 1.0]
                    else:
                        base = [
                            baseLayer[idx].color[0],
                            baseLayer[idx].color[1],
                            baseLayer[idx].color[2],
                            baseLayer[idx].color[3]][:]
                    for layer in topLayerArray:
                        if not getattr(obj.sxtools, layer+"Visibility"):
                            continue
                        else:
                            blend = getattr(obj.sxtools, layer+"BlendMode")
                            alpha = getattr(obj.sxtools, layer+"Alpha")
                            top = [
                                vertexColors[layer].data[idx].color[0],
                                vertexColors[layer].data[idx].color[1],
                                vertexColors[layer].data[idx].color[2],
                                vertexColors[layer].data[idx].color[3]][:]

                            # alpha blend
                            if blend == 'ALPHA':
                                for j in range(3):
                                    base[j] = (top[j] * (top[3] * alpha) + base[j] * (1 - (top[3] * alpha)))
                                base[3] += top[3]
                                if base[3] > 1.0:
                                    base[3] = 1.0
                            # additive
                            elif blend == 'ADD':
                                for j in range(3):
                                    base[j] += top[j] * (top[3] * alpha)
                                base[3] += top[3]
                                if base[3] > 1.0:
                                    base[3] = 1.0
                            # multiply
                            elif blend == 'MUL':
                                for j in range(3):
                                    # layer2 lerp with white using (1-alpha), multiply with layer1
                                    mul = ((top[j] * (top[3] * alpha) + (1.0 * (1 - (top[3] * alpha)))))
                                    base[j] = mul * base[j]        
                    
                    resultLayer[idx].color = base[:]
        bpy.ops.object.mode_set(mode = mode)

    def selectCrease(self, objects, group):
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0 }
        weight = creaseDict[group]
        bpy.ops.object.mode_set(mode = 'EDIT')

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)

            creaseLayer = bm.edges.layers.crease['SubSurfCrease']
            creaseEdges = [edge for edge in bm.edges if edge[creaseLayer] == weight]
            for edge in creaseEdges:
                edge.select = True

            bmesh.update_edit_mesh(obj.data)

    def assignCrease(self, objects, group):
        mode = objects[0].mode
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0 }
        weight = creaseDict[group]
        bpy.ops.object.mode_set(mode = 'EDIT')

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)

            creaseLayer = bm.edges.layers.crease['SubSurfCrease']
            selectedEdges = [edge for edge in bm.edges if edge.select]
            for edge in selectedEdges:
                edge[creaseLayer] = weight
                if weight == 1.0:
                    edge.smooth = False
                else:
                    edge.smooth = True

            bmesh.update_edit_mesh(obj.data)
        bpy.ops.object.mode_set(mode = mode)

    def copyChannel(self, objects, sourcemap, sourcechannel, targetmap, targetchannel, copymode = 1):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        layers = sxglobals.refArray
        channels = { 'R': 0, 'G': 1, 'B': 2, 'A': 3 , 'U': 0, 'V': 1}
        maps = {
            'LAYER1': sxglobals.refArray[0],
            'LAYER2': sxglobals.refArray[1],
            'LAYER3': sxglobals.refArray[2],
            'LAYER4': sxglobals.refArray[3],
            'LAYER5': sxglobals.refArray[4],
            'LAYER6': sxglobals.refArray[5],
            'LAYER7': sxglobals.refArray[6],
            'UVMAP0': 0,
            'UVMAP1': 1,
            'UVMAP2': 2,
            'UVMAP3': 3,
            'UVMAP4': 4,
            'UVMAP5': 5,
            'UVMAP6': 6,
            'UVMAP7': 7 }

        layer = maps[sourcemap]
        uvmap = maps[targetmap]

        for obj in objects:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers

            if copymode == 1:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = vertexColors[layer].data[idx].color[channels[sourcechannel]]
                        vertexUVs[uvmap].data[idx].uv[channels[targetchannel]] = value

            # Generate 1-bit layer masks for layers 1-7
            # so the faces can be re-colored in a game engine
            elif copymode == 2:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        for i, layer in enumerate(layers):
                            i += 1
                            if i == 1:
                                vertexUVs[uvmap].data[idx].uv[channels[targetchannel]] = i
                            else:
                                vertexAlpha = vertexColors[layer].data[idx].color[channels[sourcechannel]][3]
                                if vertexAlpha >= sxglobals.alphaTolerance:
                                    vertexUVs[uvmap].data[idx].uv[channels[targetchannel]] = i

        bpy.ops.object.mode_set(mode = mode)

    def processMesh(self):
        # placeholder for batch export preprocessor
        # 0: UV0 for basic automatically laid out UVs
        # 1: palettemasks to U1
        # 2: occlusion to V1
        # 3: transmission U2
        # 4: emission V2
        # 5: metallic U3
        # 6: smoothness V3
        # (layers 6, 7 are unpaletted, metallic color in 7?)
        # 7: gradient mask layer8 U4
        # 8: gradient mask layer9 V4
        # 9: RGBA overlay UV5, UV6
        # static flag to object
        pass


    def mergeLayersManager(self, objects, sourceLayer, direction):
        #TODO: fix layer7 with layerCount
        forbidden = ['occlusion', 'metallic', 'roughness', 'transmission', 'emission']
        if (sourceLayer == 'layer1') and (direction == 'UP'):
            print('SX Tools Error: Cannot merge layer1')
            return
        elif (sourceLayer == 'layer7') and (direction == 'DOWN'):
            print('SX Tools Error: Cannot merge layer7')
            return
        elif sourceLayer in forbidden:
            print('SX Tools Error: Cannot merge material channels')
            return

        layerIndex = sxglobals.refArray.index(sourceLayer)

        if direction == 'UP':
            targetLayer = sxglobals.refArray[layerIndex - 1]
        else:
            targetLayer = sxglobals.refArray[layerIndex + 1]

        self.mergeLayers(objects, sourceLayer, targetLayer)    

    def mergeLayers(self, objects, sourceLayer, targetLayer):
        sourceIndex = sxglobals.refArray.index(sourceLayer)
        targetIndex = sxglobals.refArray.index(targetLayer)
        layerOrder = sorted((sourceIndex, targetIndex))
        baseLayer = sxglobals.refArray[layerOrder[0]]
        topLayer = [sxglobals.refArray[layerOrder[1]], ]

        for obj in objects:
            setattr(obj.sxtools, sourceLayer+'Visibility', True)
            setattr(obj.sxtools, targetLayer+'Visibility', True)

        self.blendLayers(objects, topLayer, baseLayer, targetLayer)
        self.clearLayers(objects, sourceLayer)

        for obj in objects:
            setattr(obj.sxtools, sourceLayer+'BlendMode', 'ALPHA')
            setattr(obj.sxtools, targetLayer+'BlendMode', 'ALPHA')

        bpy.context.active_object.data.vertex_colors.active_index = targetIndex
        bpy.context.active_object.sxtools.selectedlayer = targetIndex

    def rayRandomizer(self):
        u1 = random.uniform(0, 1)
        u2 = random.uniform(0, 1)
        r = math.sqrt(u1)
        theta = 2*math.pi*u2

        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return (x, y, math.sqrt(max(0, 1 - u1)))

    def bakeOcclusion(self, objects, layer, rayCount=250, blend=0.0, bias=0.000001):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        scene = bpy.context.scene
        contribution = 1.0/float(rayCount)
        hemiSphere = [None] * rayCount
        bias = 1e-5

        for idx in range(rayCount):
            hemiSphere[idx] = self.rayRandomizer()

        for obj in objects:
            vertexColors = obj.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            mat = obj.matrix_world
            
            dicts = self.selectionHandler(obj)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]

            for vert_idx, loop_indices in vertLoopDict.items():
                occValue = 1.0
                scnOccValue = 1.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                forward = Vector((0, 0, 1))

                # Pass 1: Local space occlusion for individual object
                if 0.0 <= blend < 1.0:
                    biasVec = tuple([bias*x for x in vertNormal])
                    rotQuat = forward.rotation_difference(vertNormal)
                    vertPos = vertLoc

                    # offset ray origin with normal bias
                    vertPos = (vertPos[0] + biasVec[0], vertPos[1] + biasVec[1], vertPos[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        hit, loc, normal, index = obj.ray_cast(vertPos, sample)

                        if hit:
                            occValue -= contribution

                # Pass 2: Worldspace occlusion for scene
                if 0.0 < blend <= 1.0:
                    scnNormal = mat @ vertNormal
                    biasVec = tuple([bias*x for x in scnNormal])
                    rotQuat = forward.rotation_difference(scnNormal)
                    scnVertPos = mat @ vertLoc

                    # offset ray origin with normal bias
                    scnVertPos = (scnVertPos[0] + biasVec[0], scnVertPos[1] + biasVec[1], scnVertPos[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        scnHit, scnLoc, scnNormal, scnIndex, scnObj, ma = scene.ray_cast(scene.view_layers[0], scnVertPos, sample)

                        if scnHit:
                            scnOccValue -= contribution

                for loop_idx in loop_indices:
                    vertexColors[loop_idx].color = [
                        (occValue * (1.0 - blend) + scnOccValue * blend),
                        (occValue * (1.0 - blend) + scnOccValue * blend),
                        (occValue * (1.0 - blend) + scnOccValue * blend),
                        1.0]

        bpy.ops.object.mode_set(mode = mode)

    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Core Functions
# ------------------------------------------------------------------------
def updateLayers(self, context):
    if not sxglobals.refreshInProgress:
        shadingMode(self, context)

        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refLayerArray[idx]
        alphaVal = getattr(context.active_object.sxtools, 'activeLayerAlpha')
        blendVal = getattr(context.active_object.sxtools, 'activeLayerBlendMode')
        visVal = getattr(context.active_object.sxtools, 'activeLayerVisibility')

        for obj in objects:
            obj.data.vertex_colors.active_index = idx
            setattr(obj.sxtools, layer+'Alpha', alphaVal)
            setattr(obj.sxtools, layer+'BlendMode', blendVal)
            setattr(obj.sxtools, layer+'Visibility', visVal)

            sxglobals.refreshInProgress = True
            setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
            setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
            setattr(obj.sxtools, 'activeLayerVisibility', visVal)
            sxglobals.refreshInProgress = False

        setup.setupGeometry()
        tools.compositeLayers(objects)

def refreshActives(self, context):
    sxglobals.refreshInProgress = True
    objects = context.view_layer.objects.selected
    obj = context.active_object.sxtools
    idx = obj.selectedlayer
    layer = sxglobals.refLayerArray[idx]

    if layer != 'composite':
        for obj in objects:
            obj.data.vertex_colors.active_index = idx

            alphaVal = getattr(obj.sxtools, layer+'Alpha')
            blendVal = getattr(obj.sxtools, layer+'BlendMode')
            visVal = getattr(obj.sxtools, layer+'Visibility')

            setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
            setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
            setattr(obj.sxtools, 'activeLayerVisibility', visVal)

        tools.compositeLayers(objects)
        sxglobals.refreshInProgress = False

def shadingMode(self, context):
    mode = context.scene.sxtools.shadingmode
    objects = context.view_layer.objects.selected
    layer = context.active_object.data.vertex_colors.active.name
    sxmaterial = bpy.data.materials['SXMaterial']
    
    if mode == 'FULL':
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        areas = bpy.context.workspace.screens[0].areas
        shading = 'RENDERED'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    if (space.shading.type == 'WIREFRAME') or (space.shading.type == 'SOLID'):
                        space.shading.type = shading

        # Disconnect vertex color output from emission
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)

        # Reconnect vertex color to mixer
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Mix'].inputs['Color1']
        sxmaterial.node_tree.links.new(input, output)

        # Reconnect mixer to base color
        output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color']
        sxmaterial.node_tree.links.new(input, output)

        # Reconnect metallic and roughness
        output = sxmaterial.node_tree.nodes['Separate XYZ.001'].outputs['X']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Metallic']
        sxmaterial.node_tree.links.new(input, output)

        output = sxmaterial.node_tree.nodes['Invert'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Roughness']
        sxmaterial.node_tree.links.new(input, output)

    else:
        areas = bpy.context.workspace.screens[0].areas
        shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = shading

        # Disconnect base color, metallic and roughness
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)

        # Check if already debug
        if len(sxmaterial.node_tree.nodes['Mix'].outputs[0].links) > 0:
            attrLink = sxmaterial.node_tree.nodes['Mix'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)
            attrLink = sxmaterial.node_tree.nodes['Separate XYZ.001'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)
            attrLink = sxmaterial.node_tree.nodes['Invert'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)

        # Connect vertex color source to emission
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        sxmaterial.node_tree.links.new(input, output)


# ------------------------------------------------------------------------
#    Settings and preferences
# ------------------------------------------------------------------------

class SXTOOLS_objectprops(bpy.types.PropertyGroup):
    # TODO: Generate props with an iteration?

    selectedlayer: bpy.props.IntProperty(
        name = 'Selected Layer',
        min = 0,
        max = 7,
        default = 0,
        update = refreshActives)

    activeLayerAlpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0,
        update = updateLayers)
    activeLayerBlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA',
        update = updateLayers)
    activeLayerVisibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True,
        update = updateLayers)    

    layer1Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer1BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer1Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer2Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer2BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer2Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer3Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer3BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer3Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer4Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer4BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer4Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer5Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer5BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer5Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer6Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer6BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer6Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)

    layer7Alpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0)
    layer7BlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')
    layer7Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)


class SXTOOLS_sceneprops(bpy.types.PropertyGroup):
    shadingmode: bpy.props.EnumProperty(
        name = "Shading Mode",
        items = [
            ('FULL','Full',''),
            ('DEBUG','Debug',''),
            ('ALPHA','Alpha','')],
        default = 'FULL',
        update = updateLayers)

    fillcolor: bpy.props.FloatVectorProperty(
        name = "Fill Color",
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    fillalpha: bpy.props.BoolProperty(
        name = "Overwrite Alpha",
        default = True)

    fillnoise: bpy.props.FloatProperty(
        name = "Noise",
        min = 0.0,
        max = 1.0,
        default = 0.0)

    fillmono: bpy.props.BoolProperty(
        name = "Monochrome",
        default = False)

    rampmode: bpy.props.EnumProperty(
        name = "Ramp Mode",
        items = [
            ('X','X-Axis',''),
            ('Y','Y-Axis',''),
            ('Z','Z-Axis','')],
        default = 'X')

    rampbbox: bpy.props.BoolProperty(
        name = "Global Bbox",
        default = True)

    rampalpha: bpy.props.BoolProperty(
        name = "Overwrite Alpha",
        default = True)

    mergemode: bpy.props.EnumProperty(
        name = "Merge Mode",
        items = [
            ('UP','Up',''),
            ('DOWN','Down','')],
        default = 'UP')

    occlusionblend: bpy.props.FloatProperty(
        name = "Occlusion Blend",
        min = 0.0,
        max = 1.0,
        default = 0.5)

    occlusionrays: bpy.props.IntProperty(
        name = "Ray Count",
        min = 1,
        default = 256)

    sourcemap: bpy.props.EnumProperty(
        name = "Source Map",
        items = [
            ('LAYER1','Layer1',''),
            ('LAYER2','Layer2',''),
            ('LAYER3','Layer3',''),
            ('LAYER4','Layer4',''),
            ('LAYER5','Layer5',''),
            ('LAYER6','Layer6',''),
            ('LAYER7','Layer7','')],
        default = 'LAYER1')

    targetmap: bpy.props.EnumProperty(
        name = "Target Map",
        items = [
            ('UVMAP0','UVMap',''),
            ('UVMAP1','UVMap 1',''),
            ('UVMAP2','UVMap 2',''),
            ('UVMAP3','UVMap 3',''),
            ('UVMAP4','UVMap 4',''),
            ('UVMAP5','UVMap 5',''),
            ('UVMAP6','UVMap 6',''),
            ('UVMAP7','UVMap 7','')],
        default = 'UVMAP0')

    sourcechannel: bpy.props.EnumProperty(
        name = "Source Channel",
        items = [
            ('R','R',''),
            ('G','G',''),
            ('B','B',''),
            ('B','B',''),
            ('A','A','')],
        default = 'R')

    targetchannel: bpy.props.EnumProperty(
        name = "Target Channel",
        items = [
            ('U','U',''),
            ('V','V','')],
        default = 'U')

    expandfill: bpy.props.BoolProperty(
        name = "Expand Fill",
        default = False)

    expandramp: bpy.props.BoolProperty(
        name = "Expand Ramp",
        default = False)

    expandocc: bpy.props.BoolProperty(
        name = "Expand Occlusion",
        default = False)

    expandcrease: bpy.props.BoolProperty(
        name = "Expand Crease",
        default = False)

    expandchcopy: bpy.props.BoolProperty(
        name = "Expand Channelcopy",
        default = False)


# ------------------------------------------------------------------------
#    UI Panel and Operators
# ------------------------------------------------------------------------

class SXTOOLS_PT_panel(bpy.types.Panel):

    bl_idname = "SXTOOLS_PT_panel"
    bl_label = "SX Tools"    
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        obj = context.active_object
        objType = getattr(obj, 'type', '')

        if (objType in ['MESH','CURVE']) and (len(context.view_layer.objects.selected) > 0):

            layout = self.layout
            mesh = context.active_object.data
            sxtools = context.active_object.sxtools
            scene = context.scene.sxtools
            
            if mesh.vertex_colors.active is None:
                col = self.layout.column(align = True)
                if (len(context.view_layer.objects.selected) == 1):
                    col.operator('sxtools.scenesetup', text = 'Set Up Object')
                else:
                    col.operator('sxtools.scenesetup', text = 'Set Up Objects')
            else:
                if mesh.vertex_colors.active.name != 'composite':
                    layer = sxglobals.refArray[mesh.vertex_colors.active_index]
                    row_shading = self.layout.row(align = True)
                    row_shading.prop(scene, 'shadingmode', expand = True)
                    if scene.shadingmode == 'FULL':
                        row_blend = self.layout.row(align = True)
                        row_blend.prop(sxtools, 'activeLayerVisibility')
                        row_blend.prop(sxtools, 'activeLayerBlendMode', text = 'Blend')
                        row_alpha = self.layout.row(align = True)
                        row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text = 'Layer Opacity')
                    
                layout.template_list('UI_UL_list', 'sxtools.layerList', mesh, 'vertex_colors', sxtools, 'selectedlayer', type = 'DEFAULT')

                if mesh.vertex_colors.active.name != 'composite':
                    row_merge = self.layout.row(align = True)
                    row_merge.operator('sxtools.mergeup')
                    row_merge.operator('sxtools.mergedown')
                    row_misc = self.layout.row(align = True)
                    row_misc.operator('sxtools.selmask', text = 'Select Mask')
                    row_misc.operator('sxtools.clear', text = 'Clear Layer')

                    box_fill = layout.box()
                    row_fill = box_fill.row()
                    row_fill.prop(scene, "expandfill",
                        icon="TRIA_DOWN" if scene.expandfill else "TRIA_RIGHT",
                        icon_only=True, emboss=False)
                    row_fill.label(text = 'Apply Color')

                    if scene.expandfill:
                        row_color = box_fill.row(align = True)
                        row_color.prop(scene, 'fillcolor')
                        row_noise = box_fill.row(align = True)
                        row_noise.prop(scene, 'fillnoise', slider = True)
                        col_color = box_fill.column(align = True)
                        col_color.prop(scene, 'fillmono', text = 'Monochromatic')
                        col_color.prop(scene, 'fillalpha')
                        col_color.operator('sxtools.applycolor', text = 'Apply')

                    # Gradient Tool ---------------------------------------------------
                    box = layout.box()
                    row4 = box.row()
                    row4.prop(scene, "expandramp",
                        icon="TRIA_DOWN" if scene.expandramp else "TRIA_RIGHT",
                        icon_only=True, emboss=False)

                    row4.label(text='Gradient Tool')
                    if scene.expandramp:
                        layout.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], "color_ramp", expand=True)
                        col_ramp = self.layout.column(align = True)
                        col_ramp.prop(scene, 'rampmode', text = 'Mode')
                        col_ramp.prop(scene, 'rampbbox', text = 'Use Global Bbox')
                        col_ramp.prop(scene, 'rampalpha')
                        col_ramp.operator('sxtools.applyramp', text = 'Apply')

                    # Bake Occlusion ---------------------------------------------------
                    box_occ = layout.box()
                    row_occbox = box_occ.row()
                    row_occbox.prop(scene, "expandocc",
                        icon="TRIA_DOWN" if scene.expandocc else "TRIA_RIGHT",
                        icon_only=True, emboss=False)

                    row_occbox.label(text='Ambient Occlusion')
                    if scene.expandocc:
                        col_occ = box_occ.column(align = True)
                        col_occ.prop(scene, 'occlusionrays', text = 'Ray Count')
                        col_occ.prop(scene, 'occlusionblend', slider = True, text = 'Local/Global Mix')
                        col_occ.operator('sxtools.bakeocclusion', text = 'Apply')

                    # Crease Sets ---------------------------------------------------
                    box_crease = layout.box()
                    row_crease = box_crease.row()
                    row_crease.prop(scene, 'expandcrease',
                        icon="TRIA_DOWN" if scene.expandcrease else "TRIA_RIGHT",
                        icon_only=True, emboss=False)

                    row_crease.label(text='Crease Sets')
                    if scene.expandcrease:
                        row_sets = box_crease.row(align = True)
                        row_sets.operator('sxtools.crease1', text = '25%')
                        row_sets.operator('sxtools.crease2', text = '50%')
                        row_sets.operator('sxtools.crease3', text = '75%')
                        row_sets.operator('sxtools.crease4', text = 'Hard')
                        col_sets = box_crease.column(align = True)
                        col_sets.operator('sxtools.crease0', text = 'Uncrease')

                    # Channel Copy ---------------------------------------------------
                    box_chcp = layout.box()
                    row_chcpbox = box_chcp.row()
                    row_chcpbox.prop(scene, "expandchcopy",
                        icon="TRIA_DOWN" if scene.expandchcopy else "TRIA_RIGHT",
                        icon_only=True, emboss=False)

                    row_chcpbox.label(text='Channel Copy')
                    if scene.expandchcopy:
                        row_chcp = box_chcp.row(align = True)
                        row_chcp.prop(scene, 'sourcemap', text = 'From')
                        row_chcp.prop(scene, 'sourcechannel', text = 'Data')
                        row2_chcp = box_chcp.row(align = True)
                        row2_chcp.prop(scene, 'targetmap', text = 'To')
                        row2_chcp.prop(scene, 'targetchannel', text = 'Data')
                        col_chcp = box_chcp.column(align = True)
                        col_chcp.operator('sxtools.copychannel', text = 'Apply')
        else:
            layout = self.layout               
            col = self.layout.column(align = True)
            col.label(text = 'Select a mesh to continue')


class SXTOOLS_OT_scenesetup(bpy.types.Operator):

    bl_idname = "sxtools.scenesetup"
    bl_label = "Set Up Object"
    bl_options = {"UNDO"}
    bl_description = 'Creates necessary materials and vertex color layers'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        setup.setupGeometry()
        return {"FINISHED"}


class SXTOOLS_OT_applycolor(bpy.types.Operator):

    bl_idname = "sxtools.applycolor"
    bl_label = "Apply Color"
    bl_options = {"UNDO"}
    bl_description = 'Applies fill color to selection'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]
        color = context.scene.sxtools.fillcolor
        overwrite = context.scene.sxtools.fillalpha
        noise = context.scene.sxtools.fillnoise
        mono = context.scene.sxtools.fillmono
        tools.applyColor(objects, layer, color, overwrite, noise, mono)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_applyramp(bpy.types.Operator):

    bl_idname = "sxtools.applyramp"
    bl_label = "Apply Gradient"
    bl_options = {"UNDO"}
    bl_description = 'Applies gradient to selection bounding volume across selected axis'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]
        rampmode = context.scene.sxtools.rampmode
        mergebbx = context.scene.sxtools.rampbbox
        overwrite = context.scene.sxtools.rampalpha
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        tools.applyRamp(objects, layer, ramp, rampmode, overwrite, mergebbx)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_mergeup(bpy.types.Operator):

    bl_idname = "sxtools.mergeup"
    bl_label = "Merge Up"
    bl_options = {"UNDO"}
    bl_description = 'Merge the selected layer with the one above'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]
        mergemode = 'UP'
        tools.mergeLayersManager(objects, layer, mergemode)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_mergedown(bpy.types.Operator):

    bl_idname = "sxtools.mergedown"
    bl_label = "Merge Down"
    bl_options = {"UNDO"}
    bl_description = 'Merge the selected layer with the one below'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]
        mergemode = 'DOWN'
        tools.mergeLayersManager(objects, layer, mergemode)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_clearlayers(bpy.types.Operator):

    bl_idname = "sxtools.clear"
    bl_label = "Clear Layer"
    bl_options = {"UNDO"}
    bl_description = 'Shift-click to clear all layers on object or components'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        if event.shift:
            layer = None
        else:
            idx = context.active_object.sxtools.selectedlayer
            layer = sxglobals.refArray[idx]
            #print('clearlayer: ', layer)
            # TODO: May return UVMAP?!

        tools.clearLayers(objects, layer)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_selmask(bpy.types.Operator):

    bl_idname = "sxtools.selmask"
    bl_label = "Select Layer Mask"
    bl_options = {"UNDO"}
    bl_description = 'Shift-click to invert selection'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        if event.shift:
            inverse = True
        else:
            inverse = False

        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]

        tools.selectMask(objects, layer, inverse)
        return {"FINISHED"}


class SXTOOLS_OT_bakeocclusion(bpy.types.Operator):

    bl_idname = "sxtools.bakeocclusion"
    bl_label = "Bake Occlusion"
    bl_options = {"UNDO"}
    bl_description = 'Bake ambient occlusion to vertex color'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        idx = context.active_object.sxtools.selectedlayer
        layer = sxglobals.refArray[idx]
        blend = context.scene.sxtools.occlusionblend
        rayCount = context.scene.sxtools.occlusionrays
        tools.bakeOcclusion(objects, layer, rayCount, blend)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_crease0(bpy.types.Operator):

    bl_idname = "sxtools.crease0"
    bl_label = "Crease0"
    bl_options = {"UNDO"}
    bl_description = 'Uncrease selection, shift-click to select creased edges'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        group = 'CreaseSet0'
        if event.shift:
            tools.selectCrease(objects, group)
        else:
            tools.assignCrease(objects, group)
        return {"FINISHED"}


class SXTOOLS_OT_crease1(bpy.types.Operator):

    bl_idname = "sxtools.crease1"
    bl_label = "Crease1"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set1, shift-click to select creased edges'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        group = 'CreaseSet1'
        if event.shift:
            tools.selectCrease(objects, group)
        else:
            tools.assignCrease(objects, group)
        return {"FINISHED"}


class SXTOOLS_OT_crease2(bpy.types.Operator):

    bl_idname = "sxtools.crease2"
    bl_label = "Crease2"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set2, shift-click to select creased edges'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        group = 'CreaseSet2'
        if event.shift:
            tools.selectCrease(objects, group)
        else:
            tools.assignCrease(objects, group)
        return {"FINISHED"}


class SXTOOLS_OT_crease3(bpy.types.Operator):

    bl_idname = "sxtools.crease3"
    bl_label = "Crease3"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set3, shift-click to select creased edges'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        group = 'CreaseSet3'
        if event.shift:
            tools.selectCrease(objects, group)
        else:
            tools.assignCrease(objects, group)
        return {"FINISHED"}


class SXTOOLS_OT_crease4(bpy.types.Operator):

    bl_idname = "sxtools.crease4"
    bl_label = "Crease4"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set4, shift-click to select creased edges'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        group = 'CreaseSet4'
        if event.shift:
            tools.selectCrease(objects, group)
        else:
            tools.assignCrease(objects, group)
        return {"FINISHED"}


class SXTOOLS_OT_copychannel(bpy.types.Operator):

    bl_idname = "sxtools.copychannel"
    bl_label = "Copy Channel"
    bl_options = {"UNDO"}
    bl_description = 'Copy channel data'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        sourcemap = context.scene.sxtools.sourcemap
        sourcechannel = context.scene.sxtools.sourcechannel
        targetmap = context.scene.sxtools.targetmap
        targetchannel = context.scene.sxtools.targetchannel
        tools.copyChannel(objects, sourcemap, sourcechannel, targetmap, targetchannel)
        return {"FINISHED"}


# ------------------------------------------------------------------------
#    Registration and initialization
# ------------------------------------------------------------------------
sxglobals = SXTOOLS_sxglobals()
setup = SXTOOLS_setup()
tools = SXTOOLS_tools()

classes = (
    SXTOOLS_objectprops,
    SXTOOLS_sceneprops,
    SXTOOLS_OT_scenesetup,
    SXTOOLS_OT_applycolor,
    SXTOOLS_OT_applyramp,
    SXTOOLS_OT_bakeocclusion,
    SXTOOLS_OT_crease0,
    SXTOOLS_OT_crease1,
    SXTOOLS_OT_crease2,
    SXTOOLS_OT_crease3,
    SXTOOLS_OT_crease4,
    SXTOOLS_OT_copychannel,
    SXTOOLS_OT_selmask,
    SXTOOLS_OT_clearlayers,
    SXTOOLS_OT_mergeup,
    SXTOOLS_OT_mergedown,
    SXTOOLS_PT_panel)

def init():
    pass

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Object.sxtools = bpy.props.PointerProperty(type=SXTOOLS_objectprops)
    bpy.types.Scene.sxtools = bpy.props.PointerProperty(type=SXTOOLS_sceneprops)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Object.sxtools
    del bpy.types.Scene.sxtools
    #del tools
    #del sxglobals

if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    init()
    register()

#MISSING FEATURES FROM SXTOOLS-MAYA:
# - Parallel layer sets (needs more vertex color layers)
# - Layer view features:
#   - Hide/unhide layer
#   - Copy / Paste / Swap / Merge Up / Merge Down RMB menu
#   - hidden/mask/adjustment indication
# - Active layer color palette
# - Color fill recent colors palette
# - Copy / Paste / Swap layers
# - Ramp fill color presets
# - Multi-object (and component) gradients
# - Curvature ramp
# - Luminance remap ramp
# - Occlusion baking temp groundplane
# - Master palette library load/save/apply/manage
# - PBR material library load/save/apply/manage
# - Skinning support?
# - Export settings:
#   - Submesh support
#   - Static vertex colors
#   - Hard edges on hard creases(!)
#   - Export subdivision level
#   - Smoothing angle
#   - Choose export path
#   - Export fbx settings
# - Tool settings:
#   - Prefs path, palettes path, materials path
#   - Load/save prefs file
#   - Channel enable/export prefs
#   - Export grid spacing
#   - Layer renaming
#   - _paletted suffix
#TODO:
# - Set proper shading mode after scene setup
# - Create custom layerview list items, to include UV channel properties
#   - Automatically set paint operation targets if UV channel selected?
# - Indicate active vertex selection?
# - Filter composite out of layer list
# - Add UV source channels to layer list?
# - Custom hide/show icons to layer view items
# - Assign fill color from brush color if in vertex paint mode
#   color[0] = bpy.data.brushes["Draw"].color[0]
#C.active_object.modifiers.new(type = 'EDGE_SPLIT', name = 'SX EdgeSplit')
#bpy.context.object.modifiers["EdgeSplit"].use_edge_angle = False
#C.active_object.modifiers.new(type = 'SUBSURF', name = 'SX Subdivision')
# - Store crease weigths in vertex groups?
