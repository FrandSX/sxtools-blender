bl_info = {
    "name": "SX Tools",
    "author": "Jani Kahrama / Secret Exit Ltd.",
    "version": (1, 9, 8),
    "blender": (2, 80, 0),
    "location": "View3D",
    "description": "Multi-layer vertex paint tool",
    "category": "Development",
}

import bpy
import os
import time
import random
import math
import bmesh
import json
from collections import defaultdict
from mathutils import Vector


# ------------------------------------------------------------------------
#    Globals
# ------------------------------------------------------------------------
class SXTOOLS_sxglobals(object):
    def __init__(self):
        self.refreshInProgress = False
        self.paletteDict = {}
        self.masterPaletteArray = []
        self.materialArray = []

        # name, showInLayerList, index, layerType (COLOR/UV),
        # defaultColor, defaultValue,
        # visibility, alpha, blendMode, vertexColorLayer,
        # uvLayer0, uvChannel0, uvLayer1, uvChannel1,
        # uvLayer2, uvChannel2, uvLayer3, uvChannel3,
        # hidden_in_layerView
        self.layerInitArray = [
            ('composite', False, 0, 'COLOR', [0.0, 0.0, 0.0, 1.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor0', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer1', True, 1, 'COLOR', [0.5, 0.5, 0.5, 1.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor1', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer2', True, 2, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor2', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer3', True, 3, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor3', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer4', True, 4, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor4', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer5', True, 5, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor5', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer6', True, 6, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor6', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('layer7', True, 7, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor7', '', 'U', '', 'U', '', 'U', '', 'U'),
            ('occlusion', True, 11, 'UV', [0.0, 0.0, 0.0, 0.0], 1.0, True, 1.0, 'ALPHA', '', 'UVSet1', 'V', '', 'U', '', 'U', '', 'U'),
            ('transmission', True, 14, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet2', 'U', '', 'U', '', 'U', '', 'U'),
            ('emission', True, 15, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet2', 'V', '', 'U', '', 'U', '', 'U'),
            ('metallic', True, 12, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet3', 'U', '', 'U', '', 'U', '', 'U'),
            ('smoothness', True, 13, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet3', 'V', '', 'U', '', 'U', '', 'U'),
            ('gradient1', False, 8, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet4', 'U', '', 'U', '', 'U', '', 'U'),
            ('gradient2', False, 9, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet4', 'V', '', 'U', '', 'U', '', 'U'),
            ('overlay', False, 10, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet5', 'U', 'UVSet5', 'V', 'UVSet6', 'U', 'UVSet6', 'V'),
            ('texture', False, 16, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet0', 'U', 'UVSet0', 'V', '', 'U', '', 'U'),
            ('masks', False, 17, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet1', 'U', '', 'U', '', 'U', '', 'U')]
 
        # Brush tools may leave low alpha values that break
        # palettemasks, alphaTolerance can be used to fix this
        self.alphaTolerance = 1.0
        self.copyLayer = None
        self.activeObject = None

    def __del__(self):
        print('SX Tools: Exiting sxglobals')


# ------------------------------------------------------------------------
#    File IO
# ------------------------------------------------------------------------
class SXTOOLS_files(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting tools')

    # Loads palettes.json and materials.json
    def loadFile(self, mode):
        directory = bpy.context.scene.sxtools.libraryfolder
        filePath = bpy.context.scene.sxtools.libraryfolder + mode + '.json'

        if len(directory) > 0:
            try:
                with open(filePath, 'r') as input:
                    if mode == 'palettes':
                        tempDict = {}
                        tempDict = json.load(input)
                        del sxglobals.masterPaletteArray[:]
                        while len(bpy.context.scene.sxpalettes.keys()) > 0:
                            bpy.context.scene.sxpalettes.remove(0)
                        sxglobals.masterPaletteArray = tempDict['Palettes']
                    elif mode == 'materials':
                        tempDict = {}
                        tempDict = json.load(input)
                        del sxglobals.materialArray[:]
                        while len(bpy.context.scene.sxmaterials.keys()) > 0:
                            bpy.context.scene.sxmaterials.remove(0)
                        sxglobals.materialArray = tempDict['Materials']
                    input.close()
                print('SX Tools: ' + mode + ' loaded from ' + filePath)
            except ValueError:
                print('SX Tools Error: Invalid ' + mode + ' file.')
                bpy.context.scene.sxtools.libraryfolder = ''
            except IOError:
                print('SX Tools Error: ' + mode + ' file not found!')
        else:
            print('SX Tools: No ' + mode + ' file found')

        if mode == 'palettes':
            self.loadPalettes()
        elif mode == 'materials':
            self.loadMaterials()

    def saveFile(self, mode):
        directory = bpy.context.scene.sxtools.libraryfolder
        filePath = bpy.context.scene.sxtools.libraryfolder + mode + '.json'
        # Palettes.json Materials.json

        if len(directory) > 0:
            with open(filePath, 'w') as output:
                if mode == 'palettes':
                    tempDict = {}
                    tempDict['palettes'] = sxglobals.masterPaletteArray
                    json.dump(tempDict, output, indent=4)
                elif mode == 'materials':
                    tempDict = {}
                    tempDict['materials'] = sxglobals.materialArray
                    json.dump(tempDict, output, indent=4)
                output.close()
            print('SX Tools: ' + mode + ' saved')
        else:
            print('SX Tools Warning: ' + mode + ' file location not set!')

    def loadPalettes(self):
        for categoryDict in sxglobals.masterPaletteArray:
            for category in categoryDict.keys():
                for palette in categoryDict[category]:
                    item = bpy.context.scene.sxpalettes.add()
                    item.name = palette
                    item.category = category
                    for i in range(5):
                        incolor = [0.0, 0.0, 0.0, 1.0]
                        incolor[0] = categoryDict[category][palette][i][0]
                        incolor[1] = categoryDict[category][palette][i][1]
                        incolor[2] = categoryDict[category][palette][i][2]
                        setattr(item, 'color'+str(i), incolor[:])

    def loadMaterials(self):
        for categoryDict in sxglobals.materialArray:
            for category in categoryDict.keys():
                for material in categoryDict[category]:
                    item = bpy.context.scene.sxmaterials.add()
                    item.name = material
                    item.category = category
                    for i in range(3):
                        incolor = [0.0, 0.0, 0.0, 1.0]
                        incolor[0] = categoryDict[category][material][i][0]
                        incolor[1] = categoryDict[category][material][i][1]
                        incolor[2] = categoryDict[category][material][i][2]
                        setattr(item, 'color'+str(i), incolor[:])


# ------------------------------------------------------------------------
#    Layer Data Find Functions
# ------------------------------------------------------------------------
class SXTOOLS_utils(object):
    def __init__(self):
        return None

    def findListIndex(self, obj, layer):
        index = obj.sxlayers[layer.name].index
        for i, item in enumerate(bpy.context.scene.sxlistitems):
            if item.index == index:
                return i

    def findColorLayers(self, obj):
        sxLayerArray = []
        for sxLayer in obj.sxlayers:
            if sxLayer.layerType == 'COLOR':
                sxLayerArray.append(sxLayer)
        sxLayerArray.sort(key=lambda x: sxLayer.index)

        return sxLayerArray

    def findDefaultValues(self, obj, mode):
        sxLayerArray = []
        valueArray = []
        valueDict = {}
        for sxLayer in obj.sxlayers:
            if sxLayer.layerType == 'UV':
                sxLayerArray.append(sxLayer)

        nameArray = []
        for sxLayer in sxLayerArray:
            nameArray.extend((sxLayer.uvLayer0, sxLayer.uvLayer1, sxLayer.uvLayer2, sxLayer.uvLayer3))
        nameSet = set(nameArray)

        empty = False
        for name in nameSet:
            if name == '':
                empty = True
        if empty:
            nameSet.remove('')
        uvSets = sorted(nameSet)

        for uvSet in uvSets:
            values = [uvSet, None, None]
            for sxLayer in obj.sxlayers:
                if sxLayer.uvLayer0 == uvSet:
                    if sxLayer.uvChannel0 == 'U':
                        values[1] = sxLayer.defaultValue
                    else:
                        values[2] = sxLayer.defaultValue

                if sxLayer.uvLayer1 == uvSet:
                    if sxLayer.uvChannel1 == 'U':
                        values[1] = sxLayer.defaultValue
                    else:
                        values[2] = sxLayer.defaultValue

                if sxLayer.uvLayer2 == uvSet:
                    if sxLayer.uvChannel2 == 'U':
                        values[1] = sxLayer.defaultValue
                    else:
                        values[2] = sxLayer.defaultValue

                if sxLayer.uvLayer3 == uvSet:
                    if sxLayer.uvChannel3 == 'U':
                        values[1] = sxLayer.defaultValue
                    else:
                        values[2] = sxLayer.defaultValue

            valueDict[uvSet] = (values[1], values[2])
            valueArray.append(values)

        if mode == 'Array':
            return valueArray
        elif mode == 'Dict':
            return valueDict

    def findCompLayers(self, obj):
        compLayers = []
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'COLOR') and (sxLayer.showInLayerList == True):
                compLayers.append(sxLayer)
        compLayers.sort(key=lambda x: sxLayer.index)
        return compLayers

    def findListLayers(self, obj):
        listLayers = []
        for sxLayer in obj.sxlayers:
            if sxLayer.showInLayerList == True:
                listLayers.append(sxLayer)
        listLayers.sort(key=lambda x: sxLayer.index)
        return listLayers

    def findExportChannels(self, obj, layer):
        # The mapping of material channels to UVs (setindex, uv)
        exportArray = []
        sxLayer = obj.sxlayers[layer.name]

        expLayerArray = [
            'uvLayer0',
            'uvLayer1',
            'uvLayer2',
            'uvLayer5']

        expChannelArray = [
            'uvChannel0',
            'uvChannel1',
            'uvChannel2',
            'uvChannel3']

        for i, layer in enumerate(expLayerArray):
            uvSet = getattr(sxLayer, layer)
            if uvSet == '':
                break
            else:
                value = (uvSet, getattr(sxLayer, expChannelArray[i]))
                expItem = value[:]
                exportArray.append(expItem)

        return exportArray

    def findLayerFromIndex(self, obj, index):
        for sxLayer in obj.sxlayers:
            if sxLayer.index == index:
                return sxLayer

    def __del__(self):
        print('SX Tools: Exiting utils')


# ------------------------------------------------------------------------
#    Scene Setup
# ------------------------------------------------------------------------
class SXTOOLS_setup(object):
    def __init__(self):
        return None

    # Creates the items in SX Tools layer list in the preferred order.
    # By default shows only items with "showInLayerList" enabled and
    # sorted by index.
    def setupListItems(self):
        if 'sxlistitems' not in bpy.context.scene.keys():
            listItemArray = []
            for values in sxglobals.layerInitArray:
                if values[1]:
                    listItemArray.append(values)
            listItemArray.sort(key=lambda tup: tup[2]) 

            for values in listItemArray:
                    item = bpy.context.scene.sxlistitems.add()
                    item.name = values[0]
                    item.index = values[2]

    # Generates layer instances by using the reference values
    # from layerInitArray. 
    def setupLayers(self, objs):
        for obj in objs:
            for values in sxglobals.layerInitArray:
                item = obj.sxlayers.add()
                item.name = values[0]
                item.showInLayerList = values[1]
                item.index = values[2]
                item.layerType = values[3]
                item.defaultColor = values[4]
                item.defaultValue = values[5]
                item.visibility = values[6]
                item.alpha = values[7]
                item.blendMode = values[8]
                item.vertexColorLayer = values[9]
                item.uvLayer0 = values[10]
                item.uvChannel0 = values[11]
                item.uvLayer1 = values[12]
                item.uvChannel1 = values[13]
                item.uvLayer2 = values[14]
                item.uvChannel2 = values[15]
                item.uvLayer3 = values[16]
                item.uvChannel3 = values[17]

    def setupGeometry(self, objs):
        if 'SXMaterial' not in bpy.data.materials.keys():
            self.createSXMaterial()

        sxLayers = utils.findColorLayers(objs[0])
        sxUVs = utils.findDefaultValues(objs[0], 'Array')

        for obj in objs:
            mesh = obj.data

            for vertexColor in mesh.vertex_colors.keys():
                if not 'VertexColor' in vertexColor:
                    mesh.vertex_colors.remove(vertexColor)

            for sxLayer in sxLayers:
                if not sxLayer.vertexColorLayer in mesh.vertex_colors.keys():
                    mesh.vertex_colors.new(name = sxLayer.vertexColorLayer)
                    layers.clearLayers([obj, ], sxLayer)

            for uvSet in mesh.uv_layers.keys():
                if not 'UVSet' in uvSet:
                    mesh.uv_layers.remove(mesh.uv_layers[uvSet])

            for uvSet in sxUVs:
                if not uvSet[0] in mesh.uv_layers.keys():
                    uvmap = mesh.uv_layers.new(name = uvSet[0])

            layers.clearUVs([obj, ])

            #for i in range(5):
            #    if not 'CreaseSet'+str(i) in obj.vertex_groups.keys():
            #        obj.vertex_groups.new(name = 'CreaseSet'+str(i))

            obj.active_material = bpy.data.materials['SXMaterial']

    def createSXMaterial(self):
        for values in sxglobals.layerInitArray:
            if values[0] == 'composite':
                compositeUVSet = values[9]
            elif values[0] == 'occlusion':
                occlusionUVSet = values[10]
            elif values[0] == 'metallic':
                metallicUVSet = values[10]
            elif values[0] == 'smoothness':
                smoothnessUVSet = values[10]
            elif values[0] == 'transmission':
                transmissionUVSet = values[10]
            elif values[0] == 'emission':
                emissionUVSet = values[10]

        sxmaterial = bpy.data.materials.new(name = 'SXMaterial')
        sxmaterial.use_nodes = True
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.5
        sxmaterial.node_tree.nodes['Principled BSDF'].location = (300, 200)

        sxmaterial.node_tree.nodes['Material Output'].location = (600, 200)

        # Gradient tool color ramp
        sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')
        sxmaterial.node_tree.nodes['ColorRamp'].location = (-900, 200)

        # Vertex color source
        sxmaterial.node_tree.nodes.new(type='ShaderNodeAttribute')
        sxmaterial.node_tree.nodes['Attribute'].attribute_name = compositeUVSet
        sxmaterial.node_tree.nodes['Attribute'].location = (-600, 200)

        # Occlusion source
        sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
        sxmaterial.node_tree.nodes['UV Map'].uv_map = occlusionUVSet
        sxmaterial.node_tree.nodes['UV Map'].location = (-600, 0)

        # Metallic and roughness source
        sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
        sxmaterial.node_tree.nodes['UV Map.001'].uv_map = metallicUVSet
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

        # Emission and transmission source
        sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
        sxmaterial.node_tree.nodes['UV Map.002'].uv_map = transmissionUVSet
        sxmaterial.node_tree.nodes['UV Map.002'].location = (-600, -400)

        sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
        sxmaterial.node_tree.nodes['Separate XYZ.002'].location = (-300, -400)

        sxmaterial.node_tree.nodes.new(type='ShaderNodeMixRGB')
        sxmaterial.node_tree.nodes["Mix.001"].inputs[0].default_value = 1
        sxmaterial.node_tree.nodes["Mix.001"].blend_type = 'MULTIPLY'
        sxmaterial.node_tree.nodes['Mix.001'].location = (0, -400)


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

        # Split transmission and emission
        output = sxmaterial.node_tree.nodes['UV Map.002'].outputs['UV']
        input = sxmaterial.node_tree.nodes['Separate XYZ.002'].inputs['Vector']
        sxmaterial.node_tree.links.new(input, output)

        # X to transmission
        output = sxmaterial.node_tree.nodes['Separate XYZ.002'].outputs['X']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Transmission']
        sxmaterial.node_tree.links.new(input, output)

        # Y to multiply occ/base mix
        output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color1']
        sxmaterial.node_tree.links.new(input, output)
        output = sxmaterial.node_tree.nodes['Separate XYZ.002'].outputs['Y']            
        input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color2']
        sxmaterial.node_tree.links.new(input, output)

        # Mix to emission
        output = sxmaterial.node_tree.nodes['Mix.001'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        sxmaterial.node_tree.links.new(input, output)

    def __del__(self):
        print('SX Tools: Exiting setup')


# ------------------------------------------------------------------------
#    Layer Functions
# ------------------------------------------------------------------------
class SXTOOLS_layers(object):
    def __init__(self):
        return None

    def clearLayers(self, objs, targetLayer = None):
        sxLayers = utils.findColorLayers(objs[0])
        sxUVs = utils.findDefaultValues(objs[0], 'Dict')
        if targetLayer is not None:
            fillmode = targetLayer.layerType
            if targetLayer.uvChannel0 == 'U':
                fillChannel = 0
            elif targetLayer.uvChannel0 == 'V':
                fillChannel = 1


        for obj in objs:
            if targetLayer is None:
                print('SX Tools: Clearing all layers')
                for sxLayer in sxLayers:
                    color = sxLayer.defaultColor
                    tools.applyColor([obj, ], sxLayer, color, True, 0.0)
                    setattr(obj.sxlayers[sxLayer.name], 'alpha', 1.0)
                    setattr(obj.sxlayers[sxLayer.name], 'visibility', True)
                    setattr(obj.sxlayers[sxLayer.name], 'blendMode', 'ALPHA')
            else:
                if fillmode == 'COLOR':
                    color = targetLayer.defaultColor
                    tools.applyColor([obj, ], targetLayer, color, True, 0.0)
                    setattr(obj.sxlayers[targetLayer.name], 'alpha', 1.0)
                    setattr(obj.sxlayers[targetLayer.name], 'visibility', True)
                    setattr(obj.sxlayers[targetLayer.name], 'blendMode', 'ALPHA')
                elif fillmode == 'UV':
                    self.clearUVs(objs, targetLayer)

        if targetLayer is None:
            self.clearUVs(objs, None)

    def clearUVs(self, objs, targetLayer = None):
        objDicts = tools.selectionHandler(objs)
        sxUVs = utils.findDefaultValues(objs[0], 'Dict')
        if targetLayer is not None:
            uvName = targetLayer.uvLayer0
            uvValue = targetLayer.defaultValue
            if targetLayer.uvChannel0 == 'U':
                fillChannel = 0
            elif targetLayer.uvChannel0 == 'V':
                fillChannel = 1

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objs:
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            mesh = obj.data
            if targetLayer is None:
                for i, key in enumerate(mesh.uv_layers.keys()):
                    uvName = mesh.uv_layers[i].name
                    for vert_idx, loop_indices in vertLoopDict.items():
                        for loop_idx in loop_indices:
                            mesh.uv_layers[i].data[loop_idx].uv = sxUVs[uvName]
            else:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        mesh.uv_layers[uvName].data[loop_idx].uv[fillChannel] = uvValue

    def compositeLayers(self, objs):
        #then = time.time()
        compLayers = utils.findCompLayers(objs[0])
        shadingmode = bpy.context.scene.sxtools.shadingmode
        listIdx = bpy.context.scene.sxtools.listIndex
        idx = bpy.context.scene.sxlistitems[listIdx].index
        #idx = objs[0].sxtools.selectedlayer
        layer = utils.findLayerFromIndex(objs[0], idx)

        channels = { 'R': 0, 'G': 1, 'B': 2, 'A': 3 , 'U': 0, 'V': 1}

        if shadingmode == 'FULL':
            self.blendLayers(objs, compLayers, objs[0].sxlayers['composite'], objs[0].sxlayers['composite'])
        else:
            if layer.layerType == 'COLOR':
                self.blendDebug(objs, layer, shadingmode)
            elif layer.name == 'overlay':
                pass
            else:
                mode = objs[0].mode
                bpy.ops.object.mode_set(mode = 'OBJECT')
                for obj in objs:
                    vertexColors = obj.data.vertex_colors
                    vertexUVs = obj.data.uv_layers

                    for poly in obj.data.polygons:
                        for loop_idx in poly.loop_indices:
                            value = vertexUVs[layer.uvLayer0].data[loop_idx].uv[channels[layer.uvChannel0]]
                            vertexColors[obj.sxlayers['composite'].vertexColorLayer].data[loop_idx].color = [value, value, value, 1.0]

                bpy.ops.object.mode_set(mode = mode)

        #now = time.time()
        #print("Compositing duration: ", now-then, " seconds")

    def blendDebug(self, objs, layer, shadingmode):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            resultLayer = vertexColors[obj.sxlayers['composite'].vertexColorLayer].data
            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    if shadingmode == 'DEBUG':
                        top = [
                            vertexColors[layer.vertexColorLayer].data[idx].color[0],
                            vertexColors[layer.vertexColorLayer].data[idx].color[1],
                            vertexColors[layer.vertexColorLayer].data[idx].color[2],
                            vertexColors[layer.vertexColorLayer].data[idx].color[3]][:]
                    elif shadingmode == 'ALPHA':
                        top = [
                            vertexColors[layer.vertexColorLayer].data[idx].color[3],
                            vertexColors[layer.vertexColorLayer].data[idx].color[3],
                            vertexColors[layer.vertexColorLayer].data[idx].color[3],
                            vertexColors[layer.vertexColorLayer].data[idx].color[3]][:]
                    resultLayer[idx].color = top[:]

        bpy.ops.object.mode_set(mode = mode)

    def blendLayers(self, objs, topLayerArray, baseLayer, resultLayer):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            resultColors = vertexColors[resultLayer.vertexColorLayer].data
            baseColors = vertexColors[baseLayer.vertexColorLayer].data

            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    if baseLayer.name == 'composite':
                        base = [0.0, 0.0, 0.0, 1.0]
                    else:
                        base = [
                            baseColors[idx].color[0],
                            baseColors[idx].color[1],
                            baseColors[idx].color[2],
                            baseColors[idx].color[3]][:]
                    for layer in topLayerArray:
                        if not getattr(obj.sxlayers[layer.name], 'visibility'):
                            continue
                        else:
                            blend = getattr(obj.sxlayers[layer.name], 'blendMode')
                            alpha = getattr(obj.sxlayers[layer.name], 'alpha')
                            top = [
                                vertexColors[layer.vertexColorLayer].data[idx].color[0],
                                vertexColors[layer.vertexColorLayer].data[idx].color[1],
                                vertexColors[layer.vertexColorLayer].data[idx].color[2],
                                vertexColors[layer.vertexColorLayer].data[idx].color[3]][:]

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
                    
                    resultColors[idx].color = base[:]
        bpy.ops.object.mode_set(mode = mode)

    # Takes vertex color set names, uv map names, and channel IDs as input.
    # CopyChannel does not perform translation of layernames to object data sets.
    # Expected input is [obj, ...], vertexcolorsetname, R/G/B/A, uvlayername, U/V, mode
    # With mode 1, copyChannel reads sourcecolor and outputs luminance
    def copyChannel(self, objs, source, sourcechannel, target, targetchannel, fillmode):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        channels = { 'R': 0, 'G': 1, 'B': 2, 'A': 3 , 'U': 0, 'V': 1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers

            if fillmode == 0:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = vertexColors[source].data[idx].color[channels[sourcechannel]]
                        vertexUVs[target].data[idx].uv[channels[targetchannel]] = value
            elif fillmode == 1:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        color = vertexColors[source].data[idx].color
                        value = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                        vertexUVs[target].data[idx].uv[channels[targetchannel]] = value

        bpy.ops.object.mode_set(mode = mode)

    # TODO: Fix this one
    def generateMasks(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        layers = utils.findCompLayers(objs[0])

        # Generate 1-bit layer masks for layers 1-7
        # so the faces can be re-colored in a game engine
        for poly in obj.data.polygons:
            for idx in poly.loop_indices:
                for i, layer in enumerate(layers):
                    i += 1
                    if i == 1:
                        vertexUVs[uvmap].data[idx].uv[channels[targetchannel]] = i
                    else:
                        vertexAlpha = vertexColors[layer.name].data[idx].color[channels[sourcechannel]][3]
                        if vertexAlpha >= sxglobals.alphaTolerance:
                            vertexUVs[uvmap].data[idx].uv[channels[targetchannel]] = i

        bpy.ops.object.mode_set(mode = mode)

    # TODO: Handle UV merging
    def mergeLayers(self, objs, sourceLayer, targetLayer):
        if sourceLayer.index < targetLayer.index:
            baseLayer = sourceLayer
            topLayer = targetLayer
        else:
            baseLayer = targetLayer
            topLayer = sourceLayer

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.name], 'visibility', True)
            setattr(obj.sxlayers[targetLayer.name], 'visibility', True)

        self.blendLayers(objs, [topLayer, ], baseLayer, targetLayer)
        self.clearLayers(objs, sourceLayer)

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.name], 'blendMode', 'ALPHA')
            setattr(obj.sxlayers[targetLayer.name], 'blendMode', 'ALPHA')

        # TODO: this works with color layers only
        objs[0].data.vertex_colors.active_index = targetLayer.index
        #objs[0].sxtools.selectedlayer = targetLayer.index - 1
        bpy.context.scene.sxtools.listIndex = utils.findListIndex(objs[0], targetLayer)

    def pasteLayer(self, objs, sourceLayer, targetLayer, swap):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        for obj in objs:
            sourceVertexColors = obj.data.vertex_colors[sourceLayer.vertexColorLayer].data
            targetVertexColors = obj.data.vertex_colors[targetLayer.vertexColorLayer].data
            tempVertexColors = obj.data.vertex_colors[obj.sxlayers['composite'].vertexColorLayer].data

            sourceBlend = getattr(obj.sxlayers[sourceLayer.name], 'blendMode')[:]
            targetBlend = getattr(obj.sxlayers[targetLayer.name], 'blendMode')[:]

            if swap == True:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = targetVertexColors[idx].color[:]
                        tempVertexColors[idx].color = value
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = sourceVertexColors[idx].color[:]
                        targetVertexColors[idx].color = value
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = tempVertexColors[idx].color[:]
                        sourceVertexColors[idx].color = value
                setattr(obj.sxlayers[sourceLayer.name], 'blendMode', targetBlend)
                setattr(obj.sxlayers[targetLayer.name], 'blendMode', sourceBlend)
            else:
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        value = sourceVertexColors[idx].color[:]
                        targetVertexColors[idx].color = value
                setattr(obj.sxlayers[targetLayer.name], 'blendMode', sourceBlend)

        bpy.ops.object.mode_set(mode = mode)

    def updateLayerPalette(self, obj, layer):
        mode = obj.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        mesh = obj.data
        if layer.layerType == 'COLOR':
            vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
        else:
            uvValues = obj.data.uv_layers[layer.uvLayer0].data
        colorArray = []

        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                if layer.layerType == 'COLOR':
                    vColor = vertexColors[loop_idx].color[:]
                else:
                    if layer.uvChannel0 == 'U':
                        vValue = uvValues[loop_idx].uv[0]
                    else:
                        vValue = round(uvValues[loop_idx].uv[1], 1)

                if (layer.layerType == 'COLOR') and (vColor[3] != 0.0):
                    listColor = (round(vColor[0], 1), round(vColor[1], 1), round(vColor[2], 1), 1.0)
                    colorArray.append(listColor)
                elif layer.layerType == 'UV':
                    listColor = (vValue, vValue, vValue, 1.0)
                    colorArray.append(listColor)

        colorSet = set(colorArray)
        colorFreq = []
        for color in colorSet:
            colorFreq.append((colorArray.count(color), color))

        sortColors = sorted(colorFreq, key=lambda tup: tup[0])
        colLen = len(sortColors)
        while colLen < 8:
            sortColors.append((0, [0.0, 0.0, 0.0, 1.0]))
            colLen += 1

        bpy.context.scene.sxtools.layerpalette1 = sortColors[0][1]
        bpy.context.scene.sxtools.layerpalette2 = sortColors[1][1]
        bpy.context.scene.sxtools.layerpalette3 = sortColors[2][1]
        bpy.context.scene.sxtools.layerpalette4 = sortColors[3][1]
        bpy.context.scene.sxtools.layerpalette5 = sortColors[4][1]
        bpy.context.scene.sxtools.layerpalette6 = sortColors[5][1]
        bpy.context.scene.sxtools.layerpalette7 = sortColors[6][1]
        bpy.context.scene.sxtools.layerpalette8 = sortColors[7][1]

        bpy.ops.object.mode_set(mode = mode)

    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------
class SXTOOLS_tools(object):
    def __init__(self):
        return None

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

    # Analyze if multi-object selection is in object or component mode,
    # return appropriate vertices
    def selectionHandler(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        objDicts = {}
        objSel = False
        faceSel = False
        vertSel = False

        if mode == 'OBJECT':
            objSel = True
        else:
            for obj in objs:
                mesh = obj.data
                if (True in [poly.select for poly in mesh.polygons]):
                    faceSel = True
                elif (True in [vertex.select for vertex in mesh.vertices]):
                    vertSel = True

        for obj in objs:
            mesh = obj.data
            mat = obj.matrix_world

            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            vertWorldPosDict = defaultdict(list)

            if objSel or faceSel:
                for poly in mesh.polygons:
                    if poly.select or objSel:
                        for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                            vertLoopDict[vert_idx].append(loop_idx)
                            vertPosDict[vert_idx] = (
                                mesh.vertices[vert_idx].co,
                                mesh.vertices[vert_idx].normal)
                            vertWorldPosDict[vert_idx] = (
                                mat @ mesh.vertices[vert_idx].co,
                                mat @ mesh.vertices[vert_idx].normal)
            else:
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        if mesh.vertices[vert_idx].select:
                            vertLoopDict[vert_idx].append(loop_idx)
                            vertPosDict[vert_idx] = (
                                mesh.vertices[vert_idx].co,
                                mesh.vertices[vert_idx].normal)
                            vertWorldPosDict[vert_idx] = (
                                mat @ mesh.vertices[vert_idx].co,
                                mat @ mesh.vertices[vert_idx].normal)

            objDicts[obj] = (vertLoopDict, vertPosDict, vertWorldPosDict)

        bpy.ops.object.mode_set(mode = mode)
        return objDicts

    def applyColor(self, objs, layer, color, overwrite, noise = 0.0, mono = False):
        objDicts = self.selectionHandler(objs)
        fillMode = layer.layerType

        fillValue = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
        if layer.uvChannel0 == 'U':
            fillChannel = 0
        elif layer.uvChannel0 == 'V':
            fillChannel = 1

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objs:
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            if noise == 0.0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if overwrite:
                            if fillMode == 'COLOR':
                                vertexColors[loop_idx].color = color
                            elif fillMode == 'UV':
                                uvValues[loop_idx].uv[fillChannel] = fillValue
                        else:
                            if fillMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = color[0]
                                    vertexColors[loop_idx].color[1] = color[1]
                                    vertexColors[loop_idx].color[2] = color[2]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV':
                                if uvValues[loop_idx].uv[fillChannel] > 0.0:
                                    uvValues[loop_idx].uv[fillChannel] = fillValue

            else:
                if fillMode == 'COLOR':
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
                elif fillMode == 'UV':
                    for vert_idx, loop_indices in vertLoopDict.items():
                        fillNoise = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                        fillNoise += random.uniform(-fillNoise*noise, fillNoise*noise)
                        for loop_idx in loop_indices:
                            if overwrite:
                                uvValues[loop_idx].uv[fillChannel] = fillNoise
                            else:
                                if uvValues[loop_idx].uv[fillChannel] > 0.0:
                                    uvValues[loop_idx].uv[fillChannel] = fillNoise

        bpy.ops.object.mode_set(mode = mode)

    def updateRecentColors(self, color):
        scn = bpy.context.scene.sxtools
        palCols = [
            scn.fillpalette1[:],
            scn.fillpalette2[:],
            scn.fillpalette3[:],
            scn.fillpalette4[:],
            scn.fillpalette5[:],
            scn.fillpalette6[:],
            scn.fillpalette7[:],
            scn.fillpalette8[:]]
        colorArray = [
            color, palCols[0], palCols[1], palCols[2],
            palCols[3], palCols[4], palCols[5], palCols[6]]

        fillColor = color[:]
        if (fillColor not in palCols) and (fillColor[3] > 0.0):
            scn.fillpalette1 = colorArray[0][:]
            scn.fillpalette2 = colorArray[1][:]
            scn.fillpalette3 = colorArray[2][:]
            scn.fillpalette4 = colorArray[3][:]
            scn.fillpalette5 = colorArray[4][:]
            scn.fillpalette6 = colorArray[5][:]
            scn.fillpalette7 = colorArray[6][:]
            scn.fillpalette8 = colorArray[7][:]

    def applyRamp(self, objs, layer, ramp, rampmode, overwrite, mergebbx = True, noise = 0.0):
        objDicts = self.selectionHandler(objs)
        fillMode = layer.layerType
        if layer.uvChannel0 == 'U':
            fillChannel = 0
        elif layer.uvChannel0 == 'V':
            fillChannel = 1

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        curvatures = []
        if rampmode == 'C':
            objValues = self.calculateCurvature(objs, False)
        elif rampmode == 'CN':
            objValues = self.calculateCurvature(objs, True)
        elif rampmode == 'OCC':
            objValues = self.bakeOcclusion(objs, bpy.context.scene.sxtools.occlusionrays, bpy.context.scene.sxtools.occlusionblend)
        elif rampmode == 'LUM':
            objValues = self.calculateLuminance(objs, layer)

        if mergebbx:
            bbx_x = []
            bbx_y = []
            bbx_z = []
            for obj in objs:
                corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                for corner in corners:
                    bbx_x.append(corner[0])
                    bbx_y.append(corner[1])
                    bbx_z.append(corner[2])
            xmin, xmax = min(bbx_x), max(bbx_x)
            ymin, ymax = min(bbx_y), max(bbx_y)
            zmin, zmax = min(bbx_z), max(bbx_z)

        for obj in objs:
            if rampmode == 'C' or rampmode == 'CN' or rampmode == 'OCC' or rampmode == 'LUM':
                valueDict = objValues[obj]
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data
            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            mat = obj.matrix_world
            
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            
            if not mergebbx and (rampmode != 'C') and (rampmode != 'CN') and (rampmode != 'OCC') and (rampmode != 'LUM'):
                bbx = self.calculateBoundingBox(vertPosDict)
                xmin, xmax = bbx[0][0], bbx[0][1]
                ymin, ymax = bbx[1][0], bbx[1][1]
                zmin, zmax = bbx[2][0], bbx[2][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                for i, loop_idx in enumerate(loop_indices):
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
                    elif rampmode == 'C' or rampmode == 'CN' or rampmode == 'OCC':
                        ratioRaw = valueDict[vert_idx]
                    elif rampmode == 'LUM':
                        ratioRaw = valueDict[vert_idx][1]

                    if rampmode == 'LUM':
                        ratio = []
                        for rt in ratioRaw:
                            ratio.append(max(min(rt, 1), 0))
                        if overwrite:
                            if fillMode == 'COLOR':
                                vertexColors[loop_idx].color = ramp.color_ramp.evaluate(ratio[i])
                            elif fillMode == 'UV':
                                color = ramp.color_ramp.evaluate(ratio[i])
                                fillValue = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                                uvValues[loop_idx].uv[fillChannel] = fillValue
                        else:
                            if fillMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = ramp.color_ramp.evaluate(ratio[i])[0]
                                    vertexColors[loop_idx].color[1] = ramp.color_ramp.evaluate(ratio[i])[1]
                                    vertexColors[loop_idx].color[2] = ramp.color_ramp.evaluate(ratio[i])[2]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV':
                                if uvValues[loop_idx].uv[fillChannel] > 0.0:
                                    color = ramp.color_ramp.evaluate(ratio[i])
                                    fillValue = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                                    uvValues[loop_idx].uv[fillChannel] = fillValue

                    else:
                        ratio = max(min(ratioRaw, 1), 0)
                        if overwrite:
                            if fillMode == 'COLOR':
                                vertexColors[loop_idx].color = ramp.color_ramp.evaluate(ratio)
                            elif fillMode == 'UV':
                                color = ramp.color_ramp.evaluate(ratio)
                                fillValue = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                                uvValues[loop_idx].uv[fillChannel] = fillValue
                        else:
                            if fillMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = ramp.color_ramp.evaluate(ratio)[0]
                                    vertexColors[loop_idx].color[1] = ramp.color_ramp.evaluate(ratio)[1]
                                    vertexColors[loop_idx].color[2] = ramp.color_ramp.evaluate(ratio)[2]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV':
                                if uvValues[loop_idx].uv[fillChannel] > 0.0:
                                    color = ramp.color_ramp.evaluate(ratio)
                                    fillValue = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
                                    uvValues[loop_idx].uv[fillChannel] = fillValue

        bpy.ops.object.mode_set(mode = mode)

    def selectMask(self, objs, layer, inverse):
        mode = objs[0].mode

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode = 'OBJECT', toggle=False)

        objDicts = self.selectionHandler(objs)
        selMode = layer.layerType

        for obj in objs:
            if selMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif selMode == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data
                if layer.uvChannel0 == 'U':
                    selChannel = 0
                elif layer.uvChannel0 == 'V':
                    selChannel = 1
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            selList = []
            for vert_idx, loop_indices in vertLoopDict.items():
                for loop_idx in loop_indices:
                    if inverse:
                        if selMode == 'COLOR':
                            if vertexColors[loop_idx].color[3] == 0.0:
                                obj.data.vertices[vert_idx].select = True
                        elif selMode == 'UV':
                            if uvValues[loop_idx].uv[selChannel] == 0.0:
                                obj.data.vertices[vert_idx].select = True                                
                    else:
                        if selMode == 'COLOR':
                            if vertexColors[loop_idx].color[3] > 0.0:
                                obj.data.vertices[vert_idx].select = True
                        elif selMode == 'UV':
                            if uvValues[loop_idx].uv[selChannel] > 0.0:
                                obj.data.vertices[vert_idx].select = True   

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    def selectCrease(self, objs, group):
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0 }
        weight = creaseDict[group]
        bpy.ops.object.mode_set(mode = 'EDIT')

        for obj in objs:
            bm = bmesh.from_edit_mesh(obj.data)

            if 'SubSurfCrease' in bm.edges.layers.crease.keys():
                creaseLayer = bm.edges.layers.crease['SubSurfCrease']

                creaseEdges = [edge for edge in bm.edges if edge[creaseLayer] == weight]
                for edge in creaseEdges:
                    edge.select = True

            #bmesh.update_edit_mesh(obj.data)

    def assignCrease(self, objs, group, hard):
        mode = objs[0].mode
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0 }
        weight = creaseDict[group]
        bpy.ops.object.mode_set(mode = 'EDIT')

        for obj in objs:
            bm = bmesh.from_edit_mesh(obj.data)

            if 'SubSurfCrease' in bm.edges.layers.crease.keys():
                creaseLayer = bm.edges.layers.crease['SubSurfCrease']
            else:
                creaseLayer = bm.edges.layers.crease.new('SubSurfCrease')
            selectedEdges = [edge for edge in bm.edges if edge.select]
            for edge in selectedEdges:
                edge[creaseLayer] = weight
                if weight == 1.0 and hard:
                    edge.smooth = False
                else:
                    edge.smooth = True

            bmesh.update_edit_mesh(obj.data)
        bpy.ops.object.mode_set(mode = mode)

    # take sourcelayername and targetuvlayername,
    # translate to copyChannel batches
    # set copyChannel to luminance mode if RGB layer
    def layerToUV(self, objs, sourceLayer, targetLayer):
        sourcechannels = ['R', 'G', 'B', 'A']
        if sourceLayer.layerType == 'COLOR':
            fillmode = 1
        else:
            fillmode = 0

        for obj in objs:
            sourceVertexColors = obj.sxlayers[sourceLayer.name].vertexColorLayer
            targetArray = utils.findExportChannels(obj, targetLayer)
            for i, target in enumerate(targetArray):
                layers.copyChannel([obj, ], sourceVertexColors, sourcechannels[i], target[0], target[1], fillmode)

    def processMesh(self, objs):
        # placeholder for batch export preprocessor
        # 0: UV0 for basic automatically laid out UVs
        # 1: palettemasks to U1
        #layers.copyChannel(objs, 'LAYER1', 'R', 'UVMAP1', 'U')
        # static flag to object
        # Assume artist has placed occlusion, metallic, smoothness, emission and transmission
        pass

    def mergeLayersManager(self, objs, sourceLayer, direction):
        forbidden = ['composite', 'occlusion', 'metallic', 'roughness', 'transmission', 'emission']
        if (sourceLayer == 'layer1') and (direction == 'UP'):
            print('SX Tools Error: Cannot merge layer1')
            return
        elif (sourceLayer == 'layer7') and (direction == 'DOWN'):
            print('SX Tools Error: Cannot merge layer7')
            return
        elif sourceLayer in forbidden:
            print('SX Tools Error: Cannot merge selected channel')
            return

        layerIndex = sourceLayer.index

        if direction == 'UP':
            targetLayer = utils.findLayerFromIndex(objs[0], layerIndex - 1)
        else:
            targetLayer = utils.findLayerFromIndex(objs[0], layerIndex + 1)

        layers.mergeLayers(objs, sourceLayer, targetLayer)    

    def rayRandomizer(self):
        u1 = random.uniform(0, 1)
        u2 = random.uniform(0, 1)
        r = math.sqrt(u1)
        theta = 2*math.pi*u2

        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return (x, y, math.sqrt(max(0, 1 - u1)))

    def bakeOcclusion(self, objs, rayCount=250, blend=0.0, bias=0.000001):
        objDicts = {}
        objDicts = self.selectionHandler(objs)

        mode = objs[0].mode
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        scene = bpy.context.scene
        contribution = 1.0/float(rayCount)
        hemiSphere = [None] * rayCount
        bias = 1e-5

        objOcclusions = {}

        for idx in range(rayCount):
            hemiSphere[idx] = self.rayRandomizer()

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = False
        #bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.object.mode_set(mode = 'OBJECT')

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            vertWorldPosDict = objDicts[obj][2]
            vertOccDict = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                occValue = 1.0
                scnOccValue = 1.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                vertWorldLoc = Vector(vertWorldPosDict[vert_idx][0])
                vertWorldNormal = Vector(vertWorldPosDict[vert_idx][1])
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
                    scnNormal = vertWorldNormal
                    biasVec = tuple([bias*x for x in scnNormal])
                    rotQuat = forward.rotation_difference(scnNormal)
                    scnVertPos = vertWorldLoc

                    # offset ray origin with normal bias
                    scnVertPos = (scnVertPos[0] + biasVec[0], scnVertPos[1] + biasVec[1], scnVertPos[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        scnHit, scnLoc, scnNormal, scnIndex, scnObj, ma = scene.ray_cast(scene.view_layers[0], scnVertPos, sample)

                        if scnHit:
                            scnOccValue -= contribution

                for loop_idx in loop_indices:
                    vertOccDict[vert_idx] = float(occValue * (1.0 - blend) + scnOccValue * blend)
            objOcclusions[obj] = vertOccDict

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = True

        bpy.ops.object.mode_set(mode = mode)
        return objOcclusions

    # TODO: Broken for UV layers
    def calculateLuminance(self, objs, layer):
        objDicts = {}
        objDicts = self.selectionHandler(objs)

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

        objLuminances = {}

        for obj in objs:
            vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]
            vtxLuminances = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                loopLuminances = []
                for loop_idx in loop_indices:
                    fvColor = vertexColors[loop_idx].color
                    luminance = ((fvColor[0] +
                                  fvColor[0] +
                                  fvColor[2] +
                                  fvColor[1] +
                                  fvColor[1] +
                                  fvColor[1]) / float(6.0))
                    loopLuminances.append(luminance)
                vertLoopDict[vert_idx] = (loop_indices, loopLuminances)
            objLuminances[obj] = vertLoopDict

        bpy.ops.object.mode_set(mode = mode)
        return objLuminances

    def calculateCurvature(self, objs, normalize=False):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode = 'EDIT')

        objCurvatures = {}

        for obj in objs:
            vtxCurvatures = {}
            bm = bmesh.from_edit_mesh(obj.data)
            for vert in bm.verts:
                numConnected = len(vert.link_edges)
                edgeWeights = []
                angles = []
                for edge in vert.link_edges:
                    edgeWeights.append(edge.calc_length())
                    pos1 = vert.co
                    pos2 = edge.other_vert(vert).co
                    edgeVec = Vector((float(pos2[0] - pos1[0]), float(pos2[1] - pos1[1]), float(pos2[2] - pos1[2])))
                    angles.append(math.acos(vert.normal.normalized() @ edgeVec.normalized()))

                vtxCurvature = 0.0
                for i in range(numConnected):
                    curvature = angles[i] / math.pi - 0.5
                    vtxCurvature += curvature

                vtxCurvature = vtxCurvature / float(numConnected)
                if vtxCurvature > 1.0:
                    vtxCurvature = 1.0

                vtxCurvatures[vert.index] = vtxCurvature
            objCurvatures[obj] = vtxCurvatures

        # Normalize convex and concave separately
        # to maximize artist ability to crease

        if normalize:
            maxArray = []
            minArray = []
            for vtxCurvature in objCurvatures.values():
                minArray.append(min(vtxCurvature.values()))
                maxArray.append(max(vtxCurvature.values()))
            minCurv = min(minArray)
            maxCurv = max(maxArray)

            for vtxCurvatures in objCurvatures.values():
                for vert, vtxCurvature in vtxCurvatures.items():
                    if vtxCurvature < 0:
                        vtxCurvatures[vert] = (vtxCurvature / float(minCurv)) * -0.5 + 0.5
                    else:
                        vtxCurvatures[vert] = (vtxCurvature / float(maxCurv)) * 0.5 + 0.5
        else:
            for vtxCurvatures in objCurvatures.values():
                for vert, vtxCurvature in vtxCurvatures.items():
                    vtxCurvatures[vert] = (vtxCurvature + 0.5)

        bpy.ops.object.mode_set(mode = mode)
        return objCurvatures

    def applyPalette(self, objs, palette, noise, mono):
        palette = [
            bpy.context.scene.sxpalettes[palette].color0,
            bpy.context.scene.sxpalettes[palette].color1,
            bpy.context.scene.sxpalettes[palette].color2,
            bpy.context.scene.sxpalettes[palette].color3,
            bpy.context.scene.sxpalettes[palette].color4]

        for idx in range(1, 6):
            layer = utils.findLayerFromIndex(objs[0], idx)
            color = palette[idx - 1]

            self.applyColor(objs, layer, color, False, noise, mono)

    def applyMaterial(self, objs, layer, material, overwrite, noise, mono):
        sourceLayer = str(layer).upper()
        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        # Set material properties to layer, copy to UV
        self.applyColor(objs, layer, palette[2], overwrite, noise, mono)
        self.layerToUV(objs, sourceLayer, 'SMTH')
        self.applyColor(objs, layer, palette[1], overwrite, noise, mono)
        self.layerToUV(objs, sourceLayer, 'MET')
        self.applyColor(objs, layer, palette[0], overwrite, noise, mono)

    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Core Functions
# ------------------------------------------------------------------------
def updateLayers(self, context):
    if not sxglobals.refreshInProgress:
        shadingMode(self, context)

        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        #print(idx, layer)
        alphaVal = getattr(objs[0].sxtools, 'activeLayerAlpha')
        blendVal = getattr(objs[0].sxtools, 'activeLayerBlendMode')
        visVal = getattr(objs[0].sxtools, 'activeLayerVisibility')

        for obj in objs:
            obj.data.vertex_colors.active_index = idx
            if obj.sxlayers[layer.name].layerType == 'COLOR':
                setattr(obj.sxlayers[layer.name], 'alpha', alphaVal)
                setattr(obj.sxlayers[layer.name], 'blendMode', blendVal)
                setattr(obj.sxlayers[layer.name], 'visibility', visVal)

                sxglobals.refreshInProgress = True
                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)
                sxglobals.refreshInProgress = False

        setup.setupGeometry(objs)
        layers.compositeLayers(objs)

def refreshActives(self, context):
    if not sxglobals.refreshInProgress:
        sxglobals.refreshInProgress = True
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        #idx = objs[0].sxtools.selectedlayer
        layer = utils.findLayerFromIndex(objs[0], idx)
        #print(idx, layer)

        for obj in objs:
            obj.sxtools.selectedlayer = idx
            if obj.sxlayers[layer.name].layerType == 'COLOR':
                obj.data.vertex_colors.active_index = idx + 1

                alphaVal = getattr(obj.sxlayers[layer.name], 'alpha')
                blendVal = getattr(obj.sxlayers[layer.name], 'blendMode')
                visVal = getattr(obj.sxlayers[layer.name], 'visibility')

                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)

            layers.compositeLayers(objs)

        sxglobals.refreshInProgress = False
        layers.updateLayerPalette(objs[0], layer)

# Clicking a palette color would ideally set it in fillcolor, TBD
def updateColorSwatches(self, context):
    pass

def shadingMode(self, context):
    mode = context.scene.sxtools.shadingmode
    objs = selectionValidator(self, context)
    listIdx = context.scene.sxtools.listIndex
    idx = context.scene.sxlistitems[listIdx].index
    layer = utils.findLayerFromIndex(objs[0], idx)
    sxmaterial = bpy.data.materials['SXMaterial']
    
    if mode == 'FULL':
        areas = bpy.context.workspace.screens[0].areas
        shading = 'RENDERED'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    if (space.shading.type == 'WIREFRAME') or (space.shading.type == 'SOLID'):
                        space.shading.type = shading

        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.5

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

        # Reconnect transmission
        output = sxmaterial.node_tree.nodes['Separate XYZ.002'].outputs['X']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Transmission']
        sxmaterial.node_tree.links.new(input, output)

        # Reconnect emission
        output = sxmaterial.node_tree.nodes['Mix.001'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        sxmaterial.node_tree.links.new(input, output)

        # Reconnect base mix
        output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color1']
        sxmaterial.node_tree.links.new(input, output)

    else:
        areas = bpy.context.workspace.screens[0].areas
        shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
        for area in areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = shading

        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0

        # Disconnect base color, metallic and roughness
        attrLink = sxmaterial.node_tree.nodes['Attribute'].outputs[0].links[0]
        sxmaterial.node_tree.links.remove(attrLink)

        # Check if already debug
        if len(sxmaterial.node_tree.nodes['Mix.001'].outputs[0].links) > 0:
            attrLink = sxmaterial.node_tree.nodes['Mix'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)
            attrLink = sxmaterial.node_tree.nodes['Separate XYZ.001'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)
            attrLink = sxmaterial.node_tree.nodes['Invert'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)
            attrLink = sxmaterial.node_tree.nodes['Separate XYZ.002'].outputs[0].links[0]
            sxmaterial.node_tree.links.remove(attrLink)

        # Connect vertex color source to emission
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
        sxmaterial.node_tree.links.new(input, output)

def selectionValidator(self, context):
    selObjs = []
    for obj in context.view_layer.objects.selected:
        objType = getattr(obj, 'type', '')
        if objType == 'MESH':
            selObjs.append(obj)
    return selObjs

# ------------------------------------------------------------------------
#    Settings and preferences
# ------------------------------------------------------------------------
class SXTOOLS_objectprops(bpy.types.PropertyGroup):
    selectedlayer: bpy.props.IntProperty(
        name = 'Selected Layer',
        min = 0,
        max = 20,
        default = 0)

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


class SXTOOLS_sceneprops(bpy.types.PropertyGroup):
    listIndex: bpy.props.IntProperty(
        name = 'List Index',
        min = 0,
        max = 20,
        default = 0,
        update = refreshActives)

    shadingmode: bpy.props.EnumProperty(
        name = "Shading Mode",
        items = [
            ('FULL','Full',''),
            ('DEBUG','Debug',''),
            ('ALPHA','Alpha','')],
        default = 'FULL',
        update = updateLayers)

    layerpalette1: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 1',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette2: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 2',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette3: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 3',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette4: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 4',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette5: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 5',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette6: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 6',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))
    layerpalette7: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 7',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    layerpalette8: bpy.props.FloatVectorProperty(
        name = 'Layer Palette 8',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette1: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 1',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette2: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 2',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette3: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 3',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette4: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 4',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette5: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 5',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette6: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 6',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette7: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 7',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

    fillpalette8: bpy.props.FloatVectorProperty(
        name = 'Fill Palette 8',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 1.0))

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
            ('Z','Z-Axis',''),
            ('LUM', 'Luminance', ''),
            ('C','Curvature',''),
            ('CN', 'Normalized Curvature', ''),
            ('OCC', 'Ambient Occlusion', '')],
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
        max = 2000,
        default = 256)

    palettenoise: bpy.props.FloatProperty(
        name = "Noise",
        min = 0.0,
        max = 1.0,
        default = 0.0)

    palettemono: bpy.props.BoolProperty(
        name = "Monochrome",
        default = False)

    materialalpha: bpy.props.BoolProperty(
        name = "Overwrite Alpha",
        default = True)

    materialnoise: bpy.props.FloatProperty(
        name = "Noise",
        min = 0.0,
        max = 1.0,
        default = 0.0)

    materialmono: bpy.props.BoolProperty(
        name = "Monochrome",
        default = False)

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

    materialmap: bpy.props.EnumProperty(
        name = "Channel Map",
        items = [
            ('OCC','Occlusion',''),
            ('TRNS','Transmission',''),
            ('EMISS','Emission',''),
            ('MET','Metallic',''),
            ('SMTH','Smoothness',''),
            ('GRD1','Gradient 1',''),
            ('GRD2','Gradient 2',''),
            ('OVR','Overlay','')],
        default = 'OCC')

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

    hardcrease: bpy.props.BoolProperty(
        name = "Hard Crease",
        default = True)

    expandfill: bpy.props.BoolProperty(
        name = "Expand Fill",
        default = False)

    expandramp: bpy.props.BoolProperty(
        name = "Expand Ramp",
        default = False)

    expandcrease: bpy.props.BoolProperty(
        name = "Expand Crease",
        default = False)

    expandpalette: bpy.props.BoolProperty(
        name = "Expand Palette",
        default = False)

    expandmaterials: bpy.props.BoolProperty(
        name = "Expand Materials",
        default = False)

    expandchcopy: bpy.props.BoolProperty(
        name = "Expand Channelcopy",
        default = False)

    libraryfolder: bpy.props.StringProperty(
        name = 'Library Folder',
        description = 'Folder containing Materials and Palettes files',
        default = '',
        maxlen = 1024,
        subtype = 'DIR_PATH')


class SXTOOLS_masterpalette(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty(
        name = 'Category',
        description = 'Palette Category',
        default = '')

    color0: bpy.props.FloatVectorProperty(
        name = 'Palette Color 0',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name = 'Palette Color 1',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name = 'Palette Color 2',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color3: bpy.props.FloatVectorProperty(
        name = 'Palette Color 3',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color4: bpy.props.FloatVectorProperty(
        name = 'Palette Color 4',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))


class SXTOOLS_material(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty(
        name = 'Category',
        description = 'Material Category',
        default = '')

    color0: bpy.props.FloatVectorProperty(
        name = 'Material Color',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name = 'Material Metallic',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name = 'Material Smoothness',
        subtype = "COLOR",
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0))


class SXTOOLS_layer(bpy.types.PropertyGroup):
    # name: from PropertyGroup

    index: bpy.props.IntProperty(
        name = 'Layer Index',
        min = 0,
        max = 100,
        default = 0)

    layerType: bpy.props.EnumProperty(
        name = 'Layer Type',
        items = [
            ('COLOR','Color',''),
            ('UV','UV','')],
        default = 'COLOR')

    defaultColor: bpy.props.FloatVectorProperty(
        name = 'Default Color',
        subtype = 'COLOR',
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (0.0, 0.0, 0.0, 0.0))

    defaultValue: bpy.props.FloatProperty(
        name = 'Default Value',
        min = 0.0,
        max = 1.0,
        default = 0.0)

    visibility: bpy.props.BoolProperty(
        name = 'Layer Visibility',
        default = True)

    alpha: bpy.props.FloatProperty(
        name = 'Layer Alpha',
        min = 0.0,
        max = 1.0,
        default = 1.0)

    blendMode: bpy.props.EnumProperty(
        name = "Layer Blend Mode",
        items = [
            ('ALPHA','Alpha',''),
            ('ADD','Additive',''),
            ('MUL','Multiply','')],
        default = 'ALPHA')

    vertexColorLayer: bpy.props.StringProperty(
        name = 'Vertex Color Layer',
        description = 'Maps a list item to a vertex color layer',
        default = '')

    uvLayer0: bpy.props.StringProperty(
        name = 'UV Map',
        description = 'Maps a list item to a UV set',
        default = '')

    uvChannel0: bpy.props.EnumProperty(
        name = 'UV Channel',
        items = [
            ('U','U',''),
            ('V','V','')],
        default = 'U')

    uvLayer1: bpy.props.StringProperty(
        name = 'UV Map',
        description = 'Maps a list item to a UV set',
        default = '')

    uvChannel1: bpy.props.EnumProperty(
        name = 'UV Channel',
        items = [
            ('U','U',''),
            ('V','V','')],
        default = 'U')

    uvLayer2: bpy.props.StringProperty(
        name = 'UV Map',
        description = 'Maps a list item to a UV set',
        default = '')

    uvChannel2: bpy.props.EnumProperty(
        name = 'UV Channel',
        items = [
            ('U','U',''),
            ('V','V','')],
        default = 'U')

    uvLayer3: bpy.props.StringProperty(
        name = 'UV Map',
        description = 'Maps a list item to a UV set',
        default = '')

    uvChannel3: bpy.props.EnumProperty(
        name = 'UV Channel',
        items = [
            ('U','U',''),
            ('V','V','')],
        default = 'U')


    showInLayerList: bpy.props.BoolProperty(
        name = "Show in Layer List",
        default = True)


class SXTOOLS_listitem(bpy.types.PropertyGroup):
    # name: from PropertyGroup

    index: bpy.props.IntProperty(
        name = 'Item Index',
        min = 0,
        max = 100,
        default = 0)

# ------------------------------------------------------------------------
#    UI Panel and Operators
# ------------------------------------------------------------------------
class SXTOOLS_PT_panel(bpy.types.Panel):

    bl_idname = "SXTOOLS_PT_panel"
    bl_label = "SX Tools"    
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            obj = objs[0]

            layout = self.layout
            mesh = obj.data
            mode = obj.mode
            sxtools = obj.sxtools
            sxlayers = obj.sxlayers
            scene = context.scene.sxtools
            palettes = context.scene.sxpalettes
            
            if mesh.vertex_colors.active is None:
                col = self.layout.column(align = True)
                if (len(objs) == 1):
                    col.operator('sxtools.scenesetup', text = 'Set Up Object')
                else:
                    col.operator('sxtools.scenesetup', text = 'Set Up Objects')
            else:
                listIdx = context.scene.sxtools.listIndex
                sel_idx = context.scene.sxlistitems[listIdx].index
                layer = utils.findLayerFromIndex(obj, sel_idx)

                row_shading = self.layout.row(align = True)
                row_shading.prop(scene, 'shadingmode', expand = True)

                row_blend = self.layout.row(align = True)
                row_blend.prop(sxtools, 'activeLayerVisibility')
                row_blend.prop(sxtools, 'activeLayerBlendMode', text = 'Blend')
                row_alpha = self.layout.row(align = True)
                row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text = 'Layer Opacity')

                row_palette = self.layout.row(align = True)
                row_palette.prop(scene, 'layerpalette1', text = '')
                row_palette.prop(scene, 'layerpalette2', text = '')
                row_palette.prop(scene, 'layerpalette3', text = '')
                row_palette.prop(scene, 'layerpalette4', text = '')
                row_palette.prop(scene, 'layerpalette5', text = '')
                row_palette.prop(scene, 'layerpalette6', text = '')
                row_palette.prop(scene, 'layerpalette7', text = '')
                row_palette.prop(scene, 'layerpalette8', text = '')

                if (layer.layerType != 'COLOR') or (scene.shadingmode != 'FULL'):
                    row_blend.enabled = False
                    row_alpha.enabled = False

                layout.template_list('UI_UL_list', 'sxtools.layerlist', context.scene, 'sxlistitems', scene, 'listIndex', type = 'DEFAULT')
                #layout.template_list('UI_UL_list', 'sxtools.layerList', mesh, 'vertex_colors', sxtools, 'selectedlayer', type = 'DEFAULT')

                # Layer Copy Paste Merge ---------------------------------------
                row_misc1 = self.layout.row(align = True)
                row_misc1.operator('sxtools.mergeup')
                row_misc1.operator('sxtools.copylayer', text = 'Copy')
                row_misc1.operator('sxtools.clear', text = 'Clear')
                row_misc2 = self.layout.row(align = True)
                row_misc2.operator('sxtools.mergedown')
                row_misc2.operator('sxtools.pastelayer', text = 'Paste')
                row_misc2.operator('sxtools.selmask', text = 'Select Mask')

                # Color Fill ---------------------------------------------------
                box_fill = layout.box()
                row_fill = box_fill.row()
                row_fill.prop(scene, "expandfill",
                    icon="TRIA_DOWN" if scene.expandfill else "TRIA_RIGHT",
                    icon_only=True, emboss=False)
                if layer.layerType == 'COLOR':
                    row_fill.label(text = 'Apply Color')
                else:
                    row_fill.label(text = 'Apply Color (Grayscale)')

                if scene.expandfill:
                    row_fpalette = box_fill.row(align = True)
                    row_fpalette.prop(scene, 'fillpalette1', text = '')
                    row_fpalette.prop(scene, 'fillpalette2', text = '')
                    row_fpalette.prop(scene, 'fillpalette3', text = '')
                    row_fpalette.prop(scene, 'fillpalette4', text = '')
                    row_fpalette.prop(scene, 'fillpalette5', text = '')
                    row_fpalette.prop(scene, 'fillpalette6', text = '')
                    row_fpalette.prop(scene, 'fillpalette7', text = '')
                    row_fpalette.prop(scene, 'fillpalette8', text = '')
                    row_color = box_fill.row(align = True)
                    row_color.prop(scene, 'fillcolor')
                    row_noise = box_fill.row(align = True)
                    row_noise.prop(scene, 'fillnoise', slider = True)
                    col_color = box_fill.column(align = True)
                    col_color.prop(scene, 'fillmono', text = 'Monochromatic')
                    if mode == 'OBJECT':
                        col_color.prop(scene, 'fillalpha')
                    col_color.operator('sxtools.applycolor', text = 'Apply')

                # Gradient Tool ---------------------------------------------------
                box = layout.box()
                row4 = box.row()
                row4.prop(scene, "expandramp",
                    icon="TRIA_DOWN" if scene.expandramp else "TRIA_RIGHT",
                    icon_only=True, emboss=False)

                if layer.layerType == 'COLOR':
                    row4.label(text = 'Gradient Tool')
                else:
                    row4.label(text = 'Gradient Tool (Grayscale')
                if scene.expandramp:
                    layout.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], "color_ramp", expand=True)
                    col_ramp = self.layout.column(align = True)
                    col_ramp.prop(scene, 'rampmode', text = 'Mode')
                    col_ramp.prop(scene, 'rampbbox', text = 'Use Global Bbox')
                    if mode == 'OBJECT':
                        col_ramp.prop(scene, 'rampalpha')
                    if scene.rampmode == 'OCC':
                        col_ramp.prop(scene, 'occlusionrays', slider = True, text = 'Ray Count')
                        col_ramp.prop(scene, 'occlusionblend', slider = True, text = 'Local/Global Mix')

                    col_ramp.operator('sxtools.applyramp', text = 'Apply')

                # Master Palette ---------------------------------------------------
                box_palette = layout.box()
                row_palette = box_palette.row()
                row_palette.prop(scene, "expandpalette",
                    icon="TRIA_DOWN" if scene.expandpalette else "TRIA_RIGHT",
                    icon_only=True, emboss=False)
                row_palette.label(text = 'Master Palettes')

                palettes = context.scene.sxpalettes

                if scene.expandpalette:
                    category = ''
                    for name in palettes.keys():
                        palette = palettes[name]
                        if palette.category != category:
                            category = palette.category
                            row_category = box_palette.row(align = True)
                            row_category.label(text = 'CATEGORY: ' + category)
                            row_category.separator()
                        row_mpalette = box_palette.row(align = True)
                        row_mpalette.label(text = name)
                        for i in range(5):
                            row_mpalette.prop(palette, 'color'+str(i), text = '')
                        mp_button = row_mpalette.operator('sxtools.applypalette', text = 'Apply')
                        mp_button.label = palette.name[:]

                    row_mnoise = box_palette.row(align = True)
                    row_mnoise.prop(scene, 'palettenoise', slider = True)
                    col_mcolor = box_palette.column(align = True)
                    col_mcolor.prop(scene, 'palettemono', text = 'Monochromatic')

                # PBR Materials ---------------------------------------------------
                box_materials = layout.box()
                row_materials = box_materials.row()
                row_materials.prop(scene, "expandmaterials",
                    icon="TRIA_DOWN" if scene.expandmaterials else "TRIA_RIGHT",
                    icon_only=True, emboss=False)
                row_materials.label(text = 'PBR Materials')

                materials = context.scene.sxmaterials

                if scene.expandmaterials:
                    category = ''
                    for name in materials.keys():
                        material = materials[name]
                        if material.category != category:
                            category = material.category
                            row_category = box_materials.row(align = True)
                            row_category.label(text = 'CATEGORY: ' + category)
                            row_category.separator()
                        row_mat = box_materials.row(align = True)
                        row_mat.label(text = name)
                        for i in range(3):
                            row_mat.prop(material, 'color'+str(i), text = '')
                        mat_button = row_mat.operator('sxtools.applymaterial', text = 'Apply')
                        mat_button.label = material.name[:]

                    row_pbrnoise = box_materials.row(align = True)
                    row_pbrnoise.prop(scene, 'materialnoise', slider = True)
                    col_matcolor = box_materials.column(align = True)
                    col_matcolor.prop(scene, 'materialmono', text = 'Monochromatic')
                    if mode == 'OBJECT':
                        col_matcolor.prop(scene, 'materialalpha')

                # Crease Sets ---------------------------------------------------
                box_crease = layout.box()
                row_crease = box_crease.row()
                row_crease.prop(scene, 'expandcrease',
                    icon="TRIA_DOWN" if scene.expandcrease else "TRIA_RIGHT",
                    icon_only=True, emboss=False)

                row_crease.label(text='Crease Edges')
                if scene.expandcrease:
                    row_sets = box_crease.row(align = True)
                    row_sets.operator('sxtools.crease1', text = '25%')
                    row_sets.operator('sxtools.crease2', text = '50%')
                    row_sets.operator('sxtools.crease3', text = '75%')
                    row_sets.operator('sxtools.crease4', text = '100%')
                    col_sets = box_crease.column(align = True)
                    col_sets.prop(scene, 'hardcrease', text = 'Sharp on 100%')
                    col_sets.operator('sxtools.crease0', text = 'Uncrease')

                # Channel Copy ---------------------------------------------------
                box_chcp = layout.box()
                row_chcpbox = box_chcp.row()
                row_chcpbox.prop(scene, "expandchcopy",
                    icon="TRIA_DOWN" if scene.expandchcopy else "TRIA_RIGHT",
                    icon_only=True, emboss=False)

                row_chcpbox.label(text='Channel Copy')
                if scene.expandchcopy:
                    col_l2m = box_chcp.column(align = True)
                    col_l2m.prop(scene, 'sourcemap', text = 'From')
                    col_l2m.prop(scene, 'materialmap', text = 'To')
                    col_l2m.operator('sxtools.layertouv', text = 'Apply')

        else:
            layout = self.layout               
            col = self.layout.column(align = True)
            col.prop(bpy.context.scene.sxtools, 'libraryfolder', text = 'Set Library Data Folder')
            col.operator('sxtools.loadlibraries', text = 'Load Palettes and Materials')
            col.separator()
            col.label(text = 'Select a mesh to continue')


class SXTOOLS_OT_scenesetup(bpy.types.Operator):
    bl_idname = "sxtools.scenesetup"
    bl_label = "Set Up Object"
    bl_options = {"UNDO"}
    bl_description = 'Creates necessary materials and vertex color layers'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        setup.setupListItems()
        setup.setupLayers(objs)
        setup.setupGeometry(objs)
        return {"FINISHED"}


class SXTOOLS_OT_loadlibraries(bpy.types.Operator):
    bl_idname = "sxtools.loadlibraries"
    bl_label = "Load Libraries"
    bl_description = 'Load Palettes and Materials'

    def invoke(self, context, event):
        files.loadFile('palettes')
        files.loadFile('materials')
        return {"FINISHED"}


class SXTOOLS_OT_applycolor(bpy.types.Operator):
    bl_idname = "sxtools.applycolor"
    bl_label = "Apply Color"
    bl_options = {"UNDO"}
    bl_description = 'Applies fill color to selection'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        color = context.scene.sxtools.fillcolor
        overwrite = context.scene.sxtools.fillalpha
        if objs[0].mode == 'EDIT':
            overwrite = True
        noise = context.scene.sxtools.fillnoise
        mono = context.scene.sxtools.fillmono
        tools.applyColor(objs, layer, color, overwrite, noise, mono)
        tools.updateRecentColors(color)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_applyramp(bpy.types.Operator):
    bl_idname = "sxtools.applyramp"
    bl_label = "Apply Gradient"
    bl_options = {"UNDO"}
    bl_description = 'Applies gradient to selection bounding volume across selected axis'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        rampmode = context.scene.sxtools.rampmode
        mergebbx = context.scene.sxtools.rampbbox
        overwrite = context.scene.sxtools.rampalpha
        if objs[0].mode == 'EDIT':
            overwrite = True
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_mergeup(bpy.types.Operator):
    bl_idname = "sxtools.mergeup"
    bl_label = "Merge Up"
    bl_options = {"UNDO"}
    bl_description = 'Merge the selected layer with the one above'

    @classmethod
    def poll(cls, context):
        objs = context.view_layer.objects.selected
        listIdx = context.scene.sxtools.listIndex
        return listIdx != 0

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        mergemode = 'UP'
        tools.mergeLayersManager(objs, layer, mergemode)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_mergedown(bpy.types.Operator):
    bl_idname = "sxtools.mergedown"
    bl_label = "Merge Down"
    bl_options = {"UNDO"}
    bl_description = 'Merge the selected layer with the one below'

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.selected[0]
        layers = context.scene.sxlistitems.keys()
        listIdx = context.scene.sxtools.listIndex
        return listIdx != (len(layers) - 1)

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        mergemode = 'DOWN'
        tools.mergeLayersManager(objs, layer, mergemode)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_copylayer(bpy.types.Operator):
    bl_idname = "sxtools.copylayer"
    bl_label = "Copy Layer"
    bl_options = {"UNDO"}
    bl_description = 'Copy selected layer'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        sxglobals.copyLayer = layer
        return {"FINISHED"}


class SXTOOLS_OT_pastelayer(bpy.types.Operator):
    bl_idname = "sxtools.pastelayer"
    bl_label = "Paste Layer"
    bl_options = {"UNDO"}
    bl_description = 'Shift-click to swap with copied layer'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        sourceLayer = sxglobals.copyLayer
        targetLayer = utils.findLayerFromIndex(objs[0], idx)

        if event.shift:
            mode = True
        else:
            mode = False

        layers.pasteLayer(objs, sourceLayer, targetLayer, mode)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_clearlayers(bpy.types.Operator):
    bl_idname = "sxtools.clear"
    bl_label = "Clear Layer"
    bl_options = {"UNDO"}
    bl_description = 'Shift-click to clear all layers on object or components'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if event.shift:
            layer = None
        else:
            listIdx = context.scene.sxtools.listIndex
            idx = context.scene.sxlistitems[listIdx].index
            layer = utils.findLayerFromIndex(objs[0], idx)
            #print('clearlayer: ', layer)
            # TODO: May return UVMAP?!

        layers.clearLayers(objs, layer)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_selmask(bpy.types.Operator):
    bl_idname = "sxtools.selmask"
    bl_label = "Select Layer Mask"
    bl_options = {"UNDO"}
    bl_description = 'Shift-click to invert selection'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if event.shift:
            inverse = True
        else:
            inverse = False

        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)

        tools.selectMask(objs, layer, inverse)
        return {"FINISHED"}


class SXTOOLS_OT_crease0(bpy.types.Operator):
    bl_idname = "sxtools.crease0"
    bl_label = "Crease0"
    bl_options = {"UNDO"}
    bl_description = 'Uncrease selection'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        group = 'CreaseSet0'
        hard = False
        if event.shift:
            tools.selectCrease(objs, group)
        else:
            tools.assignCrease(objs, group, hard)
        return {"FINISHED"}


class SXTOOLS_OT_crease1(bpy.types.Operator):
    bl_idname = "sxtools.crease1"
    bl_label = "Crease1"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set1, shift-click to select creased edges'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        group = 'CreaseSet1'
        hard = False
        if event.shift:
            tools.selectCrease(objs, group)
        else:
            tools.assignCrease(objs, group, hard)
        return {"FINISHED"}


class SXTOOLS_OT_crease2(bpy.types.Operator):
    bl_idname = "sxtools.crease2"
    bl_label = "Crease2"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set2, shift-click to select creased edges'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        group = 'CreaseSet2'
        hard = False
        if event.shift:
            tools.selectCrease(objs, group)
        else:
            tools.assignCrease(objs, group, hard)
        return {"FINISHED"}


class SXTOOLS_OT_crease3(bpy.types.Operator):
    bl_idname = "sxtools.crease3"
    bl_label = "Crease3"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set3, shift-click to select creased edges'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        group = 'CreaseSet3'
        hard = False
        if event.shift:
            tools.selectCrease(objs, group)
        else:
            tools.assignCrease(objs, group, hard)
        return {"FINISHED"}


class SXTOOLS_OT_crease4(bpy.types.Operator):
    bl_idname = "sxtools.crease4"
    bl_label = "Crease4"
    bl_options = {"UNDO"}
    bl_description = 'Add selection to set4, shift-click to select creased edges'

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        group = 'CreaseSet4'
        hard = context.scene.sxtools.hardcrease
        if event.shift:
            tools.selectCrease(objs, group)
        else:
            tools.assignCrease(objs, group, hard)
        return {"FINISHED"}


class SXTOOLS_OT_applypalette(bpy.types.Operator):
    bl_idname = 'sxtools.applypalette'
    bl_label = 'Apply Palette'
    bl_options = {"UNDO"}
    bl_description = 'Applies selected palette to selection'

    label: bpy.props.StringProperty()

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        palette = self.label
        noise = context.scene.sxtools.palettenoise
        mono = context.scene.sxtools.palettemono

        tools.applyPalette(objs, palette, noise, mono)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_applymaterial(bpy.types.Operator):
    bl_idname = 'sxtools.applymaterial'
    bl_label = 'Apply PBR Material'
    bl_options = {"UNDO"}
    bl_description = 'Applies selected material to selection'

    label: bpy.props.StringProperty()

    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        material = self.label
        listIdx = context.scene.sxtools.listIndex
        idx = context.scene.sxlistitems[listIdx].index
        layer = utils.findLayerFromIndex(objs[0], idx)
        overwrite = context.scene.sxtools.materialalpha
        if objs[0].mode == 'EDIT':
            overwrite = True
        noise = context.scene.sxtools.materialnoise
        mono = context.scene.sxtools.materialmono

        tools.applyMaterial(objs, layer, material, overwrite, noise, mono)
        refreshActives(self, context)
        return {"FINISHED"}


class SXTOOLS_OT_layertouv(bpy.types.Operator):
    bl_idname = "sxtools.layertouv"
    bl_label = "Layer to Material"
    bl_options = {"UNDO"}
    bl_description = 'Copy layer to material UV channels'

    def invoke(self, context, event):
        refDict = {
            'LAYER1': 'layer1',
            'LAYER2': 'layer2',
            'LAYER3': 'layer3',
            'LAYER4': 'layer4',
            'LAYER5': 'layer5',
            'LAYER6': 'layer6',
            'LAYER7': 'layer7',
            'UVMAP0': 'uvSet0',
            'UVMAP1': 'uvSet1',
            'UVMAP2': 'uvSet2',
            'UVMAP3': 'uvSet3',
            'UVMAP4': 'uvSet4',
            'UVMAP5': 'uvSet5',
            'UVMAP6': 'uvSet6',
            'UVMAP7': 'uvSet7',
            'OCC': 'occlusion',
            'TRNS': 'transmission',
            'EMISS': 'emission',
            'MET': 'metallic',
            'SMTH': 'smoothness',
            'GRD1': 'gradient1',
            'GRD2': 'gradient2',
            'OVR': 'overlay' }

        objs = selectionValidator(self, context)
        sourcemap = context.scene.sxtools.sourcemap
        materialmap = context.scene.sxtools.materialmap
        tools.layerToUV(objs, objs[0].sxlayers[refDict[sourcemap]], objs[0].sxlayers[refDict[materialmap]])
        return {"FINISHED"}


# ------------------------------------------------------------------------
#    Registration and initialization
# ------------------------------------------------------------------------
sxglobals = SXTOOLS_sxglobals()
files = SXTOOLS_files()
utils = SXTOOLS_utils()
layers = SXTOOLS_layers()
setup = SXTOOLS_setup()
tools = SXTOOLS_tools()

classes = (
    SXTOOLS_objectprops,
    SXTOOLS_sceneprops,
    SXTOOLS_masterpalette,
    SXTOOLS_material,
    SXTOOLS_layer,
    SXTOOLS_listitem,
    SXTOOLS_OT_scenesetup,
    SXTOOLS_OT_loadlibraries,
    SXTOOLS_OT_applycolor,
    SXTOOLS_OT_applyramp,
    SXTOOLS_OT_crease0,
    SXTOOLS_OT_crease1,
    SXTOOLS_OT_crease2,
    SXTOOLS_OT_crease3,
    SXTOOLS_OT_crease4,
    SXTOOLS_OT_applypalette,
    SXTOOLS_OT_applymaterial,
    SXTOOLS_OT_layertouv,
    SXTOOLS_OT_copylayer,
    SXTOOLS_OT_selmask,
    SXTOOLS_OT_clearlayers,
    SXTOOLS_OT_mergeup,
    SXTOOLS_OT_mergedown,
    SXTOOLS_OT_pastelayer,
    SXTOOLS_PT_panel)

def init():
    pass

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Object.sxtools = bpy.props.PointerProperty(type = SXTOOLS_objectprops)
    bpy.types.Object.sxlayers = bpy.props.CollectionProperty(type = SXTOOLS_layer)
    bpy.types.Scene.sxtools = bpy.props.PointerProperty(type = SXTOOLS_sceneprops)
    bpy.types.Scene.sxlistitems = bpy.props.CollectionProperty(type = SXTOOLS_listitem)
    bpy.types.Scene.sxpalettes = bpy.props.CollectionProperty(type = SXTOOLS_masterpalette)
    bpy.types.Scene.sxmaterials = bpy.props.CollectionProperty(type = SXTOOLS_material)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Object.sxtools
    del bpy.types.Object.sxlayers
    del bpy.types.Scene.sxlistitems
    del bpy.types.Scene.sxtools
    del bpy.types.Scene.sxpalettes
    del bpy.types.Scene.sxmaterials
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
# - Ramp fill color presets
# - Master palette library save/manage
# - PBR material library save/manage
# - Skinning support?
# - Export settings:
#   - Submesh support
#   - Static vs. paletted vertex colors
#   - Choose export path
#   - Export fbx settings
# - Tool settings:
#   - Load/save prefs file
#   - Channel enable/export prefs
#   - Export grid spacing
#   - Layer renaming
#   - _paletted suffix
#TODO:
# - Luminance remap fails with UV layers
# - AO behaves oddly in origin
# - Crease tool select edges stops working after object/edit mode change
#   - Store crease weigths in vertex groups?
# - UI Palette layout for color swatches
# - Set proper shading mode, layer1 selected, after scene setup
# - Create custom layerview:
#   - Custom hide/show icons to layer view items
# - Assign fill color from brush color if in vertex paint mode
#   - color[0] = bpy.data.brushes["Draw"].color[0]
# - Automate modifier creation / Add visibility toggle button
#   - C.active_object.modifiers.new(type = 'EDGE_SPLIT', name = 'SX EdgeSplit')
#   - bpy.context.object.modifiers["EdgeSplit"].use_edge_angle = False
#   - C.active_object.modifiers.new(type = 'SUBSURF', name = 'SX Subdivision')
#   - And toggle modifiers in viewport:
#   - bpy.context.object.modifiers["Subdivision"].show_viewport = False

'''
Selection change:

    @classmethod
    def poll(cls, context):
        print(sxglobals.activeObject, context.active_object, (context.active_object != sxglobals.activeObject))
        return context.active_object != sxglobals.activeObject

    def execute(self, context):
        sxglobals.activeObject = context.active_object
        draw(self, context)
        return {'FINISHED'}

'''
