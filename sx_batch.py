import argparse
import bpy

def get_args():
	parser = argparse.ArgumentParser()

	# get all script args
	_, all_arguments = parser.parse_known_args()
	double_dash_index = all_arguments.index('--')
	script_args = all_arguments[double_dash_index + 1: ]

	# add parser rules
	parser.add_argument('-x', '--exportpath', help="Export Path")
	parsed_script_args, _ = parser.parse_known_args(script_args)
	return parsed_script_args

args = get_args()
export_path = str(args.exportpath)

bpy.data.scenes["Scene"].sxtools.exportfolder = export_path

bpy.ops.sxtools.loadlibraries('EXEC_DEFAULT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.sxtools.macro('EXEC_DEFAULT')

# export scene
bpy.ops.sxtools.exportfiles('EXEC_DEFAULT')

# exit
bpy.ops.wm.quit_blender('EXEC_DEFAULT')