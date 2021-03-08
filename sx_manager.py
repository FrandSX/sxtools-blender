import argparse
import subprocess
import codecs
import multiprocessing
import pathlib
import time
import json
import platform
from multiprocessing import Pool
import os
from os import listdir
from os.path import isfile, join


platform = platform.system()
if platform == 'Windows':
    blender_path = r'C:\Program Files\Blender Foundation\Blender 2.92\blender'
elif platform == 'Darwin':
    blender_path = '/Applications/Blender.app/Contents/MacOS/Blender'
elif platform == 'Linux':
    blender_path = ''

script_path = str(os.path.realpath(__file__)).replace('sx_manager.py', 'sx_batch.py')
asset_path = str(os.path.realpath(__file__)).replace('sx_manager.py', 'sx_assets.json')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--folder', help='Export all objects from folder (bypasses the Asset Library')
    parser.add_argument('-c', '--category', help='Export all objects in a category (Default, Paletted...')
    parser.add_argument('-n', '--name', help='Export an object by name')
    parser.add_argument('-f', '--filename', help='Export an object by filename')
    parser.add_argument('-t', '--tag', help='Export all tagged objects')
    parser.add_argument('-e', '--exportpath', help='Export path')
    parser.add_argument('-l', '--listonly', action='store_true', help='Do not export, only list objects that match the other arguments')
    all_arguments, ignored = parser.parse_known_args()
    return all_arguments


def update_export_path():
    export_path = r'D:\exports\\' # '/Users/frand/Desktop/exports/'

    args = get_args()
    if args.exportpath is not None:
        export_string = str(args.exportpath)
        if not export_string.endswith('/'):
            return export_string + ('/')
        else:
            return export_string
    else:
        return export_path


def load_asset_data():
    if len(asset_path) > 0:
        try:
            with open(asset_path, 'r') as input:
                temp_dict = {}
                temp_dict = json.load(input)
                input.close()
            print('SX Tools: Asset Registry loaded from ' + asset_path)
            return temp_dict
        except ValueError:
            print('SX Tools Error: Invalid Asset Registry file.')
            return False
        except IOError:
            print('SX Tools Error: Asset Registry file not found!')
            return False
    else:
        print('SX Tools: Invalid path')
        return False


def sx_process(sourcefile):
    export_path = update_export_path()
    # -d for debug
    batch_args = [blender_path, "-b", "-noaudio", sourcefile, "-P", script_path, "--", "-x", export_path]

    # subprocess.run(batch_args)
    with codecs.open(os.devnull, 'wb', encoding='utf8') as devnull:
        subprocess.check_call(batch_args, stdout=devnull, stderr=subprocess.STDOUT)


if __name__ == '__main__':
    # Step 1: Load Assets
    asset_dict = load_asset_data()

    # Step 2: Prepare source files according to args
    args = get_args()

    folder = str(args.folder)
    category = str(args.category)
    name = str(args.name)
    filename = str(args.filename)
    tag = str(args.tag)

    source_files = []
    if args.folder is not None:
        source_files = [str(folder + os.sep + f) for f in listdir(folder) if isfile(join(folder, f))]
    elif args.category is not None:
        if category in asset_dict.keys():
            for value in asset_dict[category].values():
                source_files.append(value[0])
    elif args.name is not None:
        for category in asset_dict.keys():
            if name in asset_dict[category].keys():
                source_files.append(asset_dict[category][name][0])
    elif args.filename is not None:
        for category in asset_dict.keys():
            for name, values in asset_dict[category].items():
                for value in values:
                    if filename in value:
                        source_files.append(asset_dict[category][name][0])
    elif args.tag is not None:
        for category in asset_dict.keys():
            for name, values in asset_dict[category].items():
                for value in values:
                    if tag in value:
                        source_files.append(asset_dict[category][name][0])
    else:
        for category in asset_dict.keys():
            for value in asset_dict[category].values():
                source_files.append(value[0])

    print('Source files: ')
    for file in source_files:
        print(file)

    # Step 3: Launch batch export
    if not args.listonly:
        num_cores = multiprocessing.cpu_count()

        then = time.time()
        print('SX Batch: Spawning', num_cores, 'workers')

        with Pool(processes=num_cores) as pool:
            pool.map(sx_process, source_files)

        now = time.time()
        print('SX Batch Export Finished!')
        print('Duration: ', now-then, ' seconds')
        print('Objects exported: ', len(source_files))
