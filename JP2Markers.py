import binascii

class JP2Markers:

	#Structural elements of JP2 File
    SIGNATURE               = binascii.unhexlify('0000000c6a5020200d0a870a')
    
    JP2HEADER 		    = binascii.unhexlify('6a703268')
    CONTIGUOUSCODESTREAM    = binascii.unhexlify('6a703263')
    XMLBOX                  = binascii.unhexlify('786d6c20')

	#JP2 Header components...
	
    IMAGEHEADER 	    = binascii.unhexlify('69686472')
    #BITSPERCOMPONENT 	    = binascii.unhexlify('62706363')
    COLORSPECIFICATION	    = binascii.unhexlify('636f6c72')
    #PALETTE 		    = binascii.unhexlify('70636c72')
    #COMPONENTMAPPING 	    = binascii.unhexlify('636d6170')
    #CHANNELDEFIMITION	    = binascii.unhexlify('63646566')
    #RESOLUTION		    = binascii.unhexlify('72657320')

    #	Marker segments found once we get into the contiguous codestream
    SOC = binascii.unhexlify('ff4f')					#	start of codestream
    SIZ = binascii.unhexlify('ff51')					#	Image and tile size
    COD = binascii.unhexlify('ff52')					#	Coding style default
    SOT = binascii.unhexlify('ff90')					#	Start of tile-part
    EOC = binascii.unhexlify('ffd9')					#	End of codestream

    #	Box length values
    LEN_COLOR_SPACE_BOX = 7		# 3 bytes method, precedence, approx, 4 enum_cs

    OPEN_CHEVRON = binascii.unhexlify('3c')
    NUL = binascii.unhexlify('00')
        
    #PROGRESSIONS = { 0 : 'LRCP', 1 : 'RLCP', 2 : 'RPCL', 3 : 'PCRL', 4 : 'CPRL' }
    PROGRESSIONS = {
        binascii.unhexlify('00') : 'LRCP',
        binascii.unhexlify('01') : 'RLCP',
        binascii.unhexlify('02') : 'RPCL',
        binascii.unhexlify('03') : 'PCRL',
        binascii.unhexlify('04') : 'CPRL'
    }
    
    TRANSFORMATIONS = {
        binascii.unhexlify('00') : '9-7',   #	Transformation: Lossy, 9-7 irreversible filter
        binascii.unhexlify('01') : '5-3'    #	Transformation: Lossless, 5-3 reversible filter
    }
    
    METHOD1     = binascii.unhexlify('01')
    METHOD2     = binascii.unhexlify('02')
    
    COLOURSPACE = {
        binascii.unhexlify('00000010') : 'sRGB',
        binascii.unhexlify('00000011') : 'greyscale',
        binascii.unhexlify('00000012') : 'sYCC'
    }
    
