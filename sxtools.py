bl_info = {
    'name': 'SX Tools',
    'author': 'Jani Kahrama / Secret Exit Ltd.',
    'version': (3, 9, 0),
    'blender': (2, 82, 0),
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
import sys
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
        self.lightnessUpdate = False
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
            ['overlay', False, 10, 'UV4', [0.5, 0.5, 0.5, 1.0], 0.0, True, 1.0, 'OVR', '', 'UVSet5', 'U', 'UVSet5', 'V', 'UVSet6', 'U', 'UVSet6', 'V'],
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
    def load_file(self, mode):
        prefs = bpy.context.preferences.addons['sxtools'].preferences
        directory = prefs.libraryfolder
        filePath = directory + mode + '.json'

        if len(directory) > 0:
            try:
                with open(filePath, 'r') as input:
                    tempDict = {}
                    tempDict = json.load(input)
                    if mode == 'palettes':
                        del sxglobals.masterPaletteArray[:]
                        bpy.context.scene.sxpalettes.clear()
                        sxglobals.masterPaletteArray = tempDict['Palettes']
                    elif mode == 'materials':
                        del sxglobals.materialArray[:]
                        bpy.context.scene.sxmaterials.clear()
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
                prefs.libraryfolder = ''
                return False
            except IOError:
                print('SX Tools Error: ' + mode + ' file not found!')
                return False
        else:
            print('SX Tools: No ' + mode + ' file found')
            return False

        if mode == 'palettes':
            self.load_palettes()
            return True
        elif mode == 'materials':
            self.load_materials()
            return True
        else:
            return True


    def save_file(self, mode):
        prefs = bpy.context.preferences.addons['sxtools'].preferences
        directory = prefs.libraryfolder
        filePath = directory + mode + '.json'
        # Palettes.json Materials.json

        if len(directory) > 0:
            with open(filePath, 'w') as output:
                if mode == 'palettes':
                    tempDict = {}
                    tempDict['Palettes'] = sxglobals.masterPaletteArray
                    json.dump(tempDict, output, indent=4)
                elif mode == 'materials':
                    tempDict = {}
                    tempDict['Materials'] = sxglobals.materialArray
                    json.dump(tempDict, output, indent=4)
                elif mode == 'gradients':
                    tempDict = {}
                    tempDict = sxglobals.rampDict
                    json.dump(tempDict, output, indent=4)
                output.close()
            message_box(mode + ' saved')
            # print('SX Tools: ' + mode + ' saved')
        else:
            message_box(mode + ' file location not set!', 'SX Tools Error', 'ERROR')
            # print('SX Tools Warning: ' + mode + ' file location not set!')


    def load_palettes(self):
        for categoryDict in sxglobals.masterPaletteArray:
            for category in categoryDict.keys():
                if len(categoryDict[category]) == 0:
                    item = bpy.context.scene.sxpalettes.add()
                    item.name = 'Empty'
                    item.category = category
                    for i in range(5):
                        incolor = [0.0, 0.0, 0.0, 1.0]
                        setattr(item, 'color'+str(i), incolor[:]) 
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


    def load_materials(self):
        for categoryDict in sxglobals.materialArray:
            for category in categoryDict.keys():
                if len(categoryDict[category]) == 0:
                    item = bpy.context.scene.sxmaterials.add()
                    item.name = 'Empty'
                    item.category = category
                    for i in range(3):
                        incolor = [0.0, 0.0, 0.0, 1.0]
                        setattr(item, 'color'+str(i), incolor[:]) 
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


    def save_ramp(self, rampName):
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

        self.save_file('gradients')


    # In paletted export mode, gradients and overlays are
    # not composited to VertexColor0 as that will be
    # done by the shader on the game engine side 
    def export_files(self, groups):
        scene = bpy.context.scene.sxtools
        prefs = bpy.context.preferences.addons['sxtools'].preferences
        colorspace = prefs.colorspace
        groupNames = []
        for group in groups:
            bpy.context.view_layer.objects.active = group
            bpy.ops.object.select_all(action='DESELECT')
            group.select_set(True)
            org_loc = group.location.copy()
            group.location = (0,0,0)
            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')

            selArray = bpy.context.view_layer.objects.selected

            # Only groups with meshes as children are exported
            if len(selArray) > 0:
                category = selArray[0].sxtools.category.lower()

                # Create palette masks
                layers.generate_masks(selArray)

                for sel in selArray:
                    if 'staticVertexColors' not in sel.keys():
                        sel['staticVertexColors'] = True

                    if 'sxToolsVersion' not in sel.keys():
                        sel['sxToolsVersion'] = 'SX Tools for Blender ' + str(sys.modules['sxtools'].bl_info.get('version'))

                    compLayers = utils.find_comp_layers(sel, sel['staticVertexColors'])
                    layer0 = utils.find_layer_from_index(sel, 0)
                    layer1 = utils.find_layer_from_index(sel, 1)
                    layers.blend_layers([sel, ], compLayers, layer1, layer0)

                # If linear colorspace exporting is selected
                if colorspace == 'LIN':
                    export.convert_to_linear(selArray)

                path = scene.exportfolder + category
                pathlib.Path(path).mkdir(exist_ok=True)

                if '/' in scene.exportfolder:
                    slash = '/'
                elif '\\' in scene.exportfolder:
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

        message_box('Exported ' + str(', ').join(groupNames))


# ------------------------------------------------------------------------
#    Layer Data Find Functions
# ------------------------------------------------------------------------
class SXTOOLS_utils(object):
    def __init__(self):
        return None

    # Finds groups to be exported,
    # only EMPTY objects with no parents
    def find_groups(self, objs):
        groups = []
        for obj in objs:
            if (obj.type == 'EMPTY') and (obj.parent is None):
                groups.append(obj)

            parent = obj.parent
            if (parent is not None) and (parent.type == 'EMPTY') and (parent.parent is None):
                groups.append(obj.parent)

        return set(groups)


    def find_children(self, group, objs):
        children = []
        for obj in objs:
            if obj.parent == group:
                children.append(obj)

        return children


    def find_list_index(self, obj, layer):
        index = obj.sxlayers[layer.name].index

        return sxglobals.listIndices[index]


    def find_color_layers(self, obj):
        sxLayerArray = []
        sxLayerArray.append(obj.sxlayers['composite'])
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'COLOR') and (sxLayer.enabled):
                sxLayerArray.append(sxLayer)
        sxLayerArray.sort(key=lambda x: x.index)

        return sxLayerArray


    def find_default_values(self, obj, mode):
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
                if sxLayer.layerType == 'UV4':
                    if sxLayer.uvLayer0 == uvSet:
                        values[1] = sxLayer.defaultColor[0]
                    if sxLayer.uvLayer1 == uvSet:
                        values[2] = sxLayer.defaultColor[1]
                    if sxLayer.uvLayer2 == uvSet:
                        values[1] = sxLayer.defaultColor[2]
                    if sxLayer.uvLayer3 == uvSet:
                        values[2] = sxLayer.defaultColor[3]
                else:
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


    def find_comp_layers(self, obj, staticExport=True):
        compLayers = []
        for sxLayer in obj.sxlayers:
            if (sxLayer.layerType == 'COLOR') and (sxLayer.enabled is True) and (sxLayer.index != 1):
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


    def find_layer_from_index(self, obj, index):
        for sxLayer in obj.sxlayers:
            if sxLayer.index == index:
                return sxLayer


    def find_mode_color(self, objs, layer):
        mode = objs[0].mode
        scene = bpy.context.scene.sxtools
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        channels = {'U': 0, 'V': 1}

        colorArray = []
        for obj in objs:
            mesh = obj.data
            if layer.layerType == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif layer.layerType == 'UV':
                uvValues = obj.data.uv_layers[layer.uvLayer0].data

            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    if layer.layerType == 'COLOR':
                        vertcolor = vertexColors[loop_idx].color[:]
                    elif layer.layerType == 'UV':
                        uvValue = uvValues[loop_idx].uv[channels[layer.uvChannel0]]
                        vertcolor = [uvValue, uvValue, uvValue, uvValue]

                    if vertcolor[3] > 0.0:
                        colorArray.append(vertcolor)

        if len(colorArray) == 0:
            modecolor = (0.0, 0.0, 0.0, 1.0)
        else:
            colorSet = set(tuple(color) for color in colorArray)
            colorFreq = []
            for color in colorSet:
                colorFreq.append((colorArray.count(color), color))

            sortColors = sorted(colorFreq, key=lambda tup: tup[0])
            modecolor = sortColors[0][1]

        bpy.ops.object.mode_set(mode=mode)
        return modecolor


    def __del__(self):
        print('SX Tools: Exiting utils')


# ------------------------------------------------------------------------
#    Scene Setup
# ------------------------------------------------------------------------
class SXTOOLS_setup(object):
    def __init__(self):
        return None


    def start_modal(self):
        bpy.ops.sxtools.selectionmonitor('INVOKE_DEFAULT')
        bpy.ops.sxtools.keymonitor('INVOKE_DEFAULT')
        sxglobals.modalStatus = True


    def update_init_array(self):
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
    def setup_layers(self, objs):
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


    def setup_geometry(self, objs):
        changed = False
        overwrite = bpy.context.scene.sxtools.eraseuvs

        # Build arrays of needed vertex color and UV sets,
        # VertexColor0 needed for compositing if even one
        # color layer is enabled
        # UVSet0 needed in game engine for textures and proper
        # indexing of data
        uvArray = ['UVSet0', ]
        colorArray = utils.find_color_layers(objs[0])
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
                    layers.clear_layers([obj, ], sxLayer)
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
                                    layers.clear_uvs([obj, ], sxLayer)

            # for i in range(5):
            #    if not 'CreaseSet'+str(i) in obj.vertex_groups.keys():
            #        obj.vertex_groups.new(name='CreaseSet'+str(i))

            obj.active_material = bpy.data.materials['SXMaterial']

        if changed:
            bpy.context.scene.sxtools.shadingmode = 'FULL'


    def create_sxmaterial(self):
        prefs = bpy.context.preferences.addons['sxtools'].preferences        
        if prefs.materialtype == 'SMP':
            self.create_simple_sxmaterial()
        else:
            self.create_pbr_sxmaterial()


    def create_simple_sxmaterial(self):
        scene = bpy.context.scene.sxtools
        numlayers = scene.numlayers
        numgradients = scene.numalphas
        numoverlays = scene.numoverlays

        for values in sxglobals.layerInitArray:
            if values[0] == 'composite':
                compositeUVSet = values[9]
                composite = values[1]

        sxmaterial = bpy.data.materials.new(name='SXMaterial')
        sxmaterial.use_nodes = True

        sxmaterial.node_tree.nodes.remove(sxmaterial.node_tree.nodes['Principled BSDF'])

        sxmaterial.node_tree.nodes.new(type='ShaderNodeEmission')
        sxmaterial.node_tree.nodes['Emission'].location = (800, 200)

        sxmaterial.node_tree.nodes['Material Output'].location = (1100, 200)

        # Gradient tool color ramp
        sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')
        sxmaterial.node_tree.nodes['ColorRamp'].location = (-1400, 200)

        # Palette colors
        for i in range(5):
            pCol = sxmaterial.node_tree.nodes.new(type="ShaderNodeRGB")
            pCol.name = 'PaletteColor' + str(i)
            pCol.location = (-1400, -200*i)

        sxmaterial.node_tree.nodes.new(type='ShaderNodeVertexColor')
        sxmaterial.node_tree.nodes['Vertex Color'].layer_name = compositeUVSet
        sxmaterial.node_tree.nodes['Vertex Color'].location = (-600, 200)

        output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Color']
        input = sxmaterial.node_tree.nodes['Emission'].inputs['Color']
        sxmaterial.node_tree.links.new(input, output)

        output = sxmaterial.node_tree.nodes['Emission'].outputs['Emission']
        input = sxmaterial.node_tree.nodes['Material Output'].inputs['Surface']
        sxmaterial.node_tree.links.new(input, output)


    def create_pbr_sxmaterial(self):
        scene = bpy.context.scene.sxtools
        numlayers = scene.numlayers
        numgradients = scene.numalphas
        numoverlays = scene.numoverlays

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
            elif values[0] == 'overlay':
                overlayUVSet1 = values[10]
                overlayUVSet2 = values[14]
                overlay = values[1]

        prefs = bpy.context.preferences.addons['sxtools'].preferences
        materialsubsurface = prefs.materialsubsurface
        materialtransmission = prefs.materialtransmission

        # print('layers: ', numlayers)
        # print('gradients: ', numgradients)
        # print('overlay: ', numoverlays)
        # print('composite: ', composite)
        # print('occlusion: ', occlusion)
        # print('metallic: ', metallic)
        # print('smoothness: ', smoothness)
        # print('transmission: ', transmission)
        # print('emission: ', emission)
        # print('gradient1: ', gradient1)
        # print('gradient2: ', gradient2)
        # print('overlay: ', overlay)
        # print('mat_sss: ', materialsubsurface)
        # print('mat_trans: ', materialtransmission)
        # print(sxglobals.layerInitArray)

        sxmaterial = bpy.data.materials.new(name='SXMaterial')
        sxmaterial.use_nodes = True
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = [0.0, 0.0, 0.0, 1.0]
        sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.5
        sxmaterial.node_tree.nodes['Principled BSDF'].location = (800, 200)

        sxmaterial.node_tree.nodes['Material Output'].location = (1100, 200)

        # Gradient tool color ramp
        sxmaterial.node_tree.nodes.new(type='ShaderNodeValToRGB')
        sxmaterial.node_tree.nodes['ColorRamp'].location = (-1400, 200)

        # Palette colors
        for i in range(5):
            pCol = sxmaterial.node_tree.nodes.new(type="ShaderNodeRGB")
            pCol.name = 'PaletteColor' + str(i)
            pCol.location = (-1400, -200*i)

        # Gradient1 and gradient2 source
        if gradient1 or gradient2:
            grd = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            grd.name = 'GradientUV'
            grd.uv_map = gradient1UVSet
            grd.location = (-600, -600)

            grdSep = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            grdSep.name = 'GradientXYZ'
            grdSep.location = (-300, -600)

            output = grd.outputs['UV']
            input = grdSep.inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

        # Overlay source
        if overlay:
            ovr1 = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            ovr1.name = 'OverlayUV1'
            ovr1.uv_map = overlayUVSet1
            ovr1.location = (-600, -800)

            ovr2 = sxmaterial.node_tree.nodes.new(type='ShaderNodeUVMap')
            ovr2.name = 'OverlayUV2'
            ovr2.uv_map = overlayUVSet2
            ovr2.location = (-600, -1000)

            ovrSep1 = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            ovrSep1.name = 'OverlayXYZ1'
            ovrSep1.location = (-300, -800)

            ovrSep2 = sxmaterial.node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
            ovrSep2.name = 'OverlayXYZ2'
            ovrSep2.location = (-300, -1000)

            ovrRGB = sxmaterial.node_tree.nodes.new(type='ShaderNodeCombineRGB')
            ovrRGB.name = 'OverlayCombine'
            ovrRGB.location = (0, -900)

            output = ovr1.outputs['UV']
            input = ovrSep1.inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

            output = ovr2.outputs['UV']
            input = ovrSep2.inputs['Vector']
            sxmaterial.node_tree.links.new(input, output)

            output = ovrSep1.outputs['X']
            input = ovrRGB.inputs['R']
            sxmaterial.node_tree.links.new(input, output)

            output = ovrSep1.outputs['Y']
            input = ovrRGB.inputs['G']
            sxmaterial.node_tree.links.new(input, output)

            output = ovrSep2.outputs['X']
            input = ovrRGB.inputs['B']
            sxmaterial.node_tree.links.new(input, output)

        # Vertex color and alpha sources
        for i in range(numlayers + numgradients + numoverlays - 1):
            if i < numlayers:
                colornode = sxmaterial.node_tree.nodes.new(type='ShaderNodeVertexColor')
                colornode.name = 'VertexColor' + str(i + 1)
                colornode.layer_name = 'VertexColor' + str(i + 1)
                colornode.location = (i*200-1400, 550)

            mixnode = sxmaterial.node_tree.nodes.new(type='ShaderNodeMixRGB')
            mixnode.name = 'Mix ' + str(i + 1)
            mixnode.inputs[0].default_value = 1
            mixnode.inputs[2].default_value = [1.0, 1.0, 1.0, 1.0]
            mixnode.blend_type = 'MIX'
            mixnode.use_clamp = True
            mixnode.location = (i*200-1200, 400)

            mathnode = sxmaterial.node_tree.nodes.new(type='ShaderNodeMath')
            mathnode.name = 'Opacity ' + str(i + 1)
            mathnode.operation = 'MULTIPLY'
            mathnode.use_clamp = True
            mathnode.inputs[0].default_value = 1
            mathnode.location = (i*200-1200, 750)

            # Vertex Colors, base layer connection
            if i == 0:
                output = colornode.outputs['Color']
            else:
                output = sxmaterial.node_tree.nodes['Mix ' + str(i)].outputs['Color']
            input = mixnode.inputs['Color1']
            sxmaterial.node_tree.links.new(input, output)

            # Vertex Colors, top layer connection
            if (i != 0) and (i < numlayers):
                output = colornode.outputs['Color']
                input = sxmaterial.node_tree.nodes['Mix ' + str(i)].inputs['Color2']
                sxmaterial.node_tree.links.new(input, output)

                output = colornode.outputs['Alpha']
                input = sxmaterial.node_tree.nodes['Opacity ' + str(i)].inputs[1]
                sxmaterial.node_tree.links.new(input, output)

                output = sxmaterial.node_tree.nodes['Opacity ' + str(i)].outputs['Value']
                input = sxmaterial.node_tree.nodes['Mix ' + str(i)].inputs['Fac']
                sxmaterial.node_tree.links.new(input, output)

            # Gradient (alpha overlay) base connections
            if (i >= numlayers) and (i < numlayers + numgradients):
                output = sxmaterial.node_tree.nodes['PaletteColor' + str(i - numlayers + 3)].outputs['Color']
                input = sxmaterial.node_tree.nodes['Mix ' + str(i)].inputs['Color2']
                sxmaterial.node_tree.links.new(input, output)

                if (gradient1 or gradient2) and (i == numlayers):
                    output = grdSep.outputs['X']
                    input = sxmaterial.node_tree.nodes['Opacity ' + str(i)].inputs[1]
                    sxmaterial.node_tree.links.new(input, output)
                elif (gradient2) and (i == numlayers + 1):
                    output = grdSep.outputs['Y']
                    input = sxmaterial.node_tree.nodes['Opacity ' + str(i)].inputs[1]
                    sxmaterial.node_tree.links.new(input, output)

                output = sxmaterial.node_tree.nodes['Opacity ' + str(i)].outputs['Value']
                input = sxmaterial.node_tree.nodes['Mix ' + str(i)].inputs['Fac']
                sxmaterial.node_tree.links.new(input, output)

            if (i == numlayers + numgradients + numoverlays -2):
                if overlay:
                    output = ovrRGB.outputs['Image']
                    input = sxmaterial.node_tree.nodes['Mix ' + str(i + 1)].inputs['Color2']
                    sxmaterial.node_tree.links.new(input, output)

                    output = ovrSep2.outputs['Y']
                    input = sxmaterial.node_tree.nodes['Opacity ' + str(i + 1)].inputs[1]
                    sxmaterial.node_tree.links.new(input, output)

                    output = sxmaterial.node_tree.nodes['Opacity ' + str(i + 1)].outputs['Value']
                    input = sxmaterial.node_tree.nodes['Mix ' + str(i + 1)].inputs['Fac']
                    sxmaterial.node_tree.links.new(input, output)

                    sxmaterial.node_tree.nodes['Mix ' + str(i + 1)].blend_type = 'OVERLAY'

                mixnode.name = 'Final Step'

        sxmaterial.node_tree.nodes.new(type='ShaderNodeVertexColor')
        sxmaterial.node_tree.nodes['Vertex Color'].layer_name = compositeUVSet
        sxmaterial.node_tree.nodes['Vertex Color'].location = (-600, 200)

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

        # Node connections
        # Vertex alpha to shader alpha
        output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Alpha']
        input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Alpha']
        sxmaterial.node_tree.links.new(input, output)

        # Vertex color to mixer
        output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Color']
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

        if (transmission or emission) and materialtransmission:
            # X to transmission
            output = sxmaterial.node_tree.nodes['EmissionXYZ'].outputs['X']
            input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Transmission']
            sxmaterial.node_tree.links.new(input, output)

        if (transmission or emission) and materialsubsurface:
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


    def reset_scene(self):
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


    def create_sxcollection(self):
        if 'SXObjects' not in bpy.data.collections.keys():
            sxObjects = bpy.data.collections.new('SXObjects')
        else:
            sxObjects = bpy.data.collections['SXObjects']
        for obj in bpy.data.objects:
            if (len(obj.sxtools.keys()) > 0) and (obj.name not in sxObjects.objects):
                sxObjects.objects.link(obj)

        if sxObjects.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.children.link(sxObjects)


    def __del__(self):
        print('SX Tools: Exiting setup')


# ------------------------------------------------------------------------
#    Color Conversions
# ------------------------------------------------------------------------
class SXTOOLS_convert(object):
    def __init__(self):
        return None


    def color_to_luminance(self, color):
        lumR = 0.212655
        lumG = 0.715158
        lumB = 0.072187

        linColor = self.srgb_to_linear(color)
        linLum = lumR * linColor[0] + lumG * linColor[1] + lumB * linColor[2]
        luminance = self.linear_to_srgb([linLum, linLum, linLum, 1.0])[0]
        # luminance = ((color[0] + color[0] + color[2] + color[1] + color[1] + color[1]) / float(6.0))
        return luminance


    def srgb_to_linear(self, inColor):
        outColor = []
        for i in range(4):
            if inColor[i] < 0.0:
                outColor.append(0.0)
            elif 0.0 <= inColor[i] <= 0.0404482362771082:
                outColor.append(float(inColor[i]) / 12.92)
            elif  0.0404482362771082 < inColor[i] <= 1.0: 
                outColor.append(((inColor[i] + 0.055) / 1.055) ** 2.4)
            elif inColor[i] > 1.0:
                outColor.append(1.0)

        return tuple(outColor)


    def linear_to_srgb(self, inColor):
        outColor = []
        for i in range(4):
            if inColor[i] < 0.0:
                outColor.append(0.0)
            elif 0.0 <= inColor[i] <= 0.00313066844250063:
                outColor.append(float(inColor[i]) * 12.92)
            elif  0.00313066844250063 < inColor[i] <= 1.0: 
                outColor.append(1.055 * inColor[i] ** (float(1.0)/2.4) - 0.055)
            elif inColor[i] > 1.0:
                outColor.append(1.0)

        return tuple(outColor)


    def rgb_to_hsl(self, inColor):
        R = inColor[0]
        G = inColor[1]
        B = inColor[2]
        Cmax = max(R, G, B)
        Cmin = min(R, G, B)

        H = 0.0
        S = 0.0
        L = (Cmax+Cmin)/2.0

        if L == 1.0:
            S = 0.0
        elif 0.0 < L < 0.5:
            S = (Cmax-Cmin)/(Cmax+Cmin)
        elif L >= 0.5:
            S = (Cmax-Cmin)/(2.0-Cmax-Cmin)

        if S > 0.0:
            if R == Cmax:
                H = ((G-B)/(Cmax-Cmin))*60.0
            elif G == Cmax:
                H = ((B-R)/(Cmax-Cmin)+2.0)*60.0
            elif B == Cmax:
                H = ((R-G)/(Cmax-Cmin)+4.0)*60.0

        return [H, S, L]


    def hsl_to_rgb(self, inValue):
        H, S, L = inValue

        v1 = 0.0
        v2 = 0.0

        rgb = [0.0, 0.0, 0.0]

        if S == 0.0:
            rgb = [L, L, L]
        else:
            if L < 0.5:
                v1 = L*(S+1.0)
            elif L >= 0.5:
                v1 = L+S-L*S

            v2 = 2.0*L-v1

            H = H/360.0

            tR = H + 0.333333
            tG = H
            tB = H - 0.333333

            tList = [tR, tG, tB]

            for i, t in enumerate(tList):
                if t < 0.0:
                    t += 1.0
                elif t > 1.0:
                    t -= 1.0

                if t*6.0 < 1.0:
                    rgb[i] = v2+(v1-v2)*6.0*t
                elif t*2.0 < 1.0:
                    rgb[i] = v1
                elif t*3.0 < 2.0:
                    rgb[i] = v2+(v1-v2)*(0.666666 - t)*6.0
                else:
                    rgb[i] = v2

        return rgb


    def __del__(self):
        print('SX Tools: Exiting conversions')


# ------------------------------------------------------------------------
#    Layer Functions
# ------------------------------------------------------------------------
class SXTOOLS_layers(object):
    def __init__(self):
        return None


    def clear_layers(self, objs, targetLayer=None):
        if targetLayer is None:
            print('SX Tools: Clearing all layers')
            sxLayers = utils.find_color_layers(objs[0])
            for obj in objs:
                for sxLayer in sxLayers:
                    color = sxLayer.defaultColor
                    tools.apply_color([obj, ], sxLayer, color, True, 0.0)
                    setattr(obj.sxlayers[sxLayer.index], 'alpha', 1.0)
                    setattr(obj.sxlayers[sxLayer.index], 'visibility', True)
                    setattr(obj.sxlayers[sxLayer.index], 'blendMode', 'ALPHA')

            self.clear_uvs(objs, None)

        else:
            fillMode = targetLayer.layerType
            if fillMode == 'COLOR':
                for obj in objs:
                    color = targetLayer.defaultColor
                    tools.apply_color([obj, ], targetLayer, color, True, 0.0)
                    setattr(obj.sxlayers[targetLayer.index], 'alpha', 1.0)
                    setattr(obj.sxlayers[targetLayer.index], 'visibility', True)
                    setattr(obj.sxlayers[targetLayer.index], 'blendMode', 'ALPHA')
            elif (fillMode == 'UV') or (fillMode == 'UV4'):
                self.clear_uvs(objs, targetLayer)


    def clear_uvs(self, objs, targetLayer=None):
        objDicts = tools.selection_handler(objs)
        sxUVs = utils.find_default_values(objs[0], 'Dict')
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
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
                                if targetLayer.layerType == 'UV4':
                                    mesh.uv_layers[uvName].data[loop_idx].uv = sxUVs[uvName]
                                else:
                                    mesh.uv_layers[uvName].data[loop_idx].uv[fillChannels[i]] = uvValue

        bpy.ops.object.mode_set(mode=mode)


    def composite_layers(self, objs):
        if sxglobals.composite:
            # then = time.time()
            prefs = bpy.context.preferences.addons['sxtools'].preferences
            compLayers = utils.find_comp_layers(objs[0])
            shadingmode = bpy.context.scene.sxtools.shadingmode
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)

            if shadingmode == 'FULL':
                layer0 = utils.find_layer_from_index(objs[0], 0)
                layer1 = utils.find_layer_from_index(objs[0], 1)
                self.blend_layers(objs, compLayers, layer1, layer0)
            elif prefs.materialtype != 'SMP':
                self.blend_debug(objs, layer, shadingmode)

            sxglobals.composite = False
            # now = time.time()
            # print('Compositing duration: ', now-then, ' seconds')


    def blend_debug(self, objs, layer, shadingmode):
        mode = objs[0].mode
        active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        fillmode = layer.layerType
        channels = {'U': 0, 'V':1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers
            resultColors = vertexColors[obj.sxlayers['composite'].vertexColorLayer].data
            count = len(resultColors)
            colors = [None] * count * 4

            if fillmode == 'COLOR':
                layerColors = vertexColors[layer.vertexColorLayer].data
                layerColors.foreach_get('color', colors)

                if shadingmode == 'DEBUG':
                    for i in range(count):
                        color = colors[(0+i*4):(4+i*4)]
                        a = color[3]
                        colors[(0+i*4):(4+i*4)] = [color[0] * a, color[1] * a, color[2] * a, 1.0]
                elif shadingmode == 'ALPHA':
                    for i in range(count):
                        a = colors[3+i*4]
                        colors[(0+i*4):(4+i*4)] = [a, a, a, 1.0]

            # no difference between DEBUG and ALPHA for UV fillmode
            elif fillmode == 'UV':
                layerUVs = vertexUVs[layer.uvLayer0].data
                uv = channels[layer.uvChannel0]
                uvs = [None] * count * 2
                layerUVs.foreach_get('uv', uvs)

                for i in range(count):
                    value = uvs[(uv+i*2)]
                    colors[(0+i*4):(4+i*4)] = [value, value, value, 1.0]

            elif fillmode == 'UV4':
                if shadingmode == 'DEBUG':
                    layerUVs0 = vertexUVs[layer.uvLayer0].data
                    layerUVs1 = vertexUVs[layer.uvLayer1].data
                    layerUVs2 = vertexUVs[layer.uvLayer2].data
                    layerUVs3 = vertexUVs[layer.uvLayer3].data

                    uvs0 = [None] * count * 2
                    uvs1 = [None] * count * 2
                    uvs2 = [None] * count * 2
                    uvs3 = [None] * count * 2

                    layerUVs0.foreach_get('uv', uvs0)
                    layerUVs1.foreach_get('uv', uvs1)
                    layerUVs2.foreach_get('uv', uvs2)
                    layerUVs3.foreach_get('uv', uvs3)

                    uv0 = channels[layer.uvChannel0]
                    uv1 = channels[layer.uvChannel1]
                    uv2 = channels[layer.uvChannel2]
                    uv3 = channels[layer.uvChannel3]

                    for i in range(count):
                        color = [uvs0[(uv0+i*2)], uvs1[(uv1+i*2)], uvs2[(uv2+i*2)], uvs3[(uv3+i*2)]]
                        a = color[3]
                        colors[(0+i*4):(4+i*4)] = [color[0] * a, color[1] * a, color[2] * a, 1.0]

                elif shadingmode == 'ALPHA':
                    layerUVs = vertexUVs[layer.uvLayer3].data
                    uv = channels[layer.uvChannel3]
                    uvs = [None] * count * 2
                    layerUVs.foreach_get('uv', uvs)

                    for i in range(count):
                        value = uvs[(uv+i*2)]
                        colors[(0+i*4):(4+i*4)] = [value, value, value, 1.0]

            resultColors.foreach_set('color', colors)
            # bpy.context.view_layer.update()
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode=mode)
        bpy.context.view_layer.objects.active = active


    def blend_layers(self, objs, topLayerArray, baseLayer, resultLayer):
        mode = objs[0].mode
        active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        sxmaterial = bpy.data.materials['SXMaterial'].node_tree
        channels = {'U': 0, 'V': 1}
        midpoint = 0.5 # convert.srgb_to_linear([0.5, 0.5, 0.5, 1.0])[0]

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            vertexUVs = obj.data.uv_layers
            resultColors = vertexColors[resultLayer.vertexColorLayer].data
            baseLayerColors = vertexColors[baseLayer.vertexColorLayer].data
            baseAlpha = getattr(baseLayer, 'alpha')
            count = len(baseLayerColors)
            baseColors = [None] * count * 4
            baseLayerColors.foreach_get('color', baseColors)
            # colors = np.empty(count*4, dtype=np.float32)

            for layer in topLayerArray:
                colors = [None] * count * 4
                layerIdx = layer.index

                if not getattr(obj.sxlayers[layerIdx], 'visibility'):
                    continue
                else:
                    blend = getattr(obj.sxlayers[layerIdx], 'blendMode')
                    alpha = getattr(obj.sxlayers[layerIdx], 'alpha')
                    fillmode = getattr(obj.sxlayers[layerIdx], 'layerType')

                    if fillmode == 'COLOR':
                        layerColors = vertexColors[layer.vertexColorLayer].data
                        layerColors.foreach_get('color', colors)

                    elif (layer.name == 'gradient1') or (layer.name == 'gradient2'):
                        if layer.name == 'gradient1':
                            dv = sxmaterial.nodes['PaletteColor3'].outputs[0].default_value
                        else:
                            dv = sxmaterial.nodes['PaletteColor4'].outputs[0].default_value

                        layerUVs = vertexUVs[layer.uvLayer0].data

                        uvs = [None] * count * 2
                        layerUVs.foreach_get('uv', uvs)
                        uv = channels[layer.uvChannel0]

                        for i in range(count):
                            value = uvs[(uv+i*2)]
                            colors[(0+i*4):(4+i*4)] = [dv[0], dv[1], dv[2], value]

                    elif fillmode == 'UV':
                        layerUVs = vertexUVs[layer.uvLayer0].data

                        uvs = [None] * count * 2
                        layerUVs.foreach_get('uv', uvs)
                        uv = channels[layer.uvChannel0]

                        for i in range(count):
                            value = uvs[(uv+i*2)]
                            colors[(0+i*4):(4+i*4)] = [value, value, value, 1.0]

                    elif fillmode == 'UV4':
                        layerUVs0 = vertexUVs[layer.uvLayer0].data
                        layerUVs1 = vertexUVs[layer.uvLayer1].data
                        layerUVs2 = vertexUVs[layer.uvLayer2].data
                        layerUVs3 = vertexUVs[layer.uvLayer3].data

                        uvs0 = [None] * count * 2
                        uvs1 = [None] * count * 2
                        uvs2 = [None] * count * 2
                        uvs3 = [None] * count * 2

                        layerUVs0.foreach_get('uv', uvs0)
                        layerUVs1.foreach_get('uv', uvs1)
                        layerUVs2.foreach_get('uv', uvs2)
                        layerUVs3.foreach_get('uv', uvs3)

                        uv0 = channels[layer.uvChannel0]
                        uv1 = channels[layer.uvChannel1]
                        uv2 = channels[layer.uvChannel2]
                        uv3 = channels[layer.uvChannel3]

                        for i in range(count):
                            color = [uvs0[(uv0+i*2)], uvs1[(uv1+i*2)], uvs2[(uv2+i*2)], uvs3[(uv3+i*2)]]
                            a = color[3]
                            colors[(0+i*4):(4+i*4)] = [color[0] * a, color[1] * a, color[2] * a, 1.0]

                    for i in range(count):
                        top = Vector(colors[(0+i*4):(4+i*4)])
                        base = Vector(baseColors[(0+i*4):(4+i*4)])
                        a = top[3] * alpha

                        if blend == 'ALPHA':
                            base = top * a + base * (1 - a)
                            base[3] += a
                            if base[3] > 1.0:
                                base[3] = 1.0

                        elif blend == 'ADD':
                            base += top * a
                            base[3] += a
                            if base[3] > 1.0:
                                base[3] = 1.0

                        elif blend == 'MUL':
                            for j in range(3):
                                # layer2 lerp with white using (1-alpha), multiply with layer1
                                base[j] *= top[j] * a + (1 - a)

                        elif blend == 'OVR':
                            over = Vector([0.0, 0.0, 0.0, top[3]])
                            # over[3] += top[3]
                            b = over[3] * alpha
                            for j in range(3):
                                if base[j] < midpoint:
                                    over[j] = 2.0 * base[j] * top[j]
                                else:
                                    over[j] = 1.0 - 2.0 * (1.0 - base[j]) * (1.0 - top[j])
                            base = over * b + base * (1.0 - b)
                            base[3] += a
                            if base[3] > 1.0:
                                base[3] = 1.0

                        baseColors[(0+i*4):(4+i*4)] = base
                    resultColors.foreach_set('color', baseColors)
            # bpy.context.view_layer.update()
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode=mode)
        bpy.context.view_layer.objects.active = active


    # Takes vertex color set names, uv map names, and channel IDs as input.
    # CopyChannel does not perform translation of layernames to object data sets.
    # Expected input is [obj, ...], vertexcolorsetname, R/G/B/A, uvlayername, U/V, mode
    def copy_channel(self, objs, source, sourceChannel, target, targetChannel, fillMode):
        objDicts = tools.selection_handler(objs)
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
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
                        value = convert.color_to_luminance(color)
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
                        value = convert.color_to_luminance(color)
                        vertexUVs[target].data[idx].uv[channels[targetChannel]] = value

        bpy.ops.object.mode_set(mode=mode)


    # Generate 1-bit layer masks for color layers
    # so the faces can be re-colored in a game engine
    def generate_masks(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        channels = {'R': 0, 'G': 1, 'B': 2, 'A': 3, 'U': 0, 'V': 1}

        for obj in objs:
            vertexColors = obj.data.vertex_colors
            uvValues = obj.data.uv_layers
            layers = utils.find_color_layers(obj)
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


    def flatten_alphas(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            vertexUVs = obj.data.uv_layers
            channels = {'U': 0, 'V': 1}
            for layer in obj.sxlayers:
                alpha = layer.alpha
                if (layer.name == 'gradient1') or (layer.name == 'gradient2'):
                    for poly in obj.data.polygons:
                        for idx in poly.loop_indices:
                            vertexUVs[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]] *= alpha
                    layer.alpha = 1.0
                elif layer.name == 'overlay':
                    if layer.blendMode == 'OVR':
                        for poly in obj.data.polygons:
                            for idx in poly.loop_indices:
                                base = [0.5, 0.5, 0.5, 1.0]
                                top = [
                                    vertexUVs[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]],
                                    vertexUVs[layer.uvLayer1].data[idx].uv[channels[layer.uvChannel1]],
                                    vertexUVs[layer.uvLayer2].data[idx].uv[channels[layer.uvChannel2]],
                                    vertexUVs[layer.uvLayer3].data[idx].uv[channels[layer.uvChannel3]]][:]
                                for j in range(3):
                                    base[j] = (top[j] * (top[3] * alpha) + base[j] * (1 - (top[3] * alpha)))

                                vertexUVs[layer.uvLayer0].data[idx].uv[channels[layer.uvChannel0]] = base[0]
                                vertexUVs[layer.uvLayer1].data[idx].uv[channels[layer.uvChannel1]] = base[1]
                                vertexUVs[layer.uvLayer2].data[idx].uv[channels[layer.uvChannel2]] = base[2]
                                vertexUVs[layer.uvLayer3].data[idx].uv[channels[layer.uvChannel3]] = base[3]
                    else:
                        for poly in obj.data.polygons:
                            for idx in poly.loop_indices:
                                vertexUVs[layer.uvLayer3].data[idx].uv[channels[layer.uvChannel3]] *= alpha
                    layer.alpha = 1.0

        bpy.ops.object.mode_set(mode=mode)


    def merge_layers(self, objs, sourceLayer, targetLayer):
        if sourceLayer.index < targetLayer.index:
            baseLayer = sourceLayer
            topLayer = targetLayer
        else:
            baseLayer = targetLayer
            topLayer = sourceLayer

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.index], 'visibility', True)
            setattr(obj.sxlayers[targetLayer.index], 'visibility', True)

        self.blend_layers(objs, [topLayer, ], baseLayer, targetLayer)
        self.clear_layers(objs, sourceLayer)

        for obj in objs:
            setattr(obj.sxlayers[sourceLayer.index], 'blendMode', 'ALPHA')
            setattr(obj.sxlayers[targetLayer.index], 'blendMode', 'ALPHA')

            obj.sxtools.selectedlayer = targetLayer.index


    def paste_layer(self, objs, sourceLayer, targetLayer, fillMode):
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
            tools.layer_copy_manager(objs, sourceLayer, tempLayer)
            tools.layer_copy_manager(objs, targetLayer, sourceLayer)
            tools.layer_copy_manager(objs, tempLayer, targetLayer)
        elif fillMode == 'merge':
            self.merge_layers(objs, sourceLayer, targetLayer)
        else:
            tools.layer_copy_manager(objs, sourceLayer, targetLayer)


    def update_layer_palette(self, objs, layer):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
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
                        color = [uvValue0, uvValue1, uvValue2, uvValue3]
                    elif layer.layerType == 'UV':
                        uvValue = uvValues[loop_idx].uv[channels[layer.uvChannel0]]
                        color = [uvValue, uvValue, uvValue, uvValue]

                    if color[3] > 0.0:
                        colorArray.append(color)

        if len(colorArray) == 0:
            color = (0.0, 0.0, 0.0, 1.0)
            colorArray.append(color)

        # colorSet = set(colorArray)
        colorSet = set(tuple(color) for color in colorArray)
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


    def color_layers_to_values(self, objs):
        mode = objs[0].mode
        scene = bpy.context.scene.sxtools
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        channels = {'U': 0, 'V': 1}

        for i in range(5):
            layer = objs[0].sxlayers[i+1]
            palettecolor = utils.find_mode_color(objs, layer)
            setattr(scene, 'newpalette' + str(i), palettecolor)

        bpy.ops.object.mode_set(mode=mode)


    def material_layers_to_values(self, objs):
        mode = objs[0].mode
        scene = bpy.context.scene.sxtools
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        channels = {'U': 0, 'V': 1}
        layers = [7, 12, 13]

        for i, idx in enumerate(layers):
            layer = objs[0].sxlayers[idx]
            palettecolor = utils.find_mode_color(objs, layer)
            setattr(scene, 'newmaterial' + str(i), palettecolor)

        bpy.ops.object.mode_set(mode=mode)


    def update_layer_lightness(self, objs, layer):
        lightnessDict = mesh.calculate_luminance(objs, layer, 1)
        lightnessList = []
        for vertDict in lightnessDict.values():
            for valueList in vertDict.values():
                lightnessList.extend(valueList[1])
        if len(lightnessList) == 0:
            lightnessList.extend([0.0, ])

        lightness = max(lightnessList)
        sxglobals.lightnessUpdate = True
        bpy.context.scene.sxtools.lightnessvalue = lightness
        sxglobals.lightnessUpdate = False


    def __del__(self):
        print('SX Tools: Exiting layers')


# ------------------------------------------------------------------------
#    Mesh Analysis
# ------------------------------------------------------------------------
class SXTOOLS_mesh(object):
    def __init__(self):
        return None


    def calculate_bounding_box(self, vertDict):
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


    def ray_randomizer(self, count):
        hemiSphere = [None] * count
        for i in range(count):
            u1 = random.random()
            u2 = random.random()
            r = math.sqrt(u1)
            theta = 2*math.pi*u2

            x = r * math.cos(theta)
            y = r * math.sin(theta)

            hemiSphere[i] = (x, y, math.sqrt(max(0, 1 - u1)))

        return hemiSphere


    def calculate_direction(self, objs, directionVector):
        objDicts = tools.selection_handler(objs)
        mode = objs[0].mode
        objDirections = {}

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

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


    def ground_plane(self, size, pos):
        vertArray = []
        faceArray = []
        size *= 0.5

        vert = [(pos[0]-size, pos[1]-size, pos[2])]
        vertArray.extend(vert)
        vert = [(pos[0]+size, pos[1]-size, pos[2])]
        vertArray.extend(vert)
        vert = [(pos[0]-size, pos[1]+size, pos[2])]
        vertArray.extend(vert)
        vert = [(pos[0]+size, pos[1]+size, pos[2])]
        vertArray.extend(vert)

        face = [(0, 1, 3, 2)]
        faceArray.extend(face)

        mesh = bpy.data.meshes.new('groundPlane_mesh')
        groundPlane = bpy.data.objects.new('groundPlane', mesh)
        bpy.context.scene.collection.objects.link(groundPlane)

        mesh.from_pydata(vertArray, [], faceArray)
        mesh.update(calc_edges=True)

        # groundPlane.location = pos
        return groundPlane


    def find_root_pivot(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

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


    def calculate_occlusion(self, objs, rayCount, blend, dist, groundPlane, bias=0.01):
        objDicts = tools.selection_handler(objs)
        mode = objs[0].mode
        scene = bpy.context.scene
        contribution = 1.0/float(rayCount)
        hemiSphere = self.ray_randomizer(rayCount)
        mix = max(min(blend, 1.0), 0.0)
        forward = Vector((0.0, 0.0, 1.0))
        objOcclusions = {}

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = False

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        for obj in objs:
            vertLoopDict, vertPosDict, vertWorldPosDict = objDicts[obj]
            vertOccDict = {}
            if groundPlane:
                pivot = self.find_root_pivot([obj, ])
                pivot = (pivot[0], pivot[1], pivot[2] - 0.5)
                ground = self.ground_plane(20, pivot)

            for vert_idx, loop_indices in vertLoopDict.items():
                occValue = 1.0
                scnOccValue = 1.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])
                vertWorldLoc = Vector(vertWorldPosDict[vert_idx][0])
                vertWorldNormal = Vector(vertWorldPosDict[vert_idx][1])

                # Pass 1: Local space occlusion for individual object
                if 0.0 <= mix < 1.0:
                    biasVec = tuple([bias*x for x in vertNormal])
                    rotQuat = forward.rotation_difference(vertNormal)

                    # offset ray origin with normal bias
                    vertPos = (vertLoc[0] + biasVec[0], vertLoc[1] + biasVec[1], vertLoc[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        hit, loc, normal, index = obj.ray_cast(vertPos, sample, distance=dist)

                        if hit:
                            occValue -= contribution

                # Pass 2: Worldspace occlusion for scene
                if 0.0 < mix <= 1.0:
                    biasVec = tuple([bias*x for x in vertWorldNormal])
                    rotQuat = forward.rotation_difference(vertWorldNormal)

                    # offset ray origin with normal bias
                    scnVertPos = (vertWorldLoc[0] + biasVec[0], vertWorldLoc[1] + biasVec[1], vertWorldLoc[2] + biasVec[2])

                    for sample in hemiSphere:
                        sample = Vector(sample)
                        sample.rotate(rotQuat)

                        scnHit, scnLoc, scnNormal, scnIndex, scnObj, ma = scene.ray_cast(scene.view_layers[0], scnVertPos, sample, distance=dist)

                        if scnHit:
                            scnOccValue -= contribution

                for loop_idx in loop_indices:
                    vertOccDict[vert_idx] = float((occValue * (1.0 - mix)) + (scnOccValue * mix))

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


    def calculate_thickness(self, objs, rayCount, bias=0.000001):
        objDicts = tools.selection_handler(objs)
        mode = objs[0].mode
        contribution = 1.0/float(rayCount)
        hemiSphere = self.ray_randomizer(rayCount)
        bias = 1e-5
        forward = Vector((0, 0, 1))

        distances = []
        objThicknesses = {}

        for obj in objs:
            for modifier in obj.modifiers:
                if modifier.type == 'SUBSURF':
                    modifier.show_viewport = False

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # First pass to analyze ray hit distances,
        # then set max ray distance to half of median distance
        distHemiSphere = self.ray_randomizer(20)

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]

            for vert_idx, loop_indices in vertLoopDict.items():
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])

                # Invert normal to cast inside object
                invNormal = tuple([-1*x for x in vertNormal])

                biasVec = tuple([bias*x for x in invNormal])
                rotQuat = forward.rotation_difference(invNormal)

                # offset ray origin with normal bias
                vertPos = (vertLoc[0] + biasVec[0], vertLoc[1] + biasVec[1], vertLoc[2] + biasVec[2])

                for sample in distHemiSphere:
                    sample = Vector(sample)
                    sample.rotate(rotQuat)

                    hit, loc, normal, index = obj.ray_cast(vertPos, sample)

                    if hit:
                        distanceVec = Vector((loc[0] - vertPos[0], loc[1] - vertPos[1], loc[2] - vertPos[2]))
                        distances.append(distanceVec.length)

        rayDistance = statistics.median(distances) * 0.5

        for obj in objs:
            vertLoopDict = objDicts[obj][0]
            vertPosDict = objDicts[obj][1]
            vertDict = {}

            for vert_idx, loop_indices in vertLoopDict.items():
                thicknessValue = 0.0
                vertLoc = Vector(vertPosDict[vert_idx][0])
                vertNormal = Vector(vertPosDict[vert_idx][1])

                # Invert normal to cast inside object
                invNormal = tuple([-1*x for x in vertNormal])

                biasVec = tuple([bias*x for x in invNormal])
                rotQuat = forward.rotation_difference(invNormal)

                # offset ray origin with normal bias
                vertPos = (vertLoc[0] + biasVec[0], vertLoc[1] + biasVec[1], vertLoc[2] + biasVec[2])

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

    # mode 0: luminance, mode 1: HSL lightness
    def calculate_luminance(self, objs, layer, mode):
        objDicts = tools.selection_handler(objs)
        layerType = layer.layerType
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
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
                        if mode == 0:
                            luminance = convert.color_to_luminance(fvColor)
                        else:
                            luminance = convert.rgb_to_hsl(fvColor)[2]
                    elif layerType == 'UV4':
                        fvColor = [
                            uvValues0[loop_idx].uv[channels[layer.uvChannel0]],
                            uvValues1[loop_idx].uv[channels[layer.uvChannel1]],
                            uvValues2[loop_idx].uv[channels[layer.uvChannel2]],
                            uvValues3[loop_idx].uv[channels[layer.uvChannel3]]][:]
                        if mode == 0:
                            luminance = convert.color_to_luminance(fvColor)
                        else:
                            luminance = convert.rgb_to_hsl(fvColor)[2]
                    elif layerType == 'UV':
                        luminance = uvValues[loop_idx].uv[selChannel]
                    loopLuminances.append(luminance)
                vtxLuminances[vert_idx] = (loop_indices, loopLuminances)
            objLuminances[obj] = vtxLuminances

        bpy.ops.object.mode_set(mode=mode)
        return objLuminances


    def calculate_curvature(self, objs, normalize=False):
        objCurvatures = {}
        for obj in objs:
            vtxCurvatures = {}
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            for vert in bm.verts:
                numConnected = len(vert.link_edges)
                if numConnected > 0:
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
                else:
                    vtxCurvatures[vert.index] = 0.0
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
                    if vtxCurvature < 0.0:
                        vtxCurvatures[vert] = (vtxCurvature / float(minCurv)) * -0.5 + 0.5
                    elif vtxCurvature == 0.0:
                        vtxCurvatures[vert] = 0.5
                    else:
                        vtxCurvatures[vert] = (vtxCurvature / float(maxCurv)) * 0.5 + 0.5
        else:
            for vtxCurvatures in objCurvatures.values():
                for vert, vtxCurvature in vtxCurvatures.items():
                    vtxCurvatures[vert] = (vtxCurvature + 0.5)

        return objCurvatures


    def calculate_triangles(self, objs):
        count = 0
        for obj in objs:
            if 'sxDecimate2' in obj.modifiers.keys():
                count += obj.modifiers['sxDecimate2'].face_count

        return str(count)


    def __del__(self):
        print('SX Tools: Exiting mesh')


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------
class SXTOOLS_tools(object):
    def __init__(self):
        return None


    # Analyze if multi-object selection is in object or component mode,
    # return appropriate vertices
    def selection_handler(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
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
    def apply_color(self, objs, layer, color, overwrite, noise=0.0, mono=False, maskLayer=None):
        objDicts = self.selection_handler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        fillChannel3 = channels[layer.uvChannel3]
        fillValue = convert.color_to_luminance(color)

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

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
                                    vertexColors[loop_idx].color = [color[0], color[1], color[2], maskValues[loop_idx].color[3]]
                                else:
                                    if overwrite:
                                        vertexColors[loop_idx].color = [0.0, 0.0, 0.0, 0.0]
                            elif fillMode == 'UV4':
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = color[0]
                                    uvValues1[loop_idx].uv[fillChannel1] = color[1]
                                    uvValues2[loop_idx].uv[fillChannel2] = color[2]
                                    uvValues3[loop_idx].uv[fillChannel3] = maskValues[loop_idx].color[3]
                                else:
                                    if overwrite:
                                        uvValues0[loop_idx].uv[fillChannel0] = 0.0
                                        uvValues1[loop_idx].uv[fillChannel1] = 0.0
                                        uvValues2[loop_idx].uv[fillChannel2] = 0.0
                                        uvValues3[loop_idx].uv[fillChannel3] = 0.0
                            elif fillMode == 'UV':
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillValue * maskValues[loop_idx].color[3]
                                else:
                                    if overwrite:
                                        uvValues0[loop_idx].uv[fillChannel0] = 0.0
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
                                    vertexColors[loop_idx].color = [noiseColor[0], noiseColor[1], noiseColor[2], maskValues[loop_idx].color[3]]
                                else:
                                    if overwrite:
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
                                    if overwrite:
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
                        fillNoise = convert.color_to_luminance(color)
                        fillNoise += random.uniform(-fillNoise*noise, fillNoise*noise)
                        for loop_idx in loop_indices:
                            if maskLayer:
                                if maskValues[loop_idx].color[3] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillNoise * maskValues[loop_idx].color[3]
                                else:
                                    if overwrite:
                                        uvValues0[loop_idx].uv[fillChannel0] = 0.0
                            elif overwrite:
                                uvValues0[loop_idx].uv[fillChannel0] = fillNoise
                            else:
                                if uvValues0[loop_idx].uv[fillChannel0] > 0.0:
                                    uvValues0[loop_idx].uv[fillChannel0] = fillNoise

        bpy.ops.object.mode_set(mode=mode)


    def apply_lightness(self, objs, layer, newLightness):
        objDicts = self.selection_handler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        # fillChannel3 = channels[layer.uvChannel3]

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        lightnessDict = mesh.calculate_luminance(objs, layer, 1)
        lightnessList = []
        for vertDict in lightnessDict.values():
            for valueList in vertDict.values():
                lightnessList.extend(valueList[1])

        lightness = max(lightnessList)
        offset = newLightness-lightness

        for obj in objs:
            if fillMode == 'COLOR':
                vertexColors = obj.data.vertex_colors[layer.vertexColorLayer].data
            elif fillMode == 'UV':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
            elif fillMode == 'UV4':
                uvValues0 = obj.data.uv_layers[layer.uvLayer0].data
                uvValues1 = obj.data.uv_layers[layer.uvLayer1].data
                uvValues2 = obj.data.uv_layers[layer.uvLayer2].data
                # uvValues3 = obj.data.uv_layers[layer.uvLayer3].data

            vertLoopDict = defaultdict(list)
            vertLoopDict = objDicts[obj][0]

            for vert_idx, loop_indices in vertLoopDict.items():
                for loop_idx in loop_indices:
                    if fillMode == 'COLOR':
                        color = vertexColors[loop_idx].color
                        hsl = convert.rgb_to_hsl(color)
                        hsl[2] += offset
                        if hsl[2] > 1.0:
                            hsl[2] = 1.0
                        elif hsl[2] < 0.0:
                            hsl[2] = 0.0
                        rgb = convert.hsl_to_rgb(hsl)
                        vertexColors[loop_idx].color[0] = rgb[0]
                        vertexColors[loop_idx].color[1] = rgb[1]
                        vertexColors[loop_idx].color[2] = rgb[2]

                    elif fillMode == 'UV4':
                        rgb = (uvValues0[loop_idx].uv[fillChannel0], uvValues0[loop_idx].uv[fillChannel1], uvValues0[loop_idx].uv[fillChannel2])
                        hsl = convert.rgb_to_hsl(rgb)
                        hsl[2] += offset
                        if hsl[2] > 1.0:
                            hsl[2] = 1.0
                        elif hsl[2] < 0.0:
                            hsl[2] = 0.0
                        rgb = convert.hsl_to_rgb(hsl)
                        uvValues0[loop_idx].uv[fillChannel0] = rgb[0]
                        uvValues1[loop_idx].uv[fillChannel1] = rgb[1]
                        uvValues2[loop_idx].uv[fillChannel2] = rgb[2]

                    elif fillMode == 'UV':
                        uvValues0[loop_idx].uv[fillChannel0] += offset
                        if uvValues0[loop_idx].uv[fillChannel0] > 1.0:
                            uvValues0[loop_idx].uv[fillChannel0] = 1.0
                        if uvValues0[loop_idx].uv[fillChannel0] < 0.0:
                            uvValues0[loop_idx].uv[fillChannel0] = 0.0

        bpy.ops.object.mode_set(mode=mode)


    def update_recent_colors(self, color):
        scene = bpy.context.scene.sxtools
        palCols = [
            scene.fillpalette1[:],
            scene.fillpalette2[:],
            scene.fillpalette3[:],
            scene.fillpalette4[:],
            scene.fillpalette5[:],
            scene.fillpalette6[:],
            scene.fillpalette7[:],
            scene.fillpalette8[:]]
        colorArray = [
            color, palCols[0], palCols[1], palCols[2],
            palCols[3], palCols[4], palCols[5], palCols[6]]

        fillColor = color[:]
        if (fillColor not in palCols) and (fillColor[3] > 0.0):
            for i in range(8):
                setattr(scene, 'fillpalette' + str(i + 1), colorArray[i])


    def apply_ramp(self, objs, layer, ramp, rampmode, overwrite, mergebbx=True, noise=0.0, mono=False, maskLayer=None):
        scene = bpy.context.scene.sxtools
        objDicts = self.selection_handler(objs)
        fillMode = layer.layerType
        channels = {'U': 0, 'V': 1}
        fillChannel0 = channels[layer.uvChannel0]
        fillChannel1 = channels[layer.uvChannel1]
        fillChannel2 = channels[layer.uvChannel2]
        fillChannel3 = channels[layer.uvChannel3]

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        if rampmode == 'C':
            objValues = mesh.calculate_curvature(objs, False)
        elif rampmode == 'CN':
            objValues = mesh.calculate_curvature(objs, True)
        elif rampmode == 'OCC':
            objValues = mesh.calculate_occlusion(objs, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
        elif rampmode == 'LUM':
            objValues = mesh.calculate_luminance(objs, layer, 0)
        elif rampmode == 'THK':
            objValues = mesh.calculate_thickness(objs, scene.occlusionrays, scene.occlusionbias)
        elif rampmode == 'DIR':
            inclination = (bpy.context.scene.sxtools.dirInclination - 90.0)* (2*math.pi)/360.0
            angle = (bpy.context.scene.sxtools.dirAngle + 90) * (2*math.pi)/360.0
            directionVector = (math.sin(inclination) * math.cos(angle), math.sin(inclination) * math.sin(angle), math.cos(inclination))
            directionVector = Vector(directionVector)
            objValues = mesh.calculate_direction(objs, directionVector)

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
                bbx = mesh.calculate_bounding_box(vertPosDict)
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
                        if xdiv == 0.0:
                            xdiv = 1.0
                        ratioRaw = ((fvPos[0] - xmin) / xdiv)
                    elif rampmode == 'Y':
                        ydiv = float(ymax - ymin)
                        if ydiv == 0.0:
                            ydiv = 1.0
                        ratioRaw = ((fvPos[1] - ymin) / ydiv)
                    elif rampmode == 'Z':
                        zdiv = float(zmax - zmin)
                        if zdiv == 0.0:
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
                            ratio.append(max(min(rt, 1.0), 0.0))
                        evalColor = ramp.color_ramp.evaluate(ratio[i])
                        for i, value in enumerate(evalColor):
                            color[i] = value
                    else:
                        ratio = max(min(ratioRaw, 1.0), 0.0)
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
                            fillValue = convert.color_to_luminance(color)
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
                                fillValue = convert.color_to_luminance(color)
                                uvValues0[loop_idx].uv[fillChannel0] = (fillValue + noiseColor[0])

        bpy.ops.object.mode_set(mode=mode)


    def select_mask(self, objs, layers, inverse):
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        objDicts = self.selection_handler(objs)
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


    def assign_set(self, objs, setvalue, setmode):
        mode = objs[0].mode
        modeDict = {
            'CRS': 'SubSurfCrease',
            'BEV': 'BevelWeight'}
        weight = setvalue
        modename = modeDict[setmode]

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        for obj in objs:
            bm = bmesh.from_edit_mesh(obj.data)
            mesh = obj.data

            if setmode == 'CRS':
                if modename in bm.edges.layers.crease.keys():
                    bmlayer = bm.edges.layers.crease[modename]
                else:
                    bmlayer = bm.edges.layers.crease.new(modename)
            else:
                if modename in bm.edges.layers.bevel_weight.keys():
                    bmlayer = bm.edges.layers.bevel_weight[modename]
                else:
                    bmlayer = bm.edges.layers.bevel_weight.new(modename)

            selectedEdges = [edge for edge in bm.edges if edge.select]
            for edge in selectedEdges:
                edge[bmlayer] = weight
                if setmode == 'CRS':
                    mesh.edges[edge.index].crease = weight
                    if weight == 1.0:
                        edge.smooth = False
                        mesh.edges[edge.index].use_edge_sharp = True
                    else:
                        edge.smooth = True
                        mesh.edges[edge.index].use_edge_sharp = False

            bmesh.update_edit_mesh(obj.data)

        bpy.ops.object.mode_set(mode=mode)


    def select_set(self, objs, setvalue, setmode, clearsel=False):
        modeDict = {
            'CRS': 'SubSurfCrease',
            'BEV': 'BevelWeight'}
        weight = setvalue
        modename = modeDict[setmode]

        bpy.context.view_layer.objects.active = objs[0]

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        if clearsel:
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        for obj in objs:
            bm = bmesh.from_edit_mesh(obj.data)
            mesh = obj.data

            if setmode == 'CRS':
                if modename in bm.edges.layers.crease.keys():
                    bmlayer = bm.edges.layers.crease[modename]
                else:
                    bmlayer = bm.edges.layers.crease.new(modename)
            else:
                if modename in bm.edges.layers.bevel_weight.keys():
                    bmlayer = bm.edges.layers.bevel_weight[modename]
                else:
                    bmlayer = bm.edges.layers.bevel_weight.new(modename)

            for edge in bm.edges:
                if math.isclose(edge[bmlayer], weight, abs_tol=0.1):
                    edge.select = True

            bmesh.update_edit_mesh(obj.data)


    # takes any layers in layerview, translates to copy_channel batches
    def layer_copy_manager(self, objs, sourceLayer, targetLayer):
        sourceType = sourceLayer.layerType
        targetType = targetLayer.layerType

        if sourceType == 'COLOR' and targetType == 'COLOR':
            sourceVertexColors = sourceLayer.vertexColorLayer
            layers.copy_channel(objs, sourceVertexColors, None, targetLayer.vertexColorLayer, None, 4)
        elif sourceType == 'COLOR' and targetType == 'UV4':
            sourceVertexColors = sourceLayer.vertexColorLayer
            targetUVs = [targetLayer.uvLayer0, targetLayer.uvLayer1, targetLayer.uvLayer2, targetLayer.uvLayer3]
            sourceChannels = ['R', 'G', 'B', 'A']
            targetChannels = [targetLayer.uvChannel0, targetLayer.uvChannel1, targetLayer.uvChannel2, targetLayer.uvChannel3]
            for i in range(4):
                layers.copy_channel(objs, sourceVertexColors, sourceChannels[i], targetUVs[i], targetChannels[i], 3)
        elif sourceType == 'UV4' and targetType == 'COLOR':
            sourceUVs = [sourceLayer.uvLayer0, sourceLayer.uvLayer1, sourceLayer.uvLayer2, sourceLayer.uvLayer3]
            sourceChannels = [sourceLayer.uvChannel0, sourceLayer.uvChannel1, sourceLayer.uvChannel2, sourceLayer.uvChannel3]
            targetChannels = ['R', 'G', 'B', 'A']
            for i in range(4):
                layers.copy_channel(objs, sourceUVs[i], sourceChannels[i], targetLayer.vertexColorLayer, targetChannels[i], 5)
        elif sourceType == 'UV4' and targetType == 'UV':
            targetUVs = targetLayer.uvLayer0
            targetChannel = targetLayer.uvChannel0
            layers.copy_channel(objs, sourceLayer.name, None, targetUVs, targetChannel, 6)
        elif sourceType == 'COLOR' and targetType == 'UV':
            sourceVertexColors = sourceLayer.vertexColorLayer
            targetChannel = targetLayer.uvChannel0
            layers.copy_channel(objs, sourceVertexColors, None, targetLayer.uvLayer0, targetChannel, 1)
        elif sourceType == 'UV' and targetType == 'UV':
            sourceUVs = sourceLayer.uvLayer0
            targetUVs = targetLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            targetChannel = targetLayer.uvChannel0
            layers.copy_channel(objs, sourceUVs, sourceChannel, targetUVs, targetChannel, 0)
        elif sourceType == 'UV' and targetType == 'COLOR':
            sourceUVs = sourceLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            layers.copy_channel(objs, sourceUVs, sourceChannel, targetLayer.vertexColorLayer, None, 2)
        elif sourceType == 'UV' and targetType == 'UV4':
            sourceUVs = sourceLayer.uvLayer0
            sourceChannel = sourceLayer.uvChannel0
            targetUVs = [targetLayer.uvLayer0, targetLayer.uvLayer1, targetLayer.uvLayer2, targetLayer.uvLayer3]
            targetChannels = [targetLayer.uvChannel0, targetLayer.uvChannel1, targetLayer.uvChannel2, targetLayer.uvChannel3]
            for i in range(4):
                layers.copy_channel(objs, sourceUVs, sourceChannel, targetUVs[i], targetChannels[i], 0)


    def apply_palette(self, objs, palette, noise, mono):
        palette = [
            bpy.context.scene.sxpalettes[palette].color0,
            bpy.context.scene.sxpalettes[palette].color1,
            bpy.context.scene.sxpalettes[palette].color2,
            bpy.context.scene.sxpalettes[palette].color3,
            bpy.context.scene.sxpalettes[palette].color4]

        for idx in range(1, 6):
            layer = utils.find_layer_from_index(objs[0], idx)
            color = palette[idx - 1] # convert.srgb_to_linear(palette[idx - 1])
            bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor'+str(idx-1)].outputs[0].default_value = color

            self.apply_color(objs, layer, color, False, noise, mono)


    def apply_material(self, objs, targetLayer, material, overwrite, noise, mono):
        material = bpy.context.scene.sxmaterials[material]

        self.apply_color(objs, objs[0].sxlayers['smoothness'], material.color2, overwrite, noise, mono)
        self.apply_color(objs, objs[0].sxlayers['metallic'], material.color1, overwrite, noise, mono)
        self.apply_color(objs, objs[0].sxlayers[7], material.color0, overwrite, noise, mono)


    def add_modifiers(self, objs):
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = obj.sxtools.smoothangle * (2*math.pi)/360.0

        for obj in objs:
            if 'sxMirror' not in obj.modifiers.keys():
                obj.modifiers.new(type='MIRROR', name='sxMirror')
                obj.modifiers['sxMirror'].show_viewport = False
                obj.modifiers['sxMirror'].show_expanded = False
                obj.modifiers['sxMirror'].use_axis[0] = False
                obj.modifiers['sxMirror'].use_axis[1] = False
                obj.modifiers['sxMirror'].use_axis[2] = False
                obj.modifiers['sxMirror'].use_clip = True
                obj.modifiers['sxMirror'].use_mirror_merge = True
            if 'sxSubdivision' not in obj.modifiers.keys():
                obj.modifiers.new(type='SUBSURF', name='sxSubdivision')
                obj.modifiers['sxSubdivision'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxSubdivision'].show_expanded = False
                obj.modifiers['sxSubdivision'].quality = 6
                obj.modifiers['sxSubdivision'].levels = obj.sxtools.subdivisionlevel
                obj.modifiers['sxSubdivision'].uv_smooth = 'NONE'
                obj.modifiers['sxSubdivision'].show_only_control_edges = True
                obj.modifiers['sxSubdivision'].show_on_cage = True
            if 'sxBevel' not in  obj.modifiers.keys():
                obj.modifiers.new(type='BEVEL', name='sxBevel')
                obj.modifiers['sxBevel'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxBevel'].show_expanded = False
                obj.modifiers['sxBevel'].width = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].width_pct = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].segments = obj.sxtools.bevelsegments
                obj.modifiers['sxBevel'].use_clamp_overlap = True
                obj.modifiers['sxBevel'].loop_slide = True
                obj.modifiers['sxBevel'].mark_sharp = False
                obj.modifiers['sxBevel'].harden_normals = False
                obj.modifiers['sxBevel'].offset_type = 'OFFSET' # 'WIDTH' 'PERCENT'
                obj.modifiers['sxBevel'].limit_method = 'WEIGHT'
                obj.modifiers['sxBevel'].miter_outer = 'MITER_ARC'
            if 'sxWeld' not in obj.modifiers.keys():
                obj.modifiers.new(type='WELD', name='sxWeld')
                if obj.sxtools.weldthreshold == 0:
                    obj.modifiers['sxWeld'].show_viewport = False
                else:
                    obj.modifiers['sxWeld'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxWeld'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxWeld'].show_expanded = False
                obj.modifiers['sxWeld'].merge_threshold = obj.sxtools.weldthreshold
            if 'sxDecimate' not in obj.modifiers.keys():
                obj.modifiers.new(type='DECIMATE', name='sxDecimate')
                if (obj.sxtools.subdivisionlevel == 0) or (obj.sxtools.decimation == 0.0):
                    obj.modifiers['sxDecimate'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxDecimate'].show_expanded = False
                obj.modifiers['sxDecimate'].decimate_type = 'DISSOLVE'
                obj.modifiers['sxDecimate'].angle_limit = obj.sxtools.decimation * (math.pi/180.0)
                obj.modifiers['sxDecimate'].use_dissolve_boundaries = True
                obj.modifiers['sxDecimate'].delimit = {'SHARP', 'UV'}
            if 'sxDecimate2' not in obj.modifiers.keys():
                obj.modifiers.new(type='DECIMATE', name='sxDecimate2')
                if (obj.sxtools.subdivisionlevel == 0) or (obj.sxtools.decimation == 0.0):
                    obj.modifiers['sxDecimate2'].show_viewport = False
                else:
                    obj.modifiers['sxDecimate2'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxDecimate2'].show_expanded = False
                obj.modifiers['sxDecimate2'].decimate_type = 'COLLAPSE'
                obj.modifiers['sxDecimate2'].ratio = 0.99
                obj.modifiers['sxDecimate2'].use_collapse_triangulate = True
            if 'sxWeightedNormal' not in obj.modifiers.keys():
                obj.modifiers.new(type='WEIGHTED_NORMAL', name='sxWeightedNormal')
                obj.modifiers['sxWeightedNormal'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxWeightedNormal'].show_expanded = False
                obj.modifiers['sxWeightedNormal'].mode = 'FACE_AREA_WITH_ANGLE'
                obj.modifiers['sxWeightedNormal'].weight = 95
                if hardmode == 'SMOOTH':
                    obj.modifiers['sxWeightedNormal'].keep_sharp = False
                else:
                    obj.modifiers['sxWeightedNormal'].keep_sharp = True


    def apply_modifiers(self, objs):
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            if 'sxMirror' in obj.modifiers.keys():
                if obj.modifiers['sxMirror'].show_viewport == False:
                    bpy.ops.object.modifier_remove(modifier='sxMirror')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxMirror')
            if 'sxSubdivision' in obj.modifiers.keys():
                if obj.modifiers['sxSubdivision'].levels == 0:
                    bpy.ops.object.modifier_remove(modifier='sxSubdivision')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxSubdivision')
            if 'sxBevel' in obj.modifiers.keys():
                if obj.sxtools.bevelsegments == 0:
                    bpy.ops.object.modifier_remove(modifier='sxBevel')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxBevel')
            if 'sxWeld' in obj.modifiers.keys():
                if obj.sxtools.weldthreshold == 0:
                    bpy.ops.object.modifier_remove(modifier='sxWeld')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxWeld')
            if 'sxDecimate' in obj.modifiers.keys():
                if (obj.sxtools.subdivisionlevel == 0) or (obj.sxtools.decimation == 0.0):
                    bpy.ops.object.modifier_remove(modifier='sxDecimate')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxDecimate')
            if 'sxDecimate2' in obj.modifiers.keys():
                if (obj.sxtools.subdivisionlevel == 0) or (obj.sxtools.decimation == 0.0):
                    bpy.ops.object.modifier_remove(modifier='sxDecimate2')
                else:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxDecimate2')
            if 'sxWeightedNormal' in obj.modifiers.keys():
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxWeightedNormal')


    def remove_modifiers(self, objs):
        modifiers = ['sxMirror', 'sxSubdivision', 'sxBevel', 'sxWeld', 'sxDecimate', 'sxDecimate2', 'sxEdgeSplit', 'sxWeightedNormal']
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            for modifier in modifiers:
                if modifier in obj.modifiers.keys():
                    bpy.ops.object.modifier_remove(modifier=modifier)


    def group_objects(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        pivot = mesh.find_root_pivot(objs)

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


    def create_uvset0(self, objs):
        active = bpy.context.view_layer.objects.active
        for obj in objs:
            bpy.context.view_layer.objects.active = obj
            setCount = len(obj.data.uv_layers)
            if setCount == 0:
                print('SX Tools: ', obj.name, ' has no UV Sets')
            elif setCount > 6:
                base = obj.data.uv_layers[0]
                if base.name != 'UVSet0':
                    print('SX Tools: ', obj.name, ' does not have enough free UV Set slots for the operation (2 free slots needed)')
            else:
                base = obj.data.uv_layers[0]
                if 'UVSet' not in base.name:
                    base.name = 'UVSet0'
                elif base.name == 'UVSet1':
                    obj.data.uv_layers.new(name='UVSet0')
                    for i in range(setCount):
                        uvName = obj.data.uv_layers[0].name
                        obj.data.uv_layers.active_index = 0
                        bpy.ops.mesh.uv_texture_add()
                        obj.data.uv_layers.active_index = 0
                        bpy.ops.mesh.uv_texture_remove()
                        obj.data.uv_layers[setCount].name = uvName
                else:
                    print('SX Tools: ', obj.name, ' has an unknown UV Set configuration')

        bpy.context.view_layer.objects.active = active


    def revert_objects(self, objs):
        self.remove_modifiers(objs)

        layers.clear_uvs(objs, objs[0].sxlayers['overlay'])
        layers.clear_uvs(objs, objs[0].sxlayers['occlusion'])
        layers.clear_uvs(objs, objs[0].sxlayers['metallic'])
        layers.clear_uvs(objs, objs[0].sxlayers['smoothness'])
        layers.clear_uvs(objs, objs[0].sxlayers['transmission'])


    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Validation Functions
# ------------------------------------------------------------------------
class SXTOOLS_validate(object):
    def __init__(self):
        return None


    def validate_objects(self, objs):
        ok = self.test_palette_layers(objs)

        if ok:
            print('SX Tools: Selected objects passed validation tests')
            return True
        else:
            print('SX Tools: Selected objects failed validation tests')
            return False


    # Check that objects are grouped
    def test_parents(self, objs):
        for obj in objs:
            if obj.parent is None:
                message_box('Object is not in a group: ' + obj.name)
                return False

        return True


    # if paletted, fail if layer colorcount > 1
    def test_palette_layers(self, objs):
        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        for obj in objs:
            if obj.sxtools.category != 'DEFAULT':
                mesh = obj.data
                for i in range(5):
                    colorArray = []
                    layer = utils.find_layer_from_index(obj, i+1)
                    vertexColors = mesh.vertex_colors[layer.vertexColorLayer].data

                    for poly in mesh.polygons:
                        for loop_idx in poly.loop_indices:
                            colorArray.append(vertexColors[loop_idx].color[:])

                    colorSet = set(colorArray)

                    if i == 0:
                        if len(colorSet) > 1:
                            message_box('Multiple colors in ' + obj.name + ' layer' + str(i+1))
                            bpy.ops.object.mode_set(mode=mode)
                            return False
                    else:
                        if len(colorSet) > 2:
                            message_box('Multiple colors in ' + obj.name + ' layer' + str(i+1))
                            bpy.ops.object.mode_set(mode=mode)
                            return False

        bpy.ops.object.mode_set(mode=mode)
        return True


    # if paletted, check that emissive faces have color in static channel
    def test_emissives(self, objs):
        pass


    def __del__(self):
        print('SX Tools: Exiting validate')


# ------------------------------------------------------------------------
#    Exporting Functions
# ------------------------------------------------------------------------
class SXTOOLS_export(object):
    def __init__(self):
        return None


    # LOD levels:
    # If subdivision enabled:
    #   LOD0 - Maximum subdivision and bevels
    #   LOD1 - Subdiv 1, bevels
    #   LOD2 - Control cage
    # If bevels only:
    #   LOD0 - Maximum bevel segments
    #   LOD1 - Control cage
    # NOTE: In case of bevels, prefer even-numbered segment counts!
    #       Odd-numbered bevels often generate incorrect vertex colors
    def generate_lods(self, objs):
        prefs = bpy.context.preferences.addons['sxtools'].preferences
        orgObjArray = objs[:]
        nameArray = []
        newObjArray = []
        activeObj = bpy.context.view_layer.objects.active
        scene = bpy.context.scene.sxtools

        bbx_x = []
        bbx_y = []
        bbx_z = []
        for obj in orgObjArray:
            corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            for corner in corners:
                bbx_x.append(corner[0])
                bbx_y.append(corner[1])
                bbx_z.append(corner[2])
        xmin, xmax = min(bbx_x), max(bbx_x)
        ymin, ymax = min(bbx_y), max(bbx_y)
        zmin, zmax = min(bbx_z), max(bbx_z)

        bbxheight = zmax - zmin

        # Make sure source and export Collections exist
        if 'ExportObjects' not in bpy.data.collections.keys():
            exportObjects = bpy.data.collections.new('ExportObjects')
        else:
            exportObjects = bpy.data.collections['ExportObjects']

        if 'SourceObjects' not in bpy.data.collections.keys():
            sourceObjects = bpy.data.collections.new('SourceObjects')
        else:
            sourceObjects = bpy.data.collections['SourceObjects']

        lodCount = 1
        for obj in orgObjArray:
            nameArray.append((obj.name[:], obj.data.name[:]))
            if obj.sxtools.subdivisionlevel >= 1:
                lodCount = min(3, obj.sxtools.subdivisionlevel + 1)
            elif (obj.sxtools.subdivisionlevel == 0) and ((obj.sxtools.bevelsegments) > 0):
                lodCount = 2

        if lodCount > 1:
            for i in range(lodCount):
                print('SX Tools: Generating LOD' + str(i))
                if i == 0:
                    for obj in orgObjArray:
                        obj.data.name = obj.data.name + '_LOD' + str(i)
                        obj.name = obj.name + '_LOD' + str(i)
                        newObjArray.append(obj)
                        if scene.exportquality == 'LO':
                            sourceObjects.objects.link(obj)
                else:
                    for j, obj in enumerate(orgObjArray):
                        newObj = obj.copy()
                        newObj.data = obj.data.copy()

                        newObj.data.name = nameArray[j][1] + '_LOD' + str(i)
                        newObj.name = nameArray[j][0] + '_LOD' + str(i)

                        newObj.location += Vector((0.0, 0.0, (bbxheight+prefs.lodoffset)*i))

                        bpy.context.scene.collection.objects.link(newObj)
                        exportObjects.objects.link(newObj)

                        newObj.parent = bpy.context.view_layer.objects[obj.parent.name]

                        bpy.ops.object.select_all(action='DESELECT')
                        newObj.select_set(True)
                        bpy.context.view_layer.objects.active = newObj

                        if i == 1:
                            if obj.sxtools.subdivisionlevel > 0:
                                newObj.sxtools.subdivisionlevel = 1
                                # newObj.sxtools.weldthreshold = 0
                                # newObj.modifiers['sxSubdivision'].levels = 1
                                # newObj.modifiers['sxSubdivision'].show_viewport = True
                                # newObj.modifiers['sxWeld'].show_viewport = False
                                # newObj.modifiers['sxDecimate'].show_viewport = False
                                # newObj.modifiers['sxDecimate2'].show_viewport = False
                                if obj.sxtools.bevelsegments > 0:
                                    newObj.sxtools.bevelsegments = obj.sxtools.bevelsegments
                                    # newObj.modifiers['sxBevel'].show_viewport = True
                                else:
                                    newObj.sxtools.bevelsegments = 0
                                    # newObj.modifiers['sxBevel'].show_viewport = False
                                # if ('sxBevel' in sel.modifiers.keys()) and (sel.modifiers['sxBevel'].segments > 0):
                                #     newObj.modifiers['sxBevel'].show_viewport = True
                                # else:
                                #     newObj.sxtools.bevelsegments = 0
                                #     newObj.modifiers['sxBevel'].show_viewport = False
                            elif obj.sxtools.subdivisionlevel == 0:
                                newObj.sxtools.subdivisionlevel = 0
                                newObj.sxtools.bevelsegments = 0
                                newObj.sxtools.weldthreshold = 0
                                # newObj.modifiers['sxSubdivision'].levels = 0
                                # newObj.modifiers['sxSubdivision'].show_viewport = False
                                # newObj.modifiers['sxWeld'].show_viewport = False
                                # newObj.modifiers['sxDecimate'].show_viewport = False
                                # newObj.modifiers['sxDecimate2'].show_viewport = False
                                # newObj.modifiers['sxBevel'].show_viewport = False
                        else:
                            newObj.sxtools.subdivisionlevel = 0
                            newObj.sxtools.bevelsegments = 0
                            newObj.sxtools.weldthreshold = 0
                            # newObj.modifiers['sxSubdivision'].levels = 0
                            # newObj.modifiers['sxBevel'].show_viewport = False
                            # newObj.modifiers['sxWeld'].show_viewport = False
                            # newObj.modifiers['sxDecimate'].show_viewport = False
                            # newObj.modifiers['sxDecimate2'].show_viewport = False

                        newObjArray.append(newObj)

        # activeObj.select_set(True)
        bpy.context.view_layer.objects.active = activeObj

        return orgObjArray, nameArray, newObjArray


    def convert_to_linear(self, objs):
        for obj in objs:
            vertexColors = obj.data.vertex_colors
            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    vCol = vertexColors['VertexColor0'].data[idx].color
                    vertexColors['VertexColor0'].data[idx].color = convert.srgb_to_linear(vCol)


    # This is a project-specific batch operation.
    # These should be adapted to the needs of the game,
    # baking category-specific values to achieve
    # consistent project-wide looks.
    def process_objects(self, objs):
        then = time.time()
        scene = bpy.context.scene.sxtools
        viewlayer = bpy.context.view_layer
        orgObjNames = {}

        # Make sure export and source Collections exist
        if 'ExportObjects' not in bpy.data.collections.keys():
            exportObjects = bpy.data.collections.new('ExportObjects')
        else:
            exportObjects = bpy.data.collections['ExportObjects']

        if 'SourceObjects' not in bpy.data.collections.keys():
            sourceObjects = bpy.data.collections.new('SourceObjects')
        else:
            sourceObjects = bpy.data.collections['SourceObjects']

        # Make sure objects are in groups
        for obj in objs:
            if obj.parent is None:
                obj.hide_viewport = False
                viewlayer.objects.active = obj
                tools.group_objects([obj, ])

        # Make sure auto-smooth is on
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = obj.sxtools.smoothangle * (2*math.pi)/360.0
            if '_mesh' not in obj.data.name:
                obj.data.name = obj.name + '_mesh'

        # Make sure all objects have UVSet0
        tools.create_uvset0(objs)

        # Remove empties from selected objects
        for sel in viewlayer.objects.selected:
            if sel.type != 'MESH':
                sel.select_set(False)

        # Create modifiers
        tools.add_modifiers(objs)

        # Create high-poly bake meshes
        if scene.exportquality == 'HI':
            newObjs = []
            lodObjs = []

            groups = utils.find_groups(objs)
            for group in groups:
                orgGroup = bpy.data.objects.new('empty', None)
                bpy.context.scene.collection.objects.link(orgGroup)
                orgGroup.empty_display_size = 2
                orgGroup.empty_display_type = 'PLAIN_AXES'
                orgGroup.location = group.location
                orgGroup.name = group.name + '_org'
                orgGroup.hide_viewport = True
                sourceObjects.objects.link(orgGroup)
                exportObjects.objects.link(group)

            for obj in objs:
                sourceObjects.objects.link(obj)
                orgObjNames[obj] = [obj.name, obj.data.name][:]
                obj.data.name = obj.data.name + '_org'
                obj.name = obj.name + '_org'

                newObj = obj.copy()
                newObj.data = obj.data.copy()
                newObj.name = orgObjNames[obj][0]
                newObj.data.name = orgObjNames[obj][1]
                bpy.context.scene.collection.objects.link(newObj)
                exportObjects.objects.link(newObj)

                if obj.sxtools.lodmeshes:
                    lodObjs.append(newObj)
                else:
                    newObjs.append(newObj)

                obj.parent = viewlayer.objects[obj.parent.name + '_org']

            if len(lodObjs) > 0:
                orgObjArray, nameArray, newObjArray = export.generate_lods(lodObjs)
                for newObj in newObjArray:
                    newObjs.append(newObj)

            objs = newObjs

        for obj in objs:
            obj.select_set(False)

        viewlayer.objects.active = objs[0]

        # Begin category-specific compositing operations
        for obj in objs:
            if obj.sxtools.category == '':
                obj.sxtools.category == 'DEFAULT'

        for obj in viewlayer.objects:
            if obj.type == 'MESH' and obj.hide_viewport == False:
                obj.hide_viewport = True

        # Mandatory to update visibility?
        viewlayer.update()

        categoryList = list(sxglobals.categoryDict.keys())
        categories = []
        for category in categoryList:
            categories.append(category.replace(" ", "_").upper())
        for category in categories:
            categoryObjs = []
            for obj in objs:
                if obj.sxtools.category == category:
                    categoryObjs.append(obj)

            if len(categoryObjs) > 0:
                groupList = utils.find_groups(categoryObjs)

                for group in groupList:
                    createLODs = False
                    groupObjs = utils.find_children(group, categoryObjs)
                    viewlayer.objects.active = groupObjs[0]
                    for obj in groupObjs:
                        if obj.sxtools.lodmeshes:
                            createLODs = True
                        obj.hide_viewport = False
                        obj.select_set(True)

                    if category == 'DEFAULT':
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_default(groupObjs)
                    elif category == 'PALETTED':
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_paletted(groupObjs)
                    elif category == 'VEHICLES':
                        for obj in groupObjs:
                            if ('wheel' in obj.name) or ('tire' in obj.name):
                                scene.occlusionblend = 0.0
                            else:
                                scene.occlusionblend = 0.5
                            if obj.name.endswith('_roof') or obj.name.endswith('_frame') or obj.name.endswith('_dash') or obj.name.endswith('_hood') or ('bumper' in obj.name):
                                obj.modifiers['sxDecimate2'].use_symmetry = True
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        if (scene.exportquality == 'HI') and (createLODs is True):
                            for i in range(3):
                                lodObjs = []
                                for obj in groupObjs:
                                    if '_LOD'+str(i) in obj.name:
                                        lodObjs.append(obj)
                                        # obj.select_set(True)
                                        obj.hide_viewport = False
                                    else:
                                        # obj.select_set(False)
                                        obj.hide_viewport = True
                                viewlayer.objects.active = lodObjs[0]
                                self.process_vehicles(lodObjs)
                        else:
                            self.process_vehicles(groupObjs)
                    elif category == 'BUILDINGS':
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_buildings(groupObjs)
                    elif category == 'TREES':
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_trees(groupObjs)
                    elif category == 'TRANSPARENT':
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_default(groupObjs)
                    else:
                        if scene.exportquality == 'HI':
                            tools.apply_modifiers(groupObjs)
                        self.process_default(groupObjs)

                    for obj in groupObjs:
                        obj.select_set(False)
                        obj.hide_viewport = True

                now = time.time()
                print('SX Tools: ', category, ' / ', len(groupList), ' groups duration: ', now-then, ' seconds')

        for obj in viewlayer.objects:
            if (scene.exportquality == 'HI') and ('_org' in obj.name):
                obj.hide_viewport = True
            elif obj.type == 'MESH':
                obj.hide_viewport = False

        # Bake Overlay for export
        if scene.numoverlays > 0:
            layers.flatten_alphas(objs)

        # LOD mesh generation for low-detail
        if scene.exportquality == 'LO':
            nonLodObjs = []
            for obj in objs:
                if obj.sxtools.lodmeshes is True:
                    if '_LOD' not in obj.name:
                        nonLodObjs.append(obj)
                else:
                    obj.select_set(True)

            if len(nonLodObjs) > 0:
                orgSelArray, nameArray, newObjArray = export.generate_lods(nonLodObjs)
                bpy.ops.object.select_all(action='DESELECT')
                for obj in orgSelArray:
                    obj.select_set(True)
                for obj in newObjArray:
                    obj.select_set(True)

        if scene.exportquality == 'HI':
            for obj in objs:
                obj.select_set(True)
                # obj.show_viewport = True
                obj.modifiers.new(type='WEIGHTED_NORMAL', name='sxWeightedNormal')
                obj.modifiers['sxWeightedNormal'].mode = 'FACE_AREA_WITH_ANGLE'
                obj.modifiers['sxWeightedNormal'].weight = 95
                obj.modifiers['sxWeightedNormal'].keep_sharp = True

            # self.apply_modifiers(objs)

        now = time.time()
        print('SX Tools: Mesh processing duration: ', now-then, ' seconds')


    def process_default(self, objs):
        print('SX Tools: Processing Default')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

        # Apply occlusion
        if scene.enableocclusion:
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

            tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        if scene.numoverlays != 0:
            layer = obj.sxlayers['overlay']
            rampmode = 'CN'
            scene.ramplist = 'BLACKANDWHITE'
            noise = 0.01
            mono = False

            tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
            for obj in objs:
                obj.sxlayers['overlay'].blendMode = 'OVR'
                obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Emissives are smooth
        if scene.enableemission:
            color = (1.0, 1.0, 1.0, 1.0)
            maskLayer = obj.sxlayers['emission']
            tools.select_mask(objs, [maskLayer, ], inverse=False)
            layer = obj.sxlayers['smoothness']
            overwrite = True
            noise = 0.0
            mono = True
            tools.apply_color(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def process_paletted(self, objs):
        print('SX Tools: Processing Paletted')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        maskLayer = obj.sxlayers['emission']
        tools.select_mask(objs, [maskLayer, ], inverse=False)
        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def process_vehicles(self, objs):
        print('SX Tools: Processing Vehicles')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clear_uvs(objs, obj.sxlayers['metallic'])
        layers.clear_uvs(objs, obj.sxlayers['smoothness'])
        layers.clear_uvs(objs, obj.sxlayers['transmission'])

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)
        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.01
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.find_layer_from_index(obj, 4)
        layer5 = utils.find_layer_from_index(obj, 5)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        overwrite = False

        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer4)
        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer5)

        color = (0.0, 0.0, 0.0, 1.0)
        layer6 = utils.find_layer_from_index(obj, 6)

        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer6)

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.01
        mono = True

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])

        # Combine previous mix with directional dust
        layer = obj.sxlayers['composite']
        rampmode = 'DIR'
        scene.ramplist = 'DIRECTIONALDUST'
        scene.angle = 0.0
        scene.inclination = 40.0
        noise = 0.01
        mono = True

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Apply PBR metal based on layer7
        layer = utils.find_layer_from_index(obj, 7)
        overwrite = False
        material = 'Iron'
        noise = 0.01
        mono = True

        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        tools.apply_color(objs, layer, palette[0], False, noise, mono)
        tools.apply_color(objs, obj.sxlayers['metallic'], palette[1], overwrite, noise, mono, layer)
        tools.apply_color(objs, obj.sxlayers['smoothness'], palette[2], overwrite, noise, mono, layer)

        # Mix metallic with occlusion (dirt in crevices)
        tools.layer_copy_manager(objs, obj.sxlayers['occlusion'], obj.sxlayers['composite'])
        for obj in objs:
            obj.sxlayers['metallic'].alpha = 1.0
            obj.sxlayers['metallic'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['metallic'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['metallic'])
        for obj in objs:
            obj.sxlayers['metallic'].blendMode = 'ALPHA'

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        maskLayer = obj.sxlayers['emission']
        tools.select_mask(objs, [maskLayer, ], inverse=False)
        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        # Emissives are not occluded
        layer = obj.sxlayers['occlusion']
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def process_buildings(self, objs):
        print('SX Tools: Processing Buildings')
        scene = bpy.context.scene.sxtools
        obj = objs[0]
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'WEARANDTEAR'
        noise = 0.0
        mono = False

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Windows are not occluded
        color = (1.0, 1.0, 1.0, 1.0)
        maskLayer = utils.find_layer_from_index(obj, 7)
        layer = obj.sxlayers['occlusion']
        noise = 0.0
        mono = True
        overwrite = False

        tools.apply_color(objs, layer, color, overwrite, noise, mono, maskLayer)

        color = (0.5, 0.5, 0.5, 1.0)
        layer = obj.sxlayers['overlay']
        tools.apply_color(objs, layer, color, overwrite, noise, mono, maskLayer)

        # Clear metallic, smoothness, and transmission
        layers.clear_uvs(objs, obj.sxlayers['metallic'])
        layers.clear_uvs(objs, obj.sxlayers['smoothness'])
        layers.clear_uvs(objs, obj.sxlayers['transmission'])

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.find_layer_from_index(obj, 4)
        layer5 = utils.find_layer_from_index(obj, 5)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = False
        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer4)
        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer5)

        color = (0.1, 0.1, 0.1, 1.0)

        layer6 = utils.find_layer_from_index(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = False

        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono, layer6)

        # Combine smoothness base mask with custom curvature gradient
        layer = obj.sxlayers['composite']
        for obj in objs:
            obj.sxlayers['composite'].blendMode = 'ALPHA'
            obj.sxlayers['composite'].alpha = 1.0
        rampmode = 'CN'
        scene.ramplist = 'CURVATURESMOOTHNESS'
        noise = 0.0
        mono = True

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])

        # Combine previous mix with directional dust
        layer = obj.sxlayers['composite']
        rampmode = 'DIR'
        scene.ramplist = 'DIRECTIONALDUST'
        scene.angle = 0.0
        scene.inclination = 40.0
        noise = 0.0
        mono = True

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Apply PBR glass based on layer7
        layer = utils.find_layer_from_index(obj, 7)
        overwrite = False
        obj.mode == 'OBJECT'
        material = 'Silver'
        noise = 0.01
        mono = True

        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        tools.apply_color(objs, layer, palette[0], False, noise, mono)
        tools.apply_color(objs, obj.sxlayers['metallic'], palette[1], overwrite, noise, mono, layer)
        tools.apply_color(objs, obj.sxlayers['smoothness'], palette[2], overwrite, noise, mono, layer)

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        maskLayer = obj.sxlayers['emission']
        tools.select_mask(objs, [maskLayer, ], inverse=False)
        layer = obj.sxlayers['smoothness']
        overwrite = True
        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def process_trees(self, objs):
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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        rampmode = 'CN'
        scene.ramplist = 'BLACKANDWHITE'
        noise = 0.01
        mono = False

        obj.mode == 'OBJECT'

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clear_uvs(objs, obj.sxlayers['metallic'])
        layers.clear_uvs(objs, obj.sxlayers['smoothness'])
        layers.clear_uvs(objs, obj.sxlayers['transmission'])

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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Construct layer1-7 smoothness base mask
        color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = True
        obj.mode == 'OBJECT'
        noise = 0.01
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        layer4 = utils.find_layer_from_index(obj, 4)
        layer5 = utils.find_layer_from_index(obj, 5)
        sxlayers = [layer4, layer5]
        tools.select_mask(objs, sxlayers, inverse)

        color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)

        layer = obj.sxlayers['smoothness']
        overwrite = scene.fillalpha
        if obj.mode == 'EDIT':
            overwrite = True
        noise = 0.01
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.find_layer_from_index(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono, maskLayer)

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

        tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)
        for obj in objs:
            obj.sxlayers['smoothness'].alpha = 1.0
            obj.sxlayers['smoothness'].blendMode = 'MUL'
            obj.sxlayers['composite'].alpha = 1.0
        layers.blend_layers(objs, [obj.sxlayers['smoothness'], ], obj.sxlayers['composite'], obj.sxlayers['composite'])
        tools.layer_copy_manager(objs, obj.sxlayers['composite'], obj.sxlayers['smoothness'])
        for obj in objs:
            obj.sxlayers['smoothness'].blendMode = 'ALPHA'

        # Clear layer4-5 mask from transmission
        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.find_layer_from_index(obj, 4)
        layer = obj.sxlayers['transmission']
        overwrite = True

        noise = 0.0
        mono = True
        tools.apply_color(objs, layer, color, overwrite, noise, mono, maskLayer)
        maskLayer = utils.find_layer_from_index(obj, 5)
        tools.apply_color(objs, layer, color, overwrite, noise, mono, maskLayer)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def remove_exports(self):
        if 'ExportObjects' in bpy.data.collections.keys():
            exportObjects = bpy.data.collections['ExportObjects'].objects
            for obj in exportObjects:
                bpy.data.objects.remove(obj, do_unlink=True)

        if 'SourceObjects' in bpy.data.collections.keys():
            sourceObjects = bpy.data.collections['SourceObjects'].objects
            for obj in sourceObjects:
                if obj.name.endswith('_org'):
                    obj.name = obj.name[:-4]
                elif obj.name.endswith('_LOD0'):
                    obj.name = obj.name[:-5]
                if obj.data and obj.data.name.endswith('_org'):
                    obj.data.name = obj.data.name[:-4]
                elif obj.data and obj.data.name.endswith('_LOD0'):
                    obj.data.name = obj.data.name[:-5]
                obj.hide_viewport = False
                sourceObjects.unlink(obj)


    def __del__(self):
        print('SX Tools: Exiting exports')


# ------------------------------------------------------------------------
#    Core Functions
# ------------------------------------------------------------------------
def update_layers(self, context):
    if 'SXMaterial' not in bpy.data.materials.keys():
        setup.create_sxmaterial()

    sxmaterial = bpy.data.materials['SXMaterial'].node_tree.nodes

    if not sxglobals.refreshInProgress:
        shading_mode(self, context)
        objs = selection_validator(self, context)
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

            # setup.setup_geometry(objs)
            if not context.scene.sxtools.gpucomposite:
                sxglobals.composite = True
                layers.composite_layers(objs)


def refresh_actives(self, context):
    if not sxglobals.refreshInProgress:
        sxglobals.refreshInProgress = True

        prefs = context.preferences.addons['sxtools'].preferences
        scene = context.scene.sxtools
        mode = context.scene.sxtools.shadingmode
        sxmaterial = bpy.data.materials['SXMaterial']
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            vcols = layer.vertexColorLayer

            # update Palettes-tab color values
            if scene.toolmode == 'PAL':
                layers.color_layers_to_values(objs)
            elif (prefs.materialtype != 'SMP') and (scene.toolmode == 'MAT'):
                layers.material_layers_to_values(objs)

            for obj in objs:
                setattr(obj.sxtools, 'selectedlayer', idx)
                if vcols != '':
                    obj.data.vertex_colors.active = obj.data.vertex_colors[vcols]
                    if mode != 'FULL':
                        sxmaterial.node_tree.nodes['Vertex Color'].layer_name = vcols
                alphaVal = getattr(obj.sxlayers[idx], 'alpha')
                blendVal = getattr(obj.sxlayers[idx], 'blendMode')
                visVal = getattr(obj.sxlayers[idx], 'visibility')

                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)

            # Update VertexColor0 to reflect latest layer changes
            if not context.scene.sxtools.gpucomposite:
                if mode != 'FULL':
                    sxglobals.composite = True
                layers.composite_layers(objs)
            sxglobals.refreshInProgress = False

            # Refresh SX Tools UI to latest selection
            layers.update_layer_palette(objs, layer)
            layers.update_layer_lightness(objs, layer)

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
            setup.start_modal()


def shading_mode(self, context):
    prefs = bpy.context.preferences.addons['sxtools'].preferences
    mode = context.scene.sxtools.shadingmode
    objs = selection_validator(self, context)
    context.scene.display_settings.display_device = 'sRGB'
    context.scene.view_settings.view_transform = 'Standard'

    if len(objs) > 0:
        sxmaterial = bpy.data.materials['SXMaterial']

        if prefs.materialtype == 'SMP':
            context.scene.eevee.use_bloom = False
            areas = bpy.context.workspace.screens[0].areas
            shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
            for area in areas:
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = shading
            if mode == 'FULL':
                sxmaterial.node_tree.nodes['Vertex Color'].layer_name = 'VertexColor0'
            else:
                # source to activelayer
                pass

        else:
            occlusion = objs[0].sxlayers['occlusion'].enabled
            metallic = objs[0].sxlayers['metallic'].enabled
            smoothness = objs[0].sxlayers['smoothness'].enabled
            transmission = objs[0].sxlayers['transmission'].enabled
            emission = objs[0].sxlayers['emission'].enabled

            materialsubsurface = prefs.materialsubsurface
            materialtransmission = prefs.materialtransmission

            if mode == 'FULL':
                if emission:
                    context.scene.eevee.use_bloom = True
                areas = bpy.context.workspace.screens[0].areas
                shading = 'MATERIAL'  # 'WIREFRAME' 'SOLID' 'MATERIAL' 'RENDERED'
                for area in areas:
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if ((space.shading.type == 'WIREFRAME') or
                               (space.shading.type == 'SOLID')):
                                space.shading.type = shading

                sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.5

                # Disconnect vertex color output from emission
                attrLink = sxmaterial.node_tree.nodes['Vertex Color'].outputs[0].links[0]
                sxmaterial.node_tree.links.remove(attrLink)

                # Reconnect vertex color to mixer
                output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Color']
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
                attrLink = sxmaterial.node_tree.nodes['Vertex Color'].outputs[0].links[0]
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
                output = sxmaterial.node_tree.nodes['Vertex Color'].outputs['Color']
                input = sxmaterial.node_tree.nodes['Principled BSDF'].inputs['Emission']
                sxmaterial.node_tree.links.new(input, output)

            sxglobals.prevMode = mode


def selection_validator(self, context):
    selObjs = []
    for obj in context.view_layer.objects.selected:
        if obj.type == 'MESH' and obj.hide_viewport == False:
            selObjs.append(obj)

    return selObjs


def ramp_lister(self, context):
    items = sxglobals.rampDict.keys()
    enumItems = []
    for item in items:
        sxglobals.presetLookup[item.replace(" ", "_").upper()] = item
        enumItem = (item.replace(" ", "_").upper(), item, '')
        enumItems.append(enumItem)
    return enumItems


def category_lister(self, context):
    items = sxglobals.categoryDict.keys()
    enumItems = []
    for item in items:
        sxglobals.presetLookup[item.replace(" ", "_").upper()] = item
        enumItem = (item.replace(" ", "_").upper(), item, '')
        enumItems.append(enumItem)
    return enumItems


def palette_category_lister(self, context):
    palettes = context.scene.sxpalettes
    categories = []
    for palette in palettes:
        categoryEnum = palette.category.replace(" ", "").upper()
        if categoryEnum not in sxglobals.presetLookup.keys():
            sxglobals.presetLookup[categoryEnum] = palette.category
        enumItem = (categoryEnum, palette.category, '')
        categories.append(enumItem)
    enumItems = list(set(categories))
    return enumItems


def material_category_lister(self, context):
    materials = context.scene.sxmaterials
    categories = []
    for material in materials:
        categoryEnum = material.category.replace(" ", "").upper()
        if categoryEnum not in sxglobals.presetLookup.keys():
            sxglobals.presetLookup[categoryEnum] = material.category
        enumItem = (material.category.replace(" ", "").upper(), material.category, '')
        categories.append(enumItem)
    enumItems = list(set(categories))
    return enumItems


def load_category(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        categoryData = sxglobals.categoryDict[sxglobals.presetLookup[objs[0].sxtools.category]]
        for i in range(7):
            layer = utils.find_layer_from_index(objs[0], i+1)
            layer.name = categoryData[i]

        for obj in objs:
            if obj.sxtools.category != objs[0].sxtools.category:
                obj.sxtools.category = objs[0].sxtools.category
                for i in range(7):
                    layer = utils.find_layer_from_index(obj, i+1)
                    layer.name = categoryData[i]

            obj.sxtools.staticvertexcolors = str(categoryData[7])
            obj.sxtools.smoothness1 = categoryData[8]
            obj.sxtools.smoothness2 = categoryData[9]
            obj.sxtools.overlaystrength = categoryData[10]

        bpy.data.materials['SXMaterial'].blend_method = categoryData[11]
        if categoryData[11] == 'BLEND':
            bpy.data.materials['SXMaterial'].use_backface_culling = True
        else:
            bpy.data.materials['SXMaterial'].use_backface_culling = False


def load_ramp(self, context):
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


def load_libraries(self, context):
    status1 = files.load_file('palettes')
    status2 = files.load_file('materials')
    status3 = files.load_file('gradients')
    status4 = files.load_file('categories')

    if status1 and status2 and status3 and status4:
        message_box('Libraries loaded successfully')
        sxglobals.librariesLoaded = True


def adjust_lightness(self, context):
    if not sxglobals.lightnessUpdate:
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)

            tools.apply_lightness(objs, layer, context.scene.sxtools.lightnessvalue)

            sxglobals.composite = True
            refresh_actives(self, context)


def update_modifier_visibility(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        vis = objs[0].sxtools.modifiervisibility
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            if obj.sxtools.modifiervisibility != vis:
                obj.sxtools.modifiervisibility = vis

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxMirror' in obj.modifiers.keys():
                obj.modifiers['sxMirror'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxSubdivision' in obj.modifiers.keys():
                if (obj.sxtools.subdivisionlevel == 0):
                    obj.modifiers['sxSubdivision'].show_viewport = False
                else:
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
                if obj.sxtools.bevelsegments == 0:
                    obj.modifiers['sxBevel'].show_viewport = False
                else:
                    obj.modifiers['sxBevel'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxWeld' in obj.modifiers.keys():
                if (obj.sxtools.weldthreshold == 0):
                    obj.modifiers['sxWeld'].show_viewport = False
                else:
                    obj.modifiers['sxWeld'].show_viewport = obj.sxtools.modifiervisibility
            if 'sxWeightedNormal' in obj.modifiers.keys():
                obj.modifiers['sxWeightedNormal'].show_viewport = obj.sxtools.modifiervisibility

        bpy.ops.object.mode_set(mode=mode)


def update_mirror_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        xmirror = objs[0].sxtools.xmirror
        ymirror = objs[0].sxtools.ymirror
        zmirror = objs[0].sxtools.zmirror

        for obj in objs:
            if obj.sxtools.xmirror != xmirror:
                obj.sxtools.xmirror = xmirror
            if obj.sxtools.ymirror != ymirror:
                obj.sxtools.ymirror = ymirror
            if obj.sxtools.zmirror != zmirror:
                obj.sxtools.zmirror = zmirror

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxMirror' in obj.modifiers.keys():
                obj.modifiers['sxMirror'].use_axis[0] = xmirror
                obj.modifiers['sxMirror'].use_axis[1] = ymirror
                obj.modifiers['sxMirror'].use_axis[2] = zmirror

                if xmirror or ymirror or zmirror:
                    obj.modifiers['sxMirror'].show_viewport = True
                else:
                    obj.modifiers['sxMirror'].show_viewport = False

        bpy.ops.object.mode_set(mode=mode)


def update_crease_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            if obj.sxtools.hardmode != hardmode:
                obj.sxtools.hardmode = hardmode

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxWeightedNormal' in obj.modifiers.keys():
                if hardmode == 'SMOOTH':
                    obj.modifiers['sxWeightedNormal'].keep_sharp = False
                else:
                    obj.modifiers['sxWeightedNormal'].keep_sharp = True

        bpy.ops.object.mode_set(mode=mode)


def update_subdivision_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        vis = objs[0].sxtools.modifiervisibility
        hardmode = objs[0].sxtools.hardmode
        subdivLevel = objs[0].sxtools.subdivisionlevel
        for obj in objs:
            if obj.sxtools.modifiervisibility != vis:
                obj.sxtools.modifiervisibility = vis
            if obj.sxtools.hardmode != hardmode:
                obj.sxtools.hardmode = hardmode
            if obj.sxtools.subdivisionlevel != subdivLevel:
                obj.sxtools.subdivisionlevel = subdivLevel

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxSubdivision' in obj.modifiers.keys():
                obj.modifiers['sxSubdivision'].levels = obj.sxtools.subdivisionlevel
                if obj.sxtools.subdivisionlevel == 0:
                    obj.modifiers['sxSubdivision'].show_viewport = False
                else:
                    obj.modifiers['sxSubdivision'].show_viewport = obj.sxtools.modifiervisibility
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


def update_bevel_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        bevelWidth = objs[0].sxtools.bevelwidth
        bevelSegments = objs[0].sxtools.bevelsegments
        for obj in objs:
            if obj.sxtools.bevelwidth != bevelWidth:
                obj.sxtools.bevelwidth = bevelWidth
            if obj.sxtools.bevelsegments != bevelSegments:
                obj.sxtools.bevelsegments = bevelSegments

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxBevel' in obj.modifiers.keys():
                if obj.sxtools.bevelsegments == 0:
                    obj.modifiers['sxBevel'].show_viewport = False
                else:
                    obj.modifiers['sxBevel'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxBevel'].width = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].width_pct = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].segments = obj.sxtools.bevelsegments

        bpy.ops.object.mode_set(mode=mode)


def update_weld_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        weldThreshold = objs[0].sxtools.weldthreshold
        for obj in objs:
            if obj.sxtools.weldthreshold != weldThreshold:
                obj.sxtools.weldthreshold = weldThreshold

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxWeld' in obj.modifiers.keys():
                obj.modifiers['sxWeld'].merge_threshold = weldThreshold
                if obj.sxtools.weldthreshold == 0:
                    obj.modifiers['sxWeld'].show_viewport = False
                elif (obj.sxtools.weldthreshold > 0) and obj.sxtools.modifiervisibility:
                    obj.modifiers['sxWeld'].show_viewport = True

        bpy.ops.object.mode_set(mode=mode)


def update_decimate_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        decimation = objs[0].sxtools.decimation
        for obj in objs:
            if obj.sxtools.decimation != decimation:
                obj.sxtools.decimation = decimation

        mode = objs[0].mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        for obj in objs:
            if 'sxDecimate' in obj.modifiers.keys():
                obj.modifiers['sxDecimate'].angle_limit = decimation * (math.pi/180.0)
                if obj.sxtools.decimation == 0:
                    obj.modifiers['sxDecimate'].show_viewport = False
                    obj.modifiers['sxDecimate2'].show_viewport = False
                elif (obj.sxtools.decimation > 0) and obj.sxtools.modifiervisibility:
                    obj.modifiers['sxDecimate'].show_viewport = True
                    obj.modifiers['sxDecimate2'].show_viewport = True

        bpy.ops.object.mode_set(mode=mode)


def update_custom_props(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        stc = objs[0].sxtools.staticvertexcolors
        sm1 = objs[0].sxtools.smoothness1
        sm2 = objs[0].sxtools.smoothness2
        ovr = objs[0].sxtools.overlaystrength
        lod = objs[0].sxtools.lodmeshes
        for obj in objs:
            obj['staticVertexColors'] = int(stc)
            obj['sxToolsVersion'] = 'SX Tools for Blender ' + str(sys.modules['sxtools'].bl_info.get('version'))
            if obj.sxtools.staticvertexcolors != stc:
                obj.sxtools.staticvertexcolors = stc
            if obj.sxtools.smoothness1 != sm1:
                obj.sxtools.smoothness1 = sm1
            if obj.sxtools.smoothness2 != sm2:
                obj.sxtools.smoothness2 = sm2
            if obj.sxtools.overlaystrength != ovr:
                obj.sxtools.overlaystrength = ovr
            if obj.sxtools.lodmeshes != lod:
                obj.sxtools.lodmeshes = lod


def update_smooth_angle(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        smoothAngleDeg = objs[0].sxtools.smoothangle
        smoothAngle = objs[0].sxtools.smoothangle * (2*math.pi)/360.0
        for obj in objs:
            if obj.sxtools.smoothangle != smoothAngleDeg:
                obj.sxtools.smoothangle = smoothAngleDeg

            obj.data.use_auto_smooth = True
            if obj.data.auto_smooth_angle != smoothAngle:
                obj.data.auto_smooth_angle = smoothAngle


def update_palette_layer1(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 1)
    color = (scene.newpalette0[0], scene.newpalette0[1], scene.newpalette0[2], scene.newpalette0[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor0'].outputs[0].default_value = color
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_palette_layer2(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 2)
    color = (scene.newpalette1[0], scene.newpalette1[1], scene.newpalette1[2], scene.newpalette1[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor1'].outputs[0].default_value = color
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_palette_layer3(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 3)
    color = (scene.newpalette2[0], scene.newpalette2[1], scene.newpalette2[2], scene.newpalette2[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor2'].outputs[0].default_value = color
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_palette_layer4(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 4)
    color = (scene.newpalette3[0], scene.newpalette3[1], scene.newpalette3[2], scene.newpalette3[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor3'].outputs[0].default_value = color
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_palette_layer5(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 5)
    color = (scene.newpalette4[0], scene.newpalette4[1], scene.newpalette4[2], scene.newpalette4[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor4'].outputs[0].default_value = color
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_material_layer1(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 7)
    color = (scene.newmaterial0[0], scene.newmaterial0[1], scene.newmaterial0[2], scene.newmaterial0[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if scene.enablelimit:
        hsl = convert.rgb_to_hsl(color)
        if scene.limitmode == 'MET':
            minl = float(170.0/255.0)
            if hsl[2] < minl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[1], minl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)
        else:
            minl = float(10.0/255.0)
            maxl = float(240.0/255.0)
            if hsl[2] > maxl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[1], maxl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)
            elif hsl[2] < minl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[2], minl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)

    if color != modecolor:
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_material_layer2(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 12)
    color = (scene.newmaterial1[0], scene.newmaterial1[1], scene.newmaterial1[2], scene.newmaterial1[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_material_layer3(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 13)
    color = (scene.newmaterial2[0], scene.newmaterial2[1], scene.newmaterial2[2], scene.newmaterial2[3])
    noise = scene.palettenoise
    mono = scene.palettemono
    modecolor = utils.find_mode_color(objs, layer)

    if color != modecolor:
        tools.apply_color(objs, layer, color, False, noise, mono)
        sxglobals.composite = True
        refresh_actives(self, context)


def message_box(message='', title='SX Tools', icon='INFO'):
    messageLines = message.splitlines()


    def draw(self, context):
        for line in messageLines:
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def expand_layer(self, context):
    if context.scene.sxtools.expandlayer is False:
        context.scene.sxtools.expandlayer = True


def expand_fill(self, context):
    if context.scene.sxtools.expandfill is False:
        context.scene.sxtools.expandfill = True


def expand_crease(self, context):
    if context.scene.sxtools.expandcrease is False:
        context.scene.sxtools.expandcrease = True


def expand_export(self, context):
    if context.scene.sxtools.expandexport is False:
        context.scene.sxtools.expandexport = True


def compositing_mode(self, context):
    sxmaterial = bpy.data.materials['SXMaterial'].node_tree
    swoutput = sxmaterial.nodes['Vertex Color'].outputs['Color']
    hwoutput = sxmaterial.nodes['Final Step'].outputs['Color']
    input = sxmaterial.nodes['Mix'].inputs['Color1']

    if context.scene.sxtools.gpucomposite:
        sxmaterial.links.new(input, hwoutput)
    else:
        sxmaterial.links.new(input, swoutput)


def update_scene_configuration(self, context):
    prefs = context.preferences.addons['sxtools'].preferences
    scene = context.scene.sxtools
    
    if prefs.materialtype == 'SMP':
        scene.numlayers = 7
        scene.numalphas = 0
        scene.numoverlays = 0
        scene.enableocclusion = False
        scene.enablemetallic = False
        scene.enablesmoothness = False
        scene.enabletransmission = False
        scene.enableemission = False
    else:
        scene.numlayers = 7
        scene.numalphas = 2
        scene.numoverlays = 1
        scene.enableocclusion = True
        scene.enablemetallic = True
        scene.enablesmoothness = True
        scene.enabletransmission = True
        scene.enableemission = True

@persistent
def load_post_handler(dummy):
    sxglobals.prevMode = 'FULL'
    # sxglobals.librariesLoaded = False

    setup.start_modal()


# ------------------------------------------------------------------------
#    Settings and preferences
# ------------------------------------------------------------------------
class SXTOOLS_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    libraryfolder: bpy.props.StringProperty(
        name='Library Folder',
        description='Folder containing SX Tools data files\n(materials.json, palettes.json, gradients.json)',
        default='',
        maxlen=1024,
        subtype='DIR_PATH',
        update=load_libraries)

    materialtype: bpy.props.EnumProperty(
        name='SXMaterial Type',
        description='Select between simple emission and full PBR materials',
        items=[
            ('SMP', 'Simple', ''),
            ('PBR', 'Physically Based', '')],
        default='PBR',
        update=update_scene_configuration)

    materialsubsurface: bpy.props.BoolProperty(
        name='Subsurface Scattering',
        description='Connect Transmission Layer to SXMaterial Subsurface Scattering',
        default=False)

    materialtransmission: bpy.props.BoolProperty(
        name='Transmission',
        description='Connect Transmission Layer to SXMaterial Transmission',
        default=True)

    colorspace: bpy.props.EnumProperty(
        name='Color Space for Exports',
        description='Color space for exported vertex colors',
        items=[
            ('SRGB', 'sRGB', ''),
            ('LIN', 'Linear', '')],
        default='SRGB')

    removelods: bpy.props.BoolProperty(
        name='Remove LOD Meshes After Export',
        description='Remove LOD meshes from the scene after exporting to FBX',
        default=True)

    lodoffset: bpy.props.FloatProperty(
        name='LOD Mesh Preview Z-Offset',
        min=0.0,
        max=10.0,
        default=1.0)


    def draw(self, context):
        layout = self.layout
        if self.materialtype == 'PBR':
            layout_split1 = layout.split()
            layout_split1.label(text='Connect Transmission Layer to:')
            layout_split2 = layout_split1.split()
            layout_split2.prop(self, 'materialsubsurface')
            layout_split2.prop(self, 'materialtransmission')
        layout_split3 = layout.split()
        layout_split3.label(text='Color Space for Exports:')
        layout_split3.prop(self, 'colorspace', text='')
        layout_split4 = layout.split()
        layout_split4.label(text='LOD Mesh Preview Z-Offset')
        layout_split4.prop(self, 'lodoffset', text='')
        layout_split5 = layout.split()
        layout_split5.label(text='Clear LOD Meshes After Export')
        layout_split5.prop(self, 'removelods', text='')
        layout_split6 = layout.split()
        layout_split6.label(text='Library Folder:')
        layout_split6.prop(self, 'libraryfolder', text='')


class SXTOOLS_objectprops(bpy.types.PropertyGroup):
    category: bpy.props.EnumProperty(
        name='Category Presets',
        description='Select object category\nRenames layers to match',
        items=category_lister,
        update=load_category)

    selectedlayer: bpy.props.IntProperty(
        name='Selected Layer',
        min=0,
        max=20,
        default=1,
        update=refresh_actives)

    activeLayerAlpha: bpy.props.FloatProperty(
        name='Opacity',
        min=0.0,
        max=1.0,
        default=1.0,
        update=update_layers)

    activeLayerBlendMode: bpy.props.EnumProperty(
        name='Blend Mode',
        items=[
            ('ALPHA', 'Alpha', ''),
            ('ADD', 'Additive', ''),
            ('MUL', 'Multiply', ''),
            ('OVR', 'Overlay', '')],
        default='ALPHA',
        update=update_layers)

    activeLayerVisibility: bpy.props.BoolProperty(
        name='Visibility',
        default=True,
        update=update_layers)

    modifiervisibility: bpy.props.BoolProperty(
        name='Modifier Visibility',
        default=True,
        update=update_modifier_visibility)

    smoothangle: bpy.props.FloatProperty(
        name='Normal Smoothing Angle',
        min=0.0,
        max=180.0,
        default=180.0,
        update=update_smooth_angle)

    xmirror: bpy.props.BoolProperty(
        name='X-Axis',
        default=False,
        update=update_mirror_modifier)

    ymirror: bpy.props.BoolProperty(
        name='Y-Axis',
        default=False,
        update=update_mirror_modifier)

    zmirror: bpy.props.BoolProperty(
        name='Z-Axis',
        default=False,
        update=update_mirror_modifier)

    hardmode: bpy.props.EnumProperty(
        name='Max Crease Mode',
        description='Mode for processing edges with maximum crease',
        items=[
            ('SMOOTH', 'Smooth', ''),
            ('SHARP', 'Sharp', '')],
        default='SHARP',
        update=update_crease_modifier)

    subdivisionlevel: bpy.props.IntProperty(
        name='Subdivision Level',
        min=0,
        max=6,
        default=1,
        update=update_subdivision_modifier)

    bevelwidth: bpy.props.FloatProperty(
        name='Bevel Width',
        min=0.0,
        max=100.0,
        default=0.05,
        update=update_bevel_modifier)

    bevelsegments: bpy.props.IntProperty(
        name='Bevel Segments',
        min=0,
        max=10,
        default=2,
        update=update_bevel_modifier)

    weldthreshold: bpy.props.FloatProperty(
        name='Weld Threshold',
        min=0.0,
        max=10.0,
        default=0.0,
        precision=3,
        update=update_weld_modifier)

    decimation: bpy.props.FloatProperty(
        name='Decimation',
        min=0.0,
        max=10.0,
        default=0.0,
        update=update_decimate_modifier)

    staticvertexcolors: bpy.props.EnumProperty(
        name='Vertex Color Processing Mode',
        description='Choose how to export vertex colors to a game engine\nStatic bakes all color layers to VertexColor0\nPaletted leaves overlays in alpha channels',
        items=[
            ('1', 'Static', ''),
            ('0', 'Paletted', '')],
        default='1',
        update=update_custom_props)

    smoothness1: bpy.props.FloatProperty(
        name='Layer 1-3 Base Smoothness',
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_custom_props)

    smoothness2: bpy.props.FloatProperty(
        name='Layer 4-5 Base Smoothness',
        min=0.0,
        max=1.0,
        default=0.0,
        update=update_custom_props)

    overlaystrength: bpy.props.FloatProperty(
        name='RGBA Overlay Strength',
        min=0.0,
        max=1.0,
        default=0.5,
        update=update_custom_props)

    lodmeshes: bpy.props.BoolProperty(
        name='Generate LOD Meshes',
        default=False,
        update=update_custom_props)


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
        update=update_layers)

    layerpalette1: bpy.props.FloatVectorProperty(
        name='Layer Palette 1',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette2: bpy.props.FloatVectorProperty(
        name='Layer Palette 2',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette3: bpy.props.FloatVectorProperty(
        name='Layer Palette 3',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette4: bpy.props.FloatVectorProperty(
        name='Layer Palette 4',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette5: bpy.props.FloatVectorProperty(
        name='Layer Palette 5',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette6: bpy.props.FloatVectorProperty(
        name='Layer Palette 6',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette7: bpy.props.FloatVectorProperty(
        name='Layer Palette 7',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    layerpalette8: bpy.props.FloatVectorProperty(
        name='Layer Palette 8',
        description='Color from the selected layer\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    lightnessvalue: bpy.props.FloatProperty(
        name='Lightness',
        description='The max lightness in the selection',
        min=0.0,
        max=1.0,
        default=0.0,
        update=adjust_lightness)

    toolmode: bpy.props.EnumProperty(
        name='Tool Mode',
        description='Select tool',
        items=[
            ('COL', 'Color', ''),
            ('GRD', 'Gradient', ''),
            ('PAL', 'Palette', ''),
            ('MAT', 'Material', '')],
        default='COL',
        update=expand_fill)

    fillpalette1: bpy.props.FloatVectorProperty(
        name='Recent Color 1',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette2: bpy.props.FloatVectorProperty(
        name='Recent Color 2',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette3: bpy.props.FloatVectorProperty(
        name='Recent Color 3',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette4: bpy.props.FloatVectorProperty(
        name='Recent Color 4',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette5: bpy.props.FloatVectorProperty(
        name='Recent Color 5',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette6: bpy.props.FloatVectorProperty(
        name='Recent Color 6',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette7: bpy.props.FloatVectorProperty(
        name='Recent Color 7',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillpalette8: bpy.props.FloatVectorProperty(
        name='Recent Color 8',
        description='Recent colors\nDrag and drop to Fill Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0))

    fillcolor: bpy.props.FloatVectorProperty(
        name='Fill Color',
        description='This color is applied tools\nthe selected objects or components',
        subtype='COLOR_GAMMA',
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
        items=ramp_lister,
        update=load_ramp)

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

    palettecategories: bpy.props.EnumProperty(
        name='Category',
        description='Choose palette category',
        items=palette_category_lister)

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

    materialcategories: bpy.props.EnumProperty(
        name='Category',
        description='Choose material category',
        items=material_category_lister)

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
        name='Edge Weight Mode',
        description='Display weight tools or modifier settings',
        items=[
            ('CRS', 'Crease', ''),
            ('BEV', 'Bevel', ''),
            ('SDS', 'Modifiers', '')],
        default='CRS',
        update=expand_crease)

    autocrease: bpy.props.BoolProperty(
        name='Auto Hard-Crease Bevel Edges',
        default=True)

    expandlayer: bpy.props.BoolProperty(
        name='Expand Layer Controls',
        default=False)

    expandfill: bpy.props.BoolProperty(
        name='Expand Fill',
        default=False)

    expandpal: bpy.props.BoolProperty(
        name='Expand Add Palette',
        default=False)

    newpalettename: bpy.props.StringProperty(
        name='Palette Name',
        description='New Palette Name',
        default='',
        maxlen=64)

    newpalette0: bpy.props.FloatVectorProperty(
        name='New Palette Color 0',
        description='New Palette Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_palette_layer1)

    newpalette1: bpy.props.FloatVectorProperty(
        name='New Palette Color 1',
        description='New Palette Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_palette_layer2)

    newpalette2: bpy.props.FloatVectorProperty(
        name='New Palette Color 2',
        description='New Palette Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_palette_layer3)

    newpalette3: bpy.props.FloatVectorProperty(
        name='New Palette Color 3',
        description='New Palette Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_palette_layer4)

    newpalette4: bpy.props.FloatVectorProperty(
        name='New Palette Color 4',
        description='New Palette Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_palette_layer5)

    expandmat: bpy.props.BoolProperty(
        name='Expand Add Material',
        default=False)

    newmaterialname: bpy.props.StringProperty(
        name='Material Name',
        description='New Material Name',
        default='',
        maxlen=64)

    newmaterial0: bpy.props.FloatVectorProperty(
        name='Layer 7',
        description='Diffuse Color',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_material_layer1)

    newmaterial1: bpy.props.FloatVectorProperty(
        name='Metallic',
        description='Metallic Value',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_material_layer2)

    newmaterial2: bpy.props.FloatVectorProperty(
        name='Smoothness',
        description='Smoothness Value',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=update_material_layer3)

    expandcrease: bpy.props.BoolProperty(
        name='Expand Crease',
        default=False)

    expandexport: bpy.props.BoolProperty(
        name='Expand Export',
        default=False)

    expanddebug: bpy.props.BoolProperty(
        name='Expand Debug',
        default=False)

    exportmode: bpy.props.EnumProperty(
        name='Export Mode',
        description='Display magic processing, misc utils, or export settings',
        items=[
            ('MAGIC', 'Magic', ''),
            ('UTILS', 'Utilities', ''),
            ('EXPORT', 'Export', '')],
        default='MAGIC',
        update=expand_export)

    exportquality: bpy.props.EnumProperty(
        name='Export Quality',
        description='Low Detail mode uses base mesh for baking\nHigh Detail mode bakes after applying modifiers but disables decimation',
        items=[
            ('LO', 'Low Detail', ''),
            ('HI', 'High Detail', '')],
        default='LO')

    exportfolder: bpy.props.StringProperty(
        name='Export Folder',
        description='Folder to export FBX files to',
        default='',
        maxlen=1024,
        subtype='DIR_PATH')

    gpucomposite: bpy.props.BoolProperty(
        name='GPU Compositing',
        default=False,
        update=compositing_mode)

    shift: bpy.props.BoolProperty(
        name='Shift',
        description='Keyboard input',
        default=False)

    alt: bpy.props.BoolProperty(
        name='Alt',
        description='Keyboard input',
        default=False)

    ctrl: bpy.props.BoolProperty(
        name='Ctrl',
        description='Keyboard input',
        default=False)

    enablelimit: bpy.props.BoolProperty(
        name='PBR Limit',
        description='Limit diffuse color values to PBR range',
        default=False)

    limitmode: bpy.props.EnumProperty(
        name='PBR Limit Mode',
        description='Limit diffuse values to Metallic or Non-Metallic range',
        items=[
            ('MET', 'Metallic', ''),
            ('NONMET', 'Non-Metallic', '')],
        default='MET')


class SXTOOLS_masterpalette(bpy.types.PropertyGroup):
    category: bpy.props.StringProperty(
        name='Category',
        description='Palette Category',
        default='')

    color0: bpy.props.FloatVectorProperty(
        name='Palette Color 0',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name='Palette Color 1',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name='Palette Color 2',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color3: bpy.props.FloatVectorProperty(
        name='Palette Color 3',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color4: bpy.props.FloatVectorProperty(
        name='Palette Color 4',
        subtype='COLOR_GAMMA',
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
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color1: bpy.props.FloatVectorProperty(
        name='Material Metallic',
        subtype='COLOR_GAMMA',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0))

    color2: bpy.props.FloatVectorProperty(
        name='Material Smoothness',
        subtype='COLOR_GAMMA',
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
        subtype='COLOR_GAMMA',
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
        subtype='COLOR_GAMMA',
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
        objs = selection_validator(self, context)
        if (len(objs) > 0) and (len(objs[0].sxtools.category) > 0) and sxglobals.librariesLoaded:
            obj = objs[0]

            layout = self.layout
            mode = obj.mode
            sxtools = obj.sxtools
            scene = context.scene.sxtools
            palettes = context.scene.sxpalettes
            prefs = context.preferences.addons['sxtools'].preferences
            
            if len(obj.sxlayers) == 0:
                col = self.layout.column(align=True)
                col.label(text='Set Scene Configuration:')
                col.prop(prefs, 'materialtype', text='Preset')
                if prefs.materialtype != 'SMP':
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
                layer = utils.find_layer_from_index(obj, sel_idx)
                if layer is None:
                    sel_idx = 1
                    layer = utils.find_layer_from_index(obj, sel_idx)
                    message_box('Invalid layer selected!', 'SX Tools Error', 'ERROR')
                    # print('SX Tools: Error, invalid layer selected!')

                if prefs.materialtype != 'SMP':
                    row = layout.row(align=True)
                    row.prop(sxtools, 'category', text='Category')

                row_shading = self.layout.row(align=True)
                row_shading.prop(scene, 'shadingmode', expand=True)

                # Layer Controls -----------------------------------------------
                box_layer = self.layout.box()
                row_layer = box_layer.row()
                row_layer.prop(scene, 'expandlayer',
                    icon='TRIA_DOWN' if scene.expandlayer else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                split_layer = row_layer.split()
                split_layer.label(text='Layer Blend Mode')
                split_layer.prop(sxtools, 'activeLayerBlendMode', text='')

                if ((layer.name == 'occlusion') or
                   (layer.name == 'smoothness') or
                   (layer.name == 'metallic') or
                   (layer.name == 'transmission') or
                   (layer.name == 'emission')):
                    split_layer.enabled = False

                if scene.expandlayer:
                    row_blend = box_layer.row(align=True)
                    row_blend.prop(sxtools, 'activeLayerVisibility', text='Layer Visibility')
                    row_alpha = box_layer.row(align=True)
                    row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text='Layer Opacity')
                    col_misc = box_layer.row(align=True)
                    if obj.mode == 'OBJECT':
                        col_misc.prop(scene, 'lightnessvalue', slider=True, text='Layer Lightness')
                    else:
                        col_misc.prop(scene, 'lightnessvalue', slider=True, text='Selection Lightness')

                    if ((layer.name == 'occlusion') or
                       (layer.name == 'smoothness') or
                       (layer.name == 'metallic') or
                       (layer.name == 'transmission') or
                       (layer.name == 'emission')):
                        row_blend.enabled = False
                        row_alpha.enabled = False

                    if (scene.shadingmode == 'DEBUG') or (scene.shadingmode == 'ALPHA'):
                        row_alpha.enabled = False

                row_palette = self.layout.row(align=True)
                for i in range(8):
                    row_palette.prop(scene, 'layerpalette' + str(i+1), text='')

                layout.template_list('SXTOOLS_UL_layerlist', 'sxtools.layerlist', obj, 'sxlayers', sxtools, 'selectedlayer', type='DEFAULT')
                # layout.template_list('UI_UL_list', 'sxtools.layerlist', context.scene, 'sxlistitems', scene, 'listIndex', type='DEFAULT')
                # layout.template_list('UI_UL_list', 'sxtools.layerList', mesh, 'vertex_colors', sxtools, 'selectedlayer', type='DEFAULT')

                # Layer Copy Paste Merge ---------------------------------------
                row_misc1 = self.layout.row(align=True)
                row_misc1.operator('sxtools.mergeup')
                row_misc1.operator('sxtools.copylayer', text='Copy')
                if not scene.shift:
                    clr_text = 'Clear'
                else:
                    clr_text = 'Clear All'
                row_misc1.operator('sxtools.clear', text=clr_text)
                row_misc2 = self.layout.row(align=True)
                row_misc2.operator('sxtools.mergedown')
                if scene.alt:
                    paste_text = 'Merge'
                elif scene.shift:
                    paste_text = 'Swap'
                else:
                    paste_text = 'Paste'
                row_misc2.operator('sxtools.pastelayer', text=paste_text)
                if not scene.shift:
                    sel_text = 'Select Mask'
                else:
                    sel_text = 'Select Inverse'
                row_misc2.operator('sxtools.selmask', text=sel_text)

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

                # Master Palettes -----------------------------------------------
                elif scene.toolmode == 'PAL':
                    palettes = context.scene.sxpalettes

                    row_newpalette = box_fill.row(align=True)
                    for i in range(5):
                        row_newpalette.prop(scene, 'newpalette'+str(i), text='')
                    row_newpalette.operator('sxtools.addpalette', text='', icon='ADD')

                    if scene.expandfill:
                        row_lib = box_fill.row()
                        row_lib.prop(scene, 'expandpal',
                            icon='TRIA_DOWN' if scene.expandpal else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_lib.label(text='Library')
                        if scene.expandpal:
                            category = scene.palettecategories
                            split_category = box_fill.split(factor=0.33)
                            split_category.label(text='Category:')
                            row_category = split_category.row(align=True)
                            row_category.prop(scene, 'palettecategories', text='')
                            row_category.operator('sxtools.addpalettecategory', text='', icon='ADD')
                            row_category.operator('sxtools.delpalettecategory', text='', icon='REMOVE')
                            row_category.separator()
                            for palette in palettes:
                                name = palette.name
                                if palette.category.replace(" ", "").upper() == category:
                                    row_mpalette = box_fill.row(align=True)
                                    split_mpalette = row_mpalette.split(factor=0.33)
                                    split_mpalette.label(text=name)
                                    split2_mpalette = split_mpalette.split()
                                    row2_mpalette = split2_mpalette.row(align=True)
                                    for i in range(5):
                                        row2_mpalette.prop(palette, 'color'+str(i), text='')
                                    if not scene.shift:
                                        mp_button = split2_mpalette.operator('sxtools.applypalette', text='Apply')
                                        mp_button.label = name
                                    else:
                                        mp_button = split2_mpalette.operator('sxtools.delpalette', text='Delete')
                                        mp_button.label = name

                            row_mnoise = box_fill.row(align=True)
                            row_mnoise.prop(scene, 'palettenoise', slider=True)
                            col_mcolor = box_fill.column(align=True)
                            col_mcolor.prop(scene, 'palettemono', text='Monochromatic')

                # PBR Materials -------------------------------------------------
                elif scene.toolmode == 'MAT':
                    materials = context.scene.sxmaterials

                    row_newmaterial = box_fill.row(align=True)
                    for i in range(3):
                        row_newmaterial.prop(scene, 'newmaterial'+str(i), text='')
                    row_newmaterial.operator('sxtools.addmaterial', text='', icon='ADD')

                    row_limit = box_fill.row(align=True)
                    row_limit.prop(scene, 'enablelimit', text='Limit to PBR range')
                    row_limit.prop(scene, 'limitmode', text='')

                    if scene.expandfill:
                        row_lib = box_fill.row()
                        row_lib.prop(scene, 'expandmat',
                            icon='TRIA_DOWN' if scene.expandmat else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_lib.label(text='Library')
                        if scene.expandmat:
                            category = scene.materialcategories
                            split_category = box_fill.split(factor=0.33)
                            split_category.label(text='Category:')
                            row_category = split_category.row(align=True)
                            row_category.prop(scene, 'materialcategories', text='')
                            row_category.operator('sxtools.addmaterialcategory', text='', icon='ADD')
                            row_category.operator('sxtools.delmaterialcategory', text='', icon='REMOVE')
                            row_category.separator()
                            for material in materials:
                                name = material.name
                                if material.category.replace(" ", "_").upper() == category:
                                    row_mat = box_fill.row(align=True)
                                    split_mat = row_mat.split(factor=0.33)
                                    split_mat.label(text=name)
                                    split2_mat = split_mat.split()
                                    row2_mat = split2_mat.row(align=True)
                                    for i in range(3):
                                        row2_mat.prop(material, 'color'+str(i), text='')
                                    if not scene.shift:
                                        mat_button = split2_mat.operator('sxtools.applymaterial', text='Apply')
                                        mat_button.label = name
                                    else:
                                        mat_button = split2_mat.operator('sxtools.delmaterial', text='Delete')
                                        mat_button.label = name

                            row_pbrnoise = box_fill.row(align=True)
                            row_pbrnoise.prop(scene, 'materialnoise', slider=True)
                            col_matcolor = box_fill.column(align=True)
                            col_matcolor.prop(scene, 'materialmono', text='Monochromatic')
                            if mode == 'OBJECT':
                                col_matcolor.prop(scene, 'materialalpha')

                # Crease Sets ---------------------------------------------------
                box_crease = layout.box()
                row_crease = box_crease.row()
                row_crease.prop(scene, 'expandcrease',
                    icon='TRIA_DOWN' if scene.expandcrease else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_crease.prop(scene, 'creasemode', expand=True)
                if scene.creasemode != 'SDS':
                    if scene.expandcrease:
                        row_sets = box_crease.row(align=True)
                        setbutton = row_sets.operator('sxtools.setgroup', text='25%')
                        setbutton.setmode = scene.creasemode
                        setbutton.setvalue = 0.25
                        setbutton = row_sets.operator('sxtools.setgroup', text='50%')
                        setbutton.setmode = scene.creasemode
                        setbutton.setvalue = 0.5
                        setbutton = row_sets.operator('sxtools.setgroup', text='75%')
                        setbutton.setmode = scene.creasemode
                        setbutton.setvalue = 0.75
                        setbutton = row_sets.operator('sxtools.setgroup', text='100%')
                        setbutton.setmode = scene.creasemode
                        setbutton.setvalue = 1.0
                        col_sets = box_crease.column(align=True)
                        setbutton = col_sets.operator('sxtools.setgroup', text='Clear Weights')
                        setbutton.setmode = scene.creasemode
                        setbutton.setvalue = -1.0
                elif scene.creasemode == 'SDS':
                    if scene.expandcrease:
                        col_sds = box_crease.column(align=False)
                        col_sds.prop(sxtools, 'modifiervisibility', text='Show Modifiers')
                        col_sds.label(text='Mesh Mirroring:')
                        row_mirror = box_crease.row()
                        row_mirror.prop(sxtools, 'xmirror')
                        row_mirror.prop(sxtools, 'ymirror')
                        row_mirror.prop(sxtools, 'zmirror')
                        col2_sds = box_crease.column(align=False)
                        col2_sds.prop(scene, 'autocrease', text='Auto Hard-Crease Bevels')
                        split_sds = col2_sds.split()
                        split_sds.label(text='Max Crease Mode:')
                        split_sds.prop(sxtools, 'hardmode', text='')
                        col3_sds = box_crease.column(align=True)
                        col3_sds.prop(sxtools, 'subdivisionlevel', text='Subdivision Level')
                        col3_sds.prop(sxtools, 'bevelsegments', text='Bevel Segments')
                        col3_sds.prop(sxtools, 'bevelwidth', text='Bevel Width')
                        col3_sds.prop(sxtools, 'smoothangle', text='Normal Smoothing Angle')
                        col3_sds.prop(sxtools, 'weldthreshold', text='Weld Threshold')
                        if obj.sxtools.subdivisionlevel > 0:
                            col3_sds.prop(sxtools, 'decimation', text='Decimation Limit Angle')
                            col3_sds.label(text='Selection Tri Count: '+mesh.calculate_triangles(objs))
                        col3_sds.separator()
                        col4_sds = box_crease.column(align=True)
                        modifiers = '\t'.join(obj.modifiers.keys())
                        if 'sx' in modifiers:
                            col4_sds.operator('sxtools.removemodifiers', text='Remove Modifiers')
                        else:
                            col_sds.enabled = False
                            row_mirror.enabled = False
                            col2_sds.enabled = False
                            col3_sds.enabled = False
                            col4_sds.operator('sxtools.modifiers', text='Add Modifiers')

                # Processing, Utils, and Export ------------------------------------
                box_export = layout.box()
                row_export = box_export.row()
                row_export.prop(scene, 'expandexport',
                    icon='TRIA_DOWN' if scene.expandexport else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_export.prop(scene, 'exportmode', expand=True)
                if scene.exportmode == 'MAGIC':
                    if scene.expandexport:
                        col_export = box_export.column(align=True)
                        if (obj.sxtools.category != 'DEFAULT') and (obj.sxtools.category != 'PALETTED'):
                            col_export.prop(sxtools, 'smoothness1', text='Layer1-3 Base Smoothness', slider=True)
                            col_export.prop(sxtools, 'smoothness2', text='Layer4-5 Base Smoothness', slider=True)
                        if obj.sxtools.staticvertexcolors == '0':
                            col_export.prop(sxtools, 'overlaystrength', text='Overlay Strength', slider=True)
                        col_export.prop(sxtools, 'lodmeshes', text='Create LOD Meshes')
                        col_export.label(text='Note: Check Subdivision and Bevel settings')
                        # col_export.separator()
                        if prefs.materialtype != 'SMP':
                            row2_export = box_export.row(align=True)
                            row2_export.prop(sxtools, 'staticvertexcolors', text='')
                            row2_export.prop(scene, 'exportquality', text='')
                        col2_export = box_export.column(align=True)
                        col2_export.operator('sxtools.macro', text='Magic Button')
                        if ('ExportObjects' in bpy.data.collections.keys()) and (len(bpy.data.collections['ExportObjects'].objects) > 0):
                            col2_export.operator('sxtools.removeexports', text='Remove LOD Meshes')

                elif scene.exportmode == 'UTILS':
                    if scene.expandexport:
                        col_utils = box_export.column(align=False)
                        col_utils.operator('sxtools.revertobjects', text='Revert to Control Cages')
                        if not scene.shift:
                            pivot_text = 'Set Pivots to Center of Mass'
                        else:
                            pivot_text = 'Set Pivots to Bbox Center'
                        col_utils.operator('sxtools.setpivots', text=pivot_text)
                        col_utils.operator('sxtools.groupobjects', text='Group Selected Objects')
                        row_debug = box_export.row()
                        row_debug.prop(scene, 'expanddebug',
                            icon='TRIA_DOWN' if scene.expanddebug else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_debug.label(text='Debug Tools')
                        if scene.expanddebug:
                            col_debug = box_export.column(align=True)
                            # col_debug.prop(scene, 'gpucomposite', text='GPU Compositing')
                            col_debug.operator('sxtools.create_sxcollection', text='Debug: Update SXCollection')
                            col_debug.operator('sxtools.enableall', text='Debug: Enable All Layers')
                            col_debug.operator('sxtools.applymodifiers', text='Debug: Apply Modifiers')
                            col_debug.operator('sxtools.generatemasks', text='Debug: Generate Masks')
                            col_debug.operator('sxtools.createuv0', text='Debug: Create UVSet0')
                            col_debug.operator('sxtools.generatelods', text='Debug: Create LOD Meshes')
                            col_debug.operator('sxtools.resetoverlay', text='Debug: Reset Overlay Layer')
                            col_debug.operator('sxtools.resetmaterial', text='Debug: Reset SXMaterial')
                            col_debug.operator('sxtools.resetscene', text='Debug: Reset scene (warning!)')

                elif scene.exportmode == 'EXPORT':
                    if scene.expandexport:
                        col2_export = box_export.column(align=True)
                        col2_export.label(text='Set Export Folder:')
                        col2_export.prop(scene, 'exportfolder', text='')
                        col3_export = box_export.column(align=True)
                        # col3_export.prop(sxtools, 'lodmeshes', text='Export LOD Meshes')
                        if ('sxSubdivision' not in obj.modifiers.keys()) or ('sxBevel' not in obj.modifiers.keys()):
                            col3_export.enabled = False
                        split_export = box_export.split(factor=0.1)
                        split_export.operator('sxtools.checklist', text='', icon='INFO')

                        if not scene.shift:
                            exp_text = 'Export Selected'
                        else:
                            exp_text = 'Export All'
                        exp_button = split_export.operator('sxtools.exportfiles', text=exp_text)

                        if mode == 'EDIT':
                            split_export.enabled = False

        else:
            layout = self.layout
            col = self.layout.column()
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
        objs = selection_validator(self, context)
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
        objs = selection_validator(self, context)
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
        if not context.area:
            print('Selection Monitor: Context Lost')
            sxglobals.modalStatus = False
            return {'CANCELLED'}

        selection = context.object
        scene = context.scene.sxtools

        if (len(sxglobals.masterPaletteArray) == 0) or (len(sxglobals.materialArray) == 0) or (len(sxglobals.rampDict) == 0) or (len(sxglobals.categoryDict) == 0):
            sxglobals.librariesLoaded = False

        if not sxglobals.librariesLoaded:
            load_libraries(self, context)

        if selection is not self.prevSelection:
            self.prevSelection = context.object
            if (selection is not None) and len(selection.sxlayers) > 0:
                refresh_actives(self, context)
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}

        # return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.prevSelection = context.object
        context.window_manager.modal_handler_add(self)
        print('SX Tools: Starting selection monitor')
        return {'RUNNING_MODAL'}


class SXTOOLS_OT_keymonitor(bpy.types.Operator):
    bl_idname = 'sxtools.keymonitor'
    bl_label = 'Key Monitor'

    redraw: bpy.props.BoolProperty(default=False)
    prevShift: bpy.props.BoolProperty(default=False)
    prevAlt: bpy.props.BoolProperty(default=False)
    prevCtrl: bpy.props.BoolProperty(default=False)


    def modal(self, context, event):
        if not context.area:
            print('Key Monitor: Context Lost')
            sxglobals.modalStatus = False
            return {'CANCELLED'}

        scene = context.scene.sxtools

        if (self.prevShift != event.shift):
            self.prevShift = event.shift
            scene.shift = event.shift
            self.redraw = True

        if (self.prevAlt != event.alt):
            self.prevAlt = event.alt
            scene.alt = event.alt
            self.redraw = True

        if (self.prevCtrl != event.ctrl):
            self.prevCtrl = event.ctrl
            scene.ctrl = event.ctrl
            self.redraw = True

        if self.redraw:
            context.area.tag_redraw()
            self.redraw = False
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}


    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        print('SX Tools: Starting key monitor')
        return {'RUNNING_MODAL'}


class SXTOOLS_OT_addramp(bpy.types.Operator):
    bl_idname = 'sxtools.addramp'
    bl_label = 'Add Ramp Preset'
    bl_description = 'Add ramp preset to Gradient Library'

    rampName: bpy.props.StringProperty(name='Ramp Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'rampName', text='')


    def execute(self, context):
        files.save_ramp(self.rampName)
        return {'FINISHED'}


class SXTOOLS_OT_delramp(bpy.types.Operator):
    bl_idname = 'sxtools.delramp'
    bl_label = 'Remove Ramp Preset'
    bl_description = 'Delete ramp preset from Gradient Library'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        rampEnum = context.scene.sxtools.ramplist[:]
        rampName = sxglobals.presetLookup[context.scene.sxtools.ramplist]
        del sxglobals.rampDict[rampName]
        del sxglobals.presetLookup[rampEnum]
        files.save_file('gradients')
        return {'FINISHED'}


class SXTOOLS_OT_addpalettecategory(bpy.types.Operator):
    bl_idname = 'sxtools.addpalettecategory'
    bl_label = 'Add Palette Category'
    bl_description = 'Adds a palette category to the Palette Library'

    paletteCategoryName: bpy.props.StringProperty(name='Category Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'paletteCategoryName', text='')


    def execute(self, context):
        found = False
        for i, categoryDict in enumerate(sxglobals.masterPaletteArray):
            for category in categoryDict.keys():
                if category == self.paletteCategoryName.replace(" ", ""):
                    message_box('Palette Category Exists!')
                    found = True
                    break

        if not found:
            categoryName = self.paletteCategoryName.replace(" ", "")
            categoryEnum = categoryName.upper()
            categoryDict = {categoryName: {}}

            sxglobals.masterPaletteArray.append(categoryDict)
            files.save_file('palettes')
            files.load_file('palettes')
            context.scene.sxtools.palettecategories = categoryEnum
        return {'FINISHED'}


class SXTOOLS_OT_delpalettecategory(bpy.types.Operator):
    bl_idname = 'sxtools.delpalettecategory'
    bl_label = 'Remove Palette Category'
    bl_description = 'Removes a palette category from the Palette Library'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        categoryEnum = context.scene.sxtools.palettecategories[:]
        categoryName = sxglobals.presetLookup[context.scene.sxtools.palettecategories]

        for i, categoryDict in enumerate(sxglobals.masterPaletteArray):
            for category in categoryDict.keys():
                if category == categoryName:
                    sxglobals.masterPaletteArray.remove(categoryDict)
                    del sxglobals.presetLookup[categoryEnum]
                    break

        files.save_file('palettes')
        files.load_file('palettes')
        return {'FINISHED'}


class SXTOOLS_OT_addmaterialcategory(bpy.types.Operator):
    bl_idname = 'sxtools.addmaterialcategory'
    bl_label = 'Add Material Category'
    bl_description = 'Adds a material category to the Material Library'

    materialCategoryName: bpy.props.StringProperty(name='Category Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'materialCategoryName', text='')


    def execute(self, context):
        found = False
        for i, categoryDict in enumerate(sxglobals.materialArray):
            for category in categoryDict.keys():
                if category == self.materialCategoryName.replace(" ", ""):
                    message_box('Palette Category Exists!')
                    found = True
                    break

        if not found:
            categoryName = self.materialCategoryName.replace(" ", "")
            categoryEnum = categoryName.upper()
            categoryDict = {categoryName: {}}

            sxglobals.materialArray.append(categoryDict)
            files.save_file('materials')
            files.load_file('materials')
            context.scene.sxtools.materialcategories = categoryEnum
        return {'FINISHED'}


class SXTOOLS_OT_delmaterialcategory(bpy.types.Operator):
    bl_idname = 'sxtools.delmaterialcategory'
    bl_label = 'Remove Material Category'
    bl_description = 'Removes a material category from the Material Library'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        categoryEnum = context.scene.sxtools.materialcategories[:]
        categoryName = sxglobals.presetLookup[context.scene.sxtools.materialcategories]

        for i, categoryDict in enumerate(sxglobals.materialArray):
            for category in categoryDict.keys():
                if category == categoryName:
                    sxglobals.materialArray.remove(categoryDict)
                    del sxglobals.presetLookup[categoryEnum]
                    break

        files.save_file('materials')
        files.load_file('materials')
        return {'FINISHED'}


class SXTOOLS_OT_addpalette(bpy.types.Operator):
    bl_idname = 'sxtools.addpalette'
    bl_label = 'Add Palette Preset'
    bl_description = 'Add palette preset to Palette Library'

    label: bpy.props.StringProperty(name='Palette Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'label', text='')


    def execute(self, context):
        scene = context.scene.sxtools
        paletteName = self.label.replace(" ", "")
        if paletteName in context.scene.sxpalettes:
            message_box('Palette Name Already in Use!')
        else:
            for categoryDict in sxglobals.masterPaletteArray:
                for i, category in enumerate(categoryDict.keys()):
                    if category.casefold() == context.scene.sxtools.palettecategories.casefold():
                        categoryDict[category][paletteName] = [
                        [
                            scene.newpalette0[0],
                            scene.newpalette0[1],
                            scene.newpalette0[2]
                        ],
                        [
                            scene.newpalette1[0],
                            scene.newpalette1[1],
                            scene.newpalette1[2]
                        ],
                        [
                            scene.newpalette2[0],
                            scene.newpalette2[1],
                            scene.newpalette2[2]
                        ],
                        [
                            scene.newpalette3[0],
                            scene.newpalette3[1],
                            scene.newpalette3[2]
                        ],
                        [
                            scene.newpalette4[0],
                            scene.newpalette4[1],
                            scene.newpalette4[2]
                        ]]
                    break

        files.save_file('palettes')
        files.load_file('palettes')
        return {'FINISHED'}


class SXTOOLS_OT_delpalette(bpy.types.Operator):
    bl_idname = 'sxtools.delpalette'
    bl_label = 'Remove Palette Preset'
    bl_description = 'Delete palette preset from Palette Library'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty(name='Palette Name')


    def invoke(self, context, event):
        paletteName = self.label.replace(" ", "")
        category = context.scene.sxpalettes[paletteName].category

        for i, categoryDict in enumerate(sxglobals.masterPaletteArray):
            if category in categoryDict.keys():
                del categoryDict[category][paletteName]

        files.save_file('palettes')
        files.load_file('palettes')
        return {'FINISHED'}


class SXTOOLS_OT_addmaterial(bpy.types.Operator):
    bl_idname = 'sxtools.addmaterial'
    bl_label = 'Add Material Preset'
    bl_description = 'Add palette preset to Material Library'

    materialName: bpy.props.StringProperty(name='Material Name')


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'materialName', text='')


    def execute(self, context):
        scene = context.scene.sxtools
        materialName = self.materialName.replace(" ", "")
        if materialName in context.scene.sxmaterials:
            message_box('Material Name Already in Use!')
        else:
            for categoryDict in sxglobals.materialArray:
                for i, category in enumerate(categoryDict.keys()):
                    if category.casefold() == context.scene.sxtools.materialcategories.casefold():
                        categoryDict[category][materialName] = [
                        [
                            scene.newpalette0[0],
                            scene.newpalette0[1],
                            scene.newpalette0[2]
                        ],
                        [
                            scene.newpalette1[0],
                            scene.newpalette1[1],
                            scene.newpalette1[2]
                        ],
                        [
                            scene.newpalette2[0],
                            scene.newpalette2[1],
                            scene.newpalette2[2]
                        ]]
                    break

        files.save_file('materials')
        files.load_file('materials')
        return {'FINISHED'}


class SXTOOLS_OT_delmaterial(bpy.types.Operator):
    bl_idname = 'sxtools.delmaterial'
    bl_label = 'Remove Material Preset'
    bl_description = 'Delete material preset from Material Library'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty(name='Material Name')


    def invoke(self, context, event):
        materialName = self.label.replace(" ", "")
        category = context.scene.sxmaterials[materialName].category

        for i, categoryDict in enumerate(sxglobals.materialArray):
            if category in categoryDict.keys():
                del categoryDict[category][materialName]

        files.save_file('materials')
        files.load_file('materials')
        return {'FINISHED'}


class SXTOOLS_OT_scenesetup(bpy.types.Operator):
    bl_idname = 'sxtools.scenesetup'
    bl_label = 'Set Up Object'
    bl_description = 'Creates necessary material, vertex color layers,\nUV layers, and tool-specific variables'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            setup.update_init_array()
            setup.setup_layers(objs)
            setup.create_sxmaterial()
            setup.setup_geometry(objs)

            context.scene.display_settings.display_device = 'sRGB'
            context.scene.view_settings.view_transform = 'Standard'

            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applycolor(bpy.types.Operator):
    bl_idname = 'sxtools.applycolor'
    bl_label = 'Apply Color'
    bl_description = 'Applies the Fill Color to selected objects or components'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            color = context.scene.sxtools.fillcolor # convert.srgb_to_linear(context.scene.sxtools.fillcolor)
            overwrite = context.scene.sxtools.fillalpha
            if objs[0].mode == 'EDIT':
                overwrite = True
            noise = context.scene.sxtools.fillnoise
            mono = context.scene.sxtools.fillmono
            tools.apply_color(objs, layer, color, overwrite, noise, mono)
            tools.update_recent_colors(color)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applyramp(bpy.types.Operator):
    bl_idname = 'sxtools.applyramp'
    bl_label = 'Apply Gradient'
    bl_description = 'Applies a gradient in various modes\nto the selected components or objects,\noptionally using their combined bounding volume'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            rampmode = context.scene.sxtools.rampmode
            mergebbx = context.scene.sxtools.rampbbox
            overwrite = context.scene.sxtools.rampalpha
            noise = context.scene.sxtools.rampnoise
            mono = context.scene.sxtools.rampmono
            if objs[0].mode == 'EDIT':
                overwrite = True
            ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
            tools.apply_ramp(objs, layer, ramp, rampmode, overwrite, mergebbx, noise, mono)

            sxglobals.composite = True
            refresh_actives(self, context)
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
        meshObjs = []
        for obj in objs:
            if obj.type == 'MESH':
                meshObjs.append(obj)

        idx = meshObjs[0].sxtools.selectedlayer
        layer = utils.find_layer_from_index(meshObjs[0], idx)
        if (layer.layerType == 'COLOR') and (sxglobals.listIndices[idx] != 0):
            enabled = True
        return enabled


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.find_layer_from_index(objs[0], idx)
            listIndex = utils.find_list_index(objs[0], sourceLayer)
            targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[listIndex - 1])
            layers.merge_layers(objs, sourceLayer, targetLayer)

            sxglobals.composite = True
            refresh_actives(self, context)
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
        meshObjs = []
        for obj in objs:
            if obj.type == 'MESH':
                meshObjs.append(obj)

        idx = meshObjs[0].sxtools.selectedlayer
        listIdx = sxglobals.listIndices[idx]
        layer = utils.find_layer_from_index(meshObjs[0], idx)

        if listIdx != (len(sxglobals.listIndices) - 1):
            nextIdx = sxglobals.listItems[listIdx + 1]
            nextLayer = utils.find_layer_from_index(meshObjs[0], nextIdx)

            if nextLayer.layerType != 'COLOR':
                return False

        if (listIdx != (len(sxglobals.listIndices) - 1)) and (layer.layerType == 'COLOR'):
            enabled = True
        return enabled


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.find_layer_from_index(objs[0], idx)
            listIndex = utils.find_list_index(objs[0], sourceLayer)
            targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[listIndex + 1])
            layers.merge_layers(objs, sourceLayer, targetLayer)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_copylayer(bpy.types.Operator):
    bl_idname = 'sxtools.copylayer'
    bl_label = 'Copy Layer'
    bl_description = 'Mark the selected layer for copying'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            sxglobals.copyLayer = layer
        return {'FINISHED'}

 
class SXTOOLS_OT_pastelayer(bpy.types.Operator):
    bl_idname = 'sxtools.pastelayer'
    bl_label = 'Paste Layer'
    bl_description = 'Shift-click to swap with copied layer\nAlt-click to merge with the target layer\n(Color layers only!)'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = sxglobals.copyLayer
            targetLayer = utils.find_layer_from_index(objs[0], idx)

            if event.shift:
                mode = 'swap'
            elif event.alt:
                mode = 'merge'
            else:
                mode = False

            if sourceLayer is None:
                message_box('Nothing to paste!')
                return {'FINISHED'}
            elif (targetLayer.layerType != 'COLOR') and (mode == 'merge'):
                message_box('Merging only supported with color layers')
                return {'FINISHED'}
            else:
                layers.paste_layer(objs, sourceLayer, targetLayer, mode)

                sxglobals.composite = True
                refresh_actives(self, context)
                return {'FINISHED'}
        return {'FINISHED'}


class SXTOOLS_OT_clearlayers(bpy.types.Operator):
    bl_idname = 'sxtools.clear'
    bl_label = 'Clear Layer'
    bl_description = 'Shift-click to clear all layers\non selected objects or components'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            if event.shift:
                layer = None
            else:
                idx = objs[0].sxtools.selectedlayer
                layer = utils.find_layer_from_index(objs[0], idx)

            layers.clear_layers(objs, layer)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_selmask(bpy.types.Operator):
    bl_idname = 'sxtools.selmask'
    bl_label = 'Select Layer Mask'
    bl_description = 'Click to select components with alpha\nShift-click to invert selection'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            if event.shift:
                inverse = True
            else:
                inverse = False

            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            # bpy.context.view_layer.objects.active = objs[0]
            tools.select_mask(objs, [layer, ], inverse)
        return {'FINISHED'}


class SXTOOLS_OT_setgroup(bpy.types.Operator):
    bl_idname = 'sxtools.setgroup'
    bl_label = 'Set Value'
    bl_description = 'Click to apply modifier weight to selected edges\nShift-click to add edges to selection\nAlt-click to clear selection and select edges'
    bl_options = {'UNDO'}

    setmode: bpy.props.StringProperty()
    setvalue: bpy.props.FloatProperty()

    def invoke(self, context, event):
        objs = selection_validator(self, context)
        scene = context.scene.sxtools
        if len(objs) > 0:
            setmode = self.setmode
            setvalue = self.setvalue
            if event.shift:
                tools.select_set(objs, setvalue, setmode)
            elif event.alt:
                tools.select_set(objs, setvalue, setmode, True)
            else:
                tools.assign_set(objs, setvalue, setmode)
                if (scene.autocrease) and (setmode == 'BEV') and (setvalue != -1.0):
                    tools.assign_set(objs, 1.0, 'CRS')
        return {'FINISHED'}


class SXTOOLS_OT_applypalette(bpy.types.Operator):
    bl_idname = 'sxtools.applypalette'
    bl_label = 'Apply Palette'
    bl_description = 'Applies the selected palette to selected objects\nPalette colors are applied to layers 1-5'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty()


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            palette = self.label
            noise = context.scene.sxtools.palettenoise
            mono = context.scene.sxtools.palettemono

            tools.apply_palette(objs, palette, noise, mono)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_applymaterial(bpy.types.Operator):
    bl_idname = 'sxtools.applymaterial'
    bl_label = 'Apply PBR Material'
    bl_description = 'Applies the selected material to selected objects\nAlbedo color goes to the layer7\nmetallic and smoothness values are automatically applied\nto the selected material channels'
    bl_options = {'UNDO'}

    label: bpy.props.StringProperty()


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            material = self.label
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            overwrite = context.scene.sxtools.materialalpha
            if objs[0].mode == 'EDIT':
                overwrite = True
            noise = context.scene.sxtools.materialnoise
            mono = context.scene.sxtools.materialmono

            tools.apply_material(objs, layer, material, overwrite, noise, mono)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_modifiers(bpy.types.Operator):
    bl_idname = 'sxtools.modifiers'
    bl_label = 'Add Modifiers'
    bl_description = 'Adds Subdivision, Edge Split and Weighted Normals modifiers\nto selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.add_modifiers(objs)

            if objs[0].mode == 'OBJECT':
                bpy.ops.object.shade_smooth()
        return {'FINISHED'}


class SXTOOLS_OT_applymodifiers(bpy.types.Operator):
    bl_idname = 'sxtools.applymodifiers'
    bl_label = 'Apply Modifiers'
    bl_description = 'Applies modifiers to the selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.apply_modifiers(objs)
        return {'FINISHED'}


class SXTOOLS_OT_removemodifiers(bpy.types.Operator):
    bl_idname = 'sxtools.removemodifiers'
    bl_label = 'Remove Modifiers'
    bl_description = 'Remove SX Tools modifiers from selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.remove_modifiers(objs)

            if objs[0].mode == 'OBJECT':
                bpy.ops.object.shade_flat()
        return {'FINISHED'}


class SXTOOLS_OT_generatemasks(bpy.types.Operator):
    bl_idname = 'sxtools.generatemasks'
    bl_label = 'Create Palette Masks'
    bl_description = 'Bakes masks of Layers 1-7 into a UV channel\nfor exporting to game engine\nif dynamic palettes are used'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            layers.generate_masks(objs)
            layers.flatten_alphas(objs)
        return {'FINISHED'}


class SXTOOLS_OT_enableall(bpy.types.Operator):
    bl_idname = 'sxtools.enableall'
    bl_label = 'Enable All Layers'
    bl_description = 'Enables all layers on selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scn = bpy.context.scene.sxtools
        objs = selection_validator(self, context)
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

            setup.update_init_array()
            setup.setup_layers(objs)
            setup.create_sxmaterial()
            setup.setup_geometry(objs)

            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_resetscene(bpy.types.Operator):
    bl_idname = 'sxtools.resetscene'
    bl_label = 'Reset Scene'
    bl_description = 'Clears all SX Tools data from objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        setup.reset_scene()
        return {'FINISHED'}


class SXTOOLS_OT_exportfiles(bpy.types.Operator):
    bl_idname = 'sxtools.exportfiles'
    bl_label = 'Export Selected'
    bl_description = 'Saves FBX files of multi-part objects\nAll EMPTY-type groups at root based on selection are exported\nShift-click to export all SX Tools objects in the scene'


    def invoke(self, context, event):
        prefs = context.preferences.addons['sxtools'].preferences
        if event.shift:
            setup.create_sxcollection()
            selected = bpy.data.collections['SXObjects'].all_objects
        else:
            selected = context.view_layer.objects.selected
        groups = utils.find_groups(selected)
        files.export_files(groups)
        if prefs.removelods:
            export.remove_exports()
        sxglobals.composite = True
        refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_removeexports(bpy.types.Operator):
    bl_idname = 'sxtools.removeexports'
    bl_label = 'Remove LOD Meshes'
    bl_description = 'Deletes generated LOD meshes'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        export.remove_exports()
        scene.shadingmode = 'FULL'
        return {'FINISHED'}


class SXTOOLS_OT_setpivots(bpy.types.Operator):
    bl_idname = 'sxtools.setpivots'
    bl_label = 'Set Pivots'
    bl_description = 'Set pivot to center of mass on selected objects\nShift-click to set pivot to center of bounding box'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            active = context.active_object
            for obj in objs:
                context.view_layer.objects.active = obj
                if event.shift:
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                else:
                    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')

            context.view_layer.objects.active = active
        return {'FINISHED'}


class SXTOOLS_OT_createuv0(bpy.types.Operator):
    bl_idname = 'sxtools.createuv0'
    bl_label = 'Create UVSet0'
    bl_description = 'Checks if UVSet0 is missing\nand adds it at the top of the UV sets'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.create_uvset0(objs)
        return {'FINISHED'}


class SXTOOLS_OT_groupobjects(bpy.types.Operator):
    bl_idname = 'sxtools.groupobjects'
    bl_label = 'Group Objects'
    bl_description = 'Groups objects under an empty\nwith pivot placed at the bottom center'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.group_objects(objs)
        return {'FINISHED'}


class SXTOOLS_OT_generatelods(bpy.types.Operator):
    bl_idname = 'sxtools.generatelods'
    bl_label = 'Generate LOD Meshes'
    bl_description = 'Creates LOD meshes\nfrom selected objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        orgObjs = []

        if len(objs) > 0:
            for obj in objs:
                if '_LOD' not in obj.name:
                    orgObjs.append(obj)

        if len(orgObjs) > 0:
            export.generate_lods(orgObjs)
        return {'FINISHED'}


class SXTOOLS_OT_resetmaterial(bpy.types.Operator):
    bl_idname = 'sxtools.resetmaterial'
    bl_label = 'Reset SXMaterial'
    bl_description = 'Removes and regenerates SXMaterial\nand assigns it to objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        sxMatObjs = []
        if 'SXMaterial' in bpy.data.materials.keys():
            sxMat = bpy.data.materials.get('SXMaterial')

            for obj in context.scene.objects:
                if obj.active_material == bpy.data.materials['SXMaterial']:
                    sxMatObjs.append(obj.name)
                    obj.data.materials.clear()

            sxMat.user_clear()
            bpy.data.materials.remove(sxMat)

        bpy.context.view_layer.update()
        setup.update_init_array()
        setup.create_sxmaterial()

        for objName in sxMatObjs:
            context.scene.objects[objName].sxtools.shadingmode = 'FULL'
            context.scene.objects[objName].active_material = bpy.data.materials['SXMaterial']

        return {'FINISHED'}


class SXTOOLS_OT_resetoverlay(bpy.types.Operator):
    bl_idname = 'sxtools.resetoverlay'
    bl_label = 'Reset Overlay'
    bl_description = 'Sets overlay default color to 0.5 gray'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        for obj in objs:
            obj.sxlayers['overlay'].defaultColor = [0.5, 0.5, 0.5, 1.0]

        layers.clear_uvs(objs, objs[0].sxlayers['overlay'])
        bpy.context.view_layer.update()

        return {'FINISHED'}


class SXTOOLS_OT_revertobjects(bpy.types.Operator):
    bl_idname = 'sxtools.revertobjects'
    bl_label = 'Revert to Control Cages'
    bl_description = 'Removes modifiers and clears\nlayers generated by processing'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.revert_objects(objs)

            sxglobals.composite = True
            refresh_actives(self, context)

            scene.shadingmode = 'FULL'
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.shade_flat()
        return {'FINISHED'}


class SXTOOLS_OT_loadlibraries(bpy.types.Operator):
    bl_idname = 'sxtools.loadlibraries'
    bl_label = 'Load Libraries'
    bl_description = 'Loads SX Tools libraries of\npalettes, materials, gradients and categories'


    def invoke(self, context, event):
        load_libraries(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_checklist(bpy.types.Operator):
    bl_idname = 'sxtools.checklist'
    bl_label = 'Export Checklist'
    bl_description = 'Steps to check before exporting'


    def invoke(self, context, event):
        message_box('1) Choose category\n2) Paint color layers\n2) Crease edges\n3) Set object pivots\n4) Objects must be in groups\n5) Set subdivision\n6) Set base smoothness and overlay strength\n7) Press Magic Button\n8) Set folder, Export Selected')
        return {'FINISHED'}


class SXTOOLS_OT_selectup(bpy.types.Operator):
    bl_idname = 'sxtools.selectup'
    bl_label = 'Select Layer Up'
    bl_description = 'Selects the layer above'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            listLength = len(sxglobals.listItems)
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.find_layer_from_index(objs[0], idx)
            listIndex = utils.find_list_index(objs[0], sourceLayer)
            if listIndex > 1:
                targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[listIndex - 1])
            else:
                targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[0])

            for obj in objs:
                obj.sxtools.selectedlayer = targetLayer.index

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_selectdown(bpy.types.Operator):
    bl_idname = 'sxtools.selectdown'
    bl_label = 'Select Layer Down'
    bl_description = 'Selects the layer below'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            listLength = len(sxglobals.listItems)
            idx = objs[0].sxtools.selectedlayer
            sourceLayer = utils.find_layer_from_index(objs[0], idx)
            listIndex = utils.find_list_index(objs[0], sourceLayer)
            if listIndex < (listLength - 1):
                targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[listIndex + 1])
            else:
                targetLayer = utils.find_layer_from_index(objs[0], sxglobals.listItems[listLength - 1])

            for obj in objs:
                obj.sxtools.selectedlayer = targetLayer.index

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_create_sxcollection(bpy.types.Operator):
    bl_idname = 'sxtools.create_sxcollection'
    bl_label = 'Update SXCollection'
    bl_description = 'Links all SXTools meshes into their own collection'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        setup.create_sxcollection()

        return {'FINISHED'}


class SXTOOLS_OT_macro(bpy.types.Operator):
    bl_idname = 'sxtools.macro'
    bl_label = 'Process Exports'
    bl_description = 'Calculates material channels\naccording to category.\nApplies modifiers in High Detail mode'
    bl_options = {'UNDO'}

    @classmethod
    def description(cls, context, properties):
        objs = selection_validator(cls, context)
        category = objs[0].sxtools.category
        mode = context.scene.sxtools.exportquality

        if mode == 'HI':
            modeString = 'High Detail export:\nModifiers are applied before baking\n\n'
        else:
            modeString = 'Low Detail export:\nBaking is performed on control cage (base mesh)\n\n'

        if category == 'DEFAULT':
            modeString += 'Default batch process:\n1) Overlay bake\n2) Occlusion bake\nNOTE: Overwrites existing overlay and occlusion'
        elif category == 'PALETTED':
            modeString += 'Paletted batch process:\n1) Occlusion bake\n2) Custom smoothness & metallic bake\n3) Custom overlay bake\n4) Emissive faces are smooth and non-occluded\nNOTE: Overwrites existing overlay, occlusion, transmission, metallic and smoothness'
        elif category == 'VEHICLES':
            modeString += 'Vehicle batch process:\n1) Custom occlusion bake\n2) Custom smoothness & metallic bake\n3) Custom overlay bake\n4) Emissive faces are smooth and non-occluded\nNOTE: Overwrites existing overlay, occlusion, transmission, metallic and smoothness'
        elif category == 'BUILDINGS':
            modeString += 'Buildings batch process:\n1) Overlay bake\n2) Occlusion bake\nNOTE: Overwrites existing overlay and occlusion'
        elif category == 'TREES':
            modeString += 'Trees batch process:\n1) Overlay bake\n2) Occlusion bake\nNOTE: Overwrites existing overlay and occlusion'
        elif category == 'TRANSPARENT':
            modeString += 'Buildings batch process:\n1) Overlay bake\n2) Occlusion bake\nNOTE: Overwrites existing overlay and occlusion'
        else:
            modeString += 'Batch process:\nCalculates material channels according to category'
        return modeString


    def invoke(self, context, event):
        scene = context.scene.sxtools
        objs = selection_validator(self, context)
        if len(objs) > 0:
            bpy.context.view_layer.objects.active = objs[0]
            check = validate.validate_objects(objs)
            if check:
                export.process_objects(objs)

                sxglobals.composite = True
                refresh_actives(self, context)

                scene.shadingmode = 'FULL'
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.ops.object.shade_smooth()
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Registration and initialization
# ------------------------------------------------------------------------
sxglobals = SXTOOLS_sxglobals()
files = SXTOOLS_files()
convert = SXTOOLS_convert()
utils = SXTOOLS_utils()
layers = SXTOOLS_layers()
setup = SXTOOLS_setup()
mesh = SXTOOLS_mesh()
tools = SXTOOLS_tools()
validate = SXTOOLS_validate()
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
    SXTOOLS_OT_keymonitor,
    SXTOOLS_OT_scenesetup,
    SXTOOLS_OT_applycolor,
    SXTOOLS_OT_applyramp,
    SXTOOLS_OT_addramp,
    SXTOOLS_OT_delramp,
    SXTOOLS_OT_addpalettecategory,
    SXTOOLS_OT_delpalettecategory,
    SXTOOLS_OT_addmaterialcategory,
    SXTOOLS_OT_delmaterialcategory,
    SXTOOLS_OT_addpalette,
    SXTOOLS_OT_delpalette,
    SXTOOLS_OT_addmaterial,
    SXTOOLS_OT_delmaterial,
    SXTOOLS_OT_setgroup,
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
    SXTOOLS_OT_createuv0,
    SXTOOLS_OT_groupobjects,
    SXTOOLS_OT_generatelods,
    SXTOOLS_OT_resetoverlay,
    SXTOOLS_OT_resetmaterial,
    SXTOOLS_OT_revertobjects,
    SXTOOLS_OT_loadlibraries,
    SXTOOLS_OT_checklist,
    SXTOOLS_OT_selectup,
    SXTOOLS_OT_selectdown,
    SXTOOLS_OT_create_sxcollection,
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
        kmi = km.keymap_items.new('SXTOOLS_OT_selectup', 'UP_ARROW', 'PRESS', shift=True, ctrl=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new('SXTOOLS_OT_selectdown', 'DOWN_ARROW', 'PRESS', shift=True, ctrl=True)
        addon_keymaps.append((km, kmi))
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
# - Lister methods should check for duplicates?
# - Hide Materials tab in Simple mode
# - Modifier stack occasionally staying hidden?
# - Auto-splitting and naming of mirrored geometry
# - Improve indication of when magic button is necessary
# - Auto-place pivots during processing?
# - Absolute path check
# - Different defaultColor if overlay layer blend mode changed?
# - Wrong palette after sxtools restart -> remember last palette?
# - Run from direct github zip download
#   - Split to multiple python files
#   - Default path to find libraries in the zip?
# - Skinning support
# - Submesh support
# - Investigate running processes headless from command line
# - Drive SXMaterial with custom props
# - GPU alpha accumulation
# - GPU debug mode
