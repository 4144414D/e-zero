#!/usr/bin/python
"""
GitHub:https://github.com/4144414D/e-zero 
Email:adam@nucode.co.uk

Usage:
  e-zero verify <source>... [-f]
  e-zero consolidate <source>... --master=<path> [--backup=<path>] [-fc]
  e-zero list <source>... [-f]
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
VERSION="BETA 0.0.1"

from multiprocessing import Process, Lock, active_children, Queue
from docopt import docopt
import os
import fnmatch
import subprocess
import time
import sys

def print_list(name,list_data):
        print
        print name
        for item in list_data:
                print item

def print_totals(files,sorted_dest=False):
        print
        print "Total images:\t\t",
        print len(files)
        print "Total sources:\t\t",
        sorted_paths = get_roots(files)
        print len(sorted_paths)
        if sorted_dest:
                print "Total destinations:\t",
                print len(sorted_dest)
        print "Total size:\t\t",
        print bytes2human(total_file_size(files))

def check_dependency(command,name,target):
        null = open(os.devnull,'w')
        result = 0
        try:
                result = subprocess.call(command, stdout=null, stderr=null)
        except:
                result = -1
        if result != target:
                print time.strftime('%Y-%m-%d %H:%M:%S'),
                print "ERROR: " + name + "in not installed or accessible from path."
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
                files = (files + (find_files_helper(path,pattern)))
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
                exit(1)

def check_writeable_helper(path,mode='RW'):
        """This function is used to check if we can write to a single file path"""
        if mode == 'RW':
                return os.access(path, os.W_OK) and os.access(path, os.R_OK)
        elif mode == 'RO':
                if (not os.access(path, os.W_OK)) and os.access(path, os.R_OK):
                        return True
                else:
                        return False
                
def check_writeable(paths,mode='RW'):
        """This function is used to check if we can write to all paths in a list of paths"""
        result = True
        for path in paths:
                result = result and check_writeable_helper(path,mode)
        if not result:
                if mode == 'RW':
                        print "ERROR: Not all folders are writeable"
                elif mode == 'RO':
                        print "ERROR: Not all folders are read only"
                for item in paths:
                        print item,
                        if check_writeable_helper(item):
                                print '- Read/Write'
                        else:
                                print '- Read Only'
                exit(1)       
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
        if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
        files = find_files(arguments['<source>'])
        source_locks = {}
        results_queue = Queue()
        sorted_paths = get_roots(files)
        for drive in sorted_paths:
                source_locks[drive] = Lock()
        print_totals(files)
        for image in files:
                p = Process(target = verify_image, args = (source_locks, results_queue, image, ))		
                p.start()
        while len(active_children()) > 0: time.sleep(1) 
        verified = []
        failed = []
        while not results_queue.empty():
                result = results_queue.get()
                if result[1] == 0:
                        verified.append(result[2])
                else:
                        failed.append(result[2])
        if len(verified) > 0: print_list('VERIFIED Images', verified)
        if len(failed) > 0: print_list('FAILED Images', failed)

def consolidate_worker(dest_lock, source_locks, dest, image, results_queue):
        finished = False
        root = get_root(image)
        while not finished:
                if not dest_lock.acquire(False):
                        time.sleep(0.1) # unable to get lock, so I must wait
                else:
                        if not source_locks[root].acquire(False):
                                dest_lock.release() # make sure my dest lock is avaible for others so that I don't block
                                time.sleep(0.1) # unable to get lock, so I must wait
                        else:
                                try:
                                        null = open(os.devnull,'w')
                                        destination_path = dest + '\\' + os.path.basename(image)[:-4]
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
        while len(active_children()) > 0: time.sleep(1) #wait until all files have copied  
	if not copy: #verify all files
		dest_lock_dict = get_roots([dest])
		for lock in dest_lock_dict:
				dest_lock_dict[lock] = Lock()
		for image in sources:
				image_path = dest + '\\' + os.path.basename(image)[:-4] + '\\' + os.path.basename(image)
				p = Process(target = verify_image, args = (dest_lock_dict, results_queue, image_path, ))		
				p.start()
		while len(active_children()) > 0: time.sleep(1) #wait until all files are verified
		
def consolidate(arguments):
        """This is the main function to deal with the consolidate command"""
        check_paths_exist(arguments['<source>'] + [arguments['--master']] + [arguments['--backup']])
        if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
        files = find_files(arguments['<source>'])
        sorted_sources = get_roots(files)
        destinations = [arguments['--master']]
        if arguments['--backup'] != None: destinations.append(arguments['--backup'])
        check_writeable(destinations)
        sorted_dest = get_roots(destinations)
        source_locks = {}
        for drive in sorted_sources:
                source_locks[drive] = Lock()
        print_totals(files,sorted_dest)
        check_for_name_clashes(files, True)
        results_queue = Queue()
        for drive in destinations:
                p = Process(target = consolidate_drive, args = (files, drive, results_queue, source_locks, arguments['--copy']))		
                p.start()
        while len(active_children()) > 0: time.sleep(1)			
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
	if len(verified) > 0: print_list('VERIFIED Images', verified)
        if len(failed_to_copy) > 0: print_list('FAILED to copy Images', failed_to_copy)
        if len(failed_to_verify) > 0: print_list('FAILED to verify Images', failed_to_verify)

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
                        print "\nERROR: Not all image names are unique"
                else:
                        print "\nWARNING: Not all image names are unique"
                for clash in sorted_unique_names:
                        if clashes[clash] > 1:
                                print clash,
                                print "appears",
                                print clashes[clash],
                                print "times"
                if mode:
                        print "\nPlease remove or rename these images so that they are named uniquely"
                        exit(1)
                        
SYMBOLS = {
#http://goo.gl/kTQMs
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
#http://stackoverflow.com/questions/13343700/bytes-to-human-readable-and-back-without-data-loss
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
        for f in files: size = size + get_size(os.path.dirname(f))
        return size

def list_files(arguments):
        check_paths_exist(arguments['<source>'])
        if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
        files = find_files(arguments['<source>'])
        files.sort()
        for image in files: print image
        print_totals(files)
        check_for_name_clashes(files)                

if __name__ == '__main__':
        check_dependency('ftkimager.exe --list-drives','FTK Imager CLI',0)
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
        exit()
