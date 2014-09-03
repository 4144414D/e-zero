#!/usr/bin/python
"""
GitHub:https://github.com/4144414D/e-zero 
Email:adam@nucode.co.uk

Usage:
  e-zero verify <source>... [-f]
  e-zero consolidate <source>... --master=<path> [--backup=<path>] [-fc]
  e-zero list <source>...
  e-zero --version 
  e-zero --help

Options:
  -h --help               Show this screen.
  --version               Show the version.
  -f, --force             Do not check if paths are write protected.
  -c, --copy              Only copy the files, do not verify them.
  -m PATH, --master PATH  The master path for consolidation. 
  -b PATH, --backup PATH  The backup path for consolidation. 
"""
VERSION="""e-zero: BETA 0.0.1"""

from multiprocessing import Process, Lock, active_children, Queue
from docopt import docopt
import os
import fnmatch
import subprocess
import time
import sys

def check_ftki():
        null = open(os.devnull,'w')
        result = 0
        try:
                result = subprocess.call('ftkimager.exe --list-drives', stdout=null, stderr=null)
        except:
                result = 1
        if result != 0:
                print "ERROR: FTK Imager CLI in not installed or accessible from path."
                exit(1)

def check_robocopy():
        null = open(os.devnull,'w')
        result = 0
        try:
                result = subprocess.call('robocopy /?', stdout=null, stderr=null)
        except:
                result = 1
        if result != 0:
                print "ERROR: robocopy in not installed or accessible from path."
                exit(1)
        
def find_files_helper(path, pattern='*.e01'):
        """This function is used to find the location of all files matching with a extension recursively inside the folder listed in path"""
        matched_files = []      
        for path, dirs, files in os.walk(os.path.abspath(path)):
                for filename in fnmatch.filter(files, pattern):
                    matched_files.append(os.path.join(path, filename))
        return matched_files

def find_files(paths, pattern='*.e01'):
        files = []
        for path in paths:
                files = (files + (find_files_helper(path)))
        files = list(set(files))
        return files

def get_root(path):
        return path[0].upper()

def check_paths_exist_helper(paths):
        """This function is used to check if all folders exist for a list of paths"""
        result = True   
        for path in paths:      
                result = result and os.path.isdir(os.path.abspath(path))
        return result

def check_paths_exist(paths):
        """This function is used to check if all folders exist for a list of paths"""
        if not check_paths_exist_helper(paths):
                print "ERROR: Not all folders exist."
                for item in paths:
                        print item,
                        if check_paths_exist_helper([item]):
                                print '- OKAY'
                        else:
                                print '- BAD'
                exit()

def check_writeable_helper(path):
        """This function is used to check if we can write to a single file path"""      
        return os.access(path, os.W_OK)

def check_readonly(paths):
        """This function is used to check if we can only read from all paths in a list of paths"""
        #I should be clever and combine with check_writeable
        result = True
        for path in paths:
                #print path
                result = result and not check_writeable_helper(path)

        if not result:
                print "ERROR: Not all folders are read only"
                for item in paths:
                        print item,
                        if not check_paths_exist_helper([item]):
                                print '- Read Only'

                        else:
                                print '- Read/Write'
                print
                print "use the -f command to force e-zero to run"
                exit()
        return result


def check_writeable(paths):
        """This function is used to check if we can write to all paths in a list of paths"""
        #I should be clever and combine with check_readonly
        result = True
        for path in paths:
                #print path
                result = result and check_writeable_helper(path)

        if not result:
                print "ERROR: Not all folders are writeable"
                for item in paths:
                        print item,
                        if check_paths_exist_helper([item]):
                                print '- Read Only'

                        else:
                                print '- Read/Write'
                exit()

        
        return result

def get_roots(paths):
        roots = set()
        for image in paths:
                roots.add(get_root(image))
        roots_dict = {}
        for root in roots:
                roots_dict[root] = []
        return roots_dict

def get_size(path):
        result = 0
        base = path
        for f in os.listdir(path):
                f = path + '/' + f 
                if os.path.isfile(f):
                        result = result + os.path.getsize(f) 
        return result

######################################################################################

def verify_image(source_locks, results_queue, image):
        finished = False
        root = get_root(image)
        while not finished:
                if not source_locks[root].acquire(False):
                        time.sleep(0.1) # unable to get lock, so I must wait
                else:
                        try:
                                null = open(os.devnull,'w')
                                print time.strftime('%Y-%m-%d %H:%M:%S'),
                                print 'ftkimager.exe --verify "' + image + '"' 
                                result = subprocess.call('ftkimager.exe --verify "' + image + '"', stdout=null, stderr=null)
                                results_queue.put(['verify',result, image])
                        finally:
                                source_locks[root].release()
                                finished = True

def verify(arguments):
        """This is the main function to deal with the verify command"""
        check_paths_exist(arguments['<source>'])
        if not arguments['--force']: check_readonly(arguments['<source>'])
        files = find_files(arguments['<source>'])

        source_locks = {}
        results_queue = Queue()
        sorted_paths = get_roots(files)
        for drive in sorted_paths:
                source_locks[drive] = Lock()

        print "Total images:\t",
        print len(files)
        print "Total sources:\t",
        print len(sorted_paths)
        print "Total size:\t",
        print bytes2human(total_file_size(files))
        for image in files:
                p = Process(target = verify_image, args = (source_locks, results_queue, image, ))		
                p.start()

        waiting = True
        display = 0
        while waiting:
                if len(active_children()) == 0:
			waiting = False
		else:
                        if display > 59:
                                sys.stdout.flush()
                                print len(active_children()),
                                print "images remaining"
                                display = 0
                        else:
                                display = display + 1
                                time.sleep(1)   

        verified = []
        failed = []
        while not results_queue.empty():
                result = results_queue.get()
                if result[1] == 0:
                        verified.append(result[2])
                else:
                        failed.append(result[2])
        
        print
        print 'VERIFIED Images'
        for image in verified:
                print image
        print
        print 'FAILED Images'
        for image in failed:
                print image

######################################################################################

def consolidate_worker(dest_lock, source_locks, dest, image, results_queue):
        finished = False
        root = get_root(image)
        while not finished:
                if not dest_lock.acquire(False):
                        time.sleep(0.1) # unable to get lock, so I must wait
                else:
                        if not source_locks[root].acquire(False):
                                dest_lock.release()
                                time.sleep(0.1) # unable to get lock, so I must wait
                        else:
                                try:
                                        null = open(os.devnull,'w')
                                        destination_path = dest + '\\' + os.path.basename(image)
                                        print time.strftime('%Y-%m-%d %H:%M:%S'),
                                        print 'robocopy "' + os.path.dirname(image) + '" "' + destination_path + '" /r:2 /w:0 /z'
                                        result = subprocess.call('robocopy "' + os.path.dirname(image) + '" "' + destination_path + '" /r:2 /w:0 /z', stdout=null, stderr=null)
                                        results_queue.put(['copy',result, destination_path])
                                finally:
                                        source_locks[root].release()
                                        dest_lock.release()
                                        finished = True

def consolidate_drive(sources, dest, results_queue, source_locks, copy=False):
        #copy all files over
        dest_lock = Lock()
        for image in sources:
                p = Process(target = consolidate_worker, args = (dest_lock, source_locks, dest, image, results_queue,))		
                p.start()
        
        waiting = True
        while waiting: #wait until all files have copied
                if len(active_children()) == 0:
                        waiting = False
                else:
                        time.sleep(1)   
	if not copy:
		#verify all files
		dest_lock_dict = get_roots([dest])
		for lock in dest_lock_dict:
				dest_lock_dict[lock] = Lock()
		for image in sources:
				image_path = dest + '\\' + os.path.basename(image) + '\\' + os.path.basename(image)
				p = Process(target = verify_image, args = (dest_lock_dict, results_queue, image_path, ))		
				p.start()
		waiting = True
		while waiting:
				if len(active_children()) == 0:
						waiting = False
				else:
						time.sleep(1) 
		

							
def consolidate(arguments):
        """This is the main function to deal with the consolidate command"""
        check_paths_exist(arguments['<source>'] + [arguments['--master']] + [arguments['--backup']])
        if not arguments['--force']: check_readonly(arguments['<source>'])
        files = find_files(arguments['<source>'])
        sorted_sources = get_roots(files)

        destinations = [arguments['--master']]
        if arguments['--backup'] != None: destinations.append(arguments['--backup'])
        check_writeable(destinations)
        sorted_dest = get_roots(destinations)
        source_locks = {}
        for drive in sorted_sources:
                source_locks[drive] = Lock()
        
        print "Total images:\t\t",
        print len(files)
        print "Total sources:\t\t",
        print len(sorted_sources)
        print "Total destinations:\t",
        print len(sorted_dest)
        print "Total size:\t\t",
        print bytes2human(total_file_size(files))
        print
        check_for_name_clashes(files, True)
        results_queue = Queue()

        for drive in destinations:
                p = Process(target = consolidate_drive, args = (files, drive, results_queue, source_locks, arguments['--copy']))		
                p.start()

        waiting = True
        display = 0
        while waiting:
                if len(active_children()) == 0:
                        waiting = False
						
	verified = []
	failed_to_verify = []
	failed_to_copy = []
        while not results_queue.empty():
                result = results_queue.get()
		if (result[0] == 'copy') and (result[1] in ['0','1']):
                        failed_to_copy.append(result[2])
                elif result[0] == 'verify':
                        if result[1] == 0:
                                verified.append(result[2])
                        else:
                                failed_to_verify.append(result[2])
							
	if len(verified) > 0:
                print
                print 'VERIFIED Images'
                for image in verified:
                        print image
                        
        if len(failed_to_copy) > 0:
                print
                print 'FAILED to copy Images'
                for image in failed_to_copy:
                        print image
                
        if len(failed_to_verify) > 0: 
                print
                print 'FAILED to verify Images'
                for image in failed_to_verify:
                        print image

######################################################################################

def check_for_name_clashes(files, mode=False):
        unique_names = set()
        for f in files:
                unique_names.add(os.path.basename(f))
        clashes = {}
        sorted_unique_names = []
        for unique_name in unique_names:
                clashes[unique_name] = 0
                sorted_unique_names.append(unique_name)
        sorted_unique_names.sort()
        
        for f in files:
                basename = os.path.basename(f)
                clashes[basename] = clashes[basename] + 1


        if len(unique_names) !=  len(files):
                if mode:
                        print "ERROR - not all image names are unique"
                else:
                        print "WARNING: Not all image names are unique"
                for clash in sorted_unique_names:
                        if clashes[clash] > 1:
                                print clash,
                                print "appears",
                                print clashes[clash],
                                print "times"
                        
                if mode:
                        print "\nPlease remove or rename these images so that they are named uniquely"
                        exit(1)

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

#http://stackoverflow.com/questions/13343700/bytes-to-human-readable-and-back-without-data-loss
def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

def total_file_size(files):
        """find total file size for image files"""
        size = 0
        for f in files:              
                size = size + get_size(os.path.dirname(f))
        return size

def list_files(arguments):
        files = find_files(arguments['<source>'])
        files.sort()
        for image in files:
                print image
        print
        print "Total images:\t",
        print len(files)
        print "Total sources:\t",
        sorted_paths = get_roots(files)
        print len(sorted_paths)
        print "Total size:\t",
        print bytes2human(total_file_size(files))
        print
        check_for_name_clashes(files)                

if __name__ == '__main__':
        check_ftki()
        arguments = docopt(__doc__, version=VERSION)
        if arguments['verify']:
                verify(arguments)
        elif arguments['consolidate']:
                consolidate(arguments)
        elif arguments['list']:
                list_files(arguments)
        else:
                print 'Something went wrong, these values will help with debugging:'
                print arguments
