import argparse
import subprocess
import codecs
import multiprocessing
import pathlib
import time
from multiprocessing import Pool
import os
from os import listdir
from os.path import isfile, join

num_cores = multiprocessing.cpu_count()

blender_path = '/Applications/Blender.app/Contents/MacOS/Blender' # r'C:\Program Files\Blender Foundation\Blender 2.92\blender'
batch_path = '/Users/frand/Documents/sxtools-blender/sx_batch.py' # r'E:\work\sxtools-blender\sx_batch.py'
export_path = '/Users/frand/Desktop/exports/' # r'D:\exports\\'
source_path = '/Users/frand/Desktop/cages' # r'D:\cages'
source_files = [str(source_path + os.sep + f) for f in listdir(source_path) if isfile(join(source_path, f))]
# print(source_files)

asset_dict = {}
# category
# - name
#   - filename
#   - tags?


def get_args():
    parser = argparse.ArgumentParser()

    # get all script args
    _, all_arguments = parser.parse_known_args()
    double_dash_index = all_arguments.index('--')
    script_args = all_arguments[double_dash_index + 1: ]

    # add parser rules
    parser.add_argument('-c', '--category', help='Asset Category')
    parser.add_argument('-n', '--name', help='Asset by Name')
    parser.add_argument('-f', '--filename', help='Asset by Filename')
    parser.add_argument('-t', '--tag', help='Asset by Tag')
    parsed_script_args, _ = parser.parse_known_args(script_args)
    return parsed_script_args


# Step 1: Load Assets
def load_asset_data(self):
    file_path = source_path + 'sx_assets.json'

    if len(source_path) > 0:
        try:
            with open(file_path, 'r') as input:
                temp_dict = {}
                temp_dict = json.load(input)
                asset_dict.clear()
                asset_dict = temp_dict

                input.close()
            print('SX Tools: Asset Registry loaded from ' + file_path)
            return True
        except ValueError:
            print('SX Tools Error: Invalid Asset Registry file.')
            return False
        except IOError:
            print('SX Tools Error: Asset Registry file not found!')
            return False
    else:
        print('SX Tools: Invalid path')
        return False


# Step 2: Prepare source files according to args
args = get_args()





# Step 3: Launch batch export
def sx_process(sourcefile):
    # -d for debug
    batch_args = [blender_path, "-b", "-noaudio", sourcefile, "-P", batch_path, "--", "-x", export_path]

    # subprocess.run(batch_args)
    with codecs.open(os.devnull, 'wb', encoding='utf8') as devnull:
        subprocess.check_call(batch_args, stdout=devnull, stderr=subprocess.STDOUT)


if __name__ == '__main__':
    then = time.time()
    print('SX Batch: Spawning', num_cores, 'workers')

    with Pool(processes=num_cores) as pool:
        pool.map(sx_process, source_files)

    now = time.time()
    print('SX Batch Export Finished!')
    print('Duration: ', now-then, ' seconds')
    print('Objects exported: ', len(source_files))
