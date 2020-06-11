bl_info = {
    'name': 'SX Tools',
    'author': 'Jani Kahrama / Secret Exit Ltd.',
    'version': (4, 3, 8),
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
import numpy as np
from bpy.app.handlers import persistent
from collections import Counter
from mathutils import Vector


# ------------------------------------------------------------------------
#    Globals
# ------------------------------------------------------------------------
class SXTOOLS_sxglobals(object):
    def __init__(self):
        self.librariesLoaded = False
        self.refreshInProgress = False
        self.hslUpdate = False
        self.modalStatus = False
        self.composite = False
        self.copyLayer = None
        self.listItems = []
        self.listIndices = {}
        self.prevMode = 'FULL'
        self.mode = None

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
            ['occlusion', False, 11, 'UV', [1.0, 1.0, 1.0, 1.0], 1.0, True, 1.0, 'ALPHA', '', 'UVSet1', 'V', '', 'U', '', 'U', '', 'U'],
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

        # Keywords used by Smart Separate. Avoid using these in regular object names
        self.keywords = ['_org', '_LOD0', '_top', '_bottom', '_front', '_rear', '_left', '_right']

        # Use absolute paths
        bpy.context.preferences.filepaths.use_relative_paths = False


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
            self.load_swatches(sxglobals.masterPaletteArray)
            return True
        elif mode == 'materials':
            self.load_swatches(sxglobals.materialArray)
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


    def load_swatches(self, swatcharray):
        if swatcharray == sxglobals.materialArray:
            swatchcount = 3
            sxlist = bpy.context.scene.sxmaterials
        elif swatcharray == sxglobals.masterPaletteArray:
            swatchcount = 5
            sxlist = bpy.context.scene.sxpalettes

        for categoryDict in swatcharray:
            for category in categoryDict.keys():
                if len(categoryDict[category]) == 0:
                    item = sxlist.add()
                    item.name = 'Empty'
                    item.category = category
                    for i in range(swatchcount):
                        incolor = [0.0, 0.0, 0.0, 1.0]
                        setattr(item, 'color'+str(i), incolor[:])
                else:
                    for entry in categoryDict[category]:
                        item = sxlist.add()
                        item.name = entry
                        item.category = category
                        for i in range(swatchcount):
                            incolor = [0.0, 0.0, 0.0, 1.0]
                            incolor[0] = categoryDict[category][entry][i][0]
                            incolor[1] = categoryDict[category][entry][i][1]
                            incolor[2] = categoryDict[category][entry][i][2]
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
        empty = True

        if 'ExportObjects' not in bpy.data.collections.keys():
            exportObjects = bpy.data.collections.new('ExportObjects')
        else:
            exportObjects = bpy.data.collections['ExportObjects']

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
            objArray = []
            for sel in selArray:
                if sel.type == 'MESH':
                    objArray.append(sel)
                    sel['staticVertexColors'] = sel.sxtools.staticvertexcolors
                    sel['sxToolsVersion'] = 'SX Tools for Blender ' + str(sys.modules['sxtools'].bl_info.get('version'))

            if len(objArray) > 0:
                empty = False

                # Create palette masks
                layers.generate_masks(objArray)

                for obj in objArray:
                    compLayers = utils.find_comp_layers(obj, obj['staticVertexColors'])
                    layer0 = utils.find_layer_from_index(obj, 0)
                    layer1 = utils.find_layer_from_index(obj, 1)
                    layers.blend_layers([obj, ], compLayers, layer1, layer0)

                # If linear colorspace exporting is selected
                if colorspace == 'LIN':
                    export.convert_to_linear(objArray)

                if prefs.materialtype == 'SMP':
                    path = scene.exportfolder
                else:
                    category = objArray[0].sxtools.category.lower()
                    print('Determining path: ', objArray[0].name, category)
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

        if empty:
            message_box('No objects exported!')
        else:
            message_box('Exported:\n' + str('\n').join(groupNames))


# ------------------------------------------------------------------------
#    Useful Miscellaneous Functions
# ------------------------------------------------------------------------
class SXTOOLS_utils(object):
    def __init__(self):
        return None


    def mode_manager(self, objs, set_mode=False, revert=False):
        if set_mode:
            sxglobals.mode = objs[0].mode
            if objs[0].mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        elif revert:
            bpy.ops.object.mode_set(mode=sxglobals.mode)
            # sxglobals.mode = None
        else:
            if sxglobals.mode == None:
                print('MISSING MODE SET!')
            elif objs[0].mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


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


    def find_colors_by_frequency(self, objs, layer, numcolors=None):
        colorArray = []

        for obj in objs:
            values = generate.mask_list(obj, layers.get_layer(obj, layer), as_rgba=True)
            if values is not None:
                colorArray.extend(values)

        colors = list(filter(lambda a: a != (0.0, 0.0, 0.0, 0.0), colorArray))
        sortList = [color for color, count in Counter(colors).most_common(numcolors)]

        if numcolors is not None:
            while len(sortList) < numcolors:
                sortList.append([0.0, 0.0, 0.0, 1.0])

            sortColors = []
            for i in range(numcolors):
                sortColors.append(sortList[i])

            return sortColors
        else:
            return sortList


    def find_root_pivot(self, objs):
        xmin, xmax, ymin, ymax, zmin, zmax = self.get_object_bounding_box(objs)
        pivot = ((xmax + xmin)*0.5, (ymax + ymin)*0.5, zmin)

        return pivot


    def color_compare(self, color1, color2, tolerance=0.001):
        vec1 = Vector(color1)
        vec2 = Vector(color2)
        difference = vec1 - vec2

        return difference.length <= tolerance


    def get_object_bounding_box(self, objs):
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

        return xmin, xmax, ymin, ymax, zmin, zmax


    def get_selection_bounding_box(self, objs):
        vert_pos_list = []
        for obj in objs:
            mesh = obj.data
            mat = obj.matrix_world
            for vert in mesh.vertices:
                if vert.select:
                    vert_pos_list.append(mat @ vert.co)

        bbx = [[None, None], [None, None], [None, None]]
        for i, fvPos in enumerate(vert_pos_list):
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

        return bbx[0][0], bbx[0][1], bbx[1][0], bbx[1][1], bbx[2][0], bbx[2][1]


    def calculate_triangles(self, objs):
        count = 0
        for obj in objs:
            if 'sxDecimate2' in obj.modifiers.keys():
                count += obj.modifiers['sxDecimate2'].face_count

        return str(count)


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
                                    layers.clear_layers([obj, ], sxLayer)

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

        if sxObjects.name not in bpy.context.scene.collection.children.keys():
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


    def luminance_to_color(self, value):
        return (value, value, value, 1.0)


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

        return [H/360.0, S, L]


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

            # H = H/360.0

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
        print('SX Tools: Exiting convert')


# ------------------------------------------------------------------------
#    Value Generators and Utils
#    NOTE: Switching between EDIT and OBJECT modes is slow.
#          Make sure OBJECT mode is enabled before calling
#          any functions in this class!
# ------------------------------------------------------------------------
class SXTOOLS_generate(object):
    def __init__(self):
        return None


    def curvature_list(self, obj, masklayer=None):
        scene = bpy.context.scene.sxtools
        normalize = scene.curvaturenormalize
        vert_curv_dict = {}
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

                vtxCurvature = min(vtxCurvature / float(numConnected), 1.0)

                vert_curv_dict[vert.index] = vtxCurvature
            else:
                vert_curv_dict[vert.index] = 0.0

        # Normalize convex and concave separately
        # to maximize artist ability to crease

        if normalize:
            minCurv = min(vert_curv_dict.values())
            maxCurv = max(vert_curv_dict.values())

            for vert, vtxCurvature in vert_curv_dict.items():
                if vtxCurvature < 0.0:
                    vert_curv_dict[vert] = (vtxCurvature / float(minCurv)) * -0.5 + 0.5
                elif vtxCurvature == 0.0:
                    vert_curv_dict[vert] = 0.5
                else:
                    vert_curv_dict[vert] = (vtxCurvature / float(maxCurv)) * 0.5 + 0.5
        else:
            for vert, vtxCurvature in vert_curv_dict.items():
                vert_curv_dict[vert] = (vtxCurvature + 0.5)

        vert_curv_list = self.vert_dict_to_loop_list(obj, vert_curv_dict, 1, 4)
        curv_list = self.mask_list(obj, vert_curv_list, masklayer)
        return curv_list


    def direction_list(self, obj, masklayer=None):
        scene = bpy.context.scene.sxtools
        coneangle = scene.dirCone
        cone = coneangle*0.5

        if coneangle == 0:
            samples = 1
        else:
            samples = coneangle * 5

        vert_dir_dict = {}
        vert_dict = self.vertex_pos_dict(obj)
        vert_ids = self.vertex_id_list(obj)

        for vert_id in vert_ids:
            vert_dir_dict[vert_id] = 0.0

        for i in range(samples):
            inclination = (scene.dirInclination + random.uniform(-cone, cone) - 90.0)* (2*math.pi)/360.0
            angle = (scene.dirAngle + random.uniform(-cone, cone) + 90) * (2*math.pi)/360.0

            direction = Vector((math.sin(inclination) * math.cos(angle), math.sin(inclination) * math.sin(angle), math.cos(inclination)))

            for vert_id in vert_ids:
                vertWorldNormal = Vector(vert_dict[vert_id][3])
                vert_dir_dict[vert_id] += max(min(vertWorldNormal @ direction, 1.0), 0.0)

        values = np.array(self.vert_dict_to_loop_list(obj, vert_dir_dict, 1, 1))
        values *= 1.0/values.max()
        values = values.tolist()

        vert_dir_list = [None] * len(values) * 4
        for i in range(len(values)):
            vert_dir_list[(0+i*4):(4+i*4)] = [values[i], values[i], values[i], 1.0]

        return self.mask_list(obj, vert_dir_list, masklayer)


    def noise_list(self, obj, amplitude=0.5, offset=0.5, mono=False, masklayer=None):

        def make_noise(amplitude, offset, mono):
            col = [None, None, None, 1.0]

            if mono:
                monoval = offset+random.uniform(-amplitude, amplitude)
                for i in range(3):
                    col[i] = monoval
            else:
                for i in range(3):
                    col[i] = offset+random.uniform(-amplitude, amplitude)
            return col

        vert_ids = self.vertex_id_list(obj)

        noise_dict = {}
        for vtx_id in vert_ids:
            noise_dict[vtx_id] = make_noise(amplitude, offset, mono)

        noise_list = self.vert_dict_to_loop_list(obj, noise_dict, 4, 4)
        return self.mask_list(obj, noise_list, masklayer)


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


    def occlusion_list(self, obj, raycount=100, blend=0.5, dist=10.0, groundplane=False, bias=0.01, masklayer=None):
        scene = bpy.context.scene
        contribution = 1.0/float(raycount)
        hemiSphere = self.ray_randomizer(raycount)
        mix = max(min(blend, 1.0), 0.0)
        forward = Vector((0.0, 0.0, 1.0))

        vert_occ_dict = {}
        vert_dict = self.vertex_pos_dict(obj)
        vert_ids = self.vertex_id_list(obj)

        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.show_viewport = False

        if groundplane:
            pivot = utils.find_root_pivot([obj, ])
            pivot = (pivot[0], pivot[1], pivot[2] - 0.5)
            ground = self.ground_plane(20, pivot)

        for vert_id in vert_ids:
            occValue = 1.0
            scnOccValue = 1.0
            vertLoc = Vector(vert_dict[vert_id][0])
            vertNormal = Vector(vert_dict[vert_id][1])
            vertWorldLoc = Vector(vert_dict[vert_id][2])
            vertWorldNormal = Vector(vert_dict[vert_id][3])

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

            vert_occ_dict[vert_id] = float((occValue * (1.0 - mix)) + (scnOccValue * mix))

        if groundplane:
            bpy.data.objects.remove(ground, do_unlink=True)

        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.show_viewport = obj.sxtools.modifiervisibility

        vert_occ_list = generate.vert_dict_to_loop_list(obj, vert_occ_dict, 1, 4)
        return self.mask_list(obj, vert_occ_list, masklayer)


    def thickness_list(self, obj, raycount, bias=0.000001, masklayer=None):
        contribution = 1.0/float(raycount)
        hemiSphere = self.ray_randomizer(raycount)
        forward = Vector((0.0, 0.0, 1.0))
        bias = 1e-5

        vert_occ_dict = {}
        vert_dict = self.vertex_pos_dict(obj)
        vert_ids = self.vertex_id_list(obj)

        distances = []

        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.show_viewport = False

        # First pass to analyze ray hit distances,
        # then set max ray distance to half of median distance
        distHemiSphere = self.ray_randomizer(20)

        for vert_id in vert_ids:
            vertLoc = Vector(vert_dict[vert_id][0])
            vertNormal = Vector(vert_dict[vert_id][1])

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

        vert_occ_dict = {}

        for vert_id in vert_ids:
            thicknessValue = 0.0
            vertLoc = Vector(vert_dict[vert_id][0])
            vertNormal = Vector(vert_dict[vert_id][1])

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

            vert_occ_dict[vert_id] = thicknessValue

        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                modifier.show_viewport = obj.sxtools.modifiervisibility

        vert_occ_list = generate.vert_dict_to_loop_list(obj, vert_occ_dict, 1, 4)
        return self.mask_list(obj, vert_occ_list, masklayer)


    def mask_list(self, obj, colors, masklayer=None, as_rgba=False):
        count = len(colors)//4

        if (masklayer is None) and (sxglobals.mode == 'OBJECT'):
            if as_rgba:
                rgba = [None] * count
                for i in range(count):
                    rgba[i] = tuple(colors[(0+i*4):(4+i*4)])
                return rgba
            else:
                return colors
        else:
            if masklayer is None:
                mask, empty = self.selection_mask(obj)
                if empty:
                    return None
            else:
                mask, empty = layers.get_layer_mask(obj, masklayer)
                if empty:
                    return None

            if as_rgba:
                rgba = [None] * count
                for i in range(count):
                    rgba[i] = tuple(Vector(colors[(0+i*4):(4+i*4)]) * mask[i])
                return rgba
            else:
                color_list = [None, None, None, None] * count
                for i in range(count):
                    color = colors[(0+i*4):(4+i*4)]
                    color[3] *= mask[i]
                    color_list[(0+i*4):(4+i*4)] = color
                return color_list


    def color_list(self, obj, color, masklayer=None, as_rgba=False):
        count = len(obj.data.vertex_colors[0].data)
        colors = [color[0], color[1], color[2], color[3]] * count

        return self.mask_list(obj, colors, masklayer, as_rgba)


    def ramp_list(self, obj, objs, rampmode, masklayer=None, mergebbx=True):
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

        # For OBJECT mode selections
        if sxglobals.mode == 'OBJECT':
            if mergebbx:
                xmin, xmax, ymin, ymax, zmin, zmax = utils.get_object_bounding_box(objs)
            else:
                xmin, xmax, ymin, ymax, zmin, zmax = utils.get_object_bounding_box([obj, ])

        # For EDIT mode multi-obj component selection
        else:
            xmin, xmax, ymin, ymax, zmin, zmax = utils.get_selection_bounding_box(objs)

        vertPosDict = self.vertex_pos_dict(obj)
        ramp_dict = {}

        for vert_id in vertPosDict.keys():
            ratioRaw = None
            ratio = None
            fvPos = vertPosDict[vert_id][2]

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

            ratio = max(min(ratioRaw, 1.0), 0.0)
            ramp_dict[vert_id] = ramp.color_ramp.evaluate(ratio)

        ramp_list = self.vert_dict_to_loop_list(obj, ramp_dict, 4, 4)

        return self.mask_list(obj, ramp_list, masklayer)


    def luminance_remap_list(self, obj, layer=None, masklayer=None, values=None):
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']
        if values is None:
            values = layers.get_luminances(obj, layer, as_rgba=False)
        colors = generate.empty_list(obj, 4)
        count = len(values)

        for i in range(count):
            ratio = max(min(values[i], 1.0), 0.0)
            colors[(0+i*4):(4+i*4)] = ramp.color_ramp.evaluate(ratio)

        return self.mask_list(obj, colors, masklayer)


    def vertex_id_list(self, obj):
        mesh = obj.data

        count = len(mesh.vertices)
        ids = [None] * count
        mesh.vertices.foreach_get('index', ids)

        return ids


    def empty_list(self, obj, channelcount):
        count = len(obj.data.uv_layers[0].data)
        looplist = [0.0] * count * channelcount

        return looplist


    def vert_dict_to_loop_list(self, obj, vert_dict, dictchannelcount, listchannelcount):
        mesh = obj.data
        loop_list = self.empty_list(obj, listchannelcount)

        if dictchannelcount < listchannelcount:
            if (dictchannelcount == 1) and (listchannelcount == 2):
                i = 0
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        value = vert_dict.get(vert_idx, 0.0)
                        loop_list[(0+i*listchannelcount):(listchannelcount+i*listchannelcount)] = [value, value]
                        i+=1 
            elif (dictchannelcount == 1) and (listchannelcount == 4):
                i = 0
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        value = vert_dict.get(vert_idx, 0.0)
                        loop_list[(0+i*listchannelcount):(listchannelcount+i*listchannelcount)] = [value, value, value, 1.0]
                        i+=1
            elif (dictchannelcount == 3) and (listchannelcount == 4):
                i = 0
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        value = vert_dict.get(vert_idx, [0.0, 0.0, 0.0])
                        loop_list[(0+i*listchannelcount):(listchannelcount+i*listchannelcount)] = [value[0], value[1], value[2], 1.0]
                        i+=1  
        else:
            if listchannelcount == 1:
                i = 0
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        loop_list[i] = vert_dict.get(vert_idx, 0.0)
                        i+=1
            else:
                i = 0
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        loop_list[(0+i*listchannelcount):(listchannelcount+i*listchannelcount)] = vert_dict.get(vert_idx, [0.0] * listchannelcount)
                        i+=1 

        return loop_list


    def vertex_pos_dict(self, obj):
        mesh = obj.data
        mat = obj.matrix_world
        ids = self.vertex_id_list(obj)

        vertex_dict = {}
        if sxglobals.mode == 'EDIT':
            for vert_id in ids:
                if mesh.vertices[vert_id].select:
                    vertex_dict[vert_id] = (mesh.vertices[vert_id].co, mesh.vertices[vert_id].normal, mat @ mesh.vertices[vert_id].co, (mat @ mesh.vertices[vert_id].normal - mat @ Vector()).normalized())
        else:
            for vert_id in ids:
                vertex_dict[vert_id] = (mesh.vertices[vert_id].co, mesh.vertices[vert_id].normal, mat @ mesh.vertices[vert_id].co, (mat @ mesh.vertices[vert_id].normal - mat @ Vector()).normalized())

        return vertex_dict


    def selection_mask(self, obj):
        mesh = obj.data
        count = len(mesh.uv_layers[0].data)
        mask = [0.0] * count

        pre_check = [None] * len(mesh.vertices)
        mesh.vertices.foreach_get('select', pre_check)
        if True not in pre_check:
            return mask, True
        else:
            i = 0
            if bpy.context.tool_settings.mesh_select_mode[2]:
                for poly in mesh.polygons:
                    sel = float(poly.select)
                    for loop_idx in poly.loop_indices:
                        mask[i] = sel
                        i+=1
            else:
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        mask[i] = float(mesh.vertices[vert_idx].select)
                        i+=1

            return mask, False


    def __del__(self):
        print('SX Tools: Exiting generate')


# ------------------------------------------------------------------------
#    Layer Functions
#    NOTE: Objects must be in OBJECT mode before calling layer functions,
#          use utils.mode_manager() before calling layer functions
#          to set and track correct state
# ------------------------------------------------------------------------
class SXTOOLS_layers(object):
    def __init__(self):
        return None


    # wrapper for low-level functions, always returns layerdata in RGBA
    def get_layer(self, obj, sourcelayer, as_rgba=False, uv_luminance=False):
        sourceType = sourcelayer.layerType
        sxmaterial = bpy.data.materials['SXMaterial'].node_tree

        if sourceType == 'COLOR':
            values = self.get_colors(obj, sourcelayer.vertexColorLayer)
        elif sourceType == 'UV':
            uvs = self.get_uvs(obj, sourcelayer.uvLayer0, channel=sourcelayer.uvChannel0)
            count = len(uvs) # len(obj.data.uv_layers[0].data)
            values = [None] * count * 4

            if (sourcelayer.name == 'gradient1') or (sourcelayer.name == 'gradient2'):
                if sourcelayer.name == 'gradient1':
                    dv = sxmaterial.nodes['PaletteColor3'].outputs[0].default_value
                else:
                    dv = sxmaterial.nodes['PaletteColor4'].outputs[0].default_value

                for i in range(count):
                    values[(0+i*4):(4+i*4)] = [dv[0], dv[1], dv[2], uvs[i]]
            elif uv_luminance:
                for i in range(count):
                    values[(0+i*4):(4+i*4)] = [1.0, 1.0, 1.0, uvs[i]]
            else:
                for i in range(count):
                    values[(0+i*4):(4+i*4)] = [uvs[i], uvs[i], uvs[i], 1.0]

        elif sourceType == 'UV4':
            values = layers.get_uv4(obj, sourcelayer)

        if as_rgba:
            count = len(values)//4
            rgba = [None] * count
            for i in range(count):
                rgba[i] = tuple(values[(0+i*4):(4+i*4)])
            return rgba
        else:
            return values


    # takes RGBA buffers, converts and writes to appropriate uv and vertex sets
    def set_layer(self, obj, colors, targetlayer):
        targetType = targetlayer.layerType

        if targetType == 'COLOR':
            layers.set_colors(obj, targetlayer.vertexColorLayer, colors)

        elif targetType == 'UV':
            target_uvs = layers.get_luminances(obj, sourcelayer=None, colors=colors, as_rgba=False)
            layers.set_uvs(obj, targetlayer.uvLayer0, target_uvs, targetlayer.uvChannel0)

        elif targetType == 'UV4':
            layers.set_uv4(obj, targetlayer, colors)


    def get_layer_mask(self, obj, sourcelayer):
        layerType = sourcelayer.layerType

        if layerType == 'COLOR':
            colors = self.get_colors(obj, sourcelayer.vertexColorLayer)
            values = colors[3::4]
        elif layerType == 'UV':
            values = self.get_uvs(obj, sourcelayer.uvLayer0, sourcelayer.uvChannel0)
        elif layerType == 'UV4':
            values = self.get_uvs(obj, sourcelayer.uvLayer3, sourcelayer.uvChannel3)

        if any(v != 0.0 for v in values):
            return values, False
        else:
            return values, True


    def get_colors(self, obj, source):
        sourceColors = obj.data.vertex_colors[source].data
        colors = [None] * len(sourceColors) * 4
        sourceColors.foreach_get('color', colors)

        return colors


    def set_colors(self, obj, target, colors):
        targetColors = obj.data.vertex_colors[target].data
        targetColors.foreach_set('color', colors)


    def get_luminances(self, obj, sourcelayer=None, colors=None, as_rgba=False):
        if colors is None:
            layerType = sourcelayer.layerType
            if layerType == 'COLOR':
                colors = self.get_colors(obj, sourcelayer.vertexColorLayer)
            elif layerType == 'UV':
                if as_rgba:
                    values = self.get_uvs(obj, sourcelayer.uvLayer0, sourcelayer.uvChannel0)
                    colors = generate.empty_list(obj, 4)
                    count = len(values)
                    for i in range(count):
                        colors[(0+i*4):(4+i*4)] = convert.luminance_to_color(values[i])
                    return colors
                else:
                    return self.get_uvs(obj, sourcelayer.uvLayer0, sourcelayer.uvChannel0)
            elif layerType == 'UV4':
                colors = self.get_uv4(obj, sourcelayer)

        if as_rgba:
            values = generate.empty_list(obj, 4)
            count = len(values)
            for i in range(count):
                values[(0+i*4):(4+i*4)] = convert.luminance_to_color(convert.color_to_luminance(colors[(0+i*4):(4+i*4)]))
        else:
            values = generate.empty_list(obj, 1)
            count = len(values)
            for i in range(count):
                values[i] = convert.color_to_luminance(colors[(0+i*4):(4+i*4)])

        return values


    def get_uvs(self, obj, sourcelayer, channel=None):
        channels = {'U': 0, 'V': 1}
        sourceUVs = obj.data.uv_layers[sourcelayer].data
        count = len(sourceUVs)
        source_uvs = [None] * count * 2
        sourceUVs.foreach_get('uv', source_uvs)

        if channel is None:
            uvs = source_uvs
        else:
            uvs = [None] * count
            sc = channels[channel]
            for i in range(count):
                uvs[i] = source_uvs[sc+i*2]

        return uvs


    # when targetchannel is None, sourceuvs is expected to contain data for both U and V
    def set_uvs(self, obj, targetlayer, sourceuvs, targetchannel=None):
        channels = {'U': 0, 'V': 1}
        targetUVs = obj.data.uv_layers[targetlayer].data

        if targetchannel is None:
            targetUVs.foreach_set('uv', sourceuvs)
        else:
            target_uvs = self.get_uvs(obj, targetlayer)
            tc = channels[targetchannel]
            count = len(sourceuvs)
            for i in range(count):
                target_uvs[tc+i*2] = sourceuvs[i]
            targetUVs.foreach_set('uv', target_uvs)


    def get_uv4(self, obj, sourcelayer, as_rgba=False):
        channels = {'U': 0, 'V':1}
        sourceUVs0 = obj.data.uv_layers[sourcelayer.uvLayer0].data
        sourceUVs1 = obj.data.uv_layers[sourcelayer.uvLayer2].data
        count = len(sourceUVs0)
        source_uvs0 = [None] * count * 2
        source_uvs1 = [None] * count * 2
        sourceUVs0.foreach_get('uv', source_uvs0)
        sourceUVs1.foreach_get('uv', source_uvs1)

        uv0 = channels[sourcelayer.uvChannel0]
        uv1 = channels[sourcelayer.uvChannel1]
        uv2 = channels[sourcelayer.uvChannel2]
        uv3 = channels[sourcelayer.uvChannel3]

        if as_rgba:
            colors = [None] * count
            for i in range(count):
                colors[i] = tuple((source_uvs0[uv0+i*2], source_uvs0[uv1+i*2], source_uvs1[uv2+i*2], source_uvs1[uv3+i*2]))
        else:
            colors = [None] * count * 4
            for i in range(count):
                colors[(0+i*4):(4+i*4)] = [source_uvs0[uv0+i*2], source_uvs0[uv1+i*2], source_uvs1[uv2+i*2], source_uvs1[uv3+i*2]]

        return colors


    def set_uv4(self, obj, targetlayer, colors):
        channels = {'U': 0, 'V':1}

        uvs0 = generate.empty_list(obj, 2)
        uvs1 = generate.empty_list(obj, 2)

        uv0 = channels[targetlayer.uvChannel0]
        uv1 = channels[targetlayer.uvChannel1]
        uv2 = channels[targetlayer.uvChannel2]
        uv3 = channels[targetlayer.uvChannel3]

        target1 = targetlayer.uvLayer0
        target2 = targetlayer.uvLayer2

        count = len(uvs0)//2
        for i in range(count):
            [uvs0[(uv0+i*2)], uvs0[(uv1+i*2)], uvs1[(uv2+i*2)], uvs1[(uv3+i*2)]] = colors[(0+i*4):(4+i*4)]

        self.set_uvs(obj, target1, uvs0, None)
        self.set_uvs(obj, target2, uvs1, None)


    def clear_layers(self, objs, targetlayer=None):
        scene = bpy.context.scene.sxtools

        def clear_layer(obj, layer):
            default_color = layer.defaultColor
            if sxglobals.mode == 'OBJECT':
                colors = generate.color_list(obj, color=default_color)
                setattr(obj.sxlayers[layer.index], 'alpha', 1.0)
                setattr(obj.sxlayers[layer.index], 'visibility', True)
                if layer == obj.sxlayers['overlay']:
                    setattr(obj.sxlayers[layer.index], 'blendMode', 'OVR')
                else:
                    setattr(obj.sxlayers[layer.index], 'blendMode', 'ALPHA')
                layers.set_layer(obj, colors, layer)
            else:
                colors = layers.get_layer(obj, layer)
                mask, empty = generate.selection_mask(obj)
                if not empty:
                    for i in range(len(mask)):
                        if mask[i] == 1.0:
                            colors[(0+i*4):(4+i*4)] = default_color
                    layers.set_layer(obj, colors, layer)

        if targetlayer is None:
            print('SX Tools: Clearing all layers')
            scene.fillalpha = True
            scene.toolopacity = 1.0
            scene.toolblend = 'ALPHA'
            for obj in objs:
                for sxlayer in obj.sxlayers:
                    clear_layer(obj, sxlayer)
                obj.data.update()
        else:
            for obj in objs:
                clear_layer(obj, targetlayer)
                obj.data.update()


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
        active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = objs[0]

        for obj in objs:
            colors = self.get_layer(obj, layer, uv_luminance=True)
            count = len(colors)//4

            if shadingmode == 'DEBUG':
                for i in range(count):
                    color = colors[(0+i*4):(4+i*4)]
                    a = color[3]
                    colors[(0+i*4):(4+i*4)] = [color[0]*a, color[1]*a, color[2]*a, 1.0]
            elif shadingmode == 'ALPHA':
                for i in range(count):
                    a = colors[3+i*4]
                    colors[(0+i*4):(4+i*4)] = [a, a, a, 1.0]

            self.set_layer(obj, colors, obj.sxlayers['composite'])
            obj.data.update()

        bpy.context.view_layer.objects.active = active


    def blend_layers(self, objs, topLayerArray, baseLayer, resultLayer, uv_luminance=False):
        active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = objs[0]

        for obj in objs:
            basecolors = self.get_layer(obj, baseLayer)

            for layer in topLayerArray:
                layerIdx = layer.index

                if getattr(obj.sxlayers[layerIdx], 'visibility'):
                    blendmode = getattr(obj.sxlayers[layerIdx], 'blendMode')
                    layeralpha = getattr(obj.sxlayers[layerIdx], 'alpha')
                    topcolors = self.get_layer(obj, obj.sxlayers[layerIdx], uv_luminance=True)
                    basecolors = tools.blend_values(topcolors, basecolors, blendmode, layeralpha)

            self.set_layer(obj, basecolors, resultLayer)
            obj.data.update()

        bpy.context.view_layer.objects.active = active


    # Generate 1-bit layer masks for color layers
    # so the faces can be re-colored in a game engine
    def generate_masks(self, objs):
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


    def flatten_alphas(self, objs):
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

        if sourceMode == 'COLOR' and (targetMode == 'COLOR' or targetMode == 'UV4'):
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


    def update_layer_panel(self, objs, layer):
        scene = bpy.context.scene.sxtools
        colors = utils.find_colors_by_frequency(objs, layer, 8)
        # Update layer HSL elements
        hArray = []
        sArray = []
        lArray = []
        for color in colors:
            hsl = convert.rgb_to_hsl(color)
            hArray.append(hsl[0])
            sArray.append(hsl[1])
            lArray.append(hsl[2])
        hue = max(hArray)
        sat = max(sArray)
        lightness = max(lArray)

        sxglobals.hslUpdate = True
        bpy.context.scene.sxtools.huevalue = hue
        bpy.context.scene.sxtools.saturationvalue = sat
        bpy.context.scene.sxtools.lightnessvalue = lightness
        sxglobals.hslUpdate = False

        # Update layer palette elements
        for i, color in enumerate(colors):
            palettecolor = [color[0], color[1], color[2], 1.0]
            setattr(scene, 'layerpalette' + str(i + 1), palettecolor)


    def color_layers_to_values(self, objs):
        scene = bpy.context.scene.sxtools

        for i in range(5):
            layer = objs[0].sxlayers[i+1]
            palettecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]
            tabcolor = getattr(scene, 'newpalette' + str(i))

            if not utils.color_compare(palettecolor, tabcolor):
                setattr(scene, 'newpalette' + str(i), palettecolor)


    def material_layers_to_values(self, objs):
        scene = bpy.context.scene.sxtools
        layers = [7, 12, 13]

        for i, idx in enumerate(layers):
            layer = objs[0].sxlayers[idx]
            palettecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]
            tabcolor = getattr(scene, 'newmaterial' + str(i))

            if not utils.color_compare(palettecolor, tabcolor):
                setattr(scene, 'newmaterial' + str(i), palettecolor)


    def __del__(self):
        print('SX Tools: Exiting layers')


# ------------------------------------------------------------------------
#    Tool Actions
# ------------------------------------------------------------------------
class SXTOOLS_tools(object):
    def __init__(self):
        return None


    def blend_values(self, topcolors, basecolors, blendmode, blendvalue):
        if topcolors == None:
            return basecolors
        else:
            count = len(basecolors)//4
            colors = [None] * count * 4
            midpoint = 0.5 # convert.srgb_to_linear([0.5, 0.5, 0.5, 1.0])[0]

            # print('blend values: ', blendmode, blendvalue, topcolors[0:4], basecolors[0:4])
            for i in range(count):
                top = Vector(topcolors[(0+i*4):(4+i*4)])
                base = Vector(basecolors[(0+i*4):(4+i*4)])
                a = top[3] * blendvalue

                if blendmode == 'ALPHA':
                    base = top * a + base * (1 - a)
                    # if i==0:
                    #     print('base alpha: ', base[3])
                    base[3] = min(base[3]+a, 1.0)
                    # if i==0:
                    #     print('base alpha again: ', base[3])

                elif blendmode == 'ADD':
                    base += top * a
                    base[3] = min(base[3]+a, 1.0)

                elif blendmode == 'MUL':
                    for j in range(3):
                        base[j] *= top[j] * a + (1 - a)

                elif blendmode == 'OVR':
                    over = Vector([0.0, 0.0, 0.0, top[3]])
                    b = over[3] * blendvalue
                    for j in range(3):
                        if base[j] < midpoint:
                            over[j] = 2.0 * base[j] * top[j]
                        else:
                            over[j] = 1.0 - 2.0 * (1.0 - base[j]) * (1.0 - top[j])
                    base = over * b + base * (1.0 - b)
                    base[3] = min(base[3]+a, 1.0)

                elif blendmode == 'CLR':
                    base = top

                if base[3] == 0.0:
                    base = [0.0, 0.0, 0.0, 0.0]
                # if i==0:
                #     print('base post blend: ', base)
                colors[(0+i*4):(4+i*4)] = base
            return colors


    def apply_tool(self, objs, targetlayer, masklayer=None, invertmask=False, color=None):
        # then = time.time()
        utils.mode_manager(objs, set_mode=True)

        scene = bpy.context.scene.sxtools
        amplitude = scene.noiseamplitude
        offset = scene.noiseoffset
        mono = scene.noisemono
        overwrite = scene.fillalpha
        blendvalue = scene.toolopacity
        blendmode = scene.toolblend
        rampmode = scene.rampmode
        if sxglobals.mode == 'EDIT':
            mergebbx = False
        else:
            mergebbx = scene.rampbbox

        for obj in objs:
            # then1 = time.time()
            if overwrite:
                masklayer = None
            else:
                if masklayer is None:
                    masklayer = targetlayer

            # Get colorbuffer
            if color is not None:
                colors = generate.color_list(obj, color, masklayer)
            elif scene.toolmode == 'COL':
                color = scene.fillcolor
                colors = generate.color_list(obj, color, masklayer)
            elif scene.toolmode == 'GRD':
                colors = generate.ramp_list(obj, objs, rampmode, masklayer, mergebbx)
            elif scene.toolmode == 'NSE':
                colors = generate.noise_list(obj, amplitude, offset, mono, masklayer)
            elif scene.toolmode == 'CRV':
                colors = generate.curvature_list(obj, masklayer)
            elif scene.toolmode == 'OCC':
                colors = generate.occlusion_list(obj, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
            elif scene.toolmode == 'THK':
                colors = generate.thickness_list(obj, scene.occlusionrays, scene.occlusionbias)
            elif scene.toolmode == 'DIR':
                colors = generate.direction_list(obj)
            elif scene.toolmode == 'LUM':
                colors = generate.luminance_remap_list(obj, targetlayer)

            if colors is not None:
                # now = time.time()
                # print('Generate colors duration: ', now-then1, ' seconds')
                # then1 = time.time()

                # Write to target

                # print('colors: ', colors)
                target_colors = layers.get_layer(obj, targetlayer)
                # print('target colors: ', blendmode, blendvalue, target_colors)
                colors = self.blend_values(colors, target_colors, blendmode, blendvalue)
                # print('blended colors:', colors)
                layers.set_layer(obj, colors, targetlayer)
                # spoon = layers.get_layer(obj, targetlayer)
                # print('readback: ', spoon)

                obj.data.update()
                # now = time.time()
                # print('Write colors duration: ', now-then1, ' seconds')

        utils.mode_manager(objs, revert=True)

        # now = time.time()
        # print('Apply tool ', scene.toolmode, ' duration: ', now-then, ' seconds')


    # mode 0: hue, mode 1: saturation, mode 2: lightness
    def apply_hsl(self, objs, layer, hslmode, newValue):
        utils.mode_manager(objs, set_mode=True)

        colors = utils.find_colors_by_frequency(objs, layer)
        valueArray = []
        for color in colors:
            hsl = convert.rgb_to_hsl(color)
            valueArray.append(hsl[hslmode])
        layervalue = max(valueArray)

        offset = newValue-layervalue

        if (layervalue != 1.0) or (layervalue == 1.0 and offset < 0.0):
            for obj in objs:
                colors = layers.get_layer(obj, layer)
                colors = generate.mask_list(obj, colors)
                if colors is not None:
                    count = len(colors)//4
                    for i in range(count):
                        color = colors[(0+i*4):(3+i*4)]
                        hsl = convert.rgb_to_hsl(color)
                        hsl[hslmode] += offset
                        rgb = convert.hsl_to_rgb(hsl)
                        colors[(0+i*4):(3+i*4)] = [rgb[0], rgb[1], rgb[2]]
                    target_colors = layers.get_layer(obj, layer)
                    colors = self.blend_values(colors, target_colors, 'ALPHA', 1.0)
                    layers.set_layer(obj, colors, layer)
                    obj.data.update()

        utils.mode_manager(objs, revert=True)


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


    def select_mask(self, objs, layer, invertmask=False):
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        for obj in objs:
            mesh = obj.data
            mask = (layers.get_layer_mask(obj, utils.find_layer_from_index(obj, layer.index)))[0]

            i = 0
            if bpy.context.tool_settings.mesh_select_mode[2]:
                for poly in mesh.polygons:
                    for loop_idx in poly.loop_indices:
                        if invertmask:
                            if mask[i] == 0.0:
                                poly.select = True
                        else:
                            if mask[i] > 0.0:
                                poly.select = True
                        i+=1
            else:
                for poly in mesh.polygons:
                    for vert_idx, loop_idx in zip(poly.vertices, poly.loop_indices):
                        if invertmask:
                            if mask[i] == 0.0:
                                mesh.vertices[vert_idx].select = True
                        else:
                            if mask[i] > 0.0:
                                mesh.vertices[vert_idx].select = True
                        i+=1

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)


    def assign_set(self, objs, setvalue, setmode):
        mode = objs[0].mode
        modeDict = {
            'CRS': 'SubSurfCrease',
            'BEV': 'BevelWeight'}
        weight = setvalue
        modename = modeDict[setmode]

        if mode == 'EDIT':

            for obj in objs:
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)

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

                bmesh.update_edit_mesh(mesh)


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

        for obj in objs:
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

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

            bmesh.update_edit_mesh(mesh)


    def layer_copy_manager(self, objs, sourcelayer, targetlayer):
        for obj in objs:
            if sourcelayer.layerType == 'UV' and targetlayer.layerType == 'UV':
                sourcevalues = layers.get_luminances(obj, sourcelayer, as_rgba=True)
            else:
                sourcevalues = layers.get_layer(obj, sourcelayer)
            layers.set_layer(obj, sourcevalues, targetlayer)


    def apply_palette(self, objs, palette, noise, mono):
        if not sxglobals.refreshInProgress:
            sxglobals.refreshInProgress = True

        scene = bpy.context.scene
        palette = [
            scene.sxpalettes[palette].color0,
            scene.sxpalettes[palette].color1,
            scene.sxpalettes[palette].color2,
            scene.sxpalettes[palette].color3,
            scene.sxpalettes[palette].color4]

        for idx in range(1, 6):
            layer = utils.find_layer_from_index(objs[0], idx)
            palette_color = palette[idx - 1] # convert.srgb_to_linear(palette[idx - 1])
            bpy.data.materials['SXMaterial'].node_tree.nodes['PaletteColor'+str(idx-1)].outputs[0].default_value = palette_color

            scene.sxtools.fillalpha = False
            self.apply_tool(objs, layer, color=palette_color, clear=True)

        sxglobals.refreshInProgress = False


    def apply_material(self, objs, targetlayer, material):
        material = bpy.context.scene.sxmaterials[material]
        scene = bpy.context.scene.sxtools

        for obj in objs:
            scene.fillalpha = False
            scene.toolopacity = 1.0
            scene.toolblend = 'ALPHA'
            self.apply_tool([obj, ], targetlayer, color=material.color0, clear=True)
            self.apply_tool([obj, ], obj.sxlayers['metallic'], masklayer=targetlayer, color=material.color1, clear=True)
            self.apply_tool([obj, ], obj.sxlayers['smoothness'], masklayer=targetlayer, color=material.color2, clear=True)


    def add_modifiers(self, objs):
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = obj.sxtools.smoothangle * (2*math.pi)/360.0

        for obj in objs:
            if 'sxMirror' not in obj.modifiers.keys():
                obj.modifiers.new(type='MIRROR', name='sxMirror')
                if obj.sxtools.xmirror or obj.sxtools.ymirror or obj.sxtools.zmirror:
                    obj.modifiers['sxMirror'].show_viewport = True
                else:
                    obj.modifiers['sxMirror'].show_viewport = False
                obj.modifiers['sxMirror'].show_expanded = False
                obj.modifiers['sxMirror'].use_axis[0] = obj.sxtools.xmirror
                obj.modifiers['sxMirror'].use_axis[1] = obj.sxtools.ymirror
                obj.modifiers['sxMirror'].use_axis[2] = obj.sxtools.zmirror
                if obj.sxtools.mirrorobject != '':
                    obj.modifiers['sxMirror'].mirror_object = bpy.context.view_layer.objects[obj.sxtools.mirrorobject]
                else:
                    obj.modifiers['sxMirror'].mirror_object = None
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
                obj.modifiers['sxBevel'].offset_type = obj.sxtools.beveltype # 'OFFSET' 'WIDTH' 'PERCENT'
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
        utils.mode_manager(objs, set_mode=True)
        bpy.context.view_layer.objects.active = objs[0]

        pivot = utils.find_root_pivot(objs)

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

        utils.mode_manager(objs, revert=True)


    # pivotmodes: 0 == no change, 1 == center of mass, 2 == center of bbox,
    # 3 == base of bbox, 4 == world origin, force == set mirror axis to zero
    def set_pivots(self, objs, pivotmode=None, force=False):
        viewlayer = bpy.context.view_layer
        active = viewlayer.objects.active
        selected = viewlayer.objects.selected[:]
        modedict = {'OFF': 0, 'MASS': 1, 'BBOX':2, 'ROOT': 3, 'ORG': 4}

        for sel in viewlayer.objects.selected:
            sel.select_set(False)

        for obj in objs:
            if pivotmode is None:
                mode = modedict[obj.sxtools.pivotmode]
            else:
                mode = pivotmode

            viewlayer.objects.active = obj
            obj.select_set(True)

            if mode == 1:
                bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
                if force:
                    pivot_loc = obj.location.copy()
                    if obj.sxtools.xmirror:
                        pivot_loc[0] = 0.0
                    if obj.sxtools.ymirror:
                        pivot_loc[1] = 0.0
                    if obj.sxtools.zmirror:
                        pivot_loc[2] = 0.0
                    bpy.context.scene.cursor.location = pivot_loc
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            elif mode == 2:
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                if force:
                    pivot_loc = obj.location.copy()
                    if obj.sxtools.xmirror:
                        pivot_loc[0] = 0.0
                    if obj.sxtools.ymirror:
                        pivot_loc[1] = 0.0
                    if obj.sxtools.zmirror:
                        pivot_loc[2] = 0.0
                    bpy.context.scene.cursor.location = pivot_loc
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            elif mode == 3:
                bpy.context.scene.cursor.location = utils.find_root_pivot([obj, ])
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            elif mode == 4:
                bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            else:
                pass

            obj.select_set(False)

        for sel in selected:
            sel.select_set(True)
        viewlayer.objects.active = active


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

        layers.clear_layers(objs, objs[0].sxlayers['overlay'])
        layers.clear_layers(objs, objs[0].sxlayers['occlusion'])
        layers.clear_layers(objs, objs[0].sxlayers['metallic'])
        layers.clear_layers(objs, objs[0].sxlayers['smoothness'])
        layers.clear_layers(objs, objs[0].sxlayers['transmission'])


    def update_palette_layer(self, objs, layerindex, color, palettenodename):
        scene = bpy.context.scene.sxtools
        layer = utils.find_layer_from_index(objs[0], layerindex)
        modecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]

        if color != modecolor:
            bpy.data.materials['SXMaterial'].node_tree.nodes[palettenodename].outputs[0].default_value = color
            scene.fillalpha = False
            tools.apply_tool(objs, layer, color=color)


    def zero_verts(self, objs):
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        for obj in objs:
            xmirror = obj.sxtools.xmirror
            ymirror = obj.sxtools.ymirror
            zmirror = obj.sxtools.zmirror
            bm = bmesh.from_edit_mesh(obj.data)

            selectedVerts = [vert for vert in bm.verts if vert.select]
            for vert in selectedVerts:
                if xmirror:
                    vert.co.x = 0.0 - obj.location.x
                if ymirror:
                    vert.co.y = 0.0 - obj.location.y
                if zmirror:
                    vert.co.z = 0.0 - obj.location.z

            bmesh.update_edit_mesh(obj.data)


    def __del__(self):
        print('SX Tools: Exiting tools')


# ------------------------------------------------------------------------
#    Validation Functions
# ------------------------------------------------------------------------
class SXTOOLS_validate(object):
    def __init__(self):
        return None


    def validate_objects(self, objs):
        ok1 = self.test_palette_layers(objs)
        ok2 = self.test_names(objs)

        if ok1 and ok2:
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
        utils.mode_manager(objs, set_mode=True)

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
                            utils.mode_manager(objs, revert=True)
                            return False
                    else:
                        if len(colorSet) > 2:
                            message_box('Multiple colors in ' + obj.name + ' layer' + str(i+1))
                            utils.mode_manager(objs, revert=True)
                            return False

        utils.mode_manager(objs, revert=True)
        return True


    # if paletted, check that emissive faces have color in static channel
    def test_emissives(self, objs):
        pass


    def test_names(self, objs):
        for obj in objs:
            if ('sxMirror' in obj.modifiers.keys()) and (obj.sxtools.xmirror or obj.sxtools.ymirror or obj.sxtools.zmirror):
                for keyword in sxglobals.keywords:
                    if keyword in obj.name:
                        message_box(obj.name + '\ncontains the substring ' + keyword + '\nreserved for Smart Separate\nfunction of Mirror Modifier')
                        return False
        return True


    def __del__(self):
        print('SX Tools: Exiting validate')


# ------------------------------------------------------------------------
#    Baking and Processing Functions
# ------------------------------------------------------------------------
class SXTOOLS_magic(object):
    def __init__(self):
        return None


    # This is a project-specific batch operation.
    # These should be adapted to the needs of the game,
    # baking category-specific values to achieve
    # consistent project-wide looks.
    def process_objects(self, objs):
        if not sxglobals.refreshInProgress:
            sxglobals.refreshInProgress = True

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
                # viewlayer.objects.active = obj
                tools.group_objects([obj, ])

            # Make sure auto-smooth is on
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
            sepObjs = []
            partObjs = []

            for obj in objs:
                if obj.sxtools.smartseparate:
                    sepObjs.append(obj)
            partObjs = export.smart_separate(sepObjs)
            for obj in partObjs:
                if obj not in objs:
                    objs.append(obj)

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
                if obj.name not in sourceObjects.objects.keys():
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
                newObjArray = export.generate_lods(lodObjs)
                for newObj in newObjArray:
                    newObjs.append(newObj)

            objs = newObjs

        # Place pivots
        tools.set_pivots(objs, force=True)

        for obj in objs:
            obj.select_set(False)

        viewlayer.objects.active = objs[0]

        # Begin category-specific compositing operations
        # Hide modifiers for performance
        for obj in objs:
            obj.sxtools.modifiervisibility = False
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
                lodObjs = export.generate_lods(nonLodObjs)
                bpy.ops.object.select_all(action='DESELECT')
                for obj in nonLodObjs:
                    obj.select_set(True)
                for obj in lodObjs:
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
        sxglobals.refreshInProgress = False

        # Enable modifier stack for LODs
        for obj in objs:
            obj.sxtools.modifiervisibility = True


    def process_default(self, objs):
        print('SX Tools: Processing Default')
        scene = bpy.context.scene.sxtools
        sxglobals.mode = 'OBJECT'
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'
        obj = objs[0]

        # Apply occlusion
        if scene.enableocclusion:
            layer = obj.sxlayers['occlusion']
            scene.toolmode = 'OCC'
            scene.fillalpha = True
            scene.noisemono = True
            scene.occlusionblend = 0.5
            scene.occlusionrays = 200
            scene.occlusionbias = 0.01

            tools.apply_tool(objs, layer)

        # Apply custom overlay
        if scene.numoverlays != 0:
            layer = obj.sxlayers['overlay']
            scene.toolmode = 'CRV'
            scene.curvaturenormalize = True

            tools.apply_tool(objs, layer)

            scene.noisemono = False
            scene.toolmode = 'NSE'
            scene.toolopacity = 0.01
            scene.toolblend = 'MUL'

            tools.apply_tool(objs, layer)
            for obj in objs:
                obj.sxlayers['overlay'].blendMode = 'OVR'
                obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Emissives are smooth
        if scene.enableemission:
            color = (1.0, 1.0, 1.0, 1.0)
            masklayer = obj.sxlayers['emission']
            layer = obj.sxlayers['smoothness']
            scene.fillalpha = True
            tools.apply_tool(objs, layer, masklayer=masklayer, color=color)

        for obj in objs:
            obj.data.update()


    def process_paletted(self, objs):
        print('SX Tools: Processing Paletted')
        scene = bpy.context.scene.sxtools
        sxglobals.mode = 'OBJECT'
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'
        obj = objs[0]

        # Apply occlusion masked by emission
        layer = obj.sxlayers['occlusion']
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200
        scene.occlusionbias = 0.01
        scene.fillalpha = True

        for obj in objs:
            colors = generate.occlusion_list(obj, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
            colors1 = layers.get_layer(obj, obj.sxlayers['emission'], uv_luminance=True)
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            layers.set_layer(obj, colors, layer)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        scene.toolmode = 'CRV'
        scene.curvaturenormalize = True

        tools.apply_tool(objs, layer)

        scene.toolmode = 'NSE'
        scene.toolopacity = 0.01
        scene.toolblend = 'MUL'
        scene.noisemono = False

        tools.apply_tool(objs, layer)

        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'

        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Emissives are smooth
        color = (1.0, 1.0, 1.0, 1.0)
        mask = obj.sxlayers['emission']
        layer = obj.sxlayers['smoothness']
        scene.fillalpha = True
        tools.apply_tool(objs, layer, masklayer=mask, color=color)

        for obj in objs:
            obj.data.update()


    def process_vehicles(self, objs):
        print('SX Tools: Processing Vehicles')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        scene = bpy.context.scene.sxtools
        sxglobals.mode = 'OBJECT'
        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'
        obj = objs[0]

        # Apply occlusion masked by emission
        layer = obj.sxlayers['occlusion']
        scene.occlusionblend = 0.5
        scene.occlusionrays = 200
        scene.occlusionbias = 0.01
        scene.fillalpha = True

        for obj in objs:
            colors0 = generate.occlusion_list(obj, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
            colors1 = layers.get_layer(obj, obj.sxlayers['emission'], uv_luminance=True)
            colors = tools.blend_values(colors1, colors0, 'ALPHA', 1.0)

            layers.set_layer(obj, colors, layer)

        # Apply custom overlay
        layer = obj.sxlayers['overlay']
        scene.toolmode = 'CRV'
        scene.curvaturenormalize = True

        tools.apply_tool(objs, layer)

        scene.toolmode = 'NSE'
        scene.toolopacity = 0.01
        scene.toolblend = 'MUL'
        scene.noisemono = False

        tools.apply_tool(objs, layer)

        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'

        for obj in objs:
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clear_layers(objs, obj.sxlayers['metallic'])
        layers.clear_layers(objs, obj.sxlayers['smoothness'])
        layers.clear_layers(objs, obj.sxlayers['transmission'])

        material = 'Iron'
        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        for obj in objs:
            # Construct layer1-7 smoothness base mask
            color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)
            colors = generate.color_list(obj, color)
            color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 4))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 5))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            color = (0.0, 0.0, 0.0, 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 6))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Combine with smoothness from PBR material
            colors1 = generate.color_list(obj, palette[2], utils.find_layer_from_index(obj, 7))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Noise for variance
            colors1 = generate.noise_list(obj, 0.01, True)
            colors = tools.blend_values(colors1, colors, 'OVR', 1.0)
            # Combine smoothness base mask with custom curvature gradient
            scene.curvaturenormalize = True
            scene.ramplist = 'CURVATURESMOOTHNESS'
            colors1 = generate.curvature_list(obj)
            values = layers.get_luminances(obj, colors=colors1)
            colors1 = generate.luminance_remap_list(obj, values=values)
            colors = tools.blend_values(colors1, colors, 'MUL', 1.0)
            # Combine previous mix with directional dust
            scene.ramplist = 'DIRECTIONALDUST'
            scene.angle = 0.0
            scene.inclination = 40.0
            colors1 = generate.direction_list(obj)
            values = layers.get_luminances(obj, colors=colors1)
            colors1 = generate.luminance_remap_list(obj, values=values)
            colors = tools.blend_values(colors1, colors, 'MUL', 1.0)
            # Emissives are smooth
            color = (1.0, 1.0, 1.0, 1.0)
            colors1 = generate.color_list(obj, color, obj.sxlayers['emission'])
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Write smoothness
            scene.fillalpha = True
            layer = obj.sxlayers['smoothness']
            layers.set_layer(obj, colors, layer)

            # Apply PBR metal based on layer7
            scene.fillalpha = False
            # noise = 0.01
            # mono = True
            scene.toolmode = 'COL'
            scene.toolopacity = 1.0
            scene.toolblend = 'ALPHA'

            # Mix metallic with occlusion (dirt in crevices)
            colors = generate.color_list(obj, palette[0], utils.find_layer_from_index(obj, 7))
            colors1 = layers.get_layer(obj, obj.sxlayers['occlusion'], uv_luminance=True)
            if colors1 is not None and colors is not None:
                colors = tools.blend_values(colors1, colors, 'MUL', 1.0)
                layers.set_layer(obj, colors, obj.sxlayers['metallic'])

            obj.data.update()


    def process_buildings(self, objs):
        print('SX Tools: Processing Buildings')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        scene = bpy.context.scene.sxtools
        sxglobals.mode = 'OBJECT'
        obj = objs[0]
        scene.toolopacity = 1.0
        scene.toolblend = 'ALPHA'
        ramp = bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp']

        # Apply occlusion
        layer = obj.sxlayers['occlusion']
        scene.toolmode = 'OCC'
        scene.fillalpha = True
        scene.noisemono = True
        scene.occlusionblend = 0.0
        scene.occlusionrays = 200
        scene.occlusionbias = 0.05
        color = (1.0, 1.0, 1.0, 1.0)
        mask = utils.find_layer_from_index(obj, 7)

        for obj in objs:
            colors = generate.occlusion_list(obj, scene.occlusionrays, scene.occlusionblend, scene.occlusiondistance, scene.occlusiongroundplane, scene.occlusionbias)
            colors1 = generate.color_list(obj, color=color, masklayer=mask)
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            layers.set_layer(obj, colors, layer)

        # Apply normalized curvature with luma remapping to overlay, clear windows
        scene.curvaturenormalize = True
        scene.ramplist = 'WEARANDTEAR'
        for obj in objs:
            layer = obj.sxlayers['overlay']
            colors = generate.curvature_list(obj)
            values = layers.get_luminances(obj, colors=colors)
            colors1 = generate.luminance_remap_list(obj, values=values)
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            color = (0.5, 0.5, 0.5, 1.0)
            colors1 = generate.color_list(obj, color=color, masklayer=mask)
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            layers.set_layer(obj, colors, layer)
            obj.sxlayers['overlay'].blendMode = 'OVR'
            obj.sxlayers['overlay'].alpha = obj.sxtools.overlaystrength

        # Clear metallic, smoothness, and transmission
        layers.clear_layers(objs, obj.sxlayers['metallic'])
        layers.clear_layers(objs, obj.sxlayers['smoothness'])
        layers.clear_layers(objs, obj.sxlayers['transmission'])

        material = 'Silver'
        palette = [
            bpy.context.scene.sxmaterials[material].color0,
            bpy.context.scene.sxmaterials[material].color1,
            bpy.context.scene.sxmaterials[material].color2]

        for obj in objs:
            # Construct layer1-7 smoothness base mask
            color = (obj.sxtools.smoothness1, obj.sxtools.smoothness1, obj.sxtools.smoothness1, 1.0)
            colors = generate.color_list(obj, color)
            color = (obj.sxtools.smoothness2, obj.sxtools.smoothness2, obj.sxtools.smoothness2, 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 4))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 5))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            color = (0.0, 0.0, 0.0, 1.0)
            colors1 = generate.color_list(obj, color, utils.find_layer_from_index(obj, 6))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Combine with smoothness from PBR material
            colors1 = generate.color_list(obj, palette[2], utils.find_layer_from_index(obj, 7))
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Noise for variance
            colors1 = generate.noise_list(obj, 0.01, True)
            colors = tools.blend_values(colors1, colors, 'OVR', 1.0)
            # Combine smoothness base mask with custom curvature gradient
            scene.curvaturenormalize = True
            scene.ramplist = 'CURVATURESMOOTHNESS'
            colors1 = generate.curvature_list(obj)
            values = layers.get_luminances(obj, colors=colors1)
            colors1 = generate.luminance_remap_list(obj, values=values)
            colors = tools.blend_values(colors1, colors, 'MUL', 1.0)
            # Combine previous mix with directional dust
            scene.ramplist = 'DIRECTIONALDUST'
            scene.dirAngle = 0.0
            scene.dirInclination = 90.0
            scene.dirCone = 30
            colors1 = generate.direction_list(obj)
            values = layers.get_luminances(obj, colors=colors1)
            colors1 = generate.luminance_remap_list(obj, values=values)
            colors = tools.blend_values(colors1, colors, 'MUL', 1.0)
            # Emissives are smooth
            color = (1.0, 1.0, 1.0, 1.0)
            colors1 = generate.color_list(obj, color, obj.sxlayers['emission'])
            colors = tools.blend_values(colors1, colors, 'ALPHA', 1.0)
            # Write smoothness
            scene.fillalpha = True
            layer = obj.sxlayers['smoothness']
            layers.set_layer(obj, colors, layer)

            # Apply PBR metal based on layer7
            scene.fillalpha = False
            # noise = 0.01
            # mono = True
            scene.toolmode = 'COL'
            scene.toolopacity = 1.0
            scene.toolblend = 'ALPHA'

            colors = generate.color_list(obj, palette[0], utils.find_layer_from_index(obj, 7))
            if colors is not None:
                layers.set_layer(obj, colors, obj.sxlayers['metallic'])

            obj.data.update()


    def process_trees(self, objs):
        print('SX Tools: Processing Trees')
        scene = bpy.context.scene.sxtools
        sxglobals.mode = 'OBJECT'
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
        layers.clear_layers(objs, obj.sxlayers['metallic'])
        layers.clear_layers(objs, obj.sxlayers['smoothness'])
        layers.clear_layers(objs, obj.sxlayers['transmission'])

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
        tools.apply_tool(objs, layer, color)

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
        tools.apply_tool(objs, layer, color)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        color = (0.0, 0.0, 0.0, 1.0)

        maskLayer = utils.find_layer_from_index(obj, 6)
        layer = obj.sxlayers['smoothness']
        overwrite = True

        noise = 0.0
        mono = True
        tools.apply_tool(objs, layer, color, masklayer=maskLayer)

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
        tools.apply_tool(objs, layer, color, masklayer=maskLayer)
        maskLayer = utils.find_layer_from_index(obj, 5)
        tools.apply_tool(objs, layer, color, masklayer=maskLayer)

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


    def __del__(self):
        print('SX Tools: Exiting magic')


# ------------------------------------------------------------------------
#    Exporting Functions
# ------------------------------------------------------------------------
class SXTOOLS_export(object):
    def __init__(self):
        return None


    def smart_separate(self, objs):
        prefs = bpy.context.preferences.addons['sxtools'].preferences
        scene = bpy.context.scene.sxtools
        view_layer = bpy.context.view_layer
        mode = objs[0].mode
        objs = objs[:]
        sepObjs = []
        for obj in objs:
            if obj.sxtools.smartseparate:
                sepObjs.append(obj)

        if 'ExportObjects' not in bpy.data.collections.keys():
            exportObjects = bpy.data.collections.new('ExportObjects')
        else:
            exportObjects = bpy.data.collections['ExportObjects']

        if 'SourceObjects' not in bpy.data.collections.keys():
            sourceObjects = bpy.data.collections.new('SourceObjects')
        else:
            sourceObjects = bpy.data.collections['SourceObjects']

        if len(sepObjs) > 0:
            for obj in sepObjs:
                if (scene.exportquality == 'LO') and (obj.name not in sourceObjects.objects.keys()) and (obj.name not in exportObjects.objects.keys()) and (obj.sxtools.xmirror or obj.sxtools.ymirror or obj.sxtools.zmirror):
                    sourceObjects.objects.link(obj)       

        separatedObjs = []
        if len(sepObjs) > 0:
            active = view_layer.objects.active
            for obj in sepObjs:
                view_layer.objects.active = obj
                refObjs = view_layer.objects[:]
                orgname = obj.name[:]
                xmirror = obj.sxtools.xmirror
                ymirror = obj.sxtools.ymirror
                zmirror = obj.sxtools.zmirror

                if obj.modifiers['sxMirror'].mirror_object is not None:
                    refLoc = obj.modifiers['sxMirror'].mirror_object.location
                else:
                    refLoc = obj.location

                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier='sxMirror')

                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.separate(type='LOOSE')

                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                newObjArray = [view_layer.objects[orgname], ]

                for vlObj in view_layer.objects:
                    if vlObj not in refObjs:
                        newObjArray.append(vlObj)
                        exportObjects.objects.link(vlObj)

                if len(newObjArray) > 1:
                    tools.set_pivots(newObjArray)
                    suffixDict = {}
                    for newObj in newObjArray:
                        view_layer.objects.active = newObj
                        zstring = ''
                        ystring = ''
                        xstring = ''
                        objLoc = newObj.location
                        if zmirror:
                            if objLoc[2] > refLoc[2]:
                                zstring = '_top'
                            elif objLoc[2] < refLoc[2]:
                                zstring = '_bottom'
                        if ymirror:
                            if objLoc[1] > refLoc[1]:
                                if prefs.flipsmarty:
                                    ystring = '_rear'
                                else:
                                    ystring = '_front'
                            elif objLoc[1] < refLoc[1]:
                                if prefs.flipsmarty:
                                    ystring = '_front'
                                else:
                                    ystring = '_rear'
                        if xmirror:
                            if objLoc[0] > refLoc[0]:
                                if prefs.flipsmartx:
                                    xstring = '_left'
                                else:
                                    xstring = '_right'
                            elif objLoc[0] < refLoc[0]:
                                if prefs.flipsmartx:
                                    xstring = '_right'
                                else:
                                    xstring = '_left'

                        if len(newObjArray) > 2 ** (zmirror + ymirror + xmirror):
                            if not zstring+ystring+xstring in suffixDict:
                                suffixDict[zstring+ystring+xstring] = 0
                            else:
                                suffixDict[zstring+ystring+xstring] += 1
                            newObj.name = orgname + str(suffixDict[zstring+ystring+xstring]) + zstring + ystring + xstring
                        else:
                            newObj.name = orgname + zstring + ystring + xstring

                        newObj.data.name = newObj.name + '_mesh'

                separatedObjs.extend(newObjArray)
            view_layer.objects.active = active
        bpy.ops.object.mode_set(mode=mode)
        return separatedObjs


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

        xmin, xmax, ymin, ymax, zmin, zmax = utils.get_object_bounding_box(orgObjArray)
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
                                if obj.sxtools.bevelsegments > 0:
                                    newObj.sxtools.bevelsegments = obj.sxtools.bevelsegments
                                else:
                                    newObj.sxtools.bevelsegments = 0
                            elif obj.sxtools.subdivisionlevel == 0:
                                newObj.sxtools.subdivisionlevel = 0
                                newObj.sxtools.bevelsegments = 0
                                newObj.sxtools.weldthreshold = 0
                        else:
                            newObj.sxtools.subdivisionlevel = 0
                            newObj.sxtools.bevelsegments = 0
                            newObj.sxtools.weldthreshold = 0

                        newObjArray.append(newObj)

        # activeObj.select_set(True)
        bpy.context.view_layer.objects.active = activeObj

        return newObjArray


    def convert_to_linear(self, objs):
        for obj in objs:
            vertexColors = obj.data.vertex_colors
            for poly in obj.data.polygons:
                for idx in poly.loop_indices:
                    vCol = vertexColors['VertexColor0'].data[idx].color
                    vertexColors['VertexColor0'].data[idx].color = convert.srgb_to_linear(vCol)


    def remove_exports(self):
        scene = bpy.context.scene.sxtools
        if 'ExportObjects' in bpy.data.collections.keys():
            exportObjects = bpy.data.collections['ExportObjects'].objects
            for obj in exportObjects:
                bpy.data.objects.remove(obj, do_unlink=True)

        if 'SourceObjects' in bpy.data.collections.keys():
            sourceObjects = bpy.data.collections['SourceObjects'].objects
            tags = sxglobals.keywords
            for obj in sourceObjects:
                if obj.type == 'MESH':
                    name = obj.name[:]
                    dataname = obj.data.name[:]
                    for tag in tags:
                        name = name.replace(tag, '')
                        dataname = dataname.replace(tag, '')
                    obj.name = name
                    obj.data.name = dataname
                    tools.remove_modifiers([obj, ])
                    tools.add_modifiers([obj, ])
                else:
                    name = obj.name[:]
                    for tag in tags:
                        name = name.replace(tag, '')
                    obj.name = name

                obj.hide_viewport = False
                sourceObjects.unlink(obj)


    def __del__(self):
        print('SX Tools: Exiting export')


# ------------------------------------------------------------------------
#    Core Functions
# ------------------------------------------------------------------------
def update_layers(self, context):
    if not sxglobals.refreshInProgress:
        # print('Updating layers')
        # then = time.time()

        if 'SXMaterial' not in bpy.data.materials.keys():
            setup.create_sxmaterial()

        # sxmaterial = bpy.data.materials['SXMaterial'].node_tree.nodes

        shading_mode(self, context)
        objs = selection_validator(self, context)

        # now = time.time()
        # print('Selection_validator: ', now-then, ' seconds')
        # then = time.time()

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

            # now = time.time()
            # print('object attribute update: ', now-then, ' seconds')
            # then = time.time()

            # setup.setup_geometry(objs)
            if not context.scene.sxtools.gpucomposite:
                sxglobals.composite = True
                layers.composite_layers(objs)

                # now = time.time()
                # print('compositing duration: ', now-then, ' seconds')


def refresh_actives(self, context):
    if not sxglobals.refreshInProgress:
        sxglobals.refreshInProgress = True

        then0 = time.time()
        then = time.time()

        prefs = context.preferences.addons['sxtools'].preferences
        scene = context.scene.sxtools
        mode = context.scene.sxtools.shadingmode
        sxmaterial = bpy.data.materials['SXMaterial']
        objs = selection_validator(self, context)

        utils.mode_manager(objs, set_mode=True)

        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            vcols = layer.vertexColorLayer

            # update Palettes-tab color values
            if scene.toolmode == 'PAL':
                layers.color_layers_to_values(objs)
            elif (prefs.materialtype != 'SMP') and (scene.toolmode == 'MAT'):
                layers.material_layers_to_values(objs)

            now = time.time()
            print('Palettes tab update duration: ', now-then, ' seconds')
            then = time.time()

            for obj in objs:
                setattr(obj.sxtools, 'selectedlayer', idx)
                if vcols != '':
                    obj.data.vertex_colors.active = obj.data.vertex_colors[vcols]
                    if (mode != 'FULL') and (prefs.materialtype == 'SMP'):
                        sxmaterial.node_tree.nodes['Vertex Color'].layer_name = vcols
                    else:
                        sxmaterial.node_tree.nodes['Vertex Color'].layer_name = 'VertexColor0'
                alphaVal = getattr(obj.sxlayers[idx], 'alpha')
                blendVal = getattr(obj.sxlayers[idx], 'blendMode')
                visVal = getattr(obj.sxlayers[idx], 'visibility')

                setattr(obj.sxtools, 'activeLayerAlpha', alphaVal)
                setattr(obj.sxtools, 'activeLayerBlendMode', blendVal)
                setattr(obj.sxtools, 'activeLayerVisibility', visVal)

            now = time.time()
            print('Object property update duration: ', now-then, ' seconds')
            then = time.time()

            # Update VertexColor0 to reflect latest layer changes
            if not context.scene.sxtools.gpucomposite:
                if mode != 'FULL':
                    sxglobals.composite = True
                layers.composite_layers(objs)

            now = time.time()
            print('Composite duration: ', now-then, ' seconds')
            then = time.time()

            # Refresh SX Tools UI to latest selection
            layers.update_layer_panel(objs, layer)

            now = time.time()
            print('Update layer panel duration: ', now-then, ' seconds')
            then = time.time()

            # Update SX Material to latest selection
            if objs[0].sxtools.category == 'TRANSPARENT':
                if bpy.data.materials['SXMaterial'].blend_method != 'BLEND':
                    bpy.data.materials['SXMaterial'].blend_method = 'BLEND'
                    bpy.data.materials['SXMaterial'].use_backface_culling = True
            else:
                if bpy.data.materials['SXMaterial'].blend_method != 'OPAQUE':
                    bpy.data.materials['SXMaterial'].blend_method = 'OPAQUE'
                    bpy.data.materials['SXMaterial'].use_backface_culling = False

            now = time.time()
            print('Material update duration: ', now-then, ' seconds')

        # Verify selectionMonitor is running
        if not sxglobals.modalStatus:
            setup.start_modal()

        utils.mode_manager(objs, revert=True)
        sxglobals.refreshInProgress = False

        now = time.time()
        print('Refresh actives duration: ', now-then0, ' seconds')


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
            context.scene.eevee.use_ssr = False
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
                if metallic or smoothness:
                    context.scene.eevee.use_ssr = True
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
                if metallic or smoothness:
                    context.scene.eevee.use_ssr = False
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


def adjust_hue(self, context):
    if not sxglobals.hslUpdate:
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)

            tools.apply_hsl(objs, layer, 0, context.scene.sxtools.huevalue)

            sxglobals.composite = True
            refresh_actives(self, context)


def adjust_saturation(self, context):
    if not sxglobals.hslUpdate:
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)

            tools.apply_hsl(objs, layer, 1, context.scene.sxtools.saturationvalue)

            sxglobals.composite = True
            refresh_actives(self, context)


def adjust_lightness(self, context):
    if not sxglobals.hslUpdate:
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)

            tools.apply_hsl(objs, layer, 2, context.scene.sxtools.lightnessvalue)

            sxglobals.composite = True
            refresh_actives(self, context)


def update_modifier_visibility(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        vis = objs[0].sxtools.modifiervisibility
        for obj in objs:
            if obj.sxtools.modifiervisibility != vis:
                obj.sxtools.modifiervisibility = vis

        utils.mode_manager(objs, set_mode=True)
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

        utils.mode_manager(objs, revert=True)


def update_mirror_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        xmirror = objs[0].sxtools.xmirror
        ymirror = objs[0].sxtools.ymirror
        zmirror = objs[0].sxtools.zmirror
        mirrorobj = objs[0].sxtools.mirrorobject

        for obj in objs:
            if obj.sxtools.xmirror != xmirror:
                obj.sxtools.xmirror = xmirror
            if obj.sxtools.ymirror != ymirror:
                obj.sxtools.ymirror = ymirror
            if obj.sxtools.zmirror != zmirror:
                obj.sxtools.zmirror = zmirror
            if obj.sxtools.mirrorobject != mirrorobj:
                obj.sxtools.mirrorobject = mirrorobj

        utils.mode_manager(objs, set_mode=True)
        for obj in objs:
            if 'sxMirror' in obj.modifiers.keys():
                obj.modifiers['sxMirror'].use_axis[0] = xmirror
                obj.modifiers['sxMirror'].use_axis[1] = ymirror
                obj.modifiers['sxMirror'].use_axis[2] = zmirror

                if mirrorobj != '':
                    obj.modifiers['sxMirror'].mirror_object = context.view_layer.objects[mirrorobj]
                else:
                    obj.modifiers['sxMirror'].mirror_object = None

                if xmirror or ymirror or zmirror:
                    obj.modifiers['sxMirror'].show_viewport = True
                else:
                    obj.modifiers['sxMirror'].show_viewport = False

        utils.mode_manager(objs, revert=True)


def update_crease_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        hardmode = objs[0].sxtools.hardmode
        for obj in objs:
            if obj.sxtools.hardmode != hardmode:
                obj.sxtools.hardmode = hardmode

        utils.mode_manager(objs, set_mode=True)
        for obj in objs:
            if 'sxWeightedNormal' in obj.modifiers.keys():
                if hardmode == 'SMOOTH':
                    obj.modifiers['sxWeightedNormal'].keep_sharp = False
                else:
                    obj.modifiers['sxWeightedNormal'].keep_sharp = True

        utils.mode_manager(objs, revert=True)


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

        utils.mode_manager(objs, set_mode=True)
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

        utils.mode_manager(objs, revert=True)


def update_bevel_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        bevelWidth = objs[0].sxtools.bevelwidth
        bevelSegments = objs[0].sxtools.bevelsegments
        bevelType = objs[0].sxtools.beveltype
        for obj in objs:
            if obj.sxtools.bevelwidth != bevelWidth:
                obj.sxtools.bevelwidth = bevelWidth
            if obj.sxtools.bevelsegments != bevelSegments:
                obj.sxtools.bevelsegments = bevelSegments
            if obj.sxtools.beveltype != bevelType:
                obj.sxtools.beveltype = bevelType

        utils.mode_manager(objs, set_mode=True)
        for obj in objs:
            if 'sxBevel' in obj.modifiers.keys():
                if obj.sxtools.bevelsegments == 0:
                    obj.modifiers['sxBevel'].show_viewport = False
                else:
                    obj.modifiers['sxBevel'].show_viewport = obj.sxtools.modifiervisibility
                obj.modifiers['sxBevel'].width = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].width_pct = obj.sxtools.bevelwidth
                obj.modifiers['sxBevel'].segments = obj.sxtools.bevelsegments
                obj.modifiers['sxBevel'].offset_type = obj.sxtools.beveltype

        utils.mode_manager(objs, revert=True)


def update_weld_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        weldThreshold = objs[0].sxtools.weldthreshold
        for obj in objs:
            if obj.sxtools.weldthreshold != weldThreshold:
                obj.sxtools.weldthreshold = weldThreshold

        utils.mode_manager(objs, set_mode=True)
        for obj in objs:
            if 'sxWeld' in obj.modifiers.keys():
                obj.modifiers['sxWeld'].merge_threshold = weldThreshold
                if obj.sxtools.weldthreshold == 0:
                    obj.modifiers['sxWeld'].show_viewport = False
                elif (obj.sxtools.weldthreshold > 0) and obj.sxtools.modifiervisibility:
                    obj.modifiers['sxWeld'].show_viewport = True

        utils.mode_manager(objs, revert=True)


def update_decimate_modifier(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        decimation = objs[0].sxtools.decimation
        for obj in objs:
            if obj.sxtools.decimation != decimation:
                obj.sxtools.decimation = decimation

        utils.mode_manager(objs, set_mode=True)
        for obj in objs:
            if 'sxDecimate' in obj.modifiers.keys():
                obj.modifiers['sxDecimate'].angle_limit = decimation * (math.pi/180.0)
                if obj.sxtools.decimation == 0:
                    obj.modifiers['sxDecimate'].show_viewport = False
                    obj.modifiers['sxDecimate2'].show_viewport = False
                elif (obj.sxtools.decimation > 0) and obj.sxtools.modifiervisibility:
                    obj.modifiers['sxDecimate'].show_viewport = True
                    obj.modifiers['sxDecimate2'].show_viewport = True

        utils.mode_manager(objs, revert=True)


def update_custom_props(self, context):
    objs = selection_validator(self, context)
    if len(objs) > 0:
        stc = objs[0].sxtools.staticvertexcolors
        sm1 = objs[0].sxtools.smoothness1
        sm2 = objs[0].sxtools.smoothness2
        ovr = objs[0].sxtools.overlaystrength
        lod = objs[0].sxtools.lodmeshes
        piv = objs[0].sxtools.pivotmode
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
            if obj.sxtools.pivotmode != piv:
                obj.sxtools.pivotmode = piv


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
    color = (scene.newpalette0[0], scene.newpalette0[1], scene.newpalette0[2], scene.newpalette0[3])
    tools.update_palette_layer(objs, 1, color, 'PaletteColor0')
    sxglobals.composite = True
    refresh_actives(self, context)


def update_palette_layer2(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    color = (scene.newpalette1[0], scene.newpalette1[1], scene.newpalette1[2], scene.newpalette1[3])
    tools.update_palette_layer(objs, 2, color, 'PaletteColor1')
    sxglobals.composite = True
    refresh_actives(self, context)


def update_palette_layer3(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    color = (scene.newpalette2[0], scene.newpalette2[1], scene.newpalette2[2], scene.newpalette2[3])
    tools.update_palette_layer(objs, 3, color, 'PaletteColor2')
    sxglobals.composite = True
    refresh_actives(self, context)


def update_palette_layer4(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    color = (scene.newpalette3[0], scene.newpalette3[1], scene.newpalette3[2], scene.newpalette3[3])
    tools.update_palette_layer(objs, 4, color, 'PaletteColor3')
    sxglobals.composite = True
    refresh_actives(self, context)


def update_palette_layer5(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    color = (scene.newpalette4[0], scene.newpalette4[1], scene.newpalette4[2], scene.newpalette4[3])
    tools.update_palette_layer(objs, 5, color, 'PaletteColor4')
    sxglobals.composite = True
    refresh_actives(self, context)


def update_material_layer1(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 7)
    color = (scene.newmaterial0[0], scene.newmaterial0[1], scene.newmaterial0[2], scene.newmaterial0[3])
    modecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]

    if scene.enablelimit:
        hsl = convert.rgb_to_hsl(color)
        if scene.limitmode == 'MET':
            minl = float(170.0/255.0)
            if hsl[2] < minl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[1], minl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)
        else:
            minl = float(50.0/255.0)
            maxl = float(240.0/255.0)
            if hsl[2] > maxl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[1], maxl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)
            elif hsl[2] < minl:
                rgb = convert.hsl_to_rgb((hsl[0], hsl[2], minl))
                color = (rgb[0], rgb[1], rgb[2], 1.0)

    if color != modecolor:
        tools.apply_tool(objs, layer, color)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_material_layer2(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 12)
    color = (scene.newmaterial1[0], scene.newmaterial1[1], scene.newmaterial1[2], scene.newmaterial1[3])
    modecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]

    if color != modecolor:
        tools.apply_tool(objs, layer, color)
        sxglobals.composite = True
        refresh_actives(self, context)


def update_material_layer3(self, context):
    scene = context.scene.sxtools
    objs = selection_validator(self, context)
    layer = utils.find_layer_from_index(objs[0], 13)
    color = (scene.newmaterial2[0], scene.newmaterial2[1], scene.newmaterial2[2], scene.newmaterial2[3])
    modecolor = utils.find_colors_by_frequency(objs, layer, 1)[0]

    if color != modecolor:
        tools.apply_tool(objs, layer, color)
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
    sxglobals.librariesLoaded = False

    for obj in bpy.data.objects:
        if (len(obj.sxtools.keys()) > 0):
            if ('sxToolsVersion' not in obj.keys()) or (obj['sxToolsVersion'] != 'SX Tools for Blender ' + str(sys.modules['sxtools'].bl_info.get('version'))):
                bpy.ops.sxtools.resetmaterial('INVOKE_DEFAULT')
                print('SX Tools: Updated SXMaterial')
                break

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

    flipsmartx: bpy.props.BoolProperty(
        name='Flip Smart X',
        description='Reverse smart naming on X-axis',
        default=False)

    flipsmarty: bpy.props.BoolProperty(
        name='Flip Smart Y',
        description='Reverse smart naming on Y-axis',
        default=False)


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
        layout_split6.label(text='Reverse Smart Mirror Naming:')        
        layout_split7 = layout_split6.split()
        layout_split7.prop(self, 'flipsmartx', text='X-Axis')
        layout_split7.prop(self, 'flipsmarty', text='Y-Axis')
        layout_split8 = layout.split()
        layout_split8.label(text='Library Folder:')
        layout_split8.prop(self, 'libraryfolder', text='')


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

    smartseparate: bpy.props.BoolProperty(
        name='Smart Separate',
        default=False)

    mirrorobject: bpy.props.StringProperty(
        name='Mirror Object',
        default='',
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

    beveltype: bpy.props.EnumProperty(
        name='Bevel Type',
        description='Bevel offset mode',
        items=[
            ('OFFSET', 'Offset', ''),
            ('WIDTH', 'Width', ''),
            ('PERCENT', 'Percent', '')],
        default='WIDTH',
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

    pivotmode: bpy.props.EnumProperty(
        name='Pivot Mode',
        description='Auto pivot placement mode',
        items=[
            ('OFF', 'No Change', ''),
            ('MASS', 'Center of Mass', ''),
            ('BBOX', 'Bbox Center', ''),
            ('ROOT', 'Bbox Base', ''),
            ('ORG', 'Origin', '')],
        default='OFF',
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

    huevalue: bpy.props.FloatProperty(
        name='Hue',
        description='The mode hue in the selection',
        min=0.0,
        max=1.0,
        default=0.0,
        update=adjust_hue)

    saturationvalue: bpy.props.FloatProperty(
        name='Saturation',
        description='The max saturation in the selection',
        min=0.0,
        max=1.0,
        default=0.0,
        update=adjust_saturation)

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
            ('CRV', 'Curvature', ''),
            ('NSE', 'Noise', ''),
            ('OCC', 'Ambient Occlusion', ''),
            ('THK', 'Mesh Thickness', ''),
            ('DIR', 'Directional', ''),
            ('LUM', 'Luminance Remap', ''),
            ('PAL', 'Palette', ''),
            ('MAT', 'Material', '')],
        default='COL',
        update=expand_fill)

    toolopacity: bpy.props.FloatProperty(
        name='Fill Opacity',
        description='Blends fill with existing layer',
        min=0.0,
        max=1.0,
        default=1.0)

    toolblend: bpy.props.EnumProperty(
        name='Fill Blend',
        description='Fill blend mode',
        items=[
            ('ALPHA', 'Alpha', ''),
            ('ADD', 'Additive', ''),
            ('MUL', 'Multiply', ''),
            ('OVR', 'Overlay', '')],
        default='ALPHA')

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

    noiseamplitude: bpy.props.FloatProperty(
        name='Amplitude',
        description='Random per-vertex noise amplitude',
        min=0.0,
        max=1.0,
        default=0.5)

    noiseoffset: bpy.props.FloatProperty(
        name='Offset',
        description='Random per-vertex noise offset',
        min=0.0,
        max=1.0,
        default=0.5)

    noisemono: bpy.props.BoolProperty(
        name='Monochrome',
        description='Uncheck to randomize all noise channels separately',
        default=False)

    rampmode: bpy.props.EnumProperty(
        name='Ramp Mode',
        description='X/Y/Z: Axis-aligned gradient',
        items=[
            ('X', 'X-Axis', ''),
            ('Y', 'Y-Axis', ''),
            ('Z', 'Z-Axis', '')],
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

    dirCone: bpy.props.IntProperty(
        name='Spread',
        description='Softens the result with multiple samples',
        min=0,
        max=360,
        default=0)

    curvaturenormalize: bpy.props.BoolProperty(
        name='Normalize Curvature',
        description='Normalize convex and concave ranges\nfor improved artistic control',
        default=False)

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

    expandmirror: bpy.props.BoolProperty(
        name='Expand Mirror',
        default=False)

    expandbevel: bpy.props.BoolProperty(
        name='Expand Bevel',
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
        prefs = bpy.context.preferences.addons['sxtools'].preferences

        if (len(objs) > 0) and (len(objs[0].sxtools.category) > 0) and sxglobals.librariesLoaded:
            obj = objs[0]

            layout = self.layout
            mode = obj.mode
            sxtools = obj.sxtools
            scene = context.scene.sxtools
            palettes = context.scene.sxpalettes
            
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

                if prefs.materialtype != 'SMP':
                    row = layout.row(align=True)
                    row.label(text='Category:')
                    row.prop(sxtools, 'category', text='')

                row_shading = self.layout.row(align=True)
                row_shading.prop(scene, 'shadingmode', expand=True)

                # Layer Controls -----------------------------------------------
                box_layer = self.layout.box()
                row_layer = box_layer.row()
                row_layer.prop(scene, 'expandlayer',
                    icon='TRIA_DOWN' if scene.expandlayer else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_alpha = row_layer.row(align=True)
                row_alpha.prop(sxtools, 'activeLayerAlpha', slider=True, text='Layer Opacity')

                if ((layer.name == 'occlusion') or
                   (layer.name == 'smoothness') or
                   (layer.name == 'metallic') or
                   (layer.name == 'transmission') or
                   (layer.name == 'emission') or
                   (scene.shadingmode != 'FULL')):
                    row_alpha.enabled = False

                if scene.expandlayer:
                    row_vis = box_layer.row(align=True)
                    row_vis.prop(sxtools, 'activeLayerVisibility', text='Layer Visibility')
                    row_blend = box_layer.row(align=True)
                    row_blend.label(text='Layer Blend Mode:')
                    row_blend.prop(sxtools, 'activeLayerBlendMode', text='')
                    row_hue = box_layer.row(align=True)
                    if obj.mode == 'OBJECT':
                        hue_text = 'Layer Hue'
                    else:
                        hue_text = 'Selection Hue'
                    row_hue.prop(scene, 'huevalue', slider=True, text=hue_text)
                    row_sat = box_layer.row(align=True)
                    if obj.mode == 'OBJECT':
                        saturation_text = 'Layer Saturation'
                    else:
                        saturation_text = 'Selection Saturation'
                    row_sat.prop(scene, 'saturationvalue', slider=True, text=saturation_text)
                    row_lightness = box_layer.row(align=True)
                    if obj.mode == 'OBJECT':
                        lightness_text = 'Layer Lightness'
                    else:
                        lightness_text = 'Selection Lightness'
                    row_lightness.prop(scene, 'lightnessvalue', slider=True, text=lightness_text)

                    if ((layer.name == 'occlusion') or
                       (layer.name == 'smoothness') or
                       (layer.name == 'metallic') or
                       (layer.name == 'transmission') or
                       (layer.name == 'emission')):
                        row_hue.enabled = False
                        row_sat.enabled = False
                        row_vis.enabled = False
                        row_blend.enabled = False

                    if ((layer.index == 8) or
                        (layer.index == 9)):
                        row_sat.enabled = False
                        row_hue.enabled = False

                    if ((layer.name == 'occlusion') or
                       (layer.name == 'smoothness') or
                       (layer.name == 'metallic') or
                       (layer.name == 'transmission') or
                       (layer.name == 'emission') or
                       (scene.shadingmode != 'FULL')):
                        row_vis.enabled = False
                        row_blend.enabled = False

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

                # Fill Tools --------------------------------------------------------
                box_fill = layout.box()
                row_fill = box_fill.row()
                row_fill.prop(scene, 'expandfill',
                    icon='TRIA_DOWN' if scene.expandfill else 'TRIA_RIGHT',
                    icon_only=True, emboss=False)
                row_fill.prop(scene, 'toolmode', text='')
                if scene.toolmode != 'PAL' and scene.toolmode != 'MAT':
                    row_fill.operator('sxtools.applytool', text='Apply')

                # Color Tool --------------------------------------------------------
                if scene.toolmode == 'COL':
                    split1_fill = box_fill.split(factor=0.33)
                    split1_fill.label(text='Fill Color')
                    split1_fill.prop(scene, 'fillcolor', text='')

                    if scene.expandfill:
                        row_fpalette = box_fill.row(align=True)
                        for i in range(8):
                            row_fpalette.prop(scene, 'fillpalette' + str(i+1), text='')
                        col_fill = box_fill.column(align=True)
                        col_fill.separator()
                        row3_fill = box_fill.row()
                        row3_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Occlusion Tool ---------------------------------------------------
                elif scene.toolmode == 'OCC' or scene.toolmode == 'THK':
                    if scene.expandfill:
                        col_fill = box_fill.column(align=True)
                        if scene.toolmode == 'OCC' or scene.toolmode == 'THK':
                            col_fill.prop(scene, 'occlusionrays', slider=True, text='Ray Count')
                            col_fill.prop(scene, 'occlusionbias', slider=True, text='Bias')
                        if scene.toolmode == 'OCC':
                            col_fill.prop(scene, 'occlusionblend', slider=True, text='Local/Global Mix')
                            col_fill.prop(scene, 'occlusiondistance', slider=True, text='Ray Distance')
                            col_fill.prop(scene, 'occlusiongroundplane', text='Ground Plane')

                        col_fill.separator()
                        row3_fill = box_fill.row()
                        row3_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Directional Tool ---------------------------------------------------
                elif scene.toolmode == 'DIR':
                    if scene.expandfill:
                        col_fill = box_fill.column(align=True)
                        col_fill.prop(scene, 'dirInclination', slider=True, text='Inclination')
                        col_fill.prop(scene, 'dirAngle', slider=True, text='Angle')
                        col_fill.prop(scene, 'dirCone', slider=True, text='Spread')

                        col_fill.separator()
                        row3_fill = box_fill.row()
                        row3_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Curvature Tool ---------------------------------------------------
                elif scene.toolmode == 'CRV':
                    if scene.expandfill:
                        col_fill = box_fill.column(align=True)
                        col_fill.prop(scene, 'curvaturenormalize', text='Normalize')

                        col_fill.separator()
                        row3_fill = box_fill.row()
                        row3_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Noise Tool -------------------------------------------------------
                elif scene.toolmode == 'NSE':
                    if scene.expandfill:
                        col_nse = box_fill.column(align=True)
                        col_nse.prop(scene, 'noiseamplitude', slider=True)
                        col_nse.prop(scene, 'noiseoffset', slider=True)
                        col_nse.prop(scene, 'noisemono', text='Monochromatic')

                        col_fill = box_fill.column(align=True)
                        col_fill.separator()
                        row3_fill = box_fill.row()
                        row3_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Gradient Tool ---------------------------------------------------
                elif scene.toolmode == 'GRD':
                    split1_fill = box_fill.split(factor=0.33)
                    split1_fill.label(text='Fill Mode')
                    split1_fill.prop(scene, 'rampmode', text='')

                    if scene.expandfill:
                        row3_fill = box_fill.row(align=True)
                        row3_fill.prop(scene, 'ramplist', text='')
                        row3_fill.operator('sxtools.addramp', text='', icon='ADD')
                        row3_fill.operator('sxtools.delramp', text='', icon='REMOVE')
                        box_fill.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], 'color_ramp', expand=True)
                        if mode == 'OBJECT':
                            box_fill.prop(scene, 'rampbbox', text='Use Combined Bounding Box')

                        col_fill = box_fill.column(align=True)
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

                        col_fill.separator()
                        row4_fill = box_fill.row()
                        row4_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

                # Luminance Remap Tool -----------------------------------------------
                elif scene.toolmode == 'LUM':
                    if scene.expandfill:
                        row3_fill = box_fill.row(align=True)
                        row3_fill.prop(scene, 'ramplist', text='')
                        row3_fill.operator('sxtools.addramp', text='', icon='ADD')
                        row3_fill.operator('sxtools.delramp', text='', icon='REMOVE')
                        box_fill.template_color_ramp(bpy.data.materials['SXMaterial'].node_tree.nodes['ColorRamp'], 'color_ramp', expand=True)

                        col_fill = box_fill.column(align=True)
                        col_fill.separator()
                        row4_fill = box_fill.row()
                        row4_fill.prop(scene, 'toolopacity', slider=True)
                        split3_fill = box_fill.split()
                        if mode == 'OBJECT':
                            split3_fill.prop(scene, 'fillalpha', text='Overwrite')
                        else:
                            split3_fill.label(text='')
                        split3_fill.prop(scene, 'toolblend', text='')

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
                    if prefs.materialtype == 'SMP':
                        if scene.expandfill:
                            box_fill.label(text='Disabled in Simple mode')
                    else:
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

                # Crease and Bevel Sets, Modifier Settings --------------------------------
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
                        row_mod1 = box_crease.row()
                        row_mod1.prop(scene, 'expandmirror',
                            icon='TRIA_DOWN' if scene.expandmirror else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_mod1.label(text='Mirror Modifier Settings')
                        if scene.expandmirror:
                            row_mirror = box_crease.row()
                            row_mirror.prop(sxtools, 'xmirror')
                            row_mirror.prop(sxtools, 'ymirror')
                            row_mirror.prop(sxtools, 'zmirror')
                            row_mirrorobj = box_crease.row()
                            row_mirrorobj.prop_search(sxtools, 'mirrorobject', context.scene, 'objects')

                        row_mod2 = box_crease.row()
                        row_mod2.prop(scene, 'expandbevel',
                            icon='TRIA_DOWN' if scene.expandbevel else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_mod2.label(text='Bevel Modifier Settings')
                        if scene.expandbevel:
                            col2_sds = box_crease.column(align=True)
                            col2_sds.prop(scene, 'autocrease', text='Auto Hard-Crease Bevels')
                            split_sds = col2_sds.split()
                            split_sds.label(text='Max Crease Mode:')
                            split_sds.prop(sxtools, 'hardmode', text='')
                            split2_sds = col2_sds.split()
                            split2_sds.label(text='Bevel Type:')
                            split2_sds.prop(sxtools, 'beveltype', text='')
                            col2_sds.prop(sxtools, 'bevelsegments', text='Bevel Segments')
                            col2_sds.prop(sxtools, 'bevelwidth', text='Bevel Width')

                        col3_sds = box_crease.column(align=True)
                        col3_sds.prop(sxtools, 'subdivisionlevel', text='Subdivision Level')
                        col3_sds.prop(sxtools, 'smoothangle', text='Normal Smoothing Angle')
                        col3_sds.prop(sxtools, 'weldthreshold', text='Weld Threshold')
                        if obj.sxtools.subdivisionlevel > 0:
                            col3_sds.prop(sxtools, 'decimation', text='Decimation Limit Angle')
                            col3_sds.label(text='Selection Tri Count: '+utils.calculate_triangles(objs))
                        # col3_sds.separator()
                        col4_sds = box_crease.column(align=True)
                        modifiers = '\t'.join(obj.modifiers.keys())
                        if 'sx' in modifiers:
                            if scene.shift:
                                col4_sds.operator('sxtools.removemodifiers', text='Remove Modifiers')
                            else:
                                if obj.sxtools.modifiervisibility:
                                    hide_text = 'Hide Modifiers'
                                else:
                                    hide_text = 'Show Modifiers'
                                col4_sds.operator('sxtools.hidemodifiers', text=hide_text)
                        else:
                            if scene.expandmirror:
                                row_mirror.enabled = False
                            if scene.expandbevel:
                                col2_sds.enabled = False
                                split_sds.enabled = False
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
                        col_export.separator()
                        split_export = col_export.split()
                        split_export.label(text='Auto-pivot:')
                        split_export.prop(sxtools, 'pivotmode', text='')
                        col_export.prop(sxtools, 'lodmeshes', text='Generate LOD Meshes')
                        col_export.label(text='Note: Check Subdivision and Bevel settings')
                        # col_export.separator()
                        if prefs.materialtype != 'SMP':
                            row2_export = box_export.row(align=True)
                            row2_export.prop(sxtools, 'staticvertexcolors', text='')
                            row2_export.prop(scene, 'exportquality', text='')
                        col2_export = box_export.column(align=True)
                        col2_export.operator('sxtools.macro', text='Magic Button')
                        if ('ExportObjects' in bpy.data.collections.keys()) and (len(bpy.data.collections['ExportObjects'].objects) > 0):
                            col2_export.operator('sxtools.removeexports', text='Remove LODs and Parts')

                elif scene.exportmode == 'UTILS':
                    if scene.expandexport:
                        col_utils = box_export.column(align=False)
                        col_utils.operator('sxtools.revertobjects', text='Revert to Control Cages')
                        if scene.shift:
                            pivot_text = 'Set Pivots to Bbox Center'
                        elif scene.ctrl:
                            pivot_text = 'Set Pivots to Bbox Base'
                        elif scene.alt:
                            pivot_text = 'Set Pivots to Origin'
                        else:
                            pivot_text = 'Set Pivots to Center of Mass'
                        col_utils.operator('sxtools.setpivots', text=pivot_text)
                        col_utils.operator('sxtools.groupobjects', text='Group Selected Objects')
                        col_utils.operator('sxtools.zeroverts', text='Zero Vertices to Mirror Axis')
                        row_debug = box_export.row()
                        row_debug.prop(scene, 'expanddebug',
                            icon='TRIA_DOWN' if scene.expanddebug else 'TRIA_RIGHT',
                            icon_only=True, emboss=False)
                        row_debug.label(text='Debug Tools')
                        if scene.expanddebug:
                            col_debug = box_export.column(align=True)
                            col_debug.prop(scene, 'gpucomposite', text='GPU Compositing')
                            col_debug.operator('sxtools.smart_separate', text='Debug: Smart Separate sxMirror')
                            col_debug.operator('sxtools.create_sxcollection', text='Debug: Update SXCollection')
                            col_debug.operator('sxtools.enableall', text='Debug: Enable All Layers')
                            col_debug.operator('sxtools.applymodifiers', text='Debug: Apply Modifiers')
                            col_debug.operator('sxtools.generatemasks', text='Debug: Generate Masks')
                            col_debug.operator('sxtools.createuv0', text='Debug: Create UVSet0')
                            col_debug.operator('sxtools.generatelods', text='Debug: Create LOD Meshes')
                            col_debug.operator('sxtools.resetoverlay', text='Debug: Reset Default Layer Values')
                            col_debug.operator('sxtools.resetmaterial', text='Debug: Reset SXMaterial')
                            col_debug.operator('sxtools.resetscene', text='Debug: Reset scene (warning!)')

                elif scene.exportmode == 'EXPORT':
                    if scene.expandexport:
                        col2_export = box_export.column(align=True)
                        if obj.sxtools.xmirror or obj.sxtools.ymirror or obj.sxtools.zmirror:
                            col2_export.prop(sxtools, 'smartseparate', text='Smart Separate')
                        col2_export.label(text='Export Folder:')
                        col2_export.prop(scene, 'exportfolder', text='')
                        split_export = box_export.split(factor=0.1)
                        split_export.operator('sxtools.checklist', text='', icon='INFO')

                        if not scene.shift:
                            exp_text = 'Export Selected'
                        else:
                            exp_text = 'Export All'
                        exp_button = split_export.operator('sxtools.exportfiles', text=exp_text)

                        if (mode == 'EDIT') or (len(scene.exportfolder) == 0):
                            split_export.enabled = False

        else:
            layout = self.layout
            col = self.layout.column()
            if sxglobals.librariesLoaded:
                col.label(text='Select a mesh to continue')
            else:
                col.label(text='Libraries not loaded')
                col.label(text='Check Add-on Preferences')
                if len(prefs.libraryfolder) > 0:
                    col.operator('sxtools.loadlibraries', text='Reload Libraries')


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

            # grd_col = pie.column()
            # grd_col.prop(scene, 'rampmode', text='')
            # grd_col.operator('sxtools.applyramp', text='Apply Gradient')

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


class SXTOOLS_OT_applytool(bpy.types.Operator):
    bl_idname = 'sxtools.applytool'
    bl_label = 'Apply Tool'
    bl_description = 'Applies the selected mode fill\nto the selected components or objects'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            idx = objs[0].sxtools.selectedlayer
            layer = utils.find_layer_from_index(objs[0], idx)
            color = context.scene.sxtools.fillcolor # convert.srgb_to_linear(context.scene.sxtools.fillcolor)

            if objs[0].mode == 'EDIT':
                context.scene.sxtools.rampalpha = True

            tools.apply_tool(objs, layer)
            if context.scene.sxtools.toolmode == 'COL':
                tools.update_recent_colors(color)

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
            utils.mode_manager(objs, set_mode=True)

            if event.shift:
                layer = None
            else:
                idx = objs[0].sxtools.selectedlayer
                layer = utils.find_layer_from_index(objs[0], idx)

            layers.clear_layers(objs, layer)

            sxglobals.composite = True
            refresh_actives(self, context)
            utils.mode_manager(objs, revert=True)
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
            tools.select_mask(objs, layer, inverse)
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

            tools.apply_material(objs, layer, material)

            sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_zeroverts(bpy.types.Operator):
    bl_idname = 'sxtools.zeroverts'
    bl_label = 'Set Vertices to Zero'
    bl_description = 'Sets the mirror axis position of\nselected vertices to zero'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.zero_verts(objs)
        return {'FINISHED'}


class SXTOOLS_OT_hidemodifiers(bpy.types.Operator):
    bl_idname = 'sxtools.hidemodifiers'
    bl_label = 'Hide Modifiers'
    bl_description = 'Hide and show modifiers on selected objects\nShift-click to remove modifiers'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        scene = context.scene.sxtools

        if objs[0].sxtools.modifiervisibility is True:
            objs[0].sxtools.modifiervisibility = False
        else:
            objs[0].sxtools.modifiervisibility = True

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
        viewlayer = context.view_layer
        selected = None

        if event.shift:
            setup.create_sxcollection()
            selected = bpy.data.collections['SXObjects'].all_objects
            if context.scene.sxtools.exportquality == 'LO':
                export.smart_separate(selected)
                setup.create_sxcollection()
                selected = bpy.data.collections['SXObjects'].all_objects
        else:
            selected = context.view_layer.objects.selected
            if context.scene.sxtools.exportquality=='LO':
                newObjs = export.smart_separate(selected)
                for obj in newObjs:
                    obj.select_set(True)
                selected = viewlayer.objects.selected

        # Make sure objects are in groups
        for obj in selected:
            if obj.parent is None:
                obj.hide_viewport = False
                # viewlayer.objects.active = obj
                if obj.type == 'MESH':
                    tools.group_objects([obj, ])

        groups = utils.find_groups(selected)
        files.export_files(groups)

        if prefs.removelods:
            export.remove_exports()
        # sxglobals.composite = True
        # refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_removeexports(bpy.types.Operator):
    bl_idname = 'sxtools.removeexports'
    bl_label = 'Remove LODs and Separated Parts'
    bl_description = 'Deletes generated LOD meshes\nand smart separations'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        scene = bpy.context.scene.sxtools
        export.remove_exports()
        scene.shadingmode = 'FULL'
        return {'FINISHED'}


class SXTOOLS_OT_setpivots(bpy.types.Operator):
    bl_idname = 'sxtools.setpivots'
    bl_label = 'Set Pivots'
    bl_description = 'Set pivot to center of mass on selected objects\nShift-click to set pivot to center of bounding box\nCtrl-click to set pivot to base of bounding box\nAlt-click to set pivot to origin'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        if event.shift:
            pivotmode = 2
        elif event.ctrl:
            pivotmode = 3
        elif event.alt:
            pivotmode = 4
        else:
            pivotmode = 1

        objs = selection_validator(self, context)
        if len(objs) > 0:
            tools.set_pivots(objs, pivotmode, force=True)

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
    bl_label = 'Reset Default Values'
    bl_description = 'Resets layer default colors'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        for obj in objs:
            obj.sxlayers['occlusion'].defaultColor = [1.0, 1.0, 1.0, 1.0]
            obj.sxlayers['overlay'].defaultColor = [0.5, 0.5, 0.5, 1.0]

        layers.clear_layers(objs, objs[0].sxlayers['overlay'])
        layers.clear_layers(objs, objs[0].sxlayers['occlusion'])
        # bpy.context.view_layer.update()
        sxglobals.composite = True
        refresh_actives(self, context)

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
        mode = context.scene.sxtools.shadingmode
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

            objs[0].sxtools.selectedlayer = targetLayer.index

            if mode != 'FULL':
                sxglobals.composite = True
            refresh_actives(self, context)
        return {'FINISHED'}


class SXTOOLS_OT_selectdown(bpy.types.Operator):
    bl_idname = 'sxtools.selectdown'
    bl_label = 'Select Layer Down'
    bl_description = 'Selects the layer below'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        mode = context.scene.sxtools.shadingmode
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

            objs[0].sxtools.selectedlayer = targetLayer.index

            if mode != 'FULL':
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


class SXTOOLS_OT_smart_separate(bpy.types.Operator):
    bl_idname = 'sxtools.smart_separate'
    bl_label = 'Smart Separate'
    bl_description = 'Separates and logically renames mirrored mesh parts'
    bl_options = {'UNDO'}


    def invoke(self, context, event):
        objs = selection_validator(self, context)
        export.smart_separate(objs)

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
                magic.process_objects(objs)

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
generate = SXTOOLS_generate()
layers = SXTOOLS_layers()
setup = SXTOOLS_setup()
tools = SXTOOLS_tools()
validate = SXTOOLS_validate()
magic = SXTOOLS_magic()
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
    SXTOOLS_OT_applytool,
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
    SXTOOLS_OT_hidemodifiers,
    SXTOOLS_OT_copylayer,
    SXTOOLS_OT_selmask,
    SXTOOLS_OT_clearlayers,
    SXTOOLS_OT_mergeup,
    SXTOOLS_OT_mergedown,
    SXTOOLS_OT_pastelayer,
    SXTOOLS_OT_zeroverts,
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
    SXTOOLS_OT_smart_separate,
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
# - UI refresh delayed by one click in some situations
# - Palette swatches not auto-updated on component selection HSL slider tweak
# - Blend modes behave slightly strangely on gradient1 and gradient2
# - Metallic broken in buildings category
# - EDIT mode HSL sliders broken
# - HSL H and S broken?
# - Re-categorize filler tools
# - magic process fails (not updated to apply_tool yet)
# - select_up and down are triggering refresh per object?
# - Limit UV4 clear workload (currently 4 passes)
# - Gradient color to update from changes in layer4 and 5 colors?
# - Investigate breaking refresh
# - "Selected layer. Double click to rename" ???
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
