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


platform = platform.system()
if platform == 'Windows':
    blender_path = r'C:\Program Files\Blender Foundation\Blender 2.92\blender'
elif platform == 'Darwin':
    blender_path = '/Applications/Blender.app/Contents/MacOS/Blender'
elif platform == 'Linux':
    blender_path = ''

# ------------------------------------------------------------------------
#    NOTE: The catalogue file should be located in the root
#          of your asset folder structure.
# ------------------------------------------------------------------------


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--open', help='Open a Catalogue file')
    parser.add_argument('-d', '--folder', help='Export all objects from folder (bypasses the Asset Library')
    parser.add_argument('-c', '--category', help='Export all objects in a category (Default, Paletted...')
    parser.add_argument('-f', '--filename', help='Export an object by filename')
    parser.add_argument('-t', '--tag', help='Export all tagged objects')
    parser.add_argument('-e', '--exportpath', help='Export path')
    parser.add_argument('-l', '--listonly', action='store_true', help='Do not export, only list objects that match the other arguments')
    all_arguments, ignored = parser.parse_known_args()
    return all_arguments


def load_asset_data():
    if len(catalogue_path) > 0:
        try:
            with open(catalogue_path, 'r') as input:
                temp_dict = {}
                temp_dict = json.load(input)
                input.close()
            print('SX Tools: Asset Registry loaded from ' + catalogue_path)
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
    args = get_args()
    script_path = str(os.path.realpath(__file__)).replace('sx_manager.py', 'sx_batch.py')
    export_path = os.path.abspath(args.exportpath)
    print('export path:', export_path)
    if export_path is None:
        batch_args = [blender_path, "-b", "-noaudio", sourcefile, "-P", script_path, "--"]
    else:
        batch_args = [blender_path, "-b", "-noaudio", sourcefile, "-P", script_path, "--", "-x", export_path]
    subprocess.run(batch_args)
    # with codecs.open(os.devnull, 'wb', encoding='utf8') as devnull:
    #     subprocess.check_call(batch_args, stdout=devnull, stderr=subprocess.STDOUT)


if __name__ == '__main__':
    args = get_args()
    catalogue_path = str(args.open)
    asset_path = os.path.split(catalogue_path)[0]
    folder = str(args.folder)
    category = str(args.category)
    filename = str(args.filename)
    tag = str(args.tag)

    asset_dict = load_asset_data()

    source_files = []
    if args.folder is not None:
        source_files = [str(folder + os.sep + f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    elif args.category is not None:
        if category in asset_dict.keys():
            for key in asset_dict[category].keys():
                source_files.append(os.path.join(asset_path, key))
    elif args.filename is not None:
        for category in asset_dict.keys():
            for key in asset_dict[category].keys():
                if filename in key:
                    source_files.append(os.path.join(asset_path, key))
    elif args.tag is not None:
        for category in asset_dict.keys():
            for key, values in asset_dict[category].items():
                for value in values:
                    if tag == value:
                        source_files.append(os.path.join(asset_path, key))
    else:
        for category in asset_dict.keys():
            for key in asset_dict[category].keys():
                source_files.append(os.path.join(asset_path, key))

    print('Source files: ')
    for file in source_files:
        print(file)

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
