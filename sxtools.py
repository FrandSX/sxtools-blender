bl_info = {
    "name": "SX Tools",
    "author": "Jani Kahrama / Secret Exit Ltd.",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D",
    "description": "Multi-layer vertex paint tool",
    "category": "Development",
}

import bpy
import time
import random
import math
from collections import defaultdict
from mathutils import Vector


# ------------------------------------------------------------------------
#    Globals
# ------------------------------------------------------------------------

global tools, sxglobals

class SXTOOLS_sxglobals(object):
    def __init__(self):
        self.updateInProgress = False
        self.syncLayerEnable = True
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

sxglobals = SXTOOLS_sxglobals()


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------

class SXTOOLS_tools(object):
    def __init__(self):
        return None

    def setupGeometry(self):
        objects = bpy.context.view_layer.objects.selected
        for object in objects:
            mesh = object.data

            if not 'layer1' in mesh.vertex_colors.keys():
                for vcol in mesh.vertex_colors:
                    mesh.vertex_colors.remove(vcol)

            for layer in sxglobals.refLayerArray:
                if not layer in mesh.vertex_colors.keys():
                    mesh.vertex_colors.new(name=layer)
                    self.clearLayers([object, ], layer)

        self.createSXMaterial()

    def clearLayers(self, objects, layer = None):
        sxglobals.syncLayerEnable = False
        for obj in objects:
            if layer is None:
                print('SX Tools: Clearing all layers')
                for i, layer in enumerate(sxglobals.refLayerArray):
                    color = sxglobals.refColorArray[i]
                    self.applyColor([obj, ], layer, color)
                    setattr(obj.sxtools, layer+'Alpha', 1.0)
                    setattr(obj.sxtools, layer+'Visibility', True)
                    setattr(obj.sxtools, layer+'BlendMode', 'ALPHA')
            else:
                color = sxglobals.refColorArray[sxglobals.refLayerArray.index(layer)]
                self.applyColor([obj, ], layer, color)
                setattr(obj.sxtools, layer+'Alpha', 1.0)
                setattr(obj.sxtools, layer+'Visibility', True)
                setattr(obj.sxtools, layer+'BlendMode', 'ALPHA')
        sxglobals.syncLayerEnable = True

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

    def applyColor(self, objects, layer, color = [0.0, 0.0, 0.0, 0.0], noise = 0.0):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for object in objects:
            vertexColors = object.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            
            dicts = self.selectionHandler(object)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]

            if noise == 0.0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        vertexColors[loop_idx].color = color
            else:
                noiseColor = [color[0], color[1], color[2], 1.0][:]
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        for i in range(3):
                            noiseColor[i] = noiseColor[i] + random.uniform(-noiseColor[i]*noise, noiseColor[i]*noise)
                        vertexColors[loop_idx].color = noiseColor

        bpy.ops.object.mode_set(mode = mode) 

    def applyRamp(self, objects, layer, ramp, rampmode, noise = 0.0):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for object in objects:
            vertexColors = object.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            
            dicts = self.selectionHandler(object)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]
            
            bbx = self.calculateBoundingBox(vertPosDict)
            xmin = bbx[0][0]
            xmax = bbx[0][1]
            ymin = bbx[1][0]
            ymax = bbx[1][1]
            zmin = bbx[2][0]
            zmax = bbx[2][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                for loop_idx in loop_indices:
                    ratioRaw = None
                    ratio = None

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
                    vertexColors[loop_idx].color = ramp.color_ramp.evaluate(ratio)

        bpy.ops.object.mode_set(mode = mode)

    def compositeLayers(self, objects):
        #then = time.time()
        mode = bpy.context.scene.sxtools.shadingmode
        layer = bpy.context.active_object.data.vertex_colors.active.name
        if mode == 'ALPHA':
            print('alphacomping')
            self.blendAlpha(objects, layer)
        else:
            print('elsecomping')
            self.blendLayers(objects, sxglobals.refArray, 'composite', 'composite')
        #now = time.time()
        #print("Compositing duration: ", now-then, " seconds")

    def blendAlpha(self, objects, layer):
        mode = objects[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for object in objects:
            vertexColors = object.data.vertex_colors
            resultLayer = vertexColors['composite'].data

            for poly in object.data.polygons:
                for idx in poly.loop_indices:
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

        for object in objects:
            vertexColors = object.data.vertex_colors
            resultLayer = vertexColors[resultLayerName].data
            baseLayer = vertexColors[baseLayerName].data

            for poly in object.data.polygons:
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
                        if not getattr(object.sxtools, layer+"Visibility"):
                            continue
                        else:
                            blend = getattr(object.sxtools, layer+"BlendMode")
                            alpha = getattr(object.sxtools, layer+"Alpha")
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

    def createSXMaterial(self):
        if 'SXMaterial' not in bpy.data.materials.keys():
            sxmaterial = bpy.data.materials.new(name = 'SXMaterial')
            sxmaterial.use_nodes = True
            sxmaterial.node_tree.nodes.new(type='ShaderNodeAttribute')
            sxmaterial.node_tree.nodes["Attribute"].attribute_name = "composite"

            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color']
            output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']

            sxmaterial.node_tree.links.new(input, output)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')

        bpy.context.active_object.active_material = bpy.data.materials['SXMaterial']

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
        
        obj = bpy.context.active_object
        if objects is None:
            objects = [obj, ]

        for object in objects:
            setattr(obj.sxtools, sourceLayer+'Visibility', True)
            setattr(obj.sxtools, targetLayer+'Visibility', True)

        self.blendLayers(objects, topLayer, baseLayer, targetLayer)
        self.clearLayers(objects, sourceLayer)

        for object in objects:
            setattr(obj.sxtools, sourceLayer+'BlendMode', 'ALPHA')
            setattr(obj.sxtools, targetLayer+'BlendMode', 'ALPHA')

        bpy.context.active_object.data.vertex_colors.active_index = targetIndex

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

        for object in objects:
            vertexColors = object.data.vertex_colors[layer].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            
            dicts = self.selectionHandler(object)
            vertLoopDict = dicts[0]
            vertPosDict = dicts[1]

            for vert_idx, loop_indices in vertLoopDict.items():
                occValue = 1.0
                scnOccValue = 1.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                mat = object.matrix_world

                # Pass 1: Local space occlusion for individual object
                if 0 <= blend < 1.0:
                    biasVec = tuple([bias*x for x in vertNormal])
                    forward = Vector((0, 0, 1))
                    rotQuat = forward.rotation_difference(vertNormal)

                    vertPos = vertLoc

                    # offset ray origin with normal bias
                    vertPos = (vertPos[0] + biasVec[0], vertPos[1] + biasVec[1], vertPos[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        hit, loc, normal, index = object.ray_cast(vertPos, sample)

                        if hit:
                            occValue -= contribution

                # Pass 2: Worldspace occlusion for scene
                if 0 < blend <= 1.0:
                    scnNormal = mat @ vertNormal
                    biasVec = tuple([bias*x for x in scnNormal])
                    forward = Vector((0, 0, 1))
                    rotQuat = forward.rotation_difference(scnNormal)

                    scnVertPos = mat @ vertLoc

                    # offset ray origin with normal bias
                    scnVertPos = (scnVertPos[0] + biasVec[0], scnVertPos[1] + biasVec[1], scnVertPos[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        scnHit, scnLoc, scnNormal, scnIndex, obj, ma = scene.ray_cast(scene.view_layers[0], scnVertPos, sample)

                        if scnHit:
                            scnOccValue -= contribution

                for loop_idx in loop_indices:
                    vertexColors[loop_idx].color = [
                        (occValue * (1 - blend) + scnOccValue * blend),
                        (occValue * (1 - blend) + scnOccValue * blend),
                        (occValue * (1 - blend) + scnOccValue * blend),
                        1.0]

        bpy.ops.object.mode_set(mode = mode)

    def __del__(self):
        print('SX Tools: Exiting tools')

# Instantiate tools
tools = SXTOOLS_tools()

def updateLayers(self, context):
    #print('updateLayers called')
    #bpy.ops.sxtools.layerchange('INVOKE_DEFAULT')
    shadingMode(self, context)
    if not sxglobals.updateInProgress:
        sxglobals.updateInProgress = True

        objects = context.view_layer.objects.selected
        idx = context.scene.sxtools.selectedlayer
        layer = context.active_object.data.vertex_colors.active.name
        alphaVal = getattr(context.active_object.sxtools, layer+'Alpha')
        blendVal = getattr(context.active_object.sxtools, layer+'BlendMode')
        visVal = getattr(context.active_object.sxtools, layer+'Visibility')

        for object in objects:
            object.data.vertex_colors.active_index = idx
            setattr(object.sxtools, layer+'Alpha', alphaVal)
            setattr(object.sxtools, layer+'BlendMode', blendVal)
            setattr(object.sxtools, layer+'Visibility', visVal)
            tools.setupGeometry()

        tools.compositeLayers(objects)
        sxglobals.updateInProgress = False

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
                    space.shading.type = shading

        sxmaterial.node_tree.nodes["Attribute"].attribute_name = 'composite'
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [0.0, 0.0, 0.0, 1.0]
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color']
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        sxmaterial.node_tree.links.new(input, output)

    elif mode == 'DEBUG':
        #bpy.ops.object.mode_set(mode = 'VERTEX_PAINT')
        areas = bpy.context.workspace.screens[0].areas
        shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = shading


        sxmaterial.node_tree.nodes['Attribute'].attribute_name = layer
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)
        sxmaterial.diffuse_color = [0.0, 0.0, 0.0, 1.0]
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        sxmaterial.node_tree.links.new(input, output)

    elif mode == 'ALPHA':
        areas = bpy.context.workspace.screens[0].areas
        shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = shading

        sxmaterial.node_tree.nodes['Attribute'].attribute_name = 'composite'
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)
        sxmaterial.diffuse_color = [0.0, 0.0, 0.0, 1.0]
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        sxmaterial.node_tree.links.new(input, output)

    tools.compositeLayers(objects)


# ------------------------------------------------------------------------
#    Settings and preferences
# ------------------------------------------------------------------------

class SXTOOLS_objectprops(bpy.types.PropertyGroup):
    # TODO: Generate props with an iteration?
    activeLayerIndex: bpy.props.IntProperty(
        name = 'Index',
        default = 0,
        update=updateLayers)

    activeLayerAlpha: bpy.props.FloatProperty(
        name = "Opacity",
        min = 0.0,
        max = 1.0,
        default = 1.0,
        update = updateLayers)
    activeLayerBlendMode: bpy.props.EnumProperty(
        name = "Blend Mode",
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA',
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
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
        items=[
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default='ALPHA')
    layer7Visibility: bpy.props.BoolProperty(
        name = "Visibility",
        default = True)


class SXTOOLS_sceneprops(bpy.types.PropertyGroup):
    shadingmode: bpy.props.EnumProperty(
        name = "Shading Mode",
        items=[
            ('FULL','Full',''),
            ('DEBUG','Debug',''),
            ('ALPHA','Alpha','')],
        default='FULL',
        update = shadingMode)

    selectedlayer: bpy.props.IntProperty(
        name = 'Selected Layer',
        min = 0,
        max = 7,
        default = 0,
        update=updateLayers)

    fillcolor: bpy.props.FloatVectorProperty(
        name="Fill Color",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    fillnoise: bpy.props.FloatProperty(
        name = "Noise",
        min = 0.0,
        max = 1.0,
        default = 0.0)

    rampmode: bpy.props.EnumProperty(
        name = "Ramp Mode",
        items=[
            ('X','X-Axis',''),
            ('Y','Y-Axis',''),
            ('Z','Z-Axis','')],
        default='X')

    mergemode: bpy.props.EnumProperty(
        name = "Merge Mode",
        items=[
            ('UP','Up',''),
            ('DOWN','Down','')],
        default='UP')

    occlusionblend: bpy.props.FloatProperty(
        name = "Occlusion Blend",
        min = 0.0,
        max = 1.0,
        default = 0.5)

    occlusionrays: bpy.props.IntProperty(
        name = "Ray Count",
        min = 1,
        default = 256)

    expandfill: bpy.props.BoolProperty(
        name = "Expand Fill",
        default = False)

    expandramp: bpy.props.BoolProperty(
        name = "Expand Ramp",
        default = False)

    expandocc: bpy.props.BoolProperty(
        name = "Expand Occlusion",
        default = False)

# ------------------------------------------------------------------------
#    UI Panel and elements
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
                col.operator("sxtools.scenesetup", text = "Set Up Object")
            else:
                if mesh.vertex_colors.active.name != 'composite':
                    layer = sxglobals.refArray[mesh.vertex_colors.active_index]
                    row_shading = self.layout.row(align = True)
                    row_shading.prop(scene, 'shadingmode', expand = True)
                    row_blend = self.layout.row(align = True)
                    row_blend.prop(sxtools, 'activeLayerVisibility')
                    row_blend.prop(sxtools, 'activeLayerBlendMode', text = 'Blend')
                    row_alpha = self.layout.row(align = True)
                    row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text = 'Layer Opacity')
                    
                layout.template_list("UI_UL_list", "sxtools.layerList", mesh, "vertex_colors", scene, 'selectedlayer', type = 'DEFAULT')

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
                        col_color.operator('sxtools.applycolor', text = 'Apply')

                    # TODO: Assign fill color from brush color if in vertex paint mode
                    #color[0] = bpy.data.brushes["Draw"].color[0]

                    box = layout.box()
                    row4 = box.row()
                    row4.prop(scene, "expandramp",
                        icon="TRIA_DOWN" if scene.expandramp else "TRIA_RIGHT",
                        icon_only=True, emboss=False)

                    row4.label(text='Gradient Tool')
                    if scene.expandramp:
                        layout.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], "color_ramp", expand=True)
                        row_ramp = self.layout.row(align = True)
                        row_ramp.prop(scene, 'rampmode', text = 'Mode')
                        row_ramp.operator('sxtools.applyramp', text = 'Apply')


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


class SXTOOLS_OT_scenesetup(bpy.types.Operator):

    bl_idname = "sxtools.scenesetup"
    bl_label = "Set Up Object"
    bl_options = {"UNDO"}
    bl_description = 'Creates necessary materials and vertex color layers'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        tools.setupGeometry()
        return {"FINISHED"}


class SXTOOLS_OT_applycolor(bpy.types.Operator):

    bl_idname = "sxtools.applycolor"
    bl_label = "Apply Color"
    bl_options = {"UNDO"}
    bl_description = 'Applies fill color to selection'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        layer = context.active_object.data.vertex_colors.active.name
        color = context.scene.sxtools.fillcolor
        noise = context.scene.sxtools.fillnoise
        tools.applyColor(objects, layer, color, noise)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_applyramp(bpy.types.Operator):

    bl_idname = "sxtools.applyramp"
    bl_label = "Apply Gradient"
    bl_options = {"UNDO"}
    bl_description = 'Applies gradient to selection bounding volume across selected axis'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        layer = context.active_object.data.vertex_colors.active.name
        rampmode = context.scene.sxtools.rampmode
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        tools.applyRamp(objects, layer, ramp, rampmode)
        tools.compositeLayers(objects)
        return {"FINISHED"}


class SXTOOLS_OT_mergeup(bpy.types.Operator):

    bl_idname = "sxtools.mergeup"
    bl_label = "Merge Up"
    bl_options = {"UNDO"}
    bl_description = 'Merge the selected layer with the one above'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        layer = objects[0].data.vertex_colors.active.name
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
        layer = objects[0].data.vertex_colors.active.name
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
            layer = objects[0].data.vertex_colors.active.name
            print('clearlayer: ', layer)
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
            layer = None
        else:
            layer = objects[0].data.vertex_colors.active.name

        #tools.clearLayers([obj, ], layer)
        return {"FINISHED"}


class SXTOOLS_OT_bakeocclusion(bpy.types.Operator):

    bl_idname = "sxtools.bakeocclusion"
    bl_label = "Bake Occlusion"
    bl_options = {"UNDO"}
    bl_description = 'Bake ambient occlusion to vertex color'

    def invoke(self, context, event):
        objects = context.view_layer.objects.selected
        layer = context.active_object.data.vertex_colors.active.name
        blend = context.scene.sxtools.occlusionblend
        rayCount = context.scene.sxtools.occlusionrays
        tools.bakeOcclusion(objects, layer, rayCount, blend)
        tools.compositeLayers(objects)
        return {"FINISHED"}

# ------------------------------------------------------------------------
#    Registration and initialization
# ------------------------------------------------------------------------

classes = (
    SXTOOLS_objectprops,
    SXTOOLS_sceneprops,
    SXTOOLS_OT_scenesetup,
    SXTOOLS_OT_applycolor,
    SXTOOLS_OT_applyramp,
    SXTOOLS_OT_bakeocclusion,
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
    init()

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
    register()

#TODO:
# - Selection from mask
# - Noise is not continuous across faces
# - Exporting to UVs
# - Filter composite out of layer list
# - Curvature ramp
# - Luminance remap ramp
# - Custom hide/show icons to layer view items
# - Swap / copy layers
# - Crease sets
# - Handle layer renaming
# - Alpha shading mode
# - Debug -> active colorset to emission?