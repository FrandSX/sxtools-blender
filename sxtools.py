bl_info = {
    'name': 'SX Tools',
    'author': 'Jani Kahrama / Secret Exit Ltd.',
    'version': (2, 39, 22),
    'blender': (2, 80, 0),
    'location': 'View3D',
    'description': 'Multi-layer vertex coloring tool',
    'category': 'Development',
}

import bpy
import time
import random
import math
import bmesh
import json
import pathlib
import statistics
from bpy.app.handlers import persistent
from collections import defaultdict
from mathutils import Vector


# ------------------------------------------------------------------------
#    Globals
# ------------------------------------------------------------------------
class SXTOOLS_sxglobals(object):
    def __init__(self):
        self.librariesLoaded = False
        self.refreshInProgress = False
        self.brightnessUpdate = False
        self.modalStatus = False
        self.composite = False
        self.copyLayer = None
        self.listItems = []
        self.listIndices = {}
        self.prevMode = 'FULL'

        self.rampDict = {}
        self.categoryDict = {}
        self.presetLookup = {}
        self.paletteDict = {}
        self.masterPaletteArray = []
        self.materialArray = []
        self.exportObjects = []
        self.sourceObjects = []

        # name, enabled, index, layerType (COLOR/UV/UV4),
        # defaultColor, defaultValue,
        # visibility, alpha, blendMode, vertexColorLayer,
        # uvLayer0, uvChannel0, uvLayer1, uvChannel1,
        # uvLayer2, uvChannel2, uvLayer3, uvChannel3
        self.layerInitArray = [
            ['composite', False, 0, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor0', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer1', False, 1, 'COLOR', [0.5, 0.5, 0.5, 1.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor1', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer2', False, 2, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor2', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer3', False, 3, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor3', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer4', False, 4, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor4', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer5', False, 5, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor5', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer6', False, 6, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor6', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['layer7', False, 7, 'COLOR', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', 'VertexColor7', '', 'U', '', 'U', '', 'U', '', 'U'],
            ['occlusion', False, 11, 'UV', [0.0, 0.0, 0.0, 0.0], 1.0, True, 1.0, 'ALPHA', '', 'UVSet1', 'V', '', 'U', '', 'U', '', 'U'],
            ['transmission', False, 14, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet2', 'U', '', 'U', '', 'U', '', 'U'],
            ['emission', False, 15, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet2', 'V', '', 'U', '', 'U', '', 'U'],
            ['metallic', False, 12, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet3', 'U', '', 'U', '', 'U', '', 'U'],
            ['smoothness', False, 13, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet3', 'V', '', 'U', '', 'U', '', 'U'],
            ['gradient1', False, 8, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet4', 'U', '', 'U', '', 'U', '', 'U'],
            ['gradient2', False, 9, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet4', 'V', '', 'U', '', 'U', '', 'U'],
            ['overlay', False, 10, 'UV4', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet5', 'U', 'UVSet5', 'V', 'UVSet6', 'U', 'UVSet6', 'V'],
            ['texture', False, 16, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet0', 'U', 'UVSet0', 'V', '', 'U', '', 'U'],
            ['masks', False, 17, 'UV', [0.0, 0.0, 0.0, 0.0], 0.0, True, 1.0, 'ALPHA', '', 'UVSet1', 'U', '', 'U', '', 'U', '', 'U']]
 
        # Brush tools may leave low alpha values that break
        # palettemasks, alphaTolerance can be used to fix this
        self.alphaTolerance = 1.0


    def __del__(self):
        print('SX Tools: Exiting sxglobals')


# ------------------------------------------------------------------------
#    File IO
# ------------------------------------------------------------------------
class SXTOOLS_files(object):
    def __init__(self):
        return None


    def __del__(self):
        print('SX Tools: Exiting files')


    # Loads palettes.json and materials.json
    def loadFile(self, mode):
        prefs = bpy.context.preferences
        directory = prefs.addons['sxtools'].preferences.libraryfolder
        filePath = directory + mode + '.json'

        if len(directory) > 0:
            try:
                with open(filePath, 'r') as input:
                    tempDict = {}
                    tempDict = json.load(input)
                    if mode == 'palettes':
                        del sxglobals.masterPaletteArray[:]
                        while len(bpy.context.scene.sxpalettes.keys()) > 0:
                            bpy.context.scene.sxpalettes.remove(0)
                        sxglobals.masterPaletteArray = tempDict['Palettes']
                    elif mode == 'materials':
                        del sxglobals.materialArray[:]
                        while len(bpy.context.scene.sxmaterials.keys()) > 0:
                            bpy.context.scene.sxmaterials.remove(0)
                        sxglobals.materialArray = tempDict['Materials']
                    elif mode == 'gradients':
                        sxglobals.rampDict.clear()
                        sxglobals.rampDict = tempDict
                    elif mode == 'categories':
                        sxglobals.categoryDict.clear()
                        sxglobals.categoryDict = tempDict

                    input.close()
                print('SX Tools: ' + mode + ' loaded from ' + filePath)
            except ValueError:
                print('SX Tools Error: Invalid ' + mode + ' file.')
                prefs.addons['sxtools'].preferences.libraryfolder = ''
                return False
            except IOError:
                print('SX Tools Error: ' + mode + ' file not found!')
                return False
        else:
            print('SX Tools: No ' + mode + ' file found')
            return False

        if mode == 'palettes':
            self.loadPalettes()
            return True
        elif mode == 'materials':
            self.loadMaterials()
            return True
        else:
            return True


    def saveFile(self, mode):
        prefs = bpy.context.preferences
        directory = prefs.addons['sxtools'].preferences.libraryfolder
        filePath = directory + mode + '.json'
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
                elif mode == 'gradients':
                    tempDict = {}
                    tempDict = sxglobals.rampDict
                    json.dump(tempDict, output, indent=4)
                output.close()
            messageBox(mode + ' saved')
            # print('SX Tools: ' + mode + ' saved')
        else:
            messageBox(mode + ' file location not set!', 'SX Tools Error', 'ERROR')
            # print('SX Tools Warning: ' + mode + ' file location not set!')


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


    def saveRamp(self, rampName):
        tempDict = {}
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'].color_ramp

        tempDict['mode'] = ramp.color_mode
        tempDict['interpolation'] = ramp.interpolation
        tempDict['hue_interpolation'] = ramp.hue_interpolation

        tempColorArray = []
        for i, element in enumerate(ramp.elements):
            tempElement = [None, [None, None, None, None], None]
            tempElement[0] = element.position
            tempElement[1] = [element.color[0], element.color[1], element.color[2], element.color[3]]
            tempColorArray.append(tempElement)

        tempDict['elements'] = tempColorArray
        sxglobals.rampDict[rampName] = tempDict

        self.saveFile('gradients')


    # In paletted export mode, gradients and overlays are
    # not composited to VertexColor0 as that will be
    # done by the shader on the game engine side 
    def exportFiles(self, groups):
        groupNames = []
        for group in groups:
            bpy.context.view_layer.objects.active = group
            bpy.ops.object.select_all(action='DESELECT')
            group.select_set(True)
            org_loc = group.location.copy()
            group.location = (0,0,0)
            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')

            selArray = bpy.context.view_layer.objects.selected
            for sel in selArray:
                if 'staticVertexColors' not in sel.keys():
                    sel['staticVertexColors'] = True

                compLayers = utils.findCompLayers(sel, sel['staticVertexColors'])
                layer0 = utils.findLayerFromIndex(sel, 0)
                layer1 = utils.findLayerFromIndex(sel, 1)
                layers.blendLayers([sel, ], compLayers, layer1, layer0)

            path = bpy.context.scene.sxtools.exportfolder + selArray[0].sxtools.category.lower()
            pathlib.Path(path).mkdir(exist_ok=True) 

            if '/' in bpy.context.scene.sxtools.exportfolder:
                slash = '/'
            elif '\\' in bpy.context.scene.sxtools.exportfolder:
                slash = '\\'

            exportPath = path + slash + group.name + '.' + 'fbx'

            bpy.ops.export_scene.fbx(
                filepath=exportPath,
                apply_scale_options='FBX_SCALE_NONE',
                use_selection=True,
                apply_unit_scale=True,
                bake_space_transform=True,
                use_mesh_modifiers=True,
                axis_up='Y',
                axis_forward='-Z',
                use_active_collection=False,
                add_leaf_bones=False,
                object_types={'ARMATURE', 'EMPTY', 'MESH'},
                use_custom_props=True)

            groupNames.append(group.name)
            group.location = org_loc

        messageBox('Exported ' + str(', ').join(groupNames))


# ------------------------------------------------------------------------
#    Layer Data Find Functions
# ------------------------------------------------------------------------
class SXTOOLS_utils(object):
    def __init__(self):
        return None

    # Finds groups to be exported,
    # only EMPTY objects with no parents
    def findGroups(self, objs):
        groups = list()
        for obj in objs:
            if (obj.type == 'EMPTY') and (obj.parent == None):
                groups.append(obj)

            parent = obj.parent
            if (parent is not None) and (parent.type == 'EMPTY') and (parent.parent == None):
                groups.append(obj.parent)

        return set(groups)


    def findChildren(self, group, objs):
        children = list()
        for obj in objs:
            if obj.parent == group:
                children.append(obj)

        return children


    def findListIndex(self, obj, layer):
        index = obj.sxlayers[layer.name].index

        return sxglobals.listIndices[index]


    def findColorLayers(self, obj):
        sxLayerArray = []
        sxLayerArray.append(obj.sxlayers['composite'])
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'COLOR') and (sxLayer.enabled):
                sxLayerArray.append(sxLayer)
        sxLayerArray.sort(key=lambda x: x.index)

        return sxLayerArray


    def findDefaultValues(self, obj, mode):
        sxLayerArray = []
        valueArray = []
        valueDict = {}
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'UV') or (sxLayer.layerType == 'UV4'):
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


    def findCompLayers(self, obj, staticExport=True):
        compLayers = []
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'COLOR') and (sxLayer.enabled == True) and (sxLayer.index != 1):
                compLayers.append(sxLayer)
        compLayers.sort(key=lambda x: x.index)
        if staticExport:
            if obj.sxlayers['gradient1'].enabled:
                compLayers.append(obj.sxlayers['gradient1'])
            if obj.sxlayers['gradient2'].enabled:
                compLayers.append(obj.sxlayers['gradient2'])
            if obj.sxlayers['overlay'].enabled:
                compLayers.append(obj.sxlayers['overlay'])

        return compLayers


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


    def startModal(self):
        bpy.ops.sxtools.selectionmonitor('INVOKE_DEFAULT')
        sxglobals.modalStatus = True


    def updateInitArray(self):
        scn = bpy.context.scene.sxtools
        layerCount = scn.numlayers
        alphaCount = scn.numalphas
        overlayCount = scn.numoverlays

        for i in range(layerCount):
            j = i + 1
            sxglobals.layerInitArray[j][1] = True
        for i in range(alphaCount):
            j = i + 13
            sxglobals.layerInitArray[j][1] = True
        for i in range(overlayCount):
            j = i + 15
            sxglobals.layerInitArray[j][1] = True

        sxglobals.layerInitArray[8][1] = scn.enableocclusion
        sxglobals.layerInitArray[9][1] = scn.enabletransmission
        sxglobals.layerInitArray[10][1] = scn.enableemission
        sxglobals.layerInitArray[11][1] = scn.enablemetallic
        sxglobals.layerInitArray[12][1] = scn.enablesmoothness


    # Generates layer instances by using the reference values
    # from layerInitArray.
    def setupLayers(self, objs):
        for obj in objs:
            initArray = sorted(sxglobals.layerInitArray, key=lambda tup: tup[2])
            for values in initArray:
                if values[0] in obj.sxlayers.keys():
                    item = obj.sxlayers[values[0]]
                else:
                    item = obj.sxlayers.add()
                    item.name = values[0]
                item.enabled = values[1]
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
        changed = False
        overwrite = bpy.context.scene.sxtools.eraseuvs

        # Build arrays of needed vertex color and UV sets,
        # VertexColor0 needed for compositing if even one
        # color layer is enabled
        # UVSet0 needed in game engine for textures and proper
        # indexing of data
        uvArray = ['UVSet0', ]
        colorArray = utils.findColorLayers(objs[0])
        for layer in objs[0].sxlayers:
            if layer.enabled:
                if layer.uvLayer0 != '':
                    uvArray.append(layer.uvLayer0)
                if layer.uvLayer1 != '':
                    uvArray.append(layer.uvLayer1)
                if layer.uvLayer2 != '':
                    uvArray.append(layer.uvLayer2)
                if layer.uvLayer3 != '':
                    uvArray.append(layer.uvLayer3)
        nameSet = set(uvArray)
        uvSets = sorted(nameSet)

        for obj in objs:
            mesh = obj.data
            uvs = uvSets[:]

            # Check if vertex color layers exist,
            # and delete if legacy data is found
            for vertexColor in mesh.vertex_colors.keys():
                if not 'VertexColor' in vertexColor:
                    mesh.vertex_colors.remove(mesh.vertex_colors[vertexColor])

            for sxLayer in colorArray:
                if not sxLayer.vertexColorLayer in mesh.vertex_colors.keys():
                    mesh.vertex_colors.new(name=sxLayer.vertexColorLayer)
                    layers.clearLayers([obj, ], sxLayer)
                    changed = True

            if len(uvs) > 0:
                if overwrite:
                    for i in range(len(mesh.uv_layers.keys())):
                        mesh.uv_layers.remove(mesh.uv_layers[0])
                else:
                    # Delete old UV sets if necessary for material channels
                    slotsNeeded = len(uvs)
                    slotsAvailable = 8 - len(mesh.uv_layers.keys())
                    for uvLayer in mesh.uv_layers.keys():
                        if uvLayer in uvs:
                            slotsNeeded -= 1
                            uvs.remove(uvLayer)

                    while slotsNeeded > slotsAvailable:
                        mesh.uv_layers.remove(mesh.uv_layers[0])
                        slotsNeeded -= 1

                clearSets = []
                for uvSet in uvs:
                    mesh.uv_layers.new(name=uvSet)
                    clearSets.append(uvSet)
                    changed = True

                if len(clearSets) > 0:
                    for uvSet in clearSets:
                        for sxLayer in obj.sxlayers:
                            if ((sxLayer.layerType == 'UV') or
                               (sxLayer.layerType == 'UV4')):
                                if ((sxLayer.uvLayer0 == uvSet) or
                                   (sxLayer.uvLayer1 == uvSet) or
                                   (sxLayer.uvLayer2 == uvSet) or
                                   (sxLayer.uvLayer3 == uvSet)):
                                    layers.clearUVs([obj, ], sxLayer)

            # for i in range(5):
            #    if not 'CreaseSet'+str(i) in obj.vertex_groups.keys():
            #        obj.vertex_groups.new(name='CreaseSet'+str(i))

            obj.active_material = bpy.data.materials['SXMaterial']

        if changed:
            bpy.context.scene.sxtools.shadingmode = 'FULL'


    def createSXMaterial(self):
        for values in sxglobals.layerInitArray:
            if values[0] == 'composite':
                compositeUVSet = values[9]
                composite = values[1]
            elif values[0] == 'occlusion':
                occlusionUVSet = values[10]
                occlusion = values[1]
            elif values[0] == 'metallic':
                metallicUVSet = values[10]
                metallic = values[1]
            elif values[0] == 'smoothness':
                smoothnessUVSet = values[10]
                smoothness = values[1]
            elif values[0] == 'transmission':
                transmissionUVSet = values[10]
                transmission = values[1]
            elif values[0] == 'emission':
                emissionUVSet = values[10]
                emission = values[1]
            elif values[0] == 'gradient1':
                gradient1UVSet = values[10]
                gradient1 = values[1]
            elif values[0] == 'gradient2':
                gradient2UVSet = values[10]
                gradient2 = values[1]

        prefs = bpy.context.preferences
        materialsubsurface = prefs.addons['sxtools'].preferences.materialsubsurface
        materialtransmission = prefs.addons['sxtools'].preferences.materialtransmission

        sxmaterial = bpy.data.materials.new(name='SXMaterial')
        sxmaterial.use_nodes = True
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.5
        sxmaterial.node_tree.nodes['Principled BSDF'].location = (600, 200)

        sxmaterial.node_tree.nodes['Material Output'].location = (900, 200)

        # Gradient tool color ramp
        sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')
        sxmaterial.node_tree.nodes['ColorRamp'].location = (-900, 200)

        # Palette colors
        for i in range(5):
            pCol = sxmaterial.node_tree.nodes.new(type="ShaderNodeRGB")
            pCol.name = 'PaletteColor' + str(i)
            sxmaterial.node_tree.nodes[pCol.name].location = (-900, -200*i)

        # Vertex alpha source
        if (2, 81, 0) < bpy.app.version:
            sxmaterial.node_tree.nodes.new(type='ShaderNodeVertexColor')
            sxmaterial.node_tree.nodes['Vertex Color'].layer_name = 'VertexColor0'
            sxmaterial.node_tree.nodes['Vertex Color'].location = (-600, 0)

        # Vertex color source
        sxmaterial.node_tree.nodes.new(type='ShaderNodeAttribute')
        sxmaterial.node_tree.nodes['Attribute'].attribute_name = compositeUVSet
        sxmaterial.node_tree.nodes['Attribute'].location = (-600, 200)

        sxmaterial.node_tree.nodes.new(type='ShaderNodeMixRGB')
        sxmaterial.node_tree.nodes['Mix'].inputs[0].default_value = 1
        sxmaterial.node_tree.nodes['Mix'].inputs[2].default_value = [1.0, 1.0, 1.0, 1.0]
        sxmaterial.node_tree.nodes['Mix'].blend_type = 'MULTIPLY'
        sxmaterial.node_tree.nodes['Mix'].location = (300, 200)

        # Occlusion source
        if occlusion:
            occ = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            occ.name = 'OcclusionUV'
            sxmaterial.node_tree.nodes['OcclusionUV'].uv_map = occlusionUVSet
            sxmaterial.node_tree.nodes['OcclusionUV'].location = (-600, 0)

            occSep = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            occSep.name = 'OcclusionXYZ'
            sxmaterial.node_tree.nodes['OcclusionXYZ'].location = (-300, 0)

        # Metallic and roughness source
        if metallic or smoothness:
            met = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            met.name = 'MetallicUV'
            sxmaterial.node_tree.nodes['MetallicUV'].uv_map = metallicUVSet
            sxmaterial.node_tree.nodes['MetallicUV'].location = (-600, -200)

            metSep = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            metSep.name = 'MetallicXYZ'
            sxmaterial.node_tree.nodes['MetallicXYZ'].location = (-300, -200)

        if smoothness:
            sxmaterial.node_tree.nodes.new(type='ShaderNodeInvert')
            sxmaterial.node_tree.nodes['Invert'].location = (300, -200)

        # Emission and transmission source
        if emission or transmission:
            ems = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            ems.name = 'EmissionUV'
            sxmaterial.node_tree.nodes['EmissionUV'].uv_map = transmissionUVSet
            sxmaterial.node_tree.nodes['EmissionUV'].location = (-600, -400)

            emsSep = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            emsSep.name = 'EmissionXYZ'
            sxmaterial.node_tree.nodes['EmissionXYZ'].location = (-300, -400)

        if emission:
            sxmaterial.node_tree.nodes.new(type='ShaderNodeMixRGB')
            sxmaterial.node_tree.nodes['Mix.001'].inputs[0].default_value = 1
            sxmaterial.node_tree.nodes['Mix.001'].blend_type = 'MULTIPLY'
            sxmaterial.node_tree.nodes['Mix.001'].location = (300, -400)

            sxmaterial.node_tree.nodes.new(type='ShaderNodeMath')
            sxmaterial.node_tree.nodes['Math'].operation = 'MULTIPLY'
            sxmaterial.node_tree.nodes['Math'].inputs[0].default_value = 10
            sxmaterial.node_tree.nodes['Math'].location = (0, -400)

        # Gradient1 and gradient2 source
        if gradient1 or gradient2:
            grd = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            grd.name = 'GradientUV'
            sxmaterial.node_tree.nodes['GradientUV'].uv_map = gradient1UVSet
            sxmaterial.node_tree.nodes['GradientUV'].location = (-600, -600)

            grdSep = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            grdSep.name = 'GradientXYZ'
            sxmaterial.node_tree.nodes['GradientXYZ'].location = (-300, -600)

        # Node connections
        # Vertex alpha to shader alpha
        if (2, 81, 0) < bpy.app.version:
            output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Alpha']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Alpha']
            sxmaterial.node_tree.links.new(input, output)

        # Vertex color to mixer
        output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Mix'].inputs['Color1']
        sxmaterial.node_tree.links.new(input, output)

        if occlusion:
            # Split occlusion from UV1
            output = sxmaterial.node_tree.nodes['OcclusionUV'].outputs['UV']
            input = sxmaterial.node_tree.nodes['OcclusionXYZ'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

            # Occlusion to mixer
            output = sxmaterial.node_tree.nodes['OcclusionXYZ'].outputs['Y']
            input = sxmaterial.node_tree.nodes['Mix'].inputs['Color2']
            sxmaterial.node_tree.links.new(input, output)

        # Mixer out to base color
        output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color']
        sxmaterial.node_tree.links.new(input, output)

        if metallic or smoothness:
            # Split metallic and smoothness
            output = sxmaterial.node_tree.nodes['MetallicUV'].outputs['UV']
            input = sxmaterial.node_tree.nodes['MetallicXYZ'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

        if metallic:
            # X to metallic
            output = sxmaterial.node_tree.nodes['MetallicXYZ'].outputs['X']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Metallic']
            sxmaterial.node_tree.links.new(input, output)

        if smoothness:
            # Invert smoothness to roughness (inverse used by Unity)
            output = sxmaterial.node_tree.nodes['MetallicXYZ'].outputs['Y']
            input = sxmaterial.node_tree.nodes['Invert'].inputs['Color']
            sxmaterial.node_tree.links.new(input, output)

            # Y to roughness
            output = sxmaterial.node_tree.nodes['Invert'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Roughness']
            sxmaterial.node_tree.links.new(input, output)

        if transmission or emission:
            # Split transmission and emission
            output = sxmaterial.node_tree.nodes['EmissionUV'].outputs['UV']
            input = sxmaterial.node_tree.nodes['EmissionXYZ'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

        if materialtransmission:
            # X to transmission
            output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['X']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Transmission']
            sxmaterial.node_tree.links.new(input, output)

        if materialsubsurface:
            # X to subsurface
            output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['X']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Subsurface']
            sxmaterial.node_tree.links.new(input, output)

        if emission:
            # Y to emission multiplier
            output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['Y']
            input = sxmaterial.node_tree.nodes['Math'].inputs[1]
            sxmaterial.node_tree.links.new(input, output)

            # Mix occlusion/base mix with emission
            output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color1']
            sxmaterial.node_tree.links.new(input, output)
            output = sxmaterial.node_tree.nodes['Math'].outputs['Value']
            input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color2']
            sxmaterial.node_tree.links.new(input, output)

            # Mix to emission
            output = sxmaterial.node_tree.nodes['Mix.001'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
            sxmaterial.node_tree.links.new(input, output)

        if gradient1 or gradient2:
            # Split gradients
            output = sxmaterial.node_tree.nodes['GradientUV'].outputs['UV']
            input = sxmaterial.node_tree.nodes['GradientXYZ'].inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)


    def resetScene(self):
        sxglobals.refreshInProgress = True
        objs = bpy.context.scene.objects
        scene = bpy.context.scene.sxtools

        for obj in objs:
            removeColList = []
            removeUVList = []
            if obj.type == 'MESH':
                for vertexColor in obj.data.vertex_colors:
                    if 'VertexColor' in vertexColor.name:
                        removeColList.append(vertexColor.name)
                for uvLayer in obj.data.uv_layers:
                    if 'UVSet' in uvLayer.name:
                        removeUVList.append(uvLayer.name)

            sxlayers = len(obj.sxlayers.keys())
            for i in range(sxlayers):
                obj.sxlayers.remove(0)

            obj.sxtools.selectedlayer = 1

            for vertexColor in removeColList:
                obj.data.vertex_colors.remove(obj.data.vertex_colors[vertexColor])
            for uvLayer in removeUVList:
                obj.data.uv_layers.remove(obj.data.uv_layers[uvLayer])

        bpy.data.materials.remove(bpy.data.materials['SXMaterial'])

        sxglobals.copyLayer = None
        sxglobals.listItems = []
        sxglobals.listIndices = {}
        sxglobals.prevMode = 'FULL'
        sxglobals.composite = False
        sxglobals.paletteDict = {}
        sxglobals.masterPaletteArray = []
        sxglobals.materialArray = []
        for value in sxglobals.layerInitArray:
            value[1] = False

        scene.numlayers = 7
        scene.numalphas = 2
        scene.numoverlays = 1
        scene.enableocclusion = True
        scene.enablemetallic = True
        scene.enablesmoothness = True
        scene.enabletransmission = True
        scene.enableemission = True
        scene.eraseuvs = True

        sxglobals.refreshInProgress = False


    def __del__(self):
        print('SX Tools: Exiting setup')


# ------------------------------------------------------------------------
#    Layer Functions
# ------------------------------------------------------------------------
class SXTOOLS_layers(object):
    def __init__(self):
        return None


    def clearLayers(self, objs, targetLayer=None):
        sxLayers = utils.findColorLayers(objs[0])

        if targetLayer is None:
            print('SX Tools: Clearing all layers')
            for obj in objs:
                for sxLayer in sxLayers:
                    color = sxLayer.defaultColor
                    tools.applyColor([obj, ], sxLayer, color, True, 0.0)
                    setattr(obj.sxlayers[sxLayer.index], 'alpha', 1.0)
                    setattr(obj.sxlayers[sxLayer.index], 'visibility', True)
                    setattr(obj.sxlayers[sxLayer.index], 'blendMode', 'ALPHA')

            self.clearUVs(objs, None)

        else:
            fillMode = targetLayer.layerType
            if fillMode == 'COLOR':
                for obj in objs:
                    color = targetLayer.defaultColor
                    tools.applyColor([obj, ], targetLayer, color, True, 0.0)
                    setattr(obj.sxlayers[targetLayer.index], 'alpha', 1.0)
                    setattr(obj.sxlayers[targetLayer.index], 'visibility', True)
                    setattr(obj.sxlayers[targetLayer.index], 'blendMode', 'ALPHA')
            elif (fillMode == 'UV') or (fillMode == 'UV4'):
                self.clearUVs(objs, targetLayer)


    def clearUVs(self, objs, targetLayer=None):
        objDicts = tools.selectionHandler(objs)
        sxUVs = utils.findDefaultValues(objs[0], 'Dict')
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        channels = {'U': 0, 'V': 1}

        if targetLayer is not None:
            uvNames = [
                targetLayer.uvLayer0,
                targetLayer.uvLayer1,
                targetLayer.uvLayer2,
                targetLayer.uvLayer3]

            fillChannels = [
                channels[targetLayer.uvChannel0],
                channels[targetLayer.uvChannel1],
                channels[targetLayer.uvChannel2],
                channels[targetLayer.uvChannel3]]

            uvValue = targetLayer.defaultValue

        for obj in objs:
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            mesh = obj.data
            if targetLayer is None:
                for i, key in enumerate(mesh.uv_layers.keys()):
                    uvName = mesh.uv_layers[i].name
                    if 'UVSet' in uvName:
                        for vert_idx, loop_indices in vertLoopDict.items():
                            for loop_idx in loop_indices:
                                mesh.uv_layers[i].data[loop_idx].uv = sxUVs[uvName]
            else:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        for i, uvName in enumerate(uvNames):
                            if uvName != '':
                                mesh.uv_layers[uvName].data[loop_idx].uv[fillChannels[i]] = uvValue

        bpy.ops.object.mode_set(mode=mode)


    def compositeLayers(self, objs):
        if sxglobals.composite:
            # then = time.time()
            compLayers = utils.findCompLayers(objs[0])
            shadingmode = bpy.context.scene.sxtools.shadingmode
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)

            if shadingmode == 'FULL':
                layer0 = utils.findLayerFromIndex(objs[0], 0)
                layer1 = utils.findLayerFromIndex(objs[0], 1)
                self.blendLayers(objs, compLayers, layer1, layer0)
            else:
                self.blendDebug(objs, layer, shadingmode)

            sxglobals.composite = False
            # now = time.time()
            # print('Compositing duration: ', now-then, ' seconds')


    def blendDebug(self, objs, layer, shadingmode):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        fillMode = layer.layerType
        channels = {'U': 0, 'V':1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers
            resultLayer = vertexColors[obj.sxlayers['composite'].vertexColorLayer].data
            for poly in obj.data.polygons:
                for loop_idx in poly.loop_indices:
                    if shadingmode == 'DEBUG':
                        if fillMode == 'COLOR':
                            top = [
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[0],
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[1],
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[2],
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[3]][:]
                            top[0] *= top[3]
                            top[1] *= top[3]
                            top[2] *= top[3]
                            top[3] = 1.0
                        elif fillMode == 'UV4':
                            top = [
                                vertexUVs[layer.uvLayer0].data[loop_idx].uv[channels[layer.uvChannel0]],
                                vertexUVs[layer.uvLayer1].data[loop_idx].uv[channels[layer.uvChannel1]],
                                vertexUVs[layer.uvLayer2].data[loop_idx].uv[channels[layer.uvChannel2]],
                                vertexUVs[layer.uvLayer3].data[loop_idx].uv[channels[layer.uvChannel3]]][:]
                            top[0] *= top[3]
                            top[1] *= top[3]
                            top[2] *= top[3]
                            top[3] = 1.0
                        elif fillMode == 'UV':
                            value = vertexUVs[layer.uvLayer0].data[loop_idx].uv[channels[layer.uvChannel0]]
                            top = [value, value, value, 1.0]
                    elif shadingmode == 'ALPHA':
                        if fillMode == 'COLOR':
                            top = [
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[3],
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[3],
                                vertexColors[layer.vertexColorLayer].data[loop_idx].color[3],
                                1.0][:]
                        elif fillMode == 'UV4':
                            value3 = vertexUVs[layer.uvLayer3].data[loop_idx].uv[channels[layer.uvChannel3]]
                            top = [value3, value3, value3, 1.0]
                        elif fillMode == 'UV':
                            value = vertexUVs[layer.uvLayer0].data[loop_idx].uv[channels[layer.uvChannel0]]
                            top = [value, value, value, 1.0]

                    resultLayer[loop_idx].color = top[:]

        bpy.ops.object.mode_set(mode=mode)


    def blendLayers(self, objs, topLayerArray, baseLayer, resultLayer):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        sxmaterial = bpy.data.materials['SXMaterial'].node_tree
        channels = {'U': 0, 'V': 1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            uvValues = obj.data.uv_layers
            resultColors = vertexColors[resultLayer.vertexColorLayer].data
            baseColors = vertexColors[baseLayer.vertexColorLayer].data
            baseAlpha = getattr(baseLayer, 'alpha')

            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    base = [
                        baseColors[idx].color[0],
                        baseColors[idx].color[1],
                        baseColors[idx].color[2],
                        baseColors[idx].color[3]][:]
                    for layer in topLayerArray:
                        layerIdx = layer.index
                        if not getattr(obj.sxlayers[layerIdx], 'visibility'):
                            continue
                        else:
                            blend = getattr(obj.sxlayers[layerIdx], 'blendMode')
                            alpha = getattr(obj.sxlayers[layerIdx], 'alpha')
                            fillmode = getattr(obj.sxlayers[layerIdx], 'layerType')

                            if fillmode == 'COLOR':
                                top = [
                                    vertexColors[layer.vertexColorLayer].data[idx].color[0],
                                    vertexColors[layer.vertexColorLayer].data[idx].color[1],
                                    vertexColors[layer.vertexColorLayer].data[idx].color[2],
                                    vertexColors[layer.vertexColorLayer].data[idx].color[3]][:]

                            elif layer.name == 'gradient1':
                                top = [
                                    sxmaterial.nodes['PaletteColor3'].outputs[0].default_value[0],
                                    sxmaterial.nodes['PaletteColor3'].outputs[0].default_value[1],
                                    sxmaterial.nodes['PaletteColor3'].outputs[0].default_value[2],
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]]]

                            elif layer.name == 'gradient2':
                                top = [
                                    sxmaterial.nodes['PaletteColor4'].outputs[0].default_value[0],
                                    sxmaterial.nodes['PaletteColor4'].outputs[0].default_value[1],
                                    sxmaterial.nodes['PaletteColor4'].outputs[0].default_value[2],
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]]]

                            elif fillmode == 'UV4':
                                top = [
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]],
                                    uvValues[layer.uvLayer1].data[idx].uv[channels[layer.uvChannel1]],
                                    uvValues[layer.uvLayer2].data[idx].uv[channels[layer.uvChannel2]],
                                    uvValues[layer.uvLayer3].data[idx].uv[channels[layer.uvChannel3]]][:]

                            elif fillmode == 'UV':
                                top = [
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]],
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]],
                                    uvValues[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]],
                                    1.0][:]

                            if blend == 'ALPHA':
                                for j in range(3):
                                    base[j] = (top[j] * (top[3] * alpha) + base[j] * (1 - (top[3] * alpha)))
                                base[3] += top[3] * alpha
                                if base[3] > 1.0:
                                    base[3] = 1.0

                            elif blend == 'ADD':
                                for j in range(3):
                                    base[j] += top[j] * (top[3] * alpha)
                                base[3] += top[3] * alpha
                                if base[3] > 1.0:
                                    base[3] = 1.0

                            elif blend == 'MUL':
                                for j in range(3):
                                    # layer2 lerp with white using (1-alpha), multiply with layer1
                                    mul = ((top[j] * (top[3] * alpha) + (1.0 * (1 - (top[3] * alpha)))))
                                    base[j] = mul * base[j]

                            elif blend == 'OVR':
                                over = [0.0, 0.0, 0.0, 0.0]
                                for j in range(3):
                                    if base[j] < 0.5:
                                        over[j] = 2.0 * base[j] * top[j]
                                    else:
                                        over[j] = 1.0 - 2.0 * (1.0 - base[j]) * (1.0 - top[j])
                                    over[3] += top[3]
                                    base[j] = (over[j] * (over[3] * alpha) + base[j] * (1.0 - (over[3] * alpha)))
                                base[3] += top[3] * alpha
                                if base[3] > 1.0:
                                    base[3] = 1.0

                    resultColors[idx].color = [base[0], base[1], base[2], base[3] * baseAlpha] # base[:]
        bpy.ops.object.mode_set(mode=mode)


    # Takes vertex color set names, uv map names, and channel IDs as input.
    # CopyChannel does not perform translation of layernames to object data sets.
    # Expected input is [obj, ...], vertexcolorsetname, R/G/B/A, uvlayername, U/V, mode
    def copyChannel(self, objs, source, sourceChannel, target, targetChannel, fillMode):
        objDicts = tools.selectionHandler(objs)
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        channels = {'R': 0, 'G': 1, 'B': 2, 'A': 3, 'U': 0, 'V': 1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers
            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            # UV to UV
            if fillMode == 0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        value = vertexUVs[source].data[idx].uv[channels[sourceChannel]]
                        vertexUVs[target].data[idx].uv[channels[targetChannel]] = value
            # RGB luminance to UV
            elif fillMode == 1:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        color = vertexColors[source].data[idx].color
                        value = mesh.colorToLuminance(color)
                        vertexUVs[target].data[idx].uv[channels[targetChannel]] = value
            # UV to RGB
            elif fillMode == 2:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        value = vertexUVs[source].data[idx].uv[channels[sourceChannel]]
                        if value > 0.0:
                            alpha = 1.0
                        else:
                            alpha = 0.0
                        vertexColors[target].data[idx].color = [value, value, value, alpha]
            # R/G/B/A to UV
            elif fillMode == 3:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        value = vertexColors[source].data[idx].color[channels[sourceChannel]]
                        vertexUVs[target].data[idx].uv[channels[targetChannel]] = value
            # RGBA to RGBA
            elif fillMode == 4:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        value = vertexColors[source].data[idx].color[:]
                        vertexColors[target].data[idx].color = value
            # UV to R/G/B/A
            elif fillMode == 5:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        value = vertexUVs[source].data[idx].uv[channels[sourceChannel]]
                        vertexColors[target].data[idx].color[channels[targetChannel]] = value
            # UV4 luminance to UV
            elif fillMode == 6:
                set0 = obj.sxlayers[source].uvLayer0
                set1 = obj.sxlayers[source].uvLayer1
                set2 = obj.sxlayers[source].uvLayer2
                channel0 = channels[obj.sxlayers[source].uvChannel0]
                channel1 = channels[obj.sxlayers[source].uvChannel1]
                channel2 = channels[obj.sxlayers[source].uvChannel2]
                for vert_idx, loop_indices in vertLoopDict.items():
                    for idx in loop_indices:
                        v0 = vertexUVs[set0].data[idx].uv[channel0]
                        v1 = vertexUVs[set1].data[idx].uv[channel1]
                        v2 = vertexUVs[set2].data[idx].uv[channel2]
                        color = [v0, v1, v2, 1.0]
                        value = mesh.colorToLuminance(color)
                        vertexUVs[target].data[idx].uv[channels[targetChannel]] = value

        bpy.ops.object.mode_set(mode=mode)


    # Generate 1-bit layer masks for color layers
    # so the faces can be re-colored in a game engine
    def generateMasks(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        channels = {'R': 0, 'G': 1, 'B': 2, 'A': 3, 'U': 0, 'V': 1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            uvValues = obj.data.uv_layers
            layers = utils.findColorLayers(obj)
            del layers[0]
            for layer in layers:
                uvmap = obj.sxlayers['masks'].uvLayer0
                targetChannel = obj.sxlayers['masks'].uvChannel0
                for poly in obj.data.polygons:
                    for idx in poly.loop_indices:
                        for i, layer in enumerate(layers):
                            i += 1
                            if i == 1:
                                uvValues[uvmap].data[idx].uv[channels[targetChannel]] = i
                            else:
                                vertexAlpha = vertexColors[layer.vertexColorLayer].data[idx].color[3]
                                if vertexAlpha >= sxglobals.alphaTolerance:
                                    uvValues[uvmap].data[idx].uv[channels[targetChannel]] = i

        bpy.ops.object.mode_set(mode=mode)


    def flattenAlphas(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            vertexUVs = obj.data.uv_layers
            channels = {'U': 0, 'V': 1}
            for layer in obj.sxlayers:
                if (layer.name == 'gradient1') or (layer.name == 'gradient2'):
                    alpha = layer.alpha
                    for poly in obj.data.polygons:
                        for idx in poly.loop_indices:
                            vertexUVs[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]] *= alpha
                    layer.alpha = 1.0

                elif layer.name == 'overlay':
                    alpha = layer.alpha
                    for poly in obj.data.polygons:
                        for idx in poly.loop_indices:
                            vertexUVs[layer.uvLayer3].data[idx].uv[channels[layer.uvChannel3]] *= alpha
                    layer.alpha = 1.0

        bpy.ops.object.mode_set(mode=mode)


    def mergeLayers(self, objs, sourceLayer, targetLayer):
        if sourceLayer.index < targetLayer.index:
            baseLayer = sourceLayer
            topLayer = targetLayer
        else:
            baseLayer = targetLayer
            topLayer = sourceLayer

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.index], 'visibility', True)
            setattr(obj.sxlayers[targetLayer.index], 'visibility', True)

        self.blendLayers(objs, [topLayer, ], baseLayer, targetLayer)
        self.clearLayers(objs, sourceLayer)

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.index], 'blendMode', 'ALPHA')
            setattr(obj.sxlayers[targetLayer.index], 'blendMode', 'ALPHA')

            obj.sxtools.selectedlayer = targetLayer.index


    def pasteLayer(self, objs, sourceLayer, targetLayer, fillMode):
        sourceMode = sourceLayer.layerType
        targetMode = targetLayer.layerType

        if sourceMode == 'COLOR' and targetMode == 'COLOR':
            for obj in objs:
                sourceBlend = getattr(obj.sxlayers[sourceLayer.index], 'blendMode')[:]
                targetBlend = getattr(obj.sxlayers[targetLayer.index], 'blendMode')[:]

                if fillMode == 'swap':
                    setattr(obj.sxlayers[sourceLayer.index], 'blendMode', targetBlend)
                    setattr(obj.sxlayers[targetLayer.index], 'blendMode', sourceBlend)
                else:
                    setattr(obj.sxlayers[targetLayer.index], 'blendMode', sourceBlend)

        if fillMode == 'swap':
            tempLayer = objs[0].sxlayers['composite']
            tools.layerCopyManager(objs, sourceLayer, tempLayer)
            tools.layerCopyManager(objs, targetLayer, sourceLayer)
            tools.layerCopyManager(objs, tempLayer, targetLayer)
        elif fillMode == 'merge':
            self.mergeLayers(objs, sourceLayer, targetLayer)
        else:
            tools.layerCopyManager(objs, sourceLayer, targetLayer)


    def updateLayerPalette(self, objs, layer):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        channels = {'U': 0, 'V': 1}
        colorArray = []

        for obj in objs:
            mesh = obj.data
            if layer.layerType == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif layer.layerType == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                uvValues3 = obj.data.uv_layers[layer.uvLayer3].data
            elif layer.layerType == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data

            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    if layer.layerType == 'COLOR':
                        color = vertexColors[loop_idx].color[:]
                    elif layer.layerType == 'UV4':
                        uvValue0 = uvValues0[loop_idx].uv[channels[layer.uvChannel0]]
                        uvValue1 = uvValues1[loop_idx].uv[channels[layer.uvChannel1]]
                        uvValue2 = uvValues2[loop_idx].uv[channels[layer.uvChannel2]]
                        uvValue3 = uvValues3[loop_idx].uv[channels[layer.uvChannel3]]
                        color = (uvValue0, uvValue1, uvValue2, uvValue3)
                    elif layer.layerType == 'UV':
                        uvValue = uvValues[loop_idx].uv[channels[layer.uvChannel0]]
                        color = (uvValue, uvValue, uvValue, uvValue)

                    if color[3] > 0.0:
                        colorArray.append(color)

        if len(colorArray) == 0:
            color = (0.0, 0.0, 0.0, 1.0)
            colorArray.append(color)

        colorSet = set(colorArray)
        colorFreq = []
        for color in colorSet:
            colorFreq.append((colorArray.count(color), color))

        sortColors = sorted(colorFreq, key=lambda tup: tup[0])
        colLen = len(sortColors)
        while colLen < 8:
            sortColors.append((0, [0.0, 0.0, 0.0, 1.0]))
            colLen += 1

        sortColors = sortColors[0::int(colLen/8)]
        scn = bpy.context.scene.sxtools
        for i in range(8):
            setattr(scn, 'layerpalette' + str(i + 1), sortColors[i][1])

        bpy.ops.object.mode_set(mode=mode)


    def updateLayerBrightness(self, objs, layer):
        luminanceDict = mesh.calculateLuminance(objs, layer)
        luminanceList = list()
        for vertDict in luminanceDict.values():
            for valueList in vertDict.values():
                luminanceList.extend(valueList[1])
        if len(luminanceList) == 0:
            luminanceList.extend([0.0, ])

        brightness = statistics.mean(luminanceList)
        sxglobals.brightnessUpdate = True
        bpy.context.scene.sxtools.brightnessvalue = brightness
        sxglobals.brightnessUpdate = False


    def __del__(self):
        print('SX Tools: Exiting layers')


# ------------------------------------------------------------------------
#    Mesh Analysis
# ------------------------------------------------------------------------
class SXTOOLS_mesh(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting mesh')


    def calculateBoundingBox(self, vertDict):
        bbx = [[None, None], [None, None], [None, None]]
        for i, fvPos in enumerate(vertDict.values()):
            fvPos = (fvPos[0][0], fvPos[0][1], fvPos[0][2])
            # first vert
            if i == 0:
                bbx[0][0] = bbx[0][1] = fvPos[0]
                bbx[1][0] = bbx[1][1] = fvPos[1]
                bbx[2][0] = bbx[2][1] = fvPos[2]
            else:
                for j in range(3):
                    if fvPos[j] < bbx[j][0]:
                        bbx[j][0] = fvPos[j]
                    elif fvPos[j] > bbx[j][1]:
                        bbx[j][1] = fvPos[j]

        return bbx


    def rayRandomizer(self):
        u1 = random.uniform(0, 1)
        u2 = random.uniform(0, 1)
        r = math.sqrt(u1)
        theta = 2*math.pi*u2

        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return (x, y, math.sqrt(max(0, 1 - u1)))


    def calculateDirection(self, objs, directionVector):
        objDicts = tools.selectionHandler(objs)
        mode = objs[0].mode
        objDirections = {}

        bpy.ops.object.mode_set(mode='OBJECT')

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertWorldPosDict = objDicts[obj][2]
            vertDirDict = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                vertWorldNormal = Vector(vertWorldPosDict[vert_idx][1])

                for loop_idx in loop_indices:
                    vertDirDict[vert_idx] = vertWorldNormal @ directionVector
            objDirections[obj] = vertDirDict

        bpy.ops.object.mode_set(mode=mode)
        return objDirections


    def groundPlane(self, size, pos):
        vertArray = []
        faceArray = []
        size = size * 0.5

        vert = [(-size, -size, 0.0)]
        vertArray.extend(vert)
        vert = [(size, -size, 0.0)]
        vertArray.extend(vert)
        vert = [(-size, size, 0.0)]
        vertArray.extend(vert)
        vert = [(size, size, 0.0)]
        vertArray.extend(vert)

        face = [(0, 1, 3, 2)]
        faceArray.extend(face)

        mesh = bpy.data.meshes.new('groundPlane_mesh')
        groundPlane = bpy.data.objects.new('groundPlane', mesh)
        bpy.context.scene.collection.objects.link(groundPlane)

        mesh.from_pydata(vertArray, [], faceArray)
        mesh.update(calc_edges=True)

        groundPlane.location = pos

        return groundPlane


    def findRootPivot(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')

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

        pivot = ((xmax + xmin)*0.5, (ymax + ymin)*0.5, zmin)
        bpy.ops.object.mode_set(mode=mode)

        return pivot


    def calculateOcclusion(self, objs, rayCount, blend, dist, groundPlane, bias=0.01):
        objDicts = tools.selectionHandler(objs)
        mode = objs[0].mode
        scene = bpy.context.scene
        contribution = 1.0/float(rayCount)
        hemiSphere = [None] * rayCount

        objOcclusions = {}

        for idx in range(rayCount):
            hemiSphere[idx] = self.rayRandomizer()

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = False

        bpy.ops.object.mode_set(mode='OBJECT')

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            vertWorldPosDict = objDicts[obj][2]
            vertOccDict = {}
            if groundPlane:
                pivot = self.findRootPivot([obj, ])
                pivot = (pivot[0], pivot[1], pivot[2] - 0.5)
                ground = self.groundPlane(20, pivot)

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

                        hit, loc, normal, index = obj.ray_cast(vertPos, sample, distance=dist)

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

                        scnHit, scnLoc, scnNormal, scnIndex, scnObj, ma = scene.ray_cast(scene.view_layers[0], scnVertPos, sample, distance=dist)

                        if scnHit:
                            scnOccValue -= contribution

                for loop_idx in loop_indices:
                    vertOccDict[vert_idx] = float(occValue * (1.0 - blend) + scnOccValue * blend)

            if groundPlane:
                bpy.data.objects.remove(ground, do_unlink=True)
                # bpy.ops.object.delete({"selected_objects": [ground, ]})

            objOcclusions[obj] = vertOccDict

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = True

        bpy.ops.object.mode_set(mode=mode)
        return objOcclusions


    def calculateThickness(self, objs, rayCount, bias=0.000001):
        objDicts = tools.selectionHandler(objs)
        mode = objs[0].mode
        contribution = 1.0/float(rayCount)
        hemiSphere = [None] * rayCount
        bias = 1e-5

        distances = list()
        objThicknesses = {}

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = False

        bpy.ops.object.mode_set(mode='OBJECT')

        # First pass to analyze ray hit distances,
        # then set max ray distance to half of median distance
        distHemiSphere = [None] * 20
        for idx in range(20):
            distHemiSphere[idx] = self.rayRandomizer()

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                forward = Vector((0, 0, 1))

                # Invert normal to cast inside object
                invNormal = tuple([-1*x for x in vertNormal])

                biasVec = tuple([bias*x for x in invNormal])
                rotQuat = forward.rotation_difference(invNormal)
                vertPos = vertLoc

                # offset ray origin with normal bias
                vertPos = (vertPos[0] + biasVec[0], vertPos[1] + biasVec[1], vertPos[2] + biasVec[2])

                for sample in distHemiSphere:
                    sample = Vector(sample)
                    sample.rotate(rotQuat)

                    hit, loc, normal, index = obj.ray_cast(vertPos, sample)

                    if hit:
                        distanceVec = (loc[0] - vertPos[0], loc[1] - vertPos[1], loc[2] - vertPos[2])
                        distanceVec = Vector(distanceVec)
                        distances.append(distanceVec.length)

        rayDistance = statistics.median(distances) * 0.5

        for idx in range(rayCount):
            hemiSphere[idx] = self.rayRandomizer()

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            vertDict = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                thicknessValue = 0.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                forward = Vector((0, 0, 1))

                # Invert normal to cast inside object
                invNormal = tuple([-1*x for x in vertNormal])

                biasVec = tuple([bias*x for x in invNormal])
                rotQuat = forward.rotation_difference(invNormal)
                vertPos = vertLoc

                # offset ray origin with normal bias
                vertPos = (vertPos[0] + biasVec[0], vertPos[1] + biasVec[1], vertPos[2] + biasVec[2])

                for sample in hemiSphere:
                    sample = Vector(sample)
                    sample.rotate(rotQuat)

                    hit, loc, normal, index = obj.ray_cast(vertPos, sample, distance=rayDistance)

                    if hit:
                        thicknessValue += contribution

                for loop_idx in loop_indices:
                    vertDict[vert_idx] = thicknessValue
            objThicknesses[obj] = vertDict

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = True

        bpy.ops.object.mode_set(mode=mode)
        return objThicknesses


    def calculateLuminance(self, objs, layer):
        objDicts = tools.selectionHandler(objs)
        layerType = layer.layerType
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        channels = {'U': 0, 'V':1}

        objLuminances = {}

        for obj in objs:
            if layerType == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif layerType == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                uvValues3 = obj.data.uv_layers[layer.uvLayer3].data
            elif layerType == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data
                if layer.uvChannel0 == 'U':
                    selChannel = 0
                elif layer.uvChannel0 == 'V':
                    selChannel = 1

            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]
            vtxLuminances = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                loopLuminances = []
                for loop_idx in loop_indices:
                    if layerType == 'COLOR':
                        fvColor = vertexColors[loop_idx].color
                        luminance = self.colorToLuminance(fvColor)
                    elif layerType == 'UV4':
                        fvColor = [
                            uvValues0[loop_idx].uv[channels[layer.uvChannel0]],
                            uvValues1[loop_idx].uv[channels[layer.uvChannel1]],
                            uvValues2[loop_idx].uv[channels[layer.uvChannel2]],
                            uvValues3[loop_idx].uv[channels[layer.uvChannel3]]][:]
                        luminance = self.colorToLuminance(fvColor)
                    elif layerType == 'UV':
                        luminance = uvValues[loop_idx].uv[selChannel]
                    loopLuminances.append(luminance)
                vtxLuminances[vert_idx] = (loop_indices, loopLuminances)
            objLuminances[obj] = vtxLuminances

        bpy.ops.object.mode_set(mode=mode)
        return objLuminances


    def colorToLuminance(self, color):
        luminance = ((color[0] +
                      color[0] +
                      color[2] +
                      color[1] +
                      color[1] +
                      color[1]) / float(6.0))

        return luminance


    def calculateCurvature(self, objs, normalize=False):
        objCurvatures = {}
        for obj in objs:
            vtxCurvatures = {}
            bm = bmesh.new()
            bm.from_mesh(obj.data)
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

        return objCurvatures


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------
class SXTOOLS_tools(object):
    def __init__(self):
        return None


    # Analyze if multi-object selection is in object or component mode,
    # return appropriate vertices
    def selectionHandler(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
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
                                (mat @ mesh.vertices[vert_idx].normal - mat @ Vector()).normalized())
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
                                (mat @ mesh.vertices[vert_idx].normal - mat @ Vector()).normalized())

            objDicts[obj] = (vertLoopDict, vertPosDict, vertWorldPosDict)

        bpy.ops.object.mode_set(mode=mode)
        return objDicts

    # maskLayer assumes color layers only
    def applyColor(self, objs, layer, color, overwrite, noise=0.0, mono=False, maskLayer=None):
        objDicts = self.selectionHandler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        fillChannel3 = channels[layer.uvChannel3]

        fillValue = mesh.colorToLuminance(color)

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')

        for obj in objs:
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
            elif fillMode == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                uvValues3 = obj.data.uv_layers[layer.uvLayer3].data

            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            if maskLayer:
                maskValues = obj.data.vertex_colors[maskLayer.vertexColorLayer].data

            if noise == 0.0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if maskLayer:
                            if fillMode == 'COLOR':
                                if maskValues[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = color[0]
                                    vertexColors[loop_idx].color[1] = color[1]
                                    vertexColors[loop_idx].color[2] = color[2]
                                    vertexColors[loop_idx].color[3] = maskValues[loop_idx].color[3]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV4':
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = color[0]
                                    uvValues1[loop_idx].uv[fillChannel1] = color[1]
                                    uvValues2[loop_idx].uv[fillChannel2] = color[2]
                                    uvValues3[loop_idx].uv[fillChannel3] = maskValues[loop_idx].color[3]
                                else:
                                    uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                    uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                    uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                    uvValues3[loop_idx].uv[fillChannel3] = 0.0
                            elif fillMode == 'UV':
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillValue * maskValues[loop_idx].color[3]
                        elif overwrite:
                            if fillMode == 'COLOR':
                                vertexColors[loop_idx].color = color
                            elif fillMode == 'UV4':
                                uvValues0[loop_idx].uv[fillChannel0] = color[0]
                                uvValues1[loop_idx].uv[fillChannel1] = color[1]
                                uvValues2[loop_idx].uv[fillChannel2] = color[2]
                                uvValues3[loop_idx].uv[fillChannel3] = color[3]
                            elif fillMode == 'UV':
                                uvValues0[loop_idx].uv[fillChannel0] = fillValue
                        else:
                            if fillMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = color[0]
                                    vertexColors[loop_idx].color[1] = color[1]
                                    vertexColors[loop_idx].color[2] = color[2]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV4':
                                if uvValues3[loop_idx].uv[fillChannel3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = color[0]
                                    uvValues1[loop_idx].uv[fillChannel1] = color[1]
                                    uvValues2[loop_idx].uv[fillChannel2] = color[2]
                                else:
                                    uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                    uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                    uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                    uvValues3[loop_idx].uv[fillChannel3] = 0.0
                            elif fillMode == 'UV':
                                if uvValues0[loop_idx].uv[fillChannel0] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillValue

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
                            if maskLayer:
                                if maskValues[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = noiseColor[0]
                                    vertexColors[loop_idx].color[1] = noiseColor[1]
                                    vertexColors[loop_idx].color[2] = noiseColor[2]
                                    vertexColors[loop_idx].color[3] = maskValues[loop_idx].color[3]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif overwrite:
                                vertexColors[loop_idx].color = noiseColor
                            else:
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    vertexColors[loop_idx].color[0] = noiseColor[0]
                                    vertexColors[loop_idx].color[1] = noiseColor[1]
                                    vertexColors[loop_idx].color[2] = noiseColor[2]
                                else:
                                    vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                elif fillMode == 'UV4':
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
                            if maskLayer:
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = noiseColor[0]
                                    uvValues1[loop_idx].uv[fillChannel1] = noiseColor[1]
                                    uvValues2[loop_idx].uv[fillChannel2] = noiseColor[2]
                                    uvValues3[loop_idx].uv[fillChannel3] = maskValues[loop_idx].color[3]
                                else:
                                    uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                    uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                    uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                    uvValues3[loop_idx].uv[fillChannel3] = 0.0
                            elif overwrite:
                                uvValues0[loop_idx].uv[fillChannel0] = noiseColor[0]
                                uvValues1[loop_idx].uv[fillChannel1] = noiseColor[1]
                                uvValues2[loop_idx].uv[fillChannel2] = noiseColor[2]
                                uvValues3[loop_idx].uv[fillChannel3] = noiseColor[3]
                            else:
                                if uvValues3[loop_idx].uv[fillChannel3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = noiseColor[0]
                                    uvValues1[loop_idx].uv[fillChannel1] = noiseColor[1]
                                    uvValues2[loop_idx].uv[fillChannel2] = noiseColor[2]
                                else:
                                    uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                    uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                    uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                    uvValues3[loop_idx].uv[fillChannel3] = 0.0
                elif fillMode == 'UV':
                    for vert_idx, loop_indices in vertLoopDict.items():
                        fillNoise = mesh.colorToLuminance(color)
                        fillNoise += random.uniform(-fillNoise*noise, fillNoise*noise)
                        for loop_idx in loop_indices:
                            if maskLayer:
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillNoise * maskValues[loop_idx].color[3]
                            elif overwrite:
                                uvValues0[loop_idx].uv[fillChannel0] = fillNoise
                            else:
                                if uvValues0[loop_idx].uv[fillChannel0] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillNoise

        bpy.ops.object.mode_set(mode=mode)


    def applyBrightness(self, objs, layer, newBrightness):
        objDicts = self.selectionHandler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        fillChannel3 = channels[layer.uvChannel3]

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')

        luminanceDict = mesh.calculateLuminance(objs, layer)
        luminanceList = list()
        for vertDict in luminanceDict.values():
            for valueList in vertDict.values():
                luminanceList.extend(valueList[1])

        avgBrightness = statistics.mean(luminanceList)
        if avgBrightness == 0.0:
            fillValue = 0.01
        else:
            fillValue = float(newBrightness)/float(avgBrightness)

        for obj in objs:
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
            elif fillMode == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                uvValues3 = obj.data.uv_layers[layer.uvLayer3].data

            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            if avgBrightness != 0.0:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if fillMode == 'COLOR':
                            for i in range(3):
                                vertexColors[loop_idx].color[i] *= fillValue
                                if vertexColors[loop_idx].color[i] > 1.0:
                                    vertexColors[loop_idx].color[i] = 1.0
                        elif fillMode == 'UV4':
                            uvValues0[loop_idx].uv[fillChannel0] *= fillValue
                            uvValues1[loop_idx].uv[fillChannel1] *= fillValue
                            uvValues2[loop_idx].uv[fillChannel2] *= fillValue
                            if uvValues0[loop_idx].uv[fillChannel0] > 1.0:
                                uvValues0[loop_idx].uv[fillChannel0] = 1.0
                            if uvValues1[loop_idx].uv[fillChannel1] > 1.0:
                                uvValues1[loop_idx].uv[fillChannel1] = 1.0
                            if uvValues2[loop_idx].uv[fillChannel2] > 1.0:
                                uvValues2[loop_idx].uv[fillChannel2] = 1.0
                        elif fillMode == 'UV':
                            uvValues0[loop_idx].uv[fillChannel0] *= fillValue
                            if uvValues0[loop_idx].uv[fillChannel0] > 1.0:
                                uvValues0[loop_idx].uv[fillChannel0] = 1.0
            else:
                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if fillMode == 'COLOR':
                            for i in range(3):
                                vertexColors[loop_idx].color[i] = fillValue
                        elif fillMode == 'UV4':
                            uvValues0[loop_idx].uv[fillChannel0] = fillValue
                            uvValues1[loop_idx].uv[fillChannel1] = fillValue
                            uvValues2[loop_idx].uv[fillChannel2] = fillValue
                        elif fillMode == 'UV':
                            uvValues0[loop_idx].uv[fillChannel0] = fillValue

        bpy.ops.object.mode_set(mode=mode)


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
            for i in range(8):
                setattr(scn, 'fillpalette' + str(i + 1), colorArray[i])


    def applyRamp(self, objs, layer, ramp, rampmode, overwrite, mergebbx=True, noise=0.0, mono=False, maskLayer=None):
        scene = bpy.context.scene.sxtools
        objDicts = self.selectionHandler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        fillChannel3 = channels[layer.uvChannel3]

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')

        if rampmode == 'C':
            objValues = mesh.calculateCurvature(objs, False)
        elif rampmode == 'CN':
            objValues = mesh.calculateCurvature(objs, True)
        elif rampmode == 'OCC':
            objValues = mesh.calculateOcclusion(objs, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
        elif rampmode == 'LUM':
            objValues = mesh.calculateLuminance(objs, layer)
        elif rampmode == 'THK':
            objValues = mesh.calculateThickness(objs, scene.occlusionrays, scene.occlusionbias)
        elif rampmode == 'DIR':
            inclination = (bpy.context.scene.sxtools.dirInclination - 90.0)* (2*math.pi)/360.0
            angle = (bpy.context.scene.sxtools.dirAngle + 90) * (2*math.pi)/360.0
            directionVector = (math.sin(inclination) * math.cos(angle), math.sin(inclination) * math.sin(angle), math.cos(inclination))
            directionVector = Vector(directionVector)
            objValues = mesh.calculateDirection(objs, directionVector)

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
            if rampmode == 'C' or rampmode == 'CN' or rampmode == 'OCC' or rampmode == 'LUM' or rampmode == 'THK' or rampmode == 'DIR':
                valueDict = objValues[obj]
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
            elif fillMode == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                uvValues3 = obj.data.uv_layers[layer.uvLayer3].data

            vertLoopDict = defaultdict(list)
            vertPosDict = defaultdict(list)
            mat = obj.matrix_world
            
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            
            if not mergebbx and (rampmode != 'C') and (rampmode != 'CN') and (rampmode != 'OCC') and (rampmode != 'LUM') and (rampmode != 'THK') and (rampmode != 'DIR'):
                bbx = mesh.calculateBoundingBox(vertPosDict)
                xmin, xmax = bbx[0][0], bbx[0][1]
                ymin, ymax = bbx[1][0], bbx[1][1]
                zmin, zmax = bbx[2][0], bbx[2][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                noiseColor = [0.0, 0.0, 0.0, 0.0]
                if mono:
                    monoNoise = random.uniform(-noise, noise)
                    for i in range(4):
                        noiseColor[i] += monoNoise
                else:
                    for i in range(4):
                        noiseColor[i] += random.uniform(-noise, noise)

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
                    elif rampmode == 'C' or rampmode == 'CN' or rampmode == 'OCC' or rampmode == 'THK' or rampmode == 'DIR':
                        ratioRaw = valueDict[vert_idx]
                    elif rampmode == 'LUM':
                        ratioRaw = valueDict[vert_idx][1]

                    color = [0.0, 0.0, 0.0, 0.0]
                    if rampmode == 'LUM':
                        ratio = []
                        for rt in ratioRaw:
                            ratio.append(max(min(rt, 1), 0))
                        evalColor = ramp.color_ramp.evaluate(ratio[i])
                        for i, value in enumerate(evalColor):
                            color[i] = value
                    else:
                        ratio = max(min(ratioRaw, 1), 0)
                        evalColor = ramp.color_ramp.evaluate(ratio)
                        for i, value in enumerate(evalColor):
                            color[i] = value

                    if overwrite:
                        if fillMode == 'COLOR':
                            for i in range(3):
                                color[i] += noiseColor[i]
                            vertexColors[loop_idx].color = color
                        elif fillMode == 'UV4':
                            uvValues0[loop_idx].uv[fillChannel0] = color[0] + noiseColor[0]
                            uvValues1[loop_idx].uv[fillChannel1] = color[1] + noiseColor[1]
                            uvValues2[loop_idx].uv[fillChannel2] = color[2] + noiseColor[2]
                            uvValues3[loop_idx].uv[fillChannel3] = color[3]
                        elif fillMode == 'UV':
                            fillValue = mesh.colorToLuminance(color)
                            uvValues0[loop_idx].uv[fillChannel0] = fillValue + noiseColor[0]
                    else:
                        if fillMode == 'COLOR':
                            if vertexColors[loop_idx].color[3] > 0.0:
                                for i in range(3):
                                    vertexColors[loop_idx].color[i] = (color[i] + noiseColor[i])
                            else:
                                vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                        elif fillMode == 'UV4':
                            if uvValues3[loop_idx].uv[fillChannel3] > 0.0:
                                uvValues0[loop_idx].uv[fillChannel0] = (color[0] + noiseColor[0])
                                uvValues1[loop_idx].uv[fillChannel1] = (color[1] + noiseColor[1])
                                uvValues2[loop_idx].uv[fillChannel2] = (color[2] + noiseColor[2])
                            else:
                                uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                uvValues3[loop_idx].uv[fillChannel3] = 0.0
                        elif fillMode == 'UV':
                            if uvValues0[loop_idx].uv[fillChannel0] > 0.0:
                                color = ramp.color_ramp.evaluate(ratio[i])
                                fillValue = mesh.colorToLuminance(color)
                                uvValues0[loop_idx].uv[fillChannel0] = (fillValue + noiseColor[0])

        bpy.ops.object.mode_set(mode=mode)


    def selectMask(self, objs, layers, inverse):
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        objDicts = self.selectionHandler(objs)
        channels = {'U': 0, 'V': 1}

        for obj in objs:
            for layer in layers:
                selMode = layer.layerType
                if selMode == 'COLOR':
                    vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
                elif selMode == 'UV4':
                    uvValues = obj.data.uv_layers[layer.uvLayer3].data
                    selChannel = channels[layer.uvChannel3]
                elif selMode == 'UV':
                    uvValues = obj.data.uv_layers[layer.uvLayer0].data
                    selChannel = channels[layer.uvChannel0]
                vertLoopDict = defaultdict(list)
                vertLoopDict = objDicts[obj][0]

                for vert_idx, loop_indices in vertLoopDict.items():
                    for loop_idx in loop_indices:
                        if inverse:
                            if selMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] == 0.0:
                                    obj.data.vertices[vert_idx].select = True
                            elif (selMode == 'UV') or (selMode == 'UV4'):
                                if uvValues[loop_idx].uv[selChannel] == 0.0:
                                    obj.data.vertices[vert_idx].select = True
                        else:
                            if selMode == 'COLOR':
                                if vertexColors[loop_idx].color[3] > 0.0:
                                    obj.data.vertices[vert_idx].select = True
                            elif (selMode == 'UV') or (selMode == 'UV4'):
                                if uvValues[loop_idx].uv[selChannel] > 0.0:
                                    obj.data.vertices[vert_idx].select = True

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)


    def selectCrease(self, objs, group):
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0}
        weight = creaseDict[group]

        bpy.context.view_layer.objects.active = objs[0]

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.object.mode_set(mode='OBJECT')

        for obj in objs:
            for edge in obj.data.edges:
                if math.isclose(edge.crease, weight, abs_tol=0.1):
                    edge.select = True

        bpy.ops.object.mode_set(mode='EDIT')


    def assignCrease(self, objs, group):
        mode = objs[0].mode
        creaseDict = {
            'CreaseSet0': -1.0, 'CreaseSet1': 0.25,
            'CreaseSet2': 0.5, 'CreaseSet3': 0.75,
            'CreaseSet4': 1.0}
        weight = creaseDict[group]
        bpy.ops.object.mode_set(mode='EDIT')

        for obj in objs:
            bm = bmesh.from_edit_mesh(obj.data)
            mesh = obj.data

            if 'SubSurfCrease' in bm.edges.layers.crease.keys():
                creaseLayer = bm.edges.layers.crease['SubSurfCrease']
            else:
                creaseLayer = bm.edges.layers.crease.new('SubSurfCrease')

            if 'BevelWeight' in bm.edges.layers.bevel_weight.keys():
                bevelWeightLayer = bm.edges.layers.bevel_weight['BevelWeight']
            else:
                bevelWeightLayer = bm.edges.layers.bevel_weight.new('BevelWeight')

            selectedEdges = [edge for edge in bm.edges if edge.select]
            for edge in selectedEdges:
                edge[creaseLayer] = weight
                mesh.edges[edge.index].crease = weight
                if weight == 1.0:
                    edge.smooth = False
                    mesh.edges[edge.index].use_edge_sharp = True
                    edge[bevelWeightLayer] = weight
                else:
                    edge.smooth = True
                    mesh.edges[edge.index].use_edge_sharp = False
                    edge[bevelWeightLayer] = -1.0

            bmesh.update_edit_mesh(obj.data)
        bpy.ops.object.mode_set(mode=mode)


    # takes any layers in layerview, translates to copyChannel batches
    def layerCopyManager(self, objs, sourceLayer, targetLayer):
        sourceType = sourceLayer.layerType
        targetType = targetLayer.layerType

        if sourceType == 'COLOR' and targetType == 'COLOR':
            sourceVertexColors = sourceLayer.vertexColorLayer
            layers.copyChannel(objs, sourceVertexColors, None, targetLayer.vertexColorLayer, None, 4)
        elif sourceType == 'COLOR' and targetType == 'UV4':
            sourceVertexColors = sourceLayer.vertexColorLayer
            targetUVs = targetLayer.uvLayer0
            sourceChannel = 'R'
            targetChannel = targetLayer.uvChannel0
            layers.copyChannel(objs, sourceVertexColors, sourceChannel, targetUVs, targetChannel, 3)
            targetUVs = targetLayer.uvLayer1
            sourceChannel = 'G'
            targetChannel = targetLayer.uvChannel1
            layers.copyChannel(objs, sourceVertexColors, sourceChannel, targetUVs, targetChannel, 3)
            targetUVs = targetLayer.uvLayer2
            sourceChannel = 'B'
            targetChannel = targetLayer.uvChannel2
            layers.copyChannel(objs, sourceVertexColors, sourceChannel, targetUVs, targetChannel, 3)
            targetUVs = targetLayer.uvLayer3
            sourceChannel = 'A'
            targetChannel = targetLayer.uvChannel3
            layers.copyChannel(objs, sourceVertexColors, sourceChannel, targetUVs, targetChannel, 3)
        elif sourceType == 'UV4' and targetType == 'COLOR':
            sourceUVs = sourceLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, 'R', 5)
            sourceUVs = sourceLayer.uvLayer1
            sourceChannel = sourceLayer.uvChannel1
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, 'G', 5)
            sourceUVs = sourceLayer.uvLayer2
            sourceChannel = sourceLayer.uvChannel2
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, 'B', 5)
            sourceUVs = sourceLayer.uvLayer3
            sourceChannel = sourceLayer.uvChannel3
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, 'A', 5)
        elif sourceType == 'UV4' and targetType == 'UV':
            targetUVs = targetLayer.uvLayer0
            targetChannel = targetLayer.uvChannel0
            layers.copyChannel(objs, sourceLayer.name, None, targetUVs, targetChannel, 6)
        elif sourceType == 'COLOR' and targetType == 'UV':
            sourceVertexColors = sourceLayer.vertexColorLayer
            targetChannel = targetLayer.uvChannel0
            layers.copyChannel(objs, sourceVertexColors, None, targetLayer.uvLayer0, targetChannel, 1)
        elif sourceType == 'UV' and targetType == 'UV':
            sourceUVs = sourceLayer.uvLayer0
            targetUVs = targetLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            targetChannel = targetLayer.uvChannel0
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)
        elif sourceType == 'UV' and targetType == 'COLOR':
            sourceUVs = sourceLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, None, 2)
        elif sourceType == 'UV' and targetType == 'UV4':
            sourceUVs = sourceLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            targetUVs = targetLayer.uvLayer0
            targetChannel = targetLayer.uvChannel0
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)
            targetUVs = targetLayer.uvLayer1
            targetChannel = targetLayer.uvChannel1
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)
            targetUVs = targetLayer.uvLayer2
            targetChannel = targetLayer.uvChannel2
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)
            targetUVs = targetLayer.uvLayer3
            targetChannel = targetLayer.uvChannel3
            layers.copyChannel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)


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
            bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor'+str(idx-1)].outputs[0].default_value = color

            self.applyColor(objs, layer, color, False, noise, mono)


    def applyMaterial(self, objs, targetLayer, material, overwrite, noise, mono):
        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        self.applyColor(objs, objs[0].sxlayers['smoothness'], palette[2], overwrite, noise, mono)
        self.applyColor(objs, objs[0].sxlayers['metallic'], palette[1], overwrite, noise, mono)
        self.applyColor(objs, targetLayer, palette[0], overwrite, noise, mono)


    def addModifiers(self, objs):
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159

        for obj in objs:
            if 'sxSubdivision' not in obj.modifiers.keys():
                obj.modifiers.new(type='SUBSURF', name='sxSubdivision')
                obj.modifiers['sxSubdivision'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxSubdivision'].quality = 6
                obj.modifiers['sxSubdivision'].levels = obj.sxtools.subdivisionlevel
                obj.modifiers['sxSubdivision'].uv_smooth = 'NONE'
                obj.modifiers['sxSubdivision'].show_only_control_edges = True
                obj.modifiers['sxSubdivision'].show_on_cage = True
            if 'sxBevel' not in  obj.modifiers.keys():
                obj.modifiers.new(type='BEVEL', name='sxBevel')
                if hardmode == 'BEVEL' or obj.sxtools.modifiervisibility:
                    obj.modifiers['sxBevel'].show_viewport = True
                else:
                    obj.modifiers['sxBevel'].show_viewport = False
                obj.modifiers['sxBevel'].width = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].width_pct = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].segments = obj.sxtools.bevelsegments
                obj.modifiers['sxBevel'].use_clamp_overlap = True
                obj.modifiers['sxBevel'].loop_slide = True
                obj.modifiers['sxBevel'].mark_sharp = False
                obj.modifiers['sxBevel'].harden_normals = True
                obj.modifiers['sxBevel'].offset_type = 'OFFSET' # 'WIDTH' 'PERCENT'
                obj.modifiers['sxBevel'].limit_method = 'WEIGHT'
                obj.modifiers['sxBevel'].miter_outer = 'MITER_ARC'
            if 'sxDecimate' not in obj.modifiers.keys():
                obj.modifiers.new(type='DECIMATE', name='sxDecimate')
                obj.modifiers['sxDecimate'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxDecimate'].decimate_type = 'DISSOLVE'
                obj.modifiers['sxDecimate'].angle_limit = obj.sxtools.decimation * (math.pi/180.0)
                obj.modifiers['sxDecimate'].use_dissolve_boundaries = True
                obj.modifiers['sxDecimate'].delimit = {'SHARP', 'UV'}
            if 'sxDecimate2' not in obj.modifiers.keys():
                obj.modifiers.new(type='DECIMATE', name='sxDecimate2')
                obj.modifiers['sxDecimate2'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxDecimate2'].decimate_type = 'COLLAPSE'
                obj.modifiers['sxDecimate2'].ratio = 0.99
                obj.modifiers['sxDecimate2'].use_collapse_triangulate = True
            if 'sxWeightedNormal' not in obj.modifiers.keys():
                obj.modifiers.new(type='WEIGHTED_NORMAL', name='sxWeightedNormal')
                obj.modifiers['sxWeightedNormal'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxWeightedNormal'].mode = 'FACE_AREA_WITH_ANGLE'
                obj.modifiers['sxWeightedNormal'].weight = 95
                if hardmode == 'SMOOTH':
                    obj.modifiers['sxWeightedNormal'].keep_sharp = False
                else:
                    obj.modifiers['sxWeightedNormal'].keep_sharp = True


    def applyModifiers(self, objs):
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            if 'sxSubdivision' in obj.modifiers.keys():
                if obj.modifiers['sxSubdivision'].levels == 0:
                    bpy.ops.object.modifier_remove(modifier='sxSubdivision')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxSubdivision')
            if 'sxBevel' in obj.modifiers.keys():
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxBevel')
            if 'sxDecimate' in obj.modifiers.keys():
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxDecimate')
            if 'sxDecimate2' in obj.modifiers.keys():
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxDecimate2')
            if 'sxWeightedNormal' in obj.modifiers.keys():
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxWeightedNormal')


    def removeModifiers(self, objs):
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            if 'sxSubdivision' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxSubdivision')
            if 'sxBevel' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxBevel')
            if 'sxDecimate' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxDecimate')
            if 'sxDecimate2' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxDecimate2')
            if 'sxEdgeSplit' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxEdgeSplit')
            if 'sxWeightedNormal' in obj.modifiers.keys():
                bpy.ops.object.modifier_remove(modifier='sxWeightedNormal')


    def groupObjects(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')

        pivot = mesh.findRootPivot(objs)

        group = bpy.data.objects.new('empty', None)
        bpy.context.scene.collection.objects.link(group)
        group.empty_display_size = 2
        group.empty_display_type = 'PLAIN_AXES'
        group.location = pivot
        group.name = objs[0].name + '_root'

        for obj in objs:
            obj.parent = group
            obj.location.x -= group.location.x
            obj.location.y -= group.location.y
            obj.location.z -= group.location.z

        bpy.ops.object.mode_set(mode=mode)


    def revertObjects(self, objs):
        self.removeModifiers(objs)

        layers.clearUVs(objs, objs[0].sxlayers['overlay'])
        layers.clearUVs(objs, objs[0].sxlayers['occlusion'])
        layers.clearUVs(objs, objs[0].sxlayers['metallic'])
        layers.clearUVs(objs, objs[0].sxlayers['smoothness'])
        layers.clearUVs(objs, objs[0].sxlayers['transmission'])


    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Exporting Functions
# ------------------------------------------------------------------------
class SXTOOLS_export(object):
    def __init__(self):
        return None


    # This is a project-specific batch operation.
    # These should be adapted to the needs of the game,
    # baking category-specific values to achieve
    # consistent project-wide looks.
    def processObjects(self, objs, mode):
        then = time.time()
        scene = bpy.context.scene.sxtools
        orgObjNames = {}

        # Make sure auto-smooth is on
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if '_mesh' not in obj.data.name:
                obj.data.name = obj.name + '_mesh'

        # Remove empties from selected objects
        for sel in bpy.context.view_layer.objects.selected:
            if sel.type != 'MESH':
                sel.select_set(False)

        # Create high-poly bake meshes
        if mode == 'HI':
            newObjs = []

            groups = utils.findGroups(objs)
            for group in groups:
                orgGroup = bpy.data.objects.new('empty', None)
                bpy.context.scene.collection.objects.link(orgGroup)
                orgGroup.empty_display_size = 2
                orgGroup.empty_display_type = 'PLAIN_AXES'   
                orgGroup.location = group.location
                orgGroup.name = group.name + '_org'
                orgGroup.hide_viewport = True
                sxglobals.sourceObjects.append(orgGroup)
                sxglobals.exportObjects.append(group)

            for obj in objs:
                sxglobals.sourceObjects.append(obj)
                newObj = obj.copy()
                newObj.data = obj.data.copy()

                orgObjNames[obj] = [obj.name, obj.data.name][:]
                obj.data.name = obj.data.name + '_org'
                obj.name = obj.name + '_org'

                newObj.name = orgObjNames[obj][0]
                newObj.data.name = orgObjNames[obj][1]

                bpy.context.scene.collection.objects.link(newObj)
                newObjs.append(newObj)
                sxglobals.exportObjects.append(newObj)

                obj.parent = bpy.context.view_layer.objects[obj.parent.name + '_org']

            objs = newObjs

        bpy.context.view_layer.objects.active = objs[0]

        # Create modifiers
        tools.addModifiers(objs)

        # Begin category-specific compositing operations
        for obj in objs:
            if obj.sxtools.category == '':
                obj.sxtools.category == 'DEFAULT'

        for obj in bpy.context.view_layer.objects:
            if obj.type == 'MESH' and obj.hide_viewport == False:
                obj.hide_viewport = True

        # Mandatory to update visibility?
        viewlayer = bpy.context.view_layer
        viewlayer.update()

        # now = time.time()
        # print('hide objects duration: ', now-then, ' seconds')

        categoryList = list(sxglobals.categoryDict.keys())
        categories = list()
        for category in categoryList:
            categories.append(category.replace(" ", "_").upper())
        for category in categories:
            categoryObjs = []
            for obj in objs:
                if obj.sxtools.category == category:
                    categoryObjs.append(obj)

            if len(categoryObjs) > 0:
                for obj in categoryObjs:
                    if obj.parent == None:
                        obj.hide_viewport = False
                        bpy.context.view_layer.objects.active = obj
                        tools.groupObjects([obj, ])
                    obj.hide_viewport = True

                groupList = utils.findGroups(categoryObjs)

                for group in groupList:
                    groupObjs = utils.findChildren(group, categoryObjs)
                    bpy.context.view_layer.objects.active = groupObjs[0]
                    for obj in groupObjs:
                        obj.hide_viewport = False
                        obj.select_set(True)

                    if category == 'DEFAULT':
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processDefault(groupObjs)
                    elif category == 'PALETTED':
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processPaletted(groupObjs)
                    elif category == 'VEHICLES':
                        for obj in groupObjs:
                            if 'wheel' in obj.name:
                                scene.occlusionblend = 0.0
                            else:
                                scene.occlusionblend = 0.5
                            if obj.name.endswith('_roof') or obj.name.endswith('_frame') or obj.name.endswith('_dash') or obj.name.endswith('_hood') or ('bumper' in obj.name):
                                obj.modifiers['sxDecimate2'].use_symmetry = True
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processVehicles(groupObjs)
                    elif category == 'BUILDINGS':
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processBuildings(groupObjs)
                    elif category == 'TREES':
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processTrees(groupObjs)
                    elif category == 'TRANSPARENT':
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processDefault(groupObjs)
                    else:
                        if mode == 'HI':
                            tools.applyModifiers(groupObjs)
                        self.processDefault(groupObjs)

                    for obj in groupObjs:
                        obj.select_set(False)
                        obj.hide_viewport = True

                now = time.time()
                print('SX Tools: ', category, ' / ', len(groupList), ' groups duration: ', now-then, ' seconds')

        for obj in bpy.context.view_layer.objects:
            if (mode == 'HI') and ('_org' in obj.name):
                obj.hide_viewport = True
            elif obj.type == 'MESH':
                obj.hide_viewport = False

        for obj in objs:
            obj.select_set(True)

        # Create palette masks
        layers.generateMasks(objs)
        layers.flattenAlphas(objs)

        # now = time.time()
        # print('masks and alphas duration: ', now-then, ' seconds')

        if mode == 'HI':
            for obj in objs:
                obj.modifiers.new(type='WEIGHTED_NORMAL', name='sxWeightedNormal')
                obj.modifiers['sxWeightedNormal'].mode = 'FACE_AREA_WITH_ANGLE'
                obj.modifiers['sxWeightedNormal'].weight = 95
                obj.modifiers['sxWeightedNormal'].keep_sharp = True

            # self.applyModifiers(objs)

        now = time.time()
        print('SX Tools: Mesh processing duration: ', now-then, ' seconds')


    def processDefault(self, objs):
        print('SX Tools: Processing Default')
        then = time.time()

        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        inverse = False

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        rampmode = 'OCC'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = True
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200

        mergebbx = scene.rampbbox
        overwrite = True
        # obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        now = time.time()
        print('Occlusion duration: ', now-then, ' seconds')

        # bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        # bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        # obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        now = time.time()
        print('Overlay duration: ', now-then, ' seconds')

        # Clear metallic, smoothness, and transmission
        layers.clearUVs(objs, obj.sxlayers['metallic'])
        layers.clearUVs(objs, obj.sxlayers['smoothness'])
        layers.clearUVs(objs, obj.sxlayers['transmission'])

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.findLayerFromIndex(obj, 4)
        layer5 = utils.findLayerFromIndex(obj, 5)
        sxlayers = [layer4, layer5]
        tools.selectMask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.1, 0.1, 0.1, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        now = time.time()
        print('Smoothness duration: ', now-then, ' seconds')

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.01
        mono = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])

        now = time.time()
        print('Detail duration: ', now-then, ' seconds')


    def processPaletted(self, objs):
        print('SX Tools: Processing Paletted')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        inverse = False

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        rampmode = 'OCC'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = True
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200

        mergebbx = scene.rampbbox
        overwrite = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clearUVs(objs, obj.sxlayers['metallic'])
        layers.clearUVs(objs, obj.sxlayers['smoothness'])
        layers.clearUVs(objs, obj.sxlayers['transmission'])

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.findLayerFromIndex(obj, 4)
        layer5 = utils.findLayerFromIndex(obj, 5)
        sxlayers = [layer4, layer5]
        tools.selectMask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.1, 0.1, 0.1, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.01
        mono = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])


    def processVehicles(self, objs):
        print('SX Tools: Processing Vehicles')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        inverse = False

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        rampmode = 'OCC'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = True
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200
        scene.occlusionbias = 0.01

        mergebbx = scene.rampbbox
        overwrite = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clearUVs(objs, obj.sxlayers['metallic'])
        layers.clearUVs(objs, obj.sxlayers['smoothness'])
        layers.clearUVs(objs, obj.sxlayers['transmission'])

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.findLayerFromIndex(obj, 4)
        layer5 = utils.findLayerFromIndex(obj, 5)
        sxlayers = [layer4, layer5]
        tools.selectMask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.01
        mono = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])

        # Combine previous mix with directional dust
        layer = obj.sxlayers['composite']
        rampmode = 'DIR'
        scene.ramplist = 'DIRECTIONALDUST'
        scene.angle = 0.0
        scene.inclination = 40.0
        noise = 0.01
        mono = True

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Apply PBR metal based on layer7
        layer = utils.findLayerFromIndex(obj, 7)
        overwrite = True
        material = 'Iron'
        noise = 0.01
        mono = True

        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        tools.applyColor(objs, layer, palette[0], False, noise, mono)
        tools.applyColor(objs, obj.sxlayers['metallic'], palette[1], overwrite, noise, mono, layer)
        tools.applyColor(objs, obj.sxlayers['smoothness'], palette[2], overwrite, noise, mono, layer)

        # Mix metallic with occlusion (dirt in crevices)
        tools.layerCopyManager(objs, obj.sxlayers['occlusion'], obj.sxlayers['composite'])
        for obj in objs:
            obj.sxlayers['metallic'].alpha = 1.0
            obj.sxlayers['metallic'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['metallic'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['metallic'])
        for obj in objs:
            obj.sxlayers['metallic'].blendMode = 'ALPHA'

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        layer = obj.sxlayers['emission']
        tools.selectMask(objs, [layer, ], inverse)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def processBuildings(self, objs):
        print('SX Tools: Processing Buildings')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        inverse = False

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        rampmode = 'OCC'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = True
        scene.occlusionblend = 0.0
        scene.occlusionrays = 200
        scene.occlusionbias = 0.05

        mergebbx = scene.rampbbox
        overwrite = True
        obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = False

        obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Windows are not occluded
        color = (1.0, 1.0, 1.0, 1.0)
        maskLayer = utils.findLayerFromIndex(obj, 7)
        layer = obj.sxlayers['occlusion']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)
        color = (0.5, 0.5, 0.5, 0.5)
        layer = obj.sxlayers['overlay']
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Clear metallic, smoothness, and transmission
        layers.clearUVs(objs, obj.sxlayers['metallic'])
        layers.clearUVs(objs, obj.sxlayers['smoothness'])
        layers.clearUVs(objs, obj.sxlayers['transmission'])

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        obj.mode == 'OBJECT'
        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.findLayerFromIndex(obj, 4)
        layer5 = utils.findLayerFromIndex(obj, 5)
        sxlayers = [layer4, layer5]
        tools.selectMask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.1, 0.1, 0.1, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.0
        mono = True

        obj.mode == 'OBJECT'

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])

        # Combine previous mix with directional dust
        layer = obj.sxlayers['composite']
        rampmode = 'DIR'
        scene.ramplist = 'DIRECTIONALDUST'
        scene.angle = 0.0
        scene.inclination = 40.0
        noise = 0.0
        mono = True

        obj.mode == 'OBJECT'

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Apply PBR glass based on layer7
        layer = utils.findLayerFromIndex(obj, 7)
        overwrite = True
        obj.mode == 'OBJECT'
        material = 'Silver'
        noise = 0.01
        mono = True

        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        tools.applyColor(objs, layer, palette[0], False, noise, mono)
        tools.applyColor(objs, obj.sxlayers['metallic'], palette[1], overwrite, noise, mono, layer)
        tools.applyColor(objs, obj.sxlayers['smoothness'], palette[2], overwrite, noise, mono, layer)

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        layer = obj.sxlayers['emission']
        tools.selectMask(objs, [layer, ], inverse)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def processTrees(self, objs):
        print('SX Tools: Processing Trees')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        inverse = False

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        rampmode = 'OCC'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.0
        mono = True
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200

        mergebbx = scene.rampbbox
        overwrite = True
        obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clearUVs(objs, obj.sxlayers['metallic'])
        layers.clearUVs(objs, obj.sxlayers['smoothness'])
        layers.clearUVs(objs, obj.sxlayers['transmission'])

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Apply thickness
        layer = obj.sxlayers['transmission']
        rampmode = 'THK'
        scene.ramplist = 'FOLIAGERAMP'
        noise = 0.0
        mono = True
        scene.occlusionrays = 500

        overwrite = True
        obj.mode == 'OBJECT'

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        obj.mode == 'OBJECT'
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.findLayerFromIndex(obj, 4)
        layer5 = utils.findLayerFromIndex(obj, 5)
        sxlayers = [layer4, layer5]
        tools.selectMask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.01
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Combine previous mix with directional dust
        layer = obj.sxlayers['composite']
        rampmode = 'DIR'
        scene.ramplist = 'DIRECTIONALDUST'
        scene.angle = 0.0
        scene.inclination = 90.0
        noise = 0.01
        mono = True

        obj.mode == 'OBJECT'

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blendLayers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layerCopyManager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Clear layer4-5 mask from transmission
        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.findLayerFromIndex(obj, 4)
        layer = obj.sxlayers['transmission']
        overwrite = True

        noise = 0.0
        mono = True
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)
        maskLayer = utils.findLayerFromIndex(obj, 5)
        tools.applyColor(objs, layer, color, overwrite, noise, mono, maskLayer)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def removeExports(self):
        objs = sxglobals.exportObjects
        # bpy.ops.object.delete({"selected_objects": objs})
        for obj in objs:
            if obj in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        sxglobals.exportObjects = []

        for obj in sxglobals.sourceObjects:
            if obj in bpy.data.objects:
                if obj.name.endswith('_org'):
                    obj.name = obj.name[:-4]
                if obj.data and obj.data.name.endswith('_org'):
                    obj.data.name = obj.data.name[:-4]
                obj.hide_viewport = False

        sxglobals.sourceObjects = []


    def __del__(self):
        print('SX Tools: Exiting exports')


# ------------------------------------------------------------------------
#    Core Functions
# ------------------------------------------------------------------------
def updateLayers(self, context):
    if 'SXMaterial' not in bpy.data.materials.keys():
        setup.createSXMaterial()

    if not sxglobals.refreshInProgress:
        shadingMode(self, context)
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            alphaVal = getattr(objs[0].sxtools, 'activeLayerAlpha')
            blendVal = getattr(objs[0].sxtools, 'activeLayerBlendMode')
            visVal = getattr(objs[0].sxtools, 'activeLayerVisibility')

            for obj in objs:
                setattr(obj.sxlayers[idx], 'alpha', alphaVal)
                setattr(obj.sxlayers[idx], 'blendMode', blendVal)
                setattr(obj.sxlayers[idx], 'visibility', visVal)

                sxglobals.refreshInProgress = True
                setattr(obj.sxtools, 'selectedlayer', idx)
                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)

                sxglobals.refreshInProgress = False

            # setup.setupGeometry(objs)
            sxglobals.composite = True
            layers.compositeLayers(objs)


def refreshActives(self, context):
    if not sxglobals.refreshInProgress:
        sxglobals.refreshInProgress = True

        mode = context.scene.sxtools.shadingmode
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)
            vcols = layer.vertexColorLayer

            for obj in objs:
                setattr(obj.sxtools, 'selectedlayer', idx)
                if vcols != '':
                    obj.data.vertex_colors.active = obj.data.vertex_colors[vcols]
                alphaVal = getattr(obj.sxlayers[idx], 'alpha')
                blendVal = getattr(obj.sxlayers[idx], 'blendMode')
                visVal = getattr(obj.sxlayers[idx], 'visibility')

                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)

            # Update VertexColor0 to reflect latest layer changes
            if mode != 'FULL':
                sxglobals.composite = True
            layers.compositeLayers(objs)
            sxglobals.refreshInProgress = False

            # Refresh SX Tools UI to latest selection
            layers.updateLayerPalette(objs, layer)
            layers.updateLayerBrightness(objs, layer)

            # Update SX Material to latest selection
            if objs[0].sxtools.category == 'TRANSPARENT':
                if bpy.data.materials['SXMaterial'].blend_method != 'BLEND':
                    bpy.data.materials['SXMaterial'].blend_method = 'BLEND'
                    bpy.data.materials['SXMaterial'].use_backface_culling = True
            else:
                if bpy.data.materials['SXMaterial'].blend_method != 'OPAQUE':
                    bpy.data.materials['SXMaterial'].blend_method = 'OPAQUE'
                    bpy.data.materials['SXMaterial'].use_backface_culling = False

        # Verify selectionMonitor is running
        if not sxglobals.modalStatus:
            setup.startModal()


# Clicking a palette color would ideally set it in fillcolor, TBD
def updateColorSwatches(self, context):
    pass


def shadingMode(self, context):
    mode = context.scene.sxtools.shadingmode
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        sxmaterial = bpy.data.materials['SXMaterial']

        occlusion = objs[0].sxlayers['occlusion'].enabled
        metallic = objs[0].sxlayers['metallic'].enabled
        smoothness = objs[0].sxlayers['smoothness'].enabled
        transmission = objs[0].sxlayers['transmission'].enabled
        emission = objs[0].sxlayers['emission'].enabled

        prefs = bpy.context.preferences
        materialsubsurface = prefs.addons['sxtools'].preferences.materialsubsurface
        materialtransmission = prefs.addons['sxtools'].preferences.materialtransmission

        if mode == 'FULL':
            if emission:
                context.scene.eevee.use_bloom = True
            areas = bpy.context.workspace.screens[0].areas
            shading = 'RENDERED'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
            for area in areas:
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if ((space.shading.type == 'WIREFRAME') or
                           (space.shading.type == 'SOLID')):
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

            if metallic:
                # Reconnect metallic and roughness
                output = sxmaterial.node_tree.nodes['MetallicXYZ'].outputs['X']
                input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Metallic']
                sxmaterial.node_tree.links.new(input, output)

            if smoothness:
                output = sxmaterial.node_tree.nodes['Invert'].outputs['Color']
                input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Roughness']
                sxmaterial.node_tree.links.new(input, output)

            if transmission:
                if materialtransmission:
                    # Reconnect transmission
                    output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['X']
                    input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Transmission']
                    sxmaterial.node_tree.links.new(input, output)

                if materialsubsurface:
                    output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['X']
                    input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Subsurface']
                    sxmaterial.node_tree.links.new(input, output)

            if emission:
                # Reconnect emission
                output = sxmaterial.node_tree.nodes['Mix.001'].outputs['Color']
                input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
                sxmaterial.node_tree.links.new(input, output)

                # Reconnect base mix
                output = sxmaterial.node_tree.nodes['Mix'].outputs['Color']
                input = sxmaterial.node_tree.nodes['Mix.001'].inputs['Color1']
                sxmaterial.node_tree.links.new(input, output)

        else:
            if emission:
                context.scene.eevee.use_bloom = False
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
            if sxglobals.prevMode == 'FULL':
                attrLink = sxmaterial.node_tree.nodes['Mix'].outputs[0].links[0]
                sxmaterial.node_tree.links.remove(attrLink)
                if metallic:
                    attrLink = sxmaterial.node_tree.nodes['MetallicXYZ'].outputs[0].links[0]
                    sxmaterial.node_tree.links.remove(attrLink)
                if smoothness:
                    attrLink = sxmaterial.node_tree.nodes['Invert'].outputs[0].links[0]
                    sxmaterial.node_tree.links.remove(attrLink)
                if transmission:
                    if materialtransmission and materialsubsurface:
                        attrLink = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs[0].links[1]
                        sxmaterial.node_tree.links.remove(attrLink)
                    if materialtransmission or materialsubsurface:
                        attrLink = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs[0].links[0]
                        sxmaterial.node_tree.links.remove(attrLink)

            # Connect vertex color source to emission
            output = sxmaterial.node_tree.nodes['Attribute'].outputs['Color']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
            sxmaterial.node_tree.links.new(input, output)

        sxglobals.prevMode = mode


def selectionValidator(self, context):
    selObjs = []
    for obj in context.view_layer.objects.selected:
        if obj.type == 'MESH' and obj.hide_viewport == False:
            selObjs.append(obj)
    return selObjs


def rampLister(self, context):
    items = sxglobals.rampDict.keys()
    enumItems = []
    for item in items:
        sxglobals.presetLookup[item.replace(" ", "_").upper()] = item
        enumItem = (item.replace(" ", "_").upper(), item, '')
        enumItems.append(enumItem)
    return enumItems


def categoryLister(self, context):
    items = sxglobals.categoryDict.keys()
    enumItems = []
    for item in items:
        sxglobals.presetLookup[item.replace(" ", "_").upper()] = item
        enumItem = (item.replace(" ", "_").upper(), item, '')
        enumItems.append(enumItem)
    return enumItems


def loadCategory(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        categoryData = sxglobals.categoryDict[sxglobals.presetLookup[objs[0].sxtools.category]]
        for i in range(7):
            layer = utils.findLayerFromIndex(objs[0], i+1)
            layer.name = categoryData[i]

        for obj in objs:
            if obj.sxtools.category != objs[0].sxtools.category:
                obj.sxtools.category = objs[0].sxtools.category
                for i in range(7):
                    layer = utils.findLayerFromIndex(obj, i+1)
                    layer.name = categoryData[i]

            obj.sxtools.staticvertexcolors = bool(categoryData[7])
            obj.sxtools.smoothness1 = categoryData[8]
            obj.sxtools.smoothness2 = categoryData[9]
            obj.sxtools.overlaystrength = categoryData[10]

        bpy.data.materials['SXMaterial'].blend_method = categoryData[11]
        if categoryData[11] == 'BLEND':
            bpy.data.materials['SXMaterial'].use_backface_culling = True
        else:
            bpy.data.materials['SXMaterial'].use_backface_culling = False


def loadRamp(self, context):
    rampName = sxglobals.presetLookup[context.scene.sxtools.ramplist]
    ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'].color_ramp
    tempDict = sxglobals.rampDict[rampName]

    ramp.color_mode = tempDict['mode']
    ramp.interpolation = tempDict['interpolation']
    ramp.hue_interpolation = tempDict['hue_interpolation']

    rampLength = len(ramp.elements)
    for i in range(rampLength-1):
        ramp.elements.remove(ramp.elements[0])

    for i, tempElement in enumerate(tempDict['elements']):
        if i == 0:
            ramp.elements[0].position = tempElement[0]
            ramp.elements[0].color = [tempElement[1][0], tempElement[1][1], tempElement[1][2], tempElement[1][3]]
        else:
            newElement = ramp.elements.new(tempElement[0])
            newElement.color = [tempElement[1][0], tempElement[1][1], tempElement[1][2], tempElement[1][3]]


def loadLibraries(self, context):
    status1 = files.loadFile('palettes')
    status2 = files.loadFile('materials')
    status3 = files.loadFile('gradients')
    status4 = files.loadFile('categories')

    if status1 and status2 and status3 and status4:
        messageBox('Libraries loaded successfully')
        sxglobals.librariesLoaded = True


def adjustBrightness(self, context):
    if not sxglobals.brightnessUpdate:
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)

            tools.applyBrightness(objs, layer, context.scene.sxtools.brightnessvalue)

            sxglobals.composite = True
            refreshActives(self, context)


def updateModifierVisibility(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        vis = objs[0].sxtools.modifiervisibility
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if obj.sxtools.modifiervisibility != vis:
                obj.sxtools.modifiervisibility = vis

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            if 'sxSubdivision' in obj.modifiers.keys():
                obj.modifiers['sxSubdivision'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxDecimate' in obj.modifiers.keys():
                if (obj.sxtools.subdivisionlevel == 0):
                    obj.modifiers['sxDecimate'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxDecimate2' in obj.modifiers.keys():
                if (obj.sxtools.subdivisionlevel == 0):
                    obj.modifiers['sxDecimate2'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate2'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxBevel' in obj.modifiers.keys():
                if hardmode == 'BEVEL' and obj.sxtools.modifiervisibility:
                    obj.modifiers['sxBevel'].show_viewport = True
                else:
                    obj.modifiers['sxBevel'].show_viewport = False
            if 'sxWeightedNormal' in obj.modifiers.keys():
                obj.modifiers['sxWeightedNormal'].show_viewport = obj.sxtools.modifiervisibility

        bpy.ops.object.mode_set(mode=mode)


def updateCreaseModifiers(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if obj.sxtools.hardmode != hardmode:
                obj.sxtools.hardmode = hardmode

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            if 'sxWeightedNormal' in obj.modifiers.keys():
                if hardmode == 'SMOOTH':
                    obj.modifiers['sxWeightedNormal'].keep_sharp = False
                else:
                    obj.modifiers['sxWeightedNormal'].keep_sharp = True

        bpy.ops.object.mode_set(mode=mode)


def updateSubdivisionModifier(self, context):
    scene = context.scene.sxtools
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        vis = objs[0].sxtools.modifiervisibility
        hardmode = objs[0].sxtools.hardmode
        subdivLevel = objs[0].sxtools.subdivisionlevel
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if obj.sxtools.modifiervisibility != vis:
                obj.sxtools.modifiervisibility = vis
            if obj.sxtools.hardmode != hardmode:
                obj.sxtools.hardmode = hardmode
            if obj.sxtools.subdivisionlevel != subdivLevel:
                obj.sxtools.subdivisionlevel = subdivLevel

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            if 'sxSubdivision' in obj.modifiers.keys():
                obj.modifiers['sxSubdivision'].levels = obj.sxtools.subdivisionlevel
            if 'sxDecimate' in obj.modifiers.keys():
                if obj.sxtools.subdivisionlevel == 0:
                    obj.modifiers['sxDecimate'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxDecimate2' in obj.modifiers.keys():
                if obj.sxtools.subdivisionlevel == 0:
                    obj.modifiers['sxDecimate2'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate2'].show_viewport = obj.sxtools.modifiervisibility

        bpy.ops.object.mode_set(mode=mode)


def updateBevelModifier(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        bevelWidth = objs[0].sxtools.bevelwidth
        bevelSegments = objs[0].sxtools.bevelsegments
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if obj.sxtools.bevelwidth != bevelWidth:
                obj.sxtools.bevelwidth = bevelWidth
            if obj.sxtools.bevelsegments != bevelSegments:
                obj.sxtools.bevelsegments = bevelSegments

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            if 'sxBevel' in obj.modifiers.keys():
                obj.modifiers['sxBevel'].width = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].width_pct = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].segments = obj.sxtools.bevelsegments

        bpy.ops.object.mode_set(mode=mode)


def updateDecimateModifier(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        decimation = objs[0].sxtools.decimation
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = 3.14159
            if obj.sxtools.decimation != decimation:
                obj.sxtools.decimation = decimation

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in objs:
            if 'sxDecimate' in obj.modifiers.keys():
                obj.modifiers['sxDecimate'].angle_limit = decimation * (math.pi/180.0)

        bpy.ops.object.mode_set(mode=mode)


def updateCustomProps(self, context):
    objs = selectionValidator(self, context)
    if len(objs) > 0:
        stc = objs[0].sxtools.staticvertexcolors
        sm1 = objs[0].sxtools.smoothness1
        sm2 = objs[0].sxtools.smoothness2
        ovr = objs[0].sxtools.overlaystrength
        for obj in objs:
            obj['staticVertexColors'] = stc
            if obj.sxtools.staticvertexcolors != stc:
                obj.sxtools.staticvertexcolors = stc
            if obj.sxtools.smoothness1 != sm1:
                obj.sxtools.smoothness1 = sm1
            if obj.sxtools.smoothness2 != sm2:
                obj.sxtools.smoothness2 = sm2
            if obj.sxtools.overlaystrength != ovr:
                obj.sxtools.overlaystrength = ovr


def messageBox(message='', title='SX Tools', icon='INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


@persistent
def load_post_handler(dummy):
    sxglobals.prevMode = 'FULL'
    sxglobals.librariesLoaded = False
    sxglobals.exportObjects = []
    sxglobals.sourceObjects = []
    setup.startModal()


# ------------------------------------------------------------------------
#    Settings and preferences
# ------------------------------------------------------------------------
class SXTOOLS_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    libraryfolder: bpy.props.StringProperty(
        name='Library Folder',
        description='Folder containing Materials and Palettes files',
        default='',
        maxlen=1024,
        subtype='DIR_PATH',
        update=loadLibraries)

    materialsubsurface: bpy.props.BoolProperty(
        name='Subsurface Scattering',
        description='Connect Transmission Layer to SXMaterial Subsurface Scattering',
        default=False)

    materialtransmission: bpy.props.BoolProperty(
        name='Transmission',
        description='Connect Transmission Layer to SXMaterial Transmission',
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.label(text='Material Preferences')
        layout.prop(self, 'materialsubsurface')
        layout.prop(self, 'materialtransmission')
        layout.separator()
        layout.label(text='Select the folder containing SX Tools data files (materials.json, palettes.json, gradients.json)')
        layout.prop(self, 'libraryfolder')


class SXTOOLS_objectprops(bpy.types.PropertyGroup):
    category: bpy.props.EnumProperty(
        name='Category Presets',
        description='Select object category\nRenames layers to match',
        items=categoryLister,
        update=loadCategory)

    selectedlayer: bpy.props.IntProperty(
        name='Selected Layer',
        min=0,
        max=20,
        default=1,
        update=refreshActives)

    activeLayerAlpha: bpy.props.FloatProperty(
        name='Opacity',
        min=0.0,
        max=1.0,
        default=1.0,
        update=updateLayers)

    activeLayerBlendMode: bpy.props.EnumProperty(
        name='Blend Mode',
        items=[
            ('ALPHA', 'Alpha', ''),
            ('ADD', 'Additive', ''),
            ('MUL', 'Multiply', ''),
            ('OVR', 'Overlay', '')],
        default='ALPHA',
        update=updateLayers)

    activeLayerVisibility: bpy.props.BoolProperty(
        name='Visibility',
        default=True,
        update=updateLayers)

    modifiervisibility: bpy.props.BoolProperty(
        name='Modifier Visibility',
        default=True,
        update=updateModifierVisibility)

    hardmode: bpy.props.EnumProperty(
        name='Max Crease Mode',
        description='Mode for processing edges with maximum crease',
        items=[
            ('SMOOTH', 'Smooth', ''),
            ('SHARP', 'Sharp', ''),
            ('BEVEL', 'Beveled', '')],
        default='BEVEL',
        update=updateCreaseModifiers)

    subdivisionlevel: bpy.props.IntProperty(
        name='Subdivision Level',
        min=0,
        max=6,
        default=1,
        update=updateSubdivisionModifier)

    bevelwidth: bpy.props.FloatProperty(
        name='Bevel Width',
        min=0.0,
        max=100.0,
        default=0.05,
        update=updateBevelModifier)

    bevelsegments: bpy.props.IntProperty(
        name='Bevel Segments',
        min=1,
        max=10,
        default=2,
        update=updateBevelModifier)

    decimation: bpy.props.FloatProperty(
        name='Decimation',
        min=0.0,
        max=10.0,
        default=0.5,
        update=updateDecimateModifier)

    staticvertexcolors: bpy.props.BoolProperty(
        name='Static Vertex Colors Export Flag',
        description='Disable to use dynamic palettes in a game engine\nWhen paletted, overlays are not composited to VertexColor0',
        default=True,
        update=updateCustomProps)

    smoothness1: bpy.props.FloatProperty(
        name='Layer 1-3 Base Smoothness',
        min=0.0,
        max=1.0,
        default=0.0,
        update=updateCustomProps)

    smoothness2: bpy.props.FloatProperty(
        name='Layer 4-5 Base Smoothness',
        min=0.0,
        max=1.0,
        default=0.0,
        update=updateCustomProps)

    overlaystrength: bpy.props.FloatProperty(
        name='RGBA Overlay Strength',
        min=0.0,
        max=1.0,
        default=0.5,
        update=updateCustomProps)


class SXTOOLS_sceneprops(bpy.types.PropertyGroup):
    numlayers: bpy.props.IntProperty(
        name='Vertex Color Layer Count',
        description='The number of vertex color layers to use in the scene',
        min=0,
        max=7,
        default=7)

    numalphas: bpy.props.IntProperty(
        name='Alpha Overlay Layer Count',
        description='The number of UV alpha overlays to use\nOnly useful with a game engine with a limited number of vertex color layers',
        min=0,
        max=2,
        default=2)

    numoverlays: bpy.props.IntProperty(
        name='RGBA Overlay Layer Count',
        description='The number of UV RGBA overlays to use\nOnly useful with a game engine with limited number of vertex color layers',
        min=0,
        max=1,
        default=1)

    enableocclusion: bpy.props.BoolProperty(
        name='Enable Occlusion',
        description='Use per-vertex ambient occlusion',
        default=True)

    enablemetallic: bpy.props.BoolProperty(
        name='Enable Metallic',
        description='Use per-vertex metallic channel values',
        default=True)

    enablesmoothness: bpy.props.BoolProperty(
        name='Enable Smoothness',
        description='Use per-vertex smoothness channel values',
        default=True)

    enabletransmission: bpy.props.BoolProperty(
        name='Enable Transmission',
        description='Use per-vertex transmission or subsurface scattering',
        default=True)

    enableemission: bpy.props.BoolProperty(
        name='Enable Emission',
        description='Use per-vertex emission values',
        default=True)

    eraseuvs: bpy.props.BoolProperty(
        name='Erase Existing UV Sets',
        description='Remove all UV Sets from objects and replace with new ones',
        default=True)

    shadingmode: bpy.props.EnumProperty(
        name='Shading Mode',
        description='Full: Composited shading with all channels enabled\nDebug: Display selected layer only, with alpha as black\nAlpha: Display layer alpha or UV values in grayscale',
        items=[
            ('FULL', 'Full', ''),
            ('DEBUG', 'Debug', ''),
            ('ALPHA', 'Alpha', '')],
        default='FULL',
        update=updateLayers)

    layerpalette1: bpy.props.FloatVectorProperty(
        name='Layer Palette 1',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette2: bpy.props.FloatVectorProperty(
        name='Layer Palette 2',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette3: bpy.props.FloatVectorProperty(
        name='Layer Palette 3',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette4: bpy.props.FloatVectorProperty(
        name='Layer Palette 4',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette5: bpy.props.FloatVectorProperty(
        name='Layer Palette 5',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette6: bpy.props.FloatVectorProperty(
        name='Layer Palette 6',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))
    layerpalette7: bpy.props.FloatVectorProperty(
        name='Layer Palette 7',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette8: bpy.props.FloatVectorProperty(
        name='Layer Palette 8',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    brightnessvalue: bpy.props.FloatProperty(
        name='Brightness',
        description='The mean brightness of the selection',
        min=0.0,
        max=1.0,
        default=0.0,
        update=adjustBrightness)

    toolmode: bpy.props.EnumProperty(
        name='Tool Mode',
        description='Display color or gradient fill tool',
        items=[
            ('COL', 'Color', ''),
            ('GRD', 'Gradient', '')],
        default='COL')

    fillpalette1: bpy.props.FloatVectorProperty(
        name='Recent Color 1',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette2: bpy.props.FloatVectorProperty(
        name='Recent Color 2',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette3: bpy.props.FloatVectorProperty(
        name='Recent Color 3',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette4: bpy.props.FloatVectorProperty(
        name='Recent Color 4',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette5: bpy.props.FloatVectorProperty(
        name='Recent Color 5',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette6: bpy.props.FloatVectorProperty(
        name='Recent Color 6',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette7: bpy.props.FloatVectorProperty(
        name='Recent Color 7',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette8: bpy.props.FloatVectorProperty(
        name='Recent Color 8',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillcolor: bpy.props.FloatVectorProperty(
        name='Fill Color',
        description='This color is applied tools\nthe selected objects or components',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    fillalpha: bpy.props.BoolProperty(
        name='Overwrite Alpha',
        description='Check to flood fill the entire selection\nUncheck to retain current alpha mask',
        default=True)

    fillnoise: bpy.props.FloatProperty(
        name='Noise',
        description='Random per-vertex noise',
        min=0.0,
        max=1.0,
        default=0.0)

    fillmono: bpy.props.BoolProperty(
        name='Monochrome',
        description='Uncheck to randomize all noise channels separately',
        default=False)

    rampmode: bpy.props.EnumProperty(
        name='Ramp Mode',
        description='X/Y/Z: Axis-aligned gradient\nDirectional: Angle and inclination vs. surface normal\nLuminance: Brightness-based tone-map\nCurvature: Apply gradient according to how convex/concave the surface is\nNormalized Curvature: As above, but better range for artists\nAmbient Occlusion: A simple AO baking mode\nThickness: Useful for driving transmission or subsurface scattering',
        items=[
            ('X', 'X-Axis', ''),
            ('Y', 'Y-Axis', ''),
            ('Z', 'Z-Axis', ''),
            ('DIR', 'Directional', ''),
            ('LUM', 'Luminance', ''),
            ('C', 'Curvature', ''),
            ('CN', 'Normalized Curvature', ''),
            ('OCC', 'Ambient Occlusion', ''),
            ('THK', 'Thickness', '')],
        default='X')

    rampbbox: bpy.props.BoolProperty(
        name='Global Bbox',
        description='Use the combined bounding volume of\nall selected objects or components.',
        default=True)

    rampalpha: bpy.props.BoolProperty(
        name='Overwrite Alpha',
        description='Check to flood fill entire selection\nUncheck to retain current alpha mask',
        default=True)

    rampnoise: bpy.props.FloatProperty(
        name='Noise',
        description='Random per-vertex noise',
        min=0.0,
        max=1.0,
        default=0.0)

    rampmono: bpy.props.BoolProperty(
        name='Monochrome',
        description='Uncheck to randomize all noise channels separately',
        default=False)

    ramplist: bpy.props.EnumProperty(
        name='Ramp Presets',
        description='Load stored ramp presets',
        items=rampLister,
        update=loadRamp)

    mergemode: bpy.props.EnumProperty(
        name='Merge Mode',
        items=[
            ('UP', 'Up', ''),
            ('DOWN', 'Down', '')],
        default='UP')

    occlusionblend: bpy.props.FloatProperty(
        name='Occlusion Blend',
        description='Blend between self-occlusion and\nthe contribution of all objects in the scene',
        min=0.0,
        max=1.0,
        default=0.5)

    occlusionrays: bpy.props.IntProperty(
        name='Ray Count',
        description='Increase ray count to reduce noise',
        min=1,
        max=2000,
        default=256)

    occlusiondistance: bpy.props.FloatProperty(
        name='Ray Distance',
        description='How far a ray can travel without\nhitting anything before being a miss',
        min=0.0,
        max=100.0,
        default=10.0)

    occlusionbias: bpy.props.FloatProperty(
        name='Bias',
        description='Offset ray start position to prevent artifacts',
        min=0.0,
        max=1.0,
        default=0.01)

    occlusiongroundplane: bpy.props.BoolProperty(
        name='Ground Plane',
        description='Enable temporary ground plane for occlusion',
        default=True)

    dirInclination: bpy.props.FloatProperty(
        name='Inclination',
        min=-90.0,
        max=90.0,
        default=0.0)

    dirAngle: bpy.props.FloatProperty(
        name='Angle',
        min=-360.0,
        max=360.0,
        default=0.0)

    palettenoise: bpy.props.FloatProperty(
        name='Noise',
        description='Random per-vertex noise',
        min=0.0,
        max=1.0,
        default=0.0)

    palettemono: bpy.props.BoolProperty(
        name='Monochrome',
        description='Uncheck to randomize all noise channels separately',
        default=False)

    materialalpha: bpy.props.BoolProperty(
        name='Overwrite Alpha',
        description='Check to flood fill entire selection\nUncheck to retain current alpha mask',
        default=True)

    materialnoise: bpy.props.FloatProperty(
        name='Noise',
        description='Random per-vertex noise',
        min=0.0,
        max=1.0,
        default=0.0)

    materialmono: bpy.props.BoolProperty(
        name='Monochrome',
        description='Uncheck to randomize all noise channels separately',
        default=False)

    creasemode: bpy.props.EnumProperty(
        name='Creasing Mode',
        description='Display creasing tools or modifier settings',
        items=[
            ('CRS', 'Creasing', ''),
            ('SDS', 'Modifiers', '')],
        default='CRS')

    expandfill: bpy.props.BoolProperty(
        name='Expand Fill',
        default=False)

    expandcrease: bpy.props.BoolProperty(
        name='Expand Crease',
        default=False)

    expandexport: bpy.props.BoolProperty(
        name='Expand Export',
        default=False)

    palettemode: bpy.props.EnumProperty(
        name='Palette Mode',
        description='Display palettes or PBR materials',
        items=[
            ('PAL', 'Palettes', ''),
            ('MAT', 'Materials', '')],
        default='PAL')

    expandpalette: bpy.props.BoolProperty(
        name='Expand Palette',
        default=False)

    exportmode: bpy.props.EnumProperty(
        name='Export Mode',
        description='Display utils or export settings',
        items=[
            ('UTILS', 'Utilities', ''),
            ('EXPORT', 'Export', '')],
        default='UTILS')

    exportquality: bpy.props.EnumProperty(
        name='Export Quality',
        description='Low-detail mode uses base mesh for baking\nHigh-detail mode bakes after applying modifiers but disables decimation',
        items=[
            ('LO', 'Low-detail', ''),
            ('HI', 'High-detail', '')],
        default='LO')

    exportfolder: bpy.props.StringProperty(
        name='Export Folder',
        description='Folder to export FBX files to',
        default='',
        maxlen=1024,
        subtype='DIR_PATH')


class SXTOOLS_masterpalette(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty(
        name='Category',
        description='Palette Category',
        default='')

    color0: bpy.props.FloatVectorProperty(
        name='Palette Color 0',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name='Palette Color 1',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name='Palette Color 2',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color3: bpy.props.FloatVectorProperty(
        name='Palette Color 3',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color4: bpy.props.FloatVectorProperty(
        name='Palette Color 4',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))


class SXTOOLS_material(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty(
        name='Category',
        description='Material Category',
        default='')

    color0: bpy.props.FloatVectorProperty(
        name='Material Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name='Material Metallic',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name='Material Smoothness',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))


class SXTOOLS_layer(bpy.types.PropertyGroup):
    # name: from PropertyGroup

    index: bpy.props.IntProperty(
        name='Layer Index',
        min=0,
        max=100,
        default=0)

    layerType: bpy.props.EnumProperty(
        name='Layer Type',
        items=[
            ('COLOR', 'Color', ''),
            ('UV', 'UV', ''),
            ('UV4', 'UV4', '')],
        default='COLOR')

    defaultColor: bpy.props.FloatVectorProperty(
        name='Default Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.0))

    defaultValue: bpy.props.FloatProperty(
        name='Default Value',
        min=0.0,
        max=1.0,
        default=0.0)

    visibility: bpy.props.BoolProperty(
        name='Layer Visibility',
        default=True)

    alpha: bpy.props.FloatProperty(
        name='Layer Alpha',
        min=0.0,
        max=1.0,
        default=1.0)

    blendMode: bpy.props.EnumProperty(
        name='Layer Blend Mode',
        items=[
            ('ALPHA', 'Alpha', ''),
            ('ADD', 'Additive', ''),
            ('MUL', 'Multiply', ''),
            ('OVR', 'Overlay', '')],
        default='ALPHA')

    vertexColorLayer: bpy.props.StringProperty(
        name='Vertex Color Layer',
        description='Maps a list item to a vertex color layer',
        default='')

    uvLayer0: bpy.props.StringProperty(
        name='UV Map',
        description='Maps a list item to a UV set',
        default='')

    uvChannel0: bpy.props.EnumProperty(
        name='UV Channel',
        items=[
            ('U', 'U', ''),
            ('V', 'V', '')],
        default='U')

    uvLayer1: bpy.props.StringProperty(
        name='UV Map',
        description='Maps a list item to a UV set',
        default='')

    uvChannel1: bpy.props.EnumProperty(
        name='UV Channel',
        items=[
            ('U', 'U', ''),
            ('V', 'V', '')],
        default='U')

    uvLayer2: bpy.props.StringProperty(
        name='UV Map',
        description='Maps a list item to a UV set',
        default='')

    uvChannel2: bpy.props.EnumProperty(
        name='UV Channel',
        items=[
            ('U', 'U', ''),
            ('V', 'V', '')],
        default='U')

    uvLayer3: bpy.props.StringProperty(
        name='UV Map',
        description='Maps a list item to a UV set',
        default='')

    uvChannel3: bpy.props.EnumProperty(
        name='UV Channel',
        items=[
            ('U', 'U', ''),
            ('V', 'V', '')],
        default='U')

    enabled: bpy.props.BoolProperty(
        name='Enabled',
        default=False)


class SXTOOLS_rampcolor(bpy.types.PropertyGroup):
    # name: from PropertyGroup

    index: bpy.props.IntProperty(
        name='Element Index',
        min=0,
        max=100,
        default=0)

    position: bpy.props.FloatProperty(
        name='Element Position',
        min=0.0,
        max=1.0,
        default=0.0)    

    color: bpy.props.FloatVectorProperty(
        name='Element Color',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))


# ------------------------------------------------------------------------
#    UI Panel and Operators
# ------------------------------------------------------------------------
class SXTOOLS_PT_panel(bpy.types.Panel):

    bl_idname = 'SXTOOLS_PT_panel'
    bl_label = 'SX Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


    def draw(self, context):
        objs = selectionValidator(self, context)
        if (len(objs) > 0) and (len(objs[0].sxtools.category) > 0) and sxglobals.librariesLoaded:
            obj = objs[0]

            layout = self.layout
            mesh = obj.data
            mode = obj.mode
            sxtools = obj.sxtools
            scene = context.scene.sxtools
            palettes = context.scene.sxpalettes
            
            if len(obj.sxlayers) == 0:
                col = self.layout.column(align=True)
                col.label(text='Set Scene Configuration:')
                col.prop(scene, 'numlayers', text='Vertex Color Layers')
                col.prop(scene, 'numalphas', text='Alpha Overlays (UV)')
                col.prop(scene, 'numoverlays', text='RGBA Overlays (UV)')
                col.prop(scene, 'enableocclusion', text='Ambient Occlusion (UV)')
                col.prop(scene, 'enablemetallic', text='Metallic (UV)')
                col.prop(scene, 'enablesmoothness', text='Smoothness (UV)')
                col.prop(scene, 'enabletransmission', text='Transmission (UV)')
                col.prop(scene, 'enableemission', text='Emission (UV)')
                col.separator()
                col.prop(scene, 'eraseuvs', text='Erase Existing UV Sets')
                if 'SXMaterial' in bpy.data.materials.keys():
                    col.enabled = False
                col2 = self.layout.column(align=True)
                if (len(objs) == 1):
                    col2.operator('sxtools.scenesetup', text='Set Up Object')
                else:
                    col2.operator('sxtools.scenesetup', text='Set Up Objects')
            else:
                sel_idx = objs[0].sxtools.selectedlayer
                layer = utils.findLayerFromIndex(obj, sel_idx)
                if layer is None:
                    sel_idx = 1
                    layer = utils.findLayerFromIndex(obj, sel_idx)
                    messageBox('Invalid layer selected!', 'SX Tools Error', 'ERROR')
                    # print('SX Tools: Error, invalid layer selected!')

                row = layout.row(align=True)
                row.prop(sxtools, 'category', text='Category')

                row_shading = self.layout.row(align=True)
                row_shading.prop(scene, 'shadingmode', expand=True)

                row_blend = self.layout.row(align=True)
                row_blend.prop(sxtools, 'activeLayerVisibility')
                row_blend.prop(sxtools, 'activeLayerBlendMode', text='Blend')
                row_alpha = self.layout.row(align=True)
                row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text='Layer Opacity')

                row_palette = self.layout.row(align=True)
                for i in range(8):
                    row_palette.prop(scene, 'layerpalette' + str(i+1), text='')

                if ((layer.name == 'occlusion') or
                   (layer.name == 'smoothness') or
                   (layer.name == 'metallic') or
                   (layer.name == 'transmission') or
                   (layer.name == 'emission')):
                    row_blend.enabled = False
                    row_alpha.enabled = False

                layout.template_list('SXTOOLS_UL_layerlist', 'sxtools.layerlist', obj, 'sxlayers', sxtools, 'selectedlayer', type='DEFAULT')
                # layout.template_list('UI_UL_list', 'sxtools.layerlist', context.scene, 'sxlistitems', scene, 'listIndex', type='DEFAULT')
                # layout.template_list('UI_UL_list', 'sxtools.layerList', mesh, 'vertex_colors', sxtools, 'selectedlayer', type='DEFAULT')

                # Layer Copy Paste Merge ---------------------------------------
                row_misc1 = self.layout.row(align=True)
                row_misc1.operator('sxtools.mergeup')
                row_misc1.operator('sxtools.copylayer', text='Copy')
                row_misc1.operator('sxtools.clear', text='Clear')
                row_misc2 = self.layout.row(align=True)
                row_misc2.operator('sxtools.mergedown')
                row_misc2.operator('sxtools.pastelayer', text='Paste')
                row_misc2.operator('sxtools.selmask', text='Select Mask')

                col_misc = self.layout.row(align=True)
                if obj.mode == 'OBJECT':
                    col_misc.prop(scene, 'brightnessvalue', slider=True, text='Layer Brightness')
                else:
                    col_misc.prop(scene, 'brightnessvalue', slider=True, text='Selection Brightness')

                # Color Fill ---------------------------------------------------
                box_fill = layout.box()
                row_fill = box_fill.row()
                row_fill.prop(scene, 'expandfill',
                    icon='TRIA_DOWN' if scene.expandfill else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_fill.prop(scene, 'toolmode', expand=True)
                row2_fill = box_fill.row()
                split_fill = row2_fill.split(factor=0.33)
                split1_fill = split_fill.row()

                if scene.toolmode == 'COL':
                    split1_fill.label(text='Fill Color')
                    split2_fill = split_fill.row()
                    split2_fill.prop(scene, 'fillcolor', text='')
                    split2_fill.operator('sxtools.applycolor', text='Apply')

                    if scene.expandfill:
                        row_fpalette = box_fill.row(align=True)
                        for i in range(8):
                            row_fpalette.prop(scene, 'fillpalette' + str(i+1), text='')
                        col_color = box_fill.column(align=True)
                        col_color.prop(scene, 'fillnoise', slider=True)
                        col_color.prop(scene, 'fillmono', text='Monochromatic')
                        if mode == 'OBJECT':
                            col_color.prop(scene, 'fillalpha')

                # Gradient Tool ---------------------------------------------------
                elif scene.toolmode == 'GRD':
                    split1_fill.label(text='Fill Mode')
                    split2_fill = split_fill.row()
                    split2_fill.prop(scene, 'rampmode', text='')
                    split2_fill.operator('sxtools.applyramp', text='Apply')

                    if scene.expandfill:
                        row3_fill = box_fill.row(align=True)
                        row3_fill.prop(scene, 'ramplist', text='')
                        row3_fill.operator('sxtools.addramp', text='', icon='ADD')
                        row3_fill.operator('sxtools.delramp', text='', icon='REMOVE')
                        box_fill.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], 'color_ramp', expand=True)
                        box_fill.prop(scene, 'rampnoise', slider=True)
                        box_fill.prop(scene, 'rampmono', text='Monochromatic')
                        box_fill.prop(scene, 'rampbbox', text='Use Combined Bounding Box')

                        col_fill = box_fill.column(align=True)
                        if mode == 'OBJECT':
                            col_fill.prop(scene, 'rampalpha')
                        if scene.rampmode == 'DIR':
                            col_fill.prop(scene, 'dirInclination', slider=True, text='Inclination')
                            col_fill.prop(scene, 'dirAngle', slider=True, text='Angle')
                        elif scene.rampmode == 'OCC' or scene.rampmode == 'THK':
                            col_fill.prop(scene, 'occlusionrays', slider=True, text='Ray Count')
                            col_fill.prop(scene, 'occlusionbias', slider=True, text='Bias')
                            if scene.rampmode == 'OCC':
                                col_fill.prop(scene, 'occlusionblend', slider=True, text='Local/Global Mix')
                                col_fill.prop(scene, 'occlusiondistance', slider=True, text='Ray Distance')
                                col_fill.prop(scene, 'occlusiongroundplane', text='Ground Plane')

                # Crease Sets ---------------------------------------------------
                box_crease = layout.box()
                row_crease = box_crease.row()
                row_crease.prop(scene, 'expandcrease',
                    icon='TRIA_DOWN' if scene.expandcrease else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_crease.prop(scene, 'creasemode', expand=True)
                if scene.creasemode == 'CRS':
                    if scene.expandcrease:
                        row_sets = box_crease.row(align=True)
                        row_sets.operator('sxtools.crease1', text='25%')
                        row_sets.operator('sxtools.crease2', text='50%')
                        row_sets.operator('sxtools.crease3', text='75%')
                        row_sets.operator('sxtools.crease4', text='100%')
                        col_sets = box_crease.column(align=True)
                        col_sets.operator('sxtools.crease0', text='Uncrease')
                elif scene.creasemode == 'SDS':
                    if scene.expandcrease:
                        col_sds = box_crease.column(align=False)
                        col_sds.prop(sxtools, 'modifiervisibility', text='Show Modifiers')
                        col_sds.label(text='100% Creases Are:')
                        row_sds = box_crease.row()
                        row_sds.prop(sxtools, 'hardmode', expand=True)
                        col2_sds = box_crease.column(align=True)
                        col2_sds.prop(sxtools, 'subdivisionlevel', text='Subdivision Level')
                        if obj.sxtools.subdivisionlevel > 0:
                            col2_sds.prop(sxtools, 'decimation', text='Decimation Limit Angle')
                        if obj.sxtools.hardmode == 'BEVEL':
                            col2_sds.prop(sxtools, 'bevelsegments', text='Bevel Segments')
                            col2_sds.prop(sxtools, 'bevelwidth', text='Bevel Width')
                        col2_sds.separator()
                        if ('sxBevel' in obj.modifiers.keys()) or ('sxSubdivision' in obj.modifiers.keys()) or ('sxDecimate' in obj.modifiers.keys()) or ('sxDecimate2' in obj.modifiers.keys()) or ('sxEdgeSplit' in obj.modifiers.keys()) or ('sxWeightedNormal' in obj.modifiers.keys()):
                            col2_sds.operator('sxtools.removemodifiers', text='Remove Modifiers')
                        if ('sxBevel' not in obj.modifiers.keys()) or ('sxSubdivision' not in obj.modifiers.keys()) or ('sxWeightedNormal' not in obj.modifiers.keys()):
                            col2_sds.operator('sxtools.modifiers', text='Add Modifiers')

                # Master Palette ---------------------------------------------------
                box_palette = layout.box()
                row_palette = box_palette.row()
                row_palette.prop(scene, 'expandpalette',
                    icon='TRIA_DOWN' if scene.expandpalette else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_palette.prop(scene, 'palettemode', expand=True)
                if scene.palettemode == 'PAL':
                    palettes = context.scene.sxpalettes

                    if scene.expandpalette:
                        category = ''
                        for name in palettes.keys():
                            palette = palettes[name]
                            if palette.category != category:
                                category = palette.category
                                row_category = box_palette.row(align=True)
                                row_category.label(text='CATEGORY: '+category)
                                row_category.separator()
                            row_mpalette = box_palette.row(align=True)
                            split_mpalette = row_mpalette.split(factor=0.33)
                            split_mpalette.label(text=name)
                            split2_mpalette = split_mpalette.split()
                            row2_mpalette = split2_mpalette.row(align=True)
                            for i in range(5):
                                row2_mpalette.prop(palette, 'color'+str(i), text='')
                            mp_button = split2_mpalette.operator('sxtools.applypalette', text='Apply')
                            mp_button.label = name

                        row_mnoise = box_palette.row(align=True)
                        row_mnoise.prop(scene, 'palettenoise', slider=True)
                        col_mcolor = box_palette.column(align=True)
                        col_mcolor.prop(scene, 'palettemono', text='Monochromatic')

                # PBR Materials ---------------------------------------------------
                elif scene.palettemode == 'MAT':
                    materials = context.scene.sxmaterials

                    if scene.expandpalette:
                        category = ''
                        for name in materials.keys():
                            material = materials[name]
                            if material.category != category:
                                category = material.category
                                row_category = box_palette.row(align=True)
                                row_category.label(text='CATEGORY: '+category)
                                row_category.separator()
                            row_mat = box_palette.row(align=True)
                            split_mat = row_mat.split(factor=0.33)
                            split_mat.label(text=name)
                            split2_mat = split_mat.split()
                            row2_mat = split2_mat.row(align=True)
                            for i in range(3):
                                row2_mat.prop(material, 'color'+str(i), text='')
                            mat_button = split2_mat.operator('sxtools.applymaterial', text='Apply')
                            mat_button.label = name

                        row_pbrnoise = box_palette.row(align=True)
                        row_pbrnoise.prop(scene, 'materialnoise', slider=True)
                        col_matcolor = box_palette.column(align=True)
                        col_matcolor.prop(scene, 'materialmono', text='Monochromatic')
                        if mode == 'OBJECT':
                            col_matcolor.prop(scene, 'materialalpha')

                # Exporting and Miscellaneous ------------------------------------
                box_export = layout.box()
                row_export = box_export.row()
                row_export.prop(scene, 'expandexport',
                    icon='TRIA_DOWN' if scene.expandexport else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_export.prop(scene, 'exportmode', expand=True)
                if scene.exportmode == 'UTILS':
                    if scene.expandexport:
                        col_masks = box_export.column(align=True)
                        col_masks.operator('sxtools.enableall', text='Debug: Enable All Layers')
                        col_masks.operator('sxtools.applymodifiers', text='Debug: Apply Modifiers')
                        col_masks.operator('sxtools.generatemasks', text='Debug: Generate Masks')
                        col_masks.separator()
                        col_masks.operator('sxtools.revertobjects', text='Revert to Control Cages')
                        col_masks.operator('sxtools.setpivots', text='Set Pivots')
                        col_masks.operator('sxtools.groupobjects', text='Group Selected Objects')

                elif scene.exportmode == 'EXPORT':
                    if scene.expandexport:
                        col_export = box_export.column(align=True)
                        col_export.prop(sxtools, 'staticvertexcolors', text='Static Vertex Colors')
                        col_export.prop(sxtools, 'smoothness1', text='Layer1-3 Base Smoothness', slider=True)
                        col_export.prop(sxtools, 'smoothness2', text='Layer4-5 Base Smoothness', slider=True)
                        col_export.prop(sxtools, 'overlaystrength', text='Overlay Strength', slider=True)
                        col_export.label(text='Note: Check Subdivision and Bevel settings')
                        col_export.separator()
                        row2_export = box_export.row(align=True)
                        row2_export.prop(scene, 'exportquality', expand=True)
                        col2_export = box_export.column(align=True)
                        col2_export.operator('sxtools.macro', text='Magic Button')
                        if len(sxglobals.exportObjects) > 0:
                            col2_export.operator('sxtools.removeexports', text='Remove Exports')
                        col2_export.separator()
                        col2_export.label(text='Set Export Folder:')
                        col2_export.prop(scene, 'exportfolder', text='')
                        col2_export.operator('sxtools.exportfiles', text='Export Selected')

        else:
            layout = self.layout
            col = self.layout.column()
            if 'SXMaterial' in bpy.data.materials.keys():
                col.operator('sxtools.resetscene', text='Reset scene')
                col.separator()
            if sxglobals.librariesLoaded:
                col.label(text='Select a mesh to continue')
            else:
                col.label(text='Libraries not loaded')
                col.label(text='Check Add-on Preferences')


class SXTOOLS_UL_layerlist(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.enabled:
                if item.visibility:
                    layout.label(text=item.name, icon='HIDE_OFF')
                else:
                    layout.label(text=item.name, icon='HIDE_ON')
            else:
                layout.enabled = False
        elif self.layout_type in {'GRID'}:
            if item.enabled:
                layout.alignment = 'CENTER'
                if item.visibility:
                    layout.label(text='', icon='HIDE_OFF')
                else:
                    layout.label(text='', icon='HIDE_ON')
            else:
                layout.enabled = False


    # Called once to draw filtering/reordering options.
    def draw_filter(self, context, layout):
        pass


    def filter_items(self, context, data, propname):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            flt_flags = []
            flt_neworder = []
            sxLayerArray = []
            sxglobals.listItems.clear()
            sxglobals.listIndices.clear()

            for sxLayer in objs[0].sxlayers:
                sxLayerArray.append(sxLayer)
                flt_neworder.append(sxLayer.index)

            flt_flags = [self.bitflag_filter_item] * len(sxLayerArray)

            for idx, layer in enumerate(sxLayerArray):
                if not layer.enabled:
                    flt_flags[idx] |= ~self.bitflag_filter_item
                else:
                    sxglobals.listItems.append(layer.index)

            for i, idx in enumerate(sxglobals.listItems):
                sxglobals.listIndices[idx] = i

            return flt_flags, flt_neworder


class SXTOOLS_MT_piemenu(bpy.types.Menu):
    bl_idname = 'SXTOOLS_MT_piemenu'
    bl_label = 'SX Tools'


    def draw(self, context):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            obj = objs[0]

            layout = self.layout
            sxtools = obj.sxtools
            scene = context.scene.sxtools

            pie = layout.menu_pie()
            fill_row = pie.row()
            fill_row.prop(scene, 'fillcolor', text='')
            fill_row.operator('sxtools.applycolor', text='Apply Color')

            grd_col = pie.column()
            grd_col.prop(scene, 'rampmode', text='')
            grd_col.operator('sxtools.applyramp', text='Apply Gradient')

            layer_col = pie.column()
            layer_col.prop(sxtools, 'activeLayerBlendMode', text='')
            layer_col.prop(sxtools, 'activeLayerVisibility', text='Visibility')
            layer_col.prop(sxtools, 'activeLayerAlpha', slider=True, text='Layer Opacity')

            pie.prop(scene, 'shadingmode', text='')

            pie.operator('sxtools.copylayer', text='Copy Selection')
            pie.operator('sxtools.pastelayer', text='Paste Selection')
            pie.operator('sxtools.clear', text='Clear Layer')

            pie.operator('sxtools.selmask', text='Select Mask')


class SXTOOLS_OT_selectionmonitor(bpy.types.Operator):
    bl_idname = 'sxtools.selectionmonitor'
    bl_label = 'Selection Monitor'

    prevSelection: None

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def modal(self, context, event):
        selection = context.object

        if (len(sxglobals.masterPaletteArray) == 0) or (len(sxglobals.materialArray) == 0) or (len(sxglobals.rampDict) == 0) or (len(sxglobals.categoryDict) == 0):
            sxglobals.librariesLoaded = False

        if not sxglobals.librariesLoaded:
            loadLibraries(self, context)

        if selection is not self.prevSelection:
            self.prevSelection = context.object
            if (selection is not None) and len(selection.sxlayers) > 0:
                refreshActives(self, context)
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.prevSelection = context.object
        context.window_manager.modal_handler_add(self)
        print('SX Tools: Starting selection monitor')
        return {'RUNNING_MODAL'}


class SXTOOLS_OT_addramp(bpy.types.Operator):
    bl_idname = 'sxtools.addramp'
    bl_label = 'Add Ramp Preset'

    rampName: bpy.props.StringProperty(name='Ramp Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'rampName', text='')


    def execute(self, context):
        files.saveRamp(self.rampName)
        return {'FINISHED'}


class SXTOOLS_OT_delramp(bpy.types.Operator):
    bl_idname = 'sxtools.delramp'
    bl_label = 'Remove Ramp Preset'
    bl_description = 'Deletes ramp preset from Gradient Library'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        rampEnum = context.scene.sxtools.ramplist[:]
        rampName = sxglobals.presetLookup[context.scene.sxtools.ramplist]
        del sxglobals.rampDict[rampName]
        del sxglobals.presetLookup[rampEnum]
        files.saveFile('gradients')
        return {'FINISHED'}


class SXTOOLS_OT_scenesetup(bpy.types.Operator):
    bl_idname = 'sxtools.scenesetup'
    bl_label = 'Set Up Object'
    bl_description = 'Creates necessary material, vertex color layers,\nUV layers, and tool-specific variables'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            setup.updateInitArray()
            setup.setupLayers(objs)
            setup.createSXMaterial()
            setup.setupGeometry(objs)

            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applycolor(bpy.types.Operator):
    bl_idname = 'sxtools.applycolor'
    bl_label = 'Apply Color'
    bl_description = 'Applies the Fill Color to selected objects or components'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)
            color = context.scene.sxtools.fillcolor
            overwrite = context.scene.sxtools.fillalpha
            if objs[0].mode == 'EDIT':
                overwrite = True
            noise = context.scene.sxtools.fillnoise
            mono = context.scene.sxtools.fillmono
            tools.applyColor(objs, layer, color, overwrite, noise, mono)
            tools.updateRecentColors(color)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applyramp(bpy.types.Operator):
    bl_idname = 'sxtools.applyramp'
    bl_label = 'Apply Gradient'
    bl_description = 'Applies a gradient in various modes\nto the selected components or objects,\noptionally using their combined bounding volume'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)
            rampmode = context.scene.sxtools.rampmode
            mergebbx = context.scene.sxtools.rampbbox
            overwrite = context.scene.sxtools.rampalpha
            noise = context.scene.sxtools.rampnoise
            mono = context.scene.sxtools.rampmono
            if objs[0].mode == 'EDIT':
                overwrite = True
            ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
            tools.applyRamp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_mergeup(bpy.types.Operator):
    bl_idname = 'sxtools.mergeup'
    bl_label = 'Merge Up'
    bl_description = 'Merges the selected color layer with the one above'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        enabled = False
        objs = context.view_layer.objects.selected
        meshObjs = list()
        for obj in objs:
            if obj.type == 'MESH':
                meshObjs.append(obj)

        idx = meshObjs[0].sxtools.selectedlayer
        layer = utils.findLayerFromIndex(meshObjs[0], idx)
        if (layer.layerType == 'COLOR') and (sxglobals.listIndices[idx] != 0):
            enabled = True
        return enabled


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.findLayerFromIndex(objs[0], idx)
            listIndex = utils.findListIndex(objs[0], sourceLayer)
            targetLayer = utils.findLayerFromIndex(objs[0], sxglobals.listItems[listIndex - 1])
            layers.mergeLayers(objs, sourceLayer, targetLayer)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_mergedown(bpy.types.Operator):
    bl_idname = 'sxtools.mergedown'
    bl_label = 'Merge Down'
    bl_description = 'Merges the selected color layer with the one below'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        enabled = False
        objs = context.view_layer.objects.selected
        meshObjs = list()
        for obj in objs:
            if obj.type == 'MESH':
                meshObjs.append(obj)

        idx = meshObjs[0].sxtools.selectedlayer
        listIdx = sxglobals.listIndices[idx]
        layer = utils.findLayerFromIndex(meshObjs[0], idx)

        if listIdx != (len(sxglobals.listIndices) - 1):
            nextIdx = sxglobals.listItems[listIdx + 1]
            nextLayer = utils.findLayerFromIndex(meshObjs[0], nextIdx)

            if nextLayer.layerType != 'COLOR':
                return False

        if (listIdx != (len(sxglobals.listIndices) - 1)) and (layer.layerType == 'COLOR'):
            enabled = True
        return enabled


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.findLayerFromIndex(objs[0], idx)
            listIndex = utils.findListIndex(objs[0], sourceLayer)
            targetLayer = utils.findLayerFromIndex(objs[0], sxglobals.listItems[listIndex + 1])
            layers.mergeLayers(objs, sourceLayer, targetLayer)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_copylayer(bpy.types.Operator):
    bl_idname = 'sxtools.copylayer'
    bl_label = 'Copy Layer'
    bl_description = 'Mark the selected layer for copying'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)
            sxglobals.copyLayer = layer
        return {'FINISHED'}


class SXTOOLS_OT_pastelayer(bpy.types.Operator):
    bl_idname = 'sxtools.pastelayer'
    bl_label = 'Paste Layer'
    bl_description = 'Shift-click to swap with copied layer\nAlt-click to merge with the target layer\n(Color layers only!)'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = sxglobals.copyLayer
            targetLayer = utils.findLayerFromIndex(objs[0], idx)

            if event.shift:
                mode = 'swap'
            elif event.alt:
                mode = 'merge'
            else:
                mode = False

            if sourceLayer == None:
                messageBox('Nothing to paste!')
                return {'FINISHED'}
            elif (targetLayer.layerType != 'COLOR') and (mode == 'merge'):
                messageBox('Merging only supported with color layers')
                return {'FINISHED'}
            else:
                layers.pasteLayer(objs, sourceLayer, targetLayer, mode)

                sxglobals.composite = True
                refreshActives(self, context)
                return {'FINISHED'}
        return {'FINISHED'}


class SXTOOLS_OT_clearlayers(bpy.types.Operator):
    bl_idname = 'sxtools.clear'
    bl_label = 'Clear Layer'
    bl_description = 'Shift-click to clear all layers\non selected objects or components'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            if event.shift:
                layer = None
            else:
                idx = objs[0].sxtools.selectedlayer
                layer = utils.findLayerFromIndex(objs[0], idx)

            layers.clearLayers(objs, layer)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_selmask(bpy.types.Operator):
    bl_idname = 'sxtools.selmask'
    bl_label = 'Select Layer Mask'
    bl_description = 'Click to select components with alpha\nShift-click to invert selection'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            if event.shift:
                inverse = True
            else:
                inverse = False

            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)

            tools.selectMask(objs, [layer, ], inverse)
        return {'FINISHED'}


class SXTOOLS_OT_crease0(bpy.types.Operator):
    bl_idname = 'sxtools.crease0'
    bl_label = 'Crease0'
    bl_description = 'Uncrease selected components'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            group = 'CreaseSet0'
            if event.shift:
                tools.selectCrease(objs, group)
            else:
                tools.assignCrease(objs, group)
        return {'FINISHED'}


class SXTOOLS_OT_crease1(bpy.types.Operator):
    bl_idname = 'sxtools.crease1'
    bl_label = 'Crease1'
    bl_description = 'Click to apply edge crease value\nShift-click to select creased edges'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            group = 'CreaseSet1'
            if event.shift:
                tools.selectCrease(objs, group)
            else:
                tools.assignCrease(objs, group)
        return {'FINISHED'}


class SXTOOLS_OT_crease2(bpy.types.Operator):
    bl_idname = 'sxtools.crease2'
    bl_label = 'Crease2'
    bl_description = 'Click to apply edge crease value\nShift-click to select creased edges'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            group = 'CreaseSet2'
            if event.shift:
                tools.selectCrease(objs, group)
            else:
                tools.assignCrease(objs, group)
        return {'FINISHED'}


class SXTOOLS_OT_crease3(bpy.types.Operator):
    bl_idname = 'sxtools.crease3'
    bl_label = 'Crease3'
    bl_description = 'Click to apply edge crease value\nShift-click to select creased edges'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            group = 'CreaseSet3'
            if event.shift:
                tools.selectCrease(objs, group)
            else:
                tools.assignCrease(objs, group)
        return {'FINISHED'}


class SXTOOLS_OT_crease4(bpy.types.Operator):
    bl_idname = 'sxtools.crease4'
    bl_label = 'Crease4'
    bl_description = 'Click to apply edge crease value\nShift-click to select creased edges'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            group = 'CreaseSet4'
            if event.shift:
                tools.selectCrease(objs, group)
            else:
                tools.assignCrease(objs, group)
        return {'FINISHED'}


class SXTOOLS_OT_applypalette(bpy.types.Operator):
    bl_idname = 'sxtools.applypalette'
    bl_label = 'Apply Palette'
    bl_description = 'Applies the selected palette to selected objects\nPalette colors are applied to layers 1-5'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty()


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            palette = self.label
            noise = context.scene.sxtools.palettenoise
            mono = context.scene.sxtools.palettemono

            tools.applyPalette(objs, palette, noise, mono)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applymaterial(bpy.types.Operator):
    bl_idname = 'sxtools.applymaterial'
    bl_label = 'Apply PBR Material'
    bl_description = 'Applies the selected material to selected objects\nAlbedo color goes to the selected color layer\nmetallic and smoothness values are automatically applied\nto the selected material channels'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty()


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            material = self.label
            idx = objs[0].sxtools.selectedlayer
            layer = utils.findLayerFromIndex(objs[0], idx)
            overwrite = context.scene.sxtools.materialalpha
            if objs[0].mode == 'EDIT':
                overwrite = True
            noise = context.scene.sxtools.materialnoise
            mono = context.scene.sxtools.materialmono

            tools.applyMaterial(objs, layer, material, overwrite, noise, mono)

            sxglobals.composite = True
            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_modifiers(bpy.types.Operator):
    bl_idname = 'sxtools.modifiers'
    bl_label = 'Add Modifiers'
    bl_description = 'Adds Subdivision, Edge Split and Weighted Normals modifiers\nto selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            tools.addModifiers(objs)

            if objs[0].mode == 'OBJECT':
                bpy.ops.object.shade_smooth()
        return {'FINISHED'}


class SXTOOLS_OT_applymodifiers(bpy.types.Operator):
    bl_idname = 'sxtools.applymodifiers'
    bl_label = 'Apply Modifiers'
    bl_description = 'Applies modifiers to the selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            tools.applyModifiers(objs)
        return {'FINISHED'}


class SXTOOLS_OT_removemodifiers(bpy.types.Operator):
    bl_idname = 'sxtools.removemodifiers'
    bl_label = 'Remove Modifiers'
    bl_description = 'Remove SX Tools modifiers from selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            tools.removeModifiers(objs)

            if objs[0].mode == 'OBJECT':
                bpy.ops.object.shade_flat()
        return {'FINISHED'}


class SXTOOLS_OT_generatemasks(bpy.types.Operator):
    bl_idname = 'sxtools.generatemasks'
    bl_label = 'Create Palette Masks'
    bl_description = 'Bakes masks of Layers 1-7 into a UV channel\nfor exporting to game engine\nif dynamic palettes are used'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            layers.generateMasks(objs)
            layers.flattenAlphas(objs)
        return {'FINISHED'}


class SXTOOLS_OT_enableall(bpy.types.Operator):
    bl_idname = 'sxtools.enableall'
    bl_label = 'Enable All Layers'
    bl_description = 'Enables all layers on selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scn = bpy.context.scene.sxtools
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            for obj in objs:
                for layer in obj.sxlayers:
                    if (layer.name != 'composite') and (layer.name != 'masks') and (layer.name != 'texture'):
                        layer.enabled = True

            bpy.data.materials.remove(bpy.data.materials['SXMaterial'])

            scn.numlayers = 7
            scn.numalphas = 2
            scn.numoverlays = 1
            scn.enableocclusion = True
            scn.enabletransmission = True
            scn.enableemission = True
            scn.enablemetallic = True
            scn.enablesmoothness = True

            setup.updateInitArray()
            setup.setupLayers(objs)
            setup.createSXMaterial()
            setup.setupGeometry(objs)

            refreshActives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_resetscene(bpy.types.Operator):
    bl_idname = 'sxtools.resetscene'
    bl_label = 'Reset Scene'
    bl_description = 'Clears all SX Tools data from objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        setup.resetScene()
        return {'FINISHED'}


class SXTOOLS_OT_exportfiles(bpy.types.Operator):
    bl_idname = 'sxtools.exportfiles'
    bl_label = 'Export Selected'
    bl_description = 'Saves FBX files of multi-part objects\nAll EMPTY groups at root based on selection are exported'


    def invoke(self, context, event):
        selected = context.view_layer.objects.selected
        groups = utils.findGroups(selected)
        files.exportFiles(groups)
        return {'FINISHED'}


class SXTOOLS_OT_removeexports(bpy.types.Operator):
    bl_idname = 'sxtools.removeexports'
    bl_label = 'Remove Exports'
    bl_description = 'Deletes generated high-poly objects\nReturns the source object to its original state'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        export.removeExports()

        scene.shadingmode = 'FULL'
        bpy.ops.object.shade_flat()
        return {'FINISHED'}


class SXTOOLS_OT_setpivots(bpy.types.Operator):
    bl_idname = 'sxtools.setpivots'
    bl_label = 'Set Pivots'
    bl_description = 'Set pivot to center of mass on selected objects\nShift-click to set pivot to center of bounding box'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            active = context.active_object
            for obj in objs:
                bpy.context.view_layer.objects.active = obj
                if event.shift:
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                else:
                    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')

            bpy.context.view_layer.objects.active = active
        return {'FINISHED'}


class SXTOOLS_OT_groupobjects(bpy.types.Operator):
    bl_idname = 'sxtools.groupobjects'
    bl_label = 'Group Objects'
    bl_description = 'Groups objects under an empty\nwith pivot placed at the bottom center'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            tools.groupObjects(objs)
        return {'FINISHED'}


class SXTOOLS_OT_revertobjects(bpy.types.Operator):
    bl_idname = 'sxtools.revertobjects'
    bl_label = 'Revert to Control Cages'
    bl_description = 'Removes modifiers and clears\nlayers generated by processing'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            tools.revertObjects(objs)

            sxglobals.composite = True
            refreshActives(self, context)

            scene.shadingmode = 'FULL'
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.shade_flat()
        return {'FINISHED'}


class SXTOOLS_OT_loadlibraries(bpy.types.Operator):
    bl_idname = 'sxtools.loadlibraries'
    bl_label = 'Load Libraries'
    bl_description = 'Loads SX Tools libraries of\npalettes, materials, gradients and categories'


    def invoke(self, context, event):
        loadLibraries(self, context)
        return {'FINISHED'}    


class SXTOOLS_OT_macro(bpy.types.Operator):
    bl_idname = 'sxtools.macro'
    bl_label = 'Process Exports'
    bl_description = 'Applies modifiers and calculates material channels\naccording to category'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        objs = selectionValidator(self, context)
        if len(objs) > 0:
            export.processObjects(objs, context.scene.sxtools.exportquality)

            sxglobals.composite = True
            refreshActives(self, context)

            scene.shadingmode = 'FULL'
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.shade_smooth()
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Registration and initialization
# ------------------------------------------------------------------------
sxglobals = SXTOOLS_sxglobals()
files = SXTOOLS_files()
utils = SXTOOLS_utils()
layers = SXTOOLS_layers()
setup = SXTOOLS_setup()
mesh = SXTOOLS_mesh()
tools = SXTOOLS_tools()
export = SXTOOLS_export()

classes = (
    SXTOOLS_preferences,
    SXTOOLS_objectprops,
    SXTOOLS_sceneprops,
    SXTOOLS_masterpalette,
    SXTOOLS_material,
    SXTOOLS_rampcolor,
    SXTOOLS_layer,
    SXTOOLS_PT_panel,
    SXTOOLS_UL_layerlist,
    SXTOOLS_MT_piemenu,
    SXTOOLS_OT_selectionmonitor,
    SXTOOLS_OT_scenesetup,
    SXTOOLS_OT_applycolor,
    SXTOOLS_OT_applyramp,
    SXTOOLS_OT_addramp,
    SXTOOLS_OT_delramp,
    SXTOOLS_OT_crease0,
    SXTOOLS_OT_crease1,
    SXTOOLS_OT_crease2,
    SXTOOLS_OT_crease3,
    SXTOOLS_OT_crease4,
    SXTOOLS_OT_applypalette,
    SXTOOLS_OT_applymaterial,
    SXTOOLS_OT_copylayer,
    SXTOOLS_OT_selmask,
    SXTOOLS_OT_clearlayers,
    SXTOOLS_OT_mergeup,
    SXTOOLS_OT_mergedown,
    SXTOOLS_OT_pastelayer,
    SXTOOLS_OT_applymodifiers,
    SXTOOLS_OT_modifiers,
    SXTOOLS_OT_removemodifiers,
    SXTOOLS_OT_generatemasks,
    SXTOOLS_OT_enableall,
    SXTOOLS_OT_resetscene,
    SXTOOLS_OT_exportfiles,
    SXTOOLS_OT_removeexports,
    SXTOOLS_OT_setpivots,
    SXTOOLS_OT_groupobjects,
    SXTOOLS_OT_revertobjects,
    SXTOOLS_OT_loadlibraries,
    SXTOOLS_OT_macro)

addon_keymaps = []


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Object.sxtools = bpy.props.PointerProperty(type=SXTOOLS_objectprops)
    bpy.types.Object.sxlayers = bpy.props.CollectionProperty(type=SXTOOLS_layer)
    bpy.types.Scene.sxtools = bpy.props.PointerProperty(type=SXTOOLS_sceneprops)
    bpy.types.Scene.sxpalettes = bpy.props.CollectionProperty(type=SXTOOLS_masterpalette)
    bpy.types.Scene.sxmaterials = bpy.props.CollectionProperty(type=SXTOOLS_material)

    bpy.app.handlers.load_post.append(load_post_handler)

    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'COMMA', 'PRESS', shift=True)
        kmi.properties.name = SXTOOLS_MT_piemenu.bl_idname
        addon_keymaps.append((km, kmi))


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Object.sxtools
    del bpy.types.Object.sxlayers
    del bpy.types.Scene.sxtools
    del bpy.types.Scene.sxpalettes
    del bpy.types.Scene.sxmaterials
    # del tools
    # del sxglobals

    bpy.app.handlers.load_post.remove(load_post_handler)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == '__main__':
    try:
        unregister()
    except:
        pass
    register()

    bpy.ops.wm.call_menu_pie(name='SXTOOLS_MT_piemenu')


# TODO:
# - Fill with 0.5 if overlay?
# - ProcessBuildings Low: windows need hard normals
# - Investigate SXMaterial auto-regeneration issues
# - Add alpha support to debug mode
# - Crease fails with face selection (no, fails with extrusion performed without going obj/edit)
# - Create and re-index UV0 if not present in processing
# - Auto-place pivots during processing?
# - Absolute path check
# - Run from direct github zip download
#   - Split to multiple python files
#   - Default path to find libraries in the zip?
# - mask/adjustment indication
# - Master palette library save/manage
# - PBR material library save/manage
# - Skinning support?
# - Submesh support
