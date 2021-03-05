import subprocess
import multiprocessing # from multiprocessing import Process
import pathlib
from multiprocessing import Pool
import os
from os import listdir
from os.path import isfile, join

num_cores = multiprocessing.cpu_count()

blender_path = r'C:\Program Files\Blender Foundation\Blender 2.92\blender'
batch_path = r'E:\work\sxtools-blender\sx_batch.py'
export_path = r'D:\exports\\'
source_path = r'D:\cages'
source_files = [str(source_path + "\\" + f) for f in listdir(source_path) if isfile(join(source_path, f))]
# print(source_files)


def sx_process(sourcefile):
    global export_path
    # start 'yourexecutable' with some parameters
    # and throw the output away
    batch_args = [blender_path, "-b", "-d", sourcefile, "-P", batch_path, "--", "-x", export_path]
    subprocess.run(batch_args)

if __name__ == '__main__':
    # p = Process(target=sx_process, args=('bob',))
    # p.start()
    # p.join()

    with Pool(processes=num_cores) as pool:
        pool.map(sx_process, source_files)

    print("SX Batch Export Finished!")
