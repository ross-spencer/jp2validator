#	jp2validator.py
#
#	Script to read lossless state of JPEG2000 image. 
#
#	Can *only* reliably spot whether an image consisting of a sing
#	tile is lossless.
#
#	TODO: To determine the reversibility of any image that uses tiling
#	one must find all tiles in the image and check the transform used
#	for each tile discovered. We onlh seek one tile.
#	
#	TODO: Support more than one XML box. 
#
#	Script also validates any XML contained in the JP2 file if the 
#	argument has been provided. 
#
#	Environment requirements: Python 2.7 or later, lxml: http://lxml.de/
#
#	Usage: 	--jp2 [jp2file]
#				--dir [dir to scan]
#				--pro [profile to validate against]
#				--dif [dif non-matching profiles input profile vs. image]
#
import recurse
import sys
import os
import binascii
import struct
import StringIO
from lxml import etree
from ProfileClass import Profile
from JP2Markers import JP2Markers
import sys
from cStringIO import StringIO
if sys.version_info >= (2,7):
	import argparse
else:
	import optparse
TILE_LEN_EOF_COMPARISON = -1	#	number of bytes remaining after subtracting the length
				#	of the first tile from the lenght of file remaiing from
				#	the beginning of the first tile (will equal zero if single tile)
_TILE_INDEX = None				#	global for tile index/length/singularity comparison
args = None					#	command line arguments need to be accessed globall
markers = JP2Markers()
profile = Profile()
input_profile = Profile()

def stderr(message):
	sys.stderr.write(message + " " + "File: " + profile.href + "\n")
def eofPresent(f):
	current = f.tell()	#record current position
	#read last two bytes from the file
	f.seek(-2,2)		#seek two, relative from EOF
	eof = f.read(2)	
	f.seek(current)		#reset the position
	
	return eof == markers.EOC
def handleCOD(f):
	x = f.tell()
	len = f.read(2)
	len = struct.unpack('>h', len)[0] - 2 # 2 bytes for len hex
	cod = f.read(len)

	#	COD: Coding Style Default marker structure
	scod					= cod[0]
	progression				= cod[1]
	multiple_component_transform 		= cod[4]
	cb_width 				= cod[6]
	cb_height 				= cod[7]
	cb_style 				= cod[8]
	transformation 				= cod[9]

	#	Bitmask to derive bypass from coding style
	#	xxxx xxx0: No bypass ||	xxxx xxx1: Bypass

	if (ord(cb_style) & 0x01) == 0x01:
		profile.set_profile_value('bypass', 'selective')
	else:
		profile.set_profile_value('bypass', 'non-selevtive')
		

	#	number of layers	
	layers = struct.unpack('>h', cod[2:4])[0]
	profile.set_profile_value('layers', layers)

	#	number of levels
	decomposition_levels = struct.unpack('>b', cod[5])[0]
	profile.set_profile_value('levels', decomposition_levels)

	prog_str = ''
	if progression in markers.PROGRESSIONS:
		prog_str = markers.PROGRESSIONS[progression]
	else:
		prog_str = 'reserved'
	profile.set_profile_value('progression', prog_str)
	
	trans_str = ''
	if transformation in markers.TRANSFORMATIONS:
		trans_str = markers.TRANSFORMATIONS[transformation]
	else:
		trans_str = 'reserved'
	profile.set_profile_value('transform', trans_str)


def handleSOT(f, file_len):
	lenPointer = f.tell()
	
	#	Get length of file from beginning of SOT length indicator
	global TILE_LEN_EOF_COMPARISON
	TILE_LEN_EOF_COMPARISON  = file_len - lenPointer
	
	len = struct.unpack('>h', f.read(2))[0] - 2	# 2 bytes for len hex	
	sot = f.read(len)

	tile_index = struct.unpack('>h', sot[0:2])[0]
	len_to_end_of_file = struct.unpack('>i', sot[2:6])[0]
	
	#tile_part_index 	= sot[6]
	#codestream_tile_parts 	= sot[7]


	global _TILE_INDEX
	_TILE_INDEX = tile_index

	TILE_LEN_EOF_COMPARISON  = (TILE_LEN_EOF_COMPARISON  - len_to_end_of_file)


def readXML(f):
	
	start_of_xml = -1
	end_of_xml = -1
	xml_str = StringIO()
	
	while True:
		byte = f.read(1)
		
		if start_of_xml == -1 and byte == markers.OPEN_CHEVRON:
			start_of_xml = f.tell()

		if start_of_xml > -1:
			if byte == markers.NUL:
				break;
			else:
				xml_str.write(byte)
		
		
	profile.add_xml_to_profile(xml_str.getvalue())
	xml_str.close()

def handleColorSpecificationBox(f, len):
	csbox = f.read(markers.LEN_COLOR_SPACE_BOX)
	method 		= csbox[0:1]
	precedence 	= csbox[1:2]
	approx 		= csbox[2:3]
	#	If enum_cs doesn't exist because
	#	method is set ot 0x02 this equals
	#	the length of the embedded profile (conveniently!)
	enum_cs 	= csbox[3:7]

	if method == markers.METHOD1:
		if enum_cs in markers.COLOURSPACE:
			#	Enumerated colorspace
			cs_out = markers.COLOURSPACE[enum_cs]
		elif method == markers.METHOD2:
			cs_out = 'Restricted ICC Profile'
			f.seek(f.tell()+enum)
		else:
			cs_out = 'reserved'
			stderr('WARNING: Reserved ISO enumerated cs Value ' + binascii.hexlify(enum_cs) + ' specified in header')
			
	elif method == markers.METHOD2:
		cs_out = 'Restricted ICC Profile'
	else:
		stderr('WARNING: Reserved ISO method value ' + binascii.hexlify(method) + ' specified in header')
		
	profile.set_profile_value('cspace', cs_out)



#	Handle the general header sections in the JP2 Header Box
#	report on existance of colour space, and color space used
def handleJP2HeaderBox(f, file_len):
	hdr_buf = []
	hdr_buf.append(f.read(1))
	hdr_buf.append(f.read(1))
	hdr_buf.append(f.read(1))
	hdr_buf.append(f.read(1))
	
	while f.tell() < file_len:
		hdr = b"".join(hdr_buf)
		if hdr == markers.IMAGEHEADER:				#	we don't use this value currently
			_IMAGEHEADER = True

		if hdr == markers.COLORSPECIFICATION:
			handleColorSpecificationBox(f, file_len)
			break;

		#read next byte into hdr
		hdr_buf[0] = hdr_buf[1]
		hdr_buf[1] = hdr_buf[2]
		hdr_buf[2] = hdr_buf[3]
		hdr_buf[3] = f.read(1)


#	Marker segments found in the first contiguous codestream box
def handleMarkerSegments(f, file_len):

	seg_buf = []
	seg_buf.append(f.read(1))
	seg_buf.append(f.read(1))

	while f.tell() <  file_len:
		seg = b"".join(seg_buf)
		if seg == markers.SOC:
			seg_buf[0] = f.read(1)
			seg_buf[1] = f.read(1)
			
		if seg == markers.COD:
			handleCOD(f)
			
		if seg == markers.SOT:
			handleSOT(f, file_len)
			break;
		
		#read next byte into seg
		seg_buf[0] = seg_buf[1]
		seg_buf[1] = f.read(1)

#	Calculate JPEG2000 tile singularity
def validateTileStatus():
	if _TILE_INDEX == 0 and TILE_LEN_EOF_COMPARISON == 0:
		#	Image consists of a single tile
		profile.set_profile_value('tiles', 1)
	else:
		#	We cannot calculate the number of tiles
		profile.set_profile_value('tiles', 'cannot calculate number of tiles')


def navigateJP2Structure(f):
	
	file_len = os.path.getsize(f.name)

	if not checkFileSignature(f):
		return

	found_xml = False

	marker_buf = []
	marker_buf.append(f.read(1))
	marker_buf.append(f.read(1))
	marker_buf.append(f.read(1))
	marker_buf.append(f.read(1))
	
	while f.tell() < file_len:
		marker = b"".join(marker_buf)

		if marker == markers.JP2HEADER:
			handleJP2HeaderBox(f, file_len)

		# TODO At the moment we ignore anu further XML Boxes after the first - we might want to output them all in future!
		if marker == markers.XMLBOX and not found_xml:
			readXML(f)
			found_xml = True

		if marker == markers.CONTIGUOUSCODESTREAM:
			handleMarkerSegments(f, file_len)
			break;

		
		#read next byte into marker
		marker_buf[0] = marker_buf[1]
		marker_buf[1] = marker_buf[2]
		marker_buf[2] = marker_buf[3]
		marker_buf[3] = f.read(1)

	#	Finally add tile information to profile

	validateTileStatus()
	
def checkFileSignature(f):
	signature = f.read(12)
	
	if signature != markers.SIGNATURE:
		stderr('JPEG2000 is not JP2 compliant, missing signature box.')
		return False
	
	if not eofPresent(f):
		stderr('ERROR: End of file marker not present. Check validity of file.')
		return False
	
	return True

def clearDownGlobals():
	global profile
	profile = Profile()

def handleDirscan(infile):
	#	Check file extension of given file, jp2 only
	if os.path.isfile(infile[0]) == True:
		if infile[0][-3:] == 'jp2':	
			handleJP2(infile[0])
			clearDownGlobals()


def handleJP2(infile=False):
	fname = ''
	if args and infile == False:
		fname = args.jp2
	elif infile:
		fname = infile
	else:
		sys.stderr.write("No file or directory to handle...\n")
		sys.exit(1)

	f = ''
	try:
		f = open(fname, 'rb')
	except IOError as (strerror):
		sys.stderr.write("IOError, couldn't load JP2 image: " + str(strerror) + "\n")
		return

	#	Set profile href for logging purposes
	profile.set_href("file://" + os.path.abspath(infile).replace('\\', '/'))

	navigateJP2Structure(f)		#	Execute main thread of program
	
	f.close()
	
	if args.dir and args.pro == False:
		sys.stdout.write(profile.output_xml(False, False))
	elif args.jp2 and args.pro == False:
		sys.stdout.write(profile.output_xml(True, True))		#	declaration, namespace
	elif args.dir and args.pro:
		validates = profile == input_profile
		sys.stdout.write(profile.href + " validates: " + str(validates) + "\n")
		if validates == False and args.dif:
			sys.stderr.write("\n" + profile.diff(input_profile) + "\n")
	elif args.jp2 and args.pro:
		validates = profile == input_profile
		sys.stdout.write(profile.href + " validates: " + str(validates) + "\n")
		if validates == False and args.dif:
			sys.stderr.write(profile.diff(input_profile) + "\n")


def handle_args_with_argparse():

	parser = argparse.ArgumentParser(description='Validate JPEG2000 images against an input profile document. Optionally output an images profile.')
	parser.add_argument('--jp2', help='Optional: Single JPEG2000 image to read.')
	parser.add_argument('--dir', help='Optional: Directory to recurse for JPEG2000 files. (example: dir/)')
	parser.add_argument('--pro', help='Optional: XML profile to validate against.', default=False)
	parser.add_argument('--dif', help='Optional: Generate diff in errorlog if validation fails.', default=False)

	if len(sys.argv)==1:
		parser.print_help()
		sys.exit(1)
	#	Parse arguments into namespace object to reference later in the 
	return parser.parse_args()


def handle_args_with_optparse():
	parser = optparse.OptionParser(description='Validate JPEG2000 images against an input profile document. Optionally output an images profile.');
	parser.add_option('--jp2', help='Optional: Single JPEG2000 image to read.')
	parser.add_option('--dir', help='Optional: Directory to recurse for JPEG2000 files. (example: dir/)')
	parser.add_option('--pro', help='Optional: XML profile to validate against.', default=False)
	parser.add_option('--dif', help='Optional: Generate diff in errorlog if validation fails.', default=False)

	if len(sys.argv)==1:
		parser.print_help()
		sys.exit(1)
	
	#	Parse arguments into namespace object to reference later in the 
	(options, args) = parser.parse_args()
	return options


def main():
	#	Usage: 	--jp2 [jp2file]
	#				--dir [dir to scan]
	#				--pro [profile to validate against]
	#				--dif [dif non-matching profiles input profile vs. image]
	#	Handle command line arguments for the script
	global args
	if sys.version_info >= (2,7):
		args = handle_args_with_argparse()
	else:
		args = handle_args_with_optparse()
	if args.dir and args.pro == False:
		sys.stdout.write("<?xml version='1.0' encoding='UTF-8'?>\n")
		sys.stdout.write("<profiles xmlns=" + profile.NAMESPACE.replace('{', '"').replace('}', '"') + ">\n")
		recurse.recurse_directories(args.dir, handleDirscan)
		sys.stdout.write("</profiles>")
	
	elif args.jp2 and args.pro == False:
		handleJP2(args.jp2)
	elif args.dir and args.pro:
		if input_profile.input_xml(args.pro) == False:
			sys.exit(1)
		else:
			recurse.recurse_directories(args.dir, handleDirscan)
	elif args.jp2 and args.pro:
		if input_profile.input_xml(args.pro) == False:
			sys.exit(1)
		else:
			handleJP2(args.jp2)

if __name__ == "__main__":
	main()
