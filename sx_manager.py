import subprocess
import multiprocessing # from multiprocessing import Process
from multiprocessing import Pool
import codecs
import os
from os import listdir
from os.path import isfile, join
from contextlib import contextmanager

@contextmanager
def terminating(thing):
    try:
        yield thing
    finally:
        thing.terminate()


num_cores = multiprocessing.cpu_count() # psutil.cpu_count(logical = False) # os.sched_getaffinity(0)
print('numcores: ', num_cores)

export_path = '/Users/frand/Desktop/vehicles/'
source_path = '/Users/frand/Desktop/cages/'
source_files = [f for f in listdir(source_path) if isfile(join(source_path, f))]
for item in source_files:
	item = source_path + item


def sx_process(sourcefile):
	global export_path
	# start 'yourexecutable' with some parameters
	# and throw the output away
	with codecs.open(os.devnull, 'wb', encoding='utf8') as devnull:
	    subprocess.check_call(["/Applications/Blender.app/Contents/MacOS/Blender",
	    					   sourcefile,
	                           "-b", "-d", "-P", "/Users/frand/Desktop/sx_batch.py -x "+export_path],
	                          stdout=devnull, stderr=subprocess.STDOUT)

if __name__ == '__main__':
    # p = Process(target=sx_process, args=('bob',))
    # p.start()
    # p.join()

	# /Applications/Blender.app/Contents/MacOS/Blender /Users/frand/Desktop/milkvan_controlcage.blend -b -d -P /Users/frand/Desktop/sx_batch.py

    with terminating(Pool(processes=num_cores)) as pool:
    	for i in range(len(source_files)):
    		print('blep', i)
        	pool.map(sx_process, source_files)

        # print same numbers in arbitrary order
        # for i in pool.imap_unordered(f, range(10)):
        #     print(i)


        print("For the moment, the pool remains available for more work")

    # exiting the 'with'-block has stopped the pool
    print("Now the pool is closed and no longer available")