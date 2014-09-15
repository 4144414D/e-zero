#!/sorry/I/only/run/on/windows
"""
GitHub:https://github.com/4144414D/e-zero 
Email:adam@nucode.co.uk

Usage:
  e-zero verify <source>... [-fv]
  e-zero consolidate <source>... --master=<path> [--backup=<path>] [-fcv]
  e-zero list <source>... [-fv]
  e-zero --version 
  e-zero --help

Options:
  -h --help               Show this screen.
  --version               Show the version.
  -f, --force             Do not check if paths are write protected.
  -c, --copy              Only copy the files, do not verify them.
  -m PATH, --master PATH  The master path for consolidation. 
  -b PATH, --backup PATH  The backup path for consolidation.
  -v, --verbose           Prints verbose log file for debugging. 
"""
VERSION="BETA 0.0.2"

from multiprocessing import Process, Lock, active_children, Queue
from docopt import docopt
import os
import fnmatch
import subprocess
import time
import sys
import shutil
import logging 

def print_list(name,list_data):
    logger = logging.getLogger('e-zero.print_list')
    print
    print name
    for item in list_data:
        print item

def print_totals(files,sorted_dest=False):
    logger = logging.getLogger('e-zero.print_totals')
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
    print

def check_dependency(command,name,target):
    logger = logging.getLogger('e-zero.check_dependency')
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
    logger = logging.getLogger('e-zero.find_files_helper')
    """This function is used to find the location of all files matching with a extension recursively inside the folder listed in path"""
    matched_files = []      
    for path, dirs, files in os.walk(os.path.abspath(path)):
        for filename in fnmatch.filter(files, pattern):
            matched_files.append(os.path.join(path, filename))
    return matched_files

def find_files(paths, pattern='*.e01'):
    logger = logging.getLogger('e-zero.find_files')
    files = []
    for path in paths:
        files = (files + (find_files_helper(path,pattern)))
    files = list(set(files))
    return files

def get_root(path):
    logger = logging.getLogger('e-zero.get_root')
    return path[0].upper()

def get_roots(paths):
    logger = logging.getLogger('e-zero.get_roots')
    roots = set()
    for image in paths:
        roots.add(get_root(image))
    roots_dict = {}
    for root in roots:
        roots_dict[root] = []
    return roots_dict
        
def check_paths_exist_helper(paths):
    logger = logging.getLogger('e-zero.check_paths_exist_helper')
    """This function is used to check if all folders exist for a list of paths"""
    result = True   
    for path in paths:      
        result = result and os.path.isdir(os.path.abspath(path))
    return result

def check_paths_exist(paths):
    logger = logging.getLogger('e-zero.check_paths_exist')
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
    logger = logging.getLogger('e-zero.check_writeable_helper')
    """This function is used to check if we can write to a single file path"""
    if mode == 'RW':
        return os.access(path, os.W_OK) and os.access(path, os.R_OK)
    elif mode == 'RO':
        if (not os.access(path, os.W_OK)) and os.access(path, os.R_OK):
            return True
        else:
            return False
        
def check_writeable(paths,mode='RW'):
    logger = logging.getLogger('e-zero.check_writeable')
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
        
def check_for_name_clashes(files, mode=False):
    logger = logging.getLogger('e-zero.check_for_name_clashes')
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

def get_size(path):
    logger = logging.getLogger('e-zero.get_size')
    result = 0
    base = path
    for f in os.listdir(path):
        f = path + '/' + f 
        if os.path.isfile(f):
            result = result + os.path.getsize(f) 
    return result
    
def bytes2human(n, format="%(value)i%(symbol)s"):
    symbols = ('Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

def total_file_size(files):
    logger = logging.getLogger('e-zero.total_file_size')
    """find total file size for image files"""
    size = 0
    for f in files: size = size + get_size(os.path.dirname(f))
    return size

def create_drive_locks(roots):
    logger = logging.getLogger('e-zero.create_drive_locks')
    drive_locks = {}
    for drive in roots:
        drive_locks[drive] = Lock()
    return drive_locks
        
def list_files(arguments):
    logger = logging.getLogger('e-zero.list_files')
    check_paths_exist(arguments['<source>'])
    if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
    files = find_files(arguments['<source>'])
    files.sort()
    for image in files: print image
    print_totals(files)
    check_for_name_clashes(files)  

def precondition_checks(sources=[],destinations=[],force=False):
    pass
    
def copy_worker(source_locks, dest_locks, job_source, job_dest, results_queue):
    logger = logging.getLogger('e-zero.copy_worker')
    try:
        null = open(os.devnull,'w')
        source_path = os.path.dirname(job_source)
        destination_path = os.path.dirname(job_dest)
        print time.strftime('%Y-%m-%d %H:%M:%S'),
        print 'xcopy "' + source_path + '" "' + destination_path + '" /SYIQ'
        result = subprocess.call('xcopy "%s" "%s" /SYIQ' % (source_path, destination_path), stdout=null, stderr=null)
        results_queue.put(['copy',result, job_dest])
    except:
        results_queue.put(['copy',-1, job_dest]) 
    finally:
        source_locks[get_root(job_source)].release()
        dest_locks[get_root(job_dest)].release()
    
def verify_worker(dest_locks, job_dest, results_queue):
    logger = logging.getLogger('e-zero.verify_worker')
    try:
        null = open(os.devnull,'w')
        print time.strftime('%Y-%m-%d %H:%M:%S'),
        print 'ftkimager.exe --verify "' + job_dest + '"' 
        result = subprocess.call('ftkimager.exe --verify "' + job_dest + '"', stdout=null, stderr=null)
        results_queue.put(['verify',result, job_dest])
    except:
        results_queue.put(['verify',-1, job_dest])
    finally:
        dest_locks[get_root(job_dest)].release()
    
def dispatcher(copy = False, verify = False, sources=[], destinations = []):
    logger = logging.getLogger('e-zero.dispatcher')
    source_roots = get_roots(sources)
    destination_roots = get_roots(destinations)
    source_locks = create_drive_locks(source_roots)
    dest_locks = create_drive_locks(destination_roots)
    results_queue = Queue()
    if copy: 
        copy_jobs = []
        if verify: destinations_to_verify = []
        for source in sources: #create jobs that need to run
            basename = os.path.basename(source)
            folder_name = basename[:-4]
            for destination in destinations:
                destination_filename = os.path.join(destination,folder_name,basename)
                copy_jobs.append([source,destination_filename])
                if verify: destinations_to_verify.append(destination_filename)
        while copy_jobs: #keep running until all copy jobs are completed
            for job in copy_jobs: #job details could be pre computed
                job_source = job[0]
                job_dest = job[1]
                job_source_root = get_root(job[0])
                job_dest_root = get_root(job[1])
                if source_locks[job_source_root].acquire(False):
                    if dest_locks[job_dest_root].acquire(False):
                        p = Process(target = copy_worker, args = (source_locks, dest_locks, job_source, job_dest, results_queue))                
                        p.start()
                        copy_jobs.remove(job)
                    else:
                        source_locks[job_source_root].release()
                        #if all children die for unknown reason release all locks
                        if len(active_children()) < 1: 
                            print 'WTF MATE'
                            #try to acquire each lock before releasing it.
                            for lock in source_locks: 
                                source_locks[lock].acquire(False)
                                source_locks[lock].release()
                            for lock in dest_locks:
                                dest_locks[lock].acquire(False)
                                dest_locks[lock].release()
            time.sleep(0.1)
        if verify: destinations = destinations_to_verify
    while len(active_children()) != 0: time.sleep(0.1)    
    if verify:
        verify_jobs = destinations
        while verify_jobs:
            for job in verify_jobs:
                job_dest = job
                job_dest_root = get_root(job)
                if dest_locks[job_dest_root].acquire(False):
                    p = Process(target = verify_worker, args = (dest_locks, job_dest, results_queue))                
                    p.start()
                    verify_jobs.remove(job)
                    #if all children die for unknown reason release all locks
                if len(active_children()) < 1: 
                    print 'WTF MATE'
                    for lock in dest_locks:
                        dest_locks[lock].acquire(False)
                        dest_locks[lock].release()
                time.sleep(0.1)
    while len(active_children()) != 0: time.sleep(0.1)    
    #deal with results queue
    verified = []
    failed_to_verify = []
    failed_to_copy = []
    while not results_queue.empty():
        result = results_queue.get()
        if (result[0] == 'copy') and (result[1] != 0):
            failed_to_copy.append(result[2])
        elif result[0] == 'verify':
            if result[1] == 0:
                verified.append(result[2])
            else:
                failed_to_verify.append(result[2])      
    if len(verified) > 0: print_list('VERIFIED Images', verified)
    if len(failed_to_copy) > 0: print_list('FAILED to copy Images', failed_to_copy)
    if len(failed_to_verify) > 0: print_list('FAILED to verify Images', failed_to_verify)

def verify(arguments):
    logger = logging.getLogger('e-zero.verify')
    """This is the main function to deal with the verify command. It calls dispatcher with sources as destinations."""
    check_paths_exist(arguments['<source>'])
    if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
    files = find_files(arguments['<source>'])
    sorted_paths = get_roots(files)
    print_totals(files)
    dispatcher(False,True,[],files)
        
def consolidate(arguments):
    logger = logging.getLogger('e-zero.consolidate')
    """This is the main function to deal with the consolidate command"""
    check_paths_exist(arguments['<source>'] + [arguments['--master']] + [arguments['--backup']])
    if not arguments['--force']: check_writeable(arguments['<source>'],'RO')
    source_files = find_files(arguments['<source>'])
    sorted_sources = get_roots(source_files)
    destinations = [arguments['--master']]
    if arguments['--backup'] != None: destinations.append(arguments['--backup'])
    check_writeable(destinations)
    check_for_name_clashes(source_files,True)
    print_totals(source_files,destinations)
    dispatcher(True,not arguments['--copy'],source_files,destinations)

if __name__ == '__main__':
    logger = logging.getLogger('e-zero')
    arguments = docopt(__doc__, version=VERSION)
    if arguments['--verbose']:
        print "Verbose mode is not implemented yet.... watch this space"
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('processing.log')
        fh.setLevel(logging.DEBUG)
        fh_formatter = logging.Formatter('%(asctime)-5s - %(name)-30s - %(message)s')
        fh.setFormatter(fh_formatter)
        #logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch_formatter = logging.Formatter('%(asctime)s %(message)s')
        ch.setFormatter(ch_formatter)
        #logger.addHandler(ch)
    logger.debug("Now checking that FTK Imager is installed")
    logger.debug("Users arguments are:\n" + str(arguments))
    check_dependency('ftkimager.exe --list-drives','FTK Imager CLI',0)
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