# recusive directory scanning module
import os
import glob

def recurse_directories(path, fp_file_handler):
	
	for infile in glob.glob( os.path.join(path, '*') ):
		if os.path.isdir(infile):
			# if dir, step further
			recurse_directories(infile, fp_file_handler)
				
		# if file, do something with it
		# glob converts to pathname list for jpylyzer / jp2validator
		fp_file_handler(glob.glob(infile))



