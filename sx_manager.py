import argparse
import subprocess
import codecs
import multiprocessing
import pathlib
import time
import json
from multiprocessing import Pool
import os
from os import listdir
from os.path import isfile, join

num_cores = multiprocessing.cpu_count()

blender_path = '/Applications/Blender.app/Contents/MacOS/Blender' # r'C:\Program Files\Blender Foundation\Blender 2.92\blender'
batch_path = '/Users/frand/Documents/sxtools-blender/sx_batch.py' # r'E:\work\sxtools-blender\sx_batch.py'
asset_path = '/Users/frand/Documents/sxtools-blender/sx_assets.json'
export_path = '/Users/frand/Desktop/exports/' # r'D:\exports\\'
# source_path = '/Users/frand/Desktop/cages' # r'D:\cages'
# 


def get_args():
    parser = argparse.ArgumentParser()

    # get all script args
    _, all_arguments = parser.parse_known_args()
    script_args = all_arguments[ : ]

    # add parser rules
    parser.add_argument('-d', '--folder', help='Asset Folder')
    parser.add_argument('-c', '--category', help='Asset Category')
    parser.add_argument('-n', '--name', help='Asset by Name')
    parser.add_argument('-f', '--filename', help='Asset by Filename')
    parser.add_argument('-t', '--tag', help='Asset by Tag')
    parser.add_argument('-e', '--exportpath', help='Export path')
    parsed_script_args, _ = parser.parse_known_args(script_args)
    return parsed_script_args


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
    # -d for debug
    batch_args = [blender_path, "-b", "-noaudio", sourcefile, "-P", batch_path, "--", "-x", export_path]

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
    # print('args: ', args)

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
    else:
        for category in asset_dict.keys():
            for value in asset_dict[category].values():
                source_files.append(value[0])

    print('Source files: ')
    for file in source_files:
        print(file)

    # Step 3: Launch batch export
    then = time.time()
    print('SX Batch: Spawning', num_cores, 'workers')

    with Pool(processes=num_cores) as pool:
        pool.map(sx_process, source_files)

    now = time.time()
    print('SX Batch Export Finished!')
    print('Duration: ', now-then, ' seconds')
    print('Objects exported: ', len(source_files))
