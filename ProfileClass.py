from xml.dom.minidom import parse
import StringIO
import lxml
import difflib
import sys
from lxml import etree
from xml.dom.minidom import parseString

class ProfileElement:

	SINGLE	=	1
	EXACT		=	2
	RANGE		= 	3
	ENUM 		= 	4

	name 		= None
	value 	= None
	type 		= None
	min 		= None
	max 		= None
	
	def __init__(self, name, value=None, type=None, min=0, max=0):
		self.name = name
		self.value = value
		self.type = type
	
	#	not strict equivalence... equivalence in relation to object semantics
	def __eq__(self, other):	
		if self.__dict__ == other.__dict__:
			return True
		elif self.name == 'layers' or self.name == 'levels':	#	extending to mean equivalence within rules
			if self.min or self.max != None:
				if other.value >= self.min and other.value <= self.min:
					return True
			if other.min or other.max != None:
				if self.value >= other.min and self.value <= self.max:
					return True
		else:
			return False
			
	def __str__(self):
		return \
		"\nname: " + str(self.name) + " " + str(type(self.name)) + \
		"\nvalue: " + str(self.value) + " " + str(type(self.value)) + \
		"\ntype: " + str(self.type) + " " + str(type(self.type)) + \
		"\nmin: " + str(self.min) + " " + str(type(self.min)) + \
		"\nmax: " + str(self.max) + " " + str(type(self.max))

class Profile:

	#	namespace
	NAMESPACE = '{http://tna.gov.uk/dp/jp2validator/profile}'
	
	#	precise values
	progression = ''
	tiles = ''
	cspace = ''
	bypass = ''
	transform = '' 
	
	#	potentially have two values
	layers = ''
	levels = ''
	
	#	xml
	xml = False
	
	#	href, object location
	href = False
	
	SCHEMA_LOCATION = 'schema/jp2validator-profile.xsd'
	
	def __init__(self):
		tmp_elem = ProfileElement	#	TODO: probably not ideal way to do this
		self.progression = ProfileElement('progression-order', 0, tmp_elem.SINGLE)
		self.tiles = ProfileElement('tiles', 0, tmp_elem.SINGLE)
		self.cspace = ProfileElement('colour-space', 0, tmp_elem.ENUM)
		self.bypass = ProfileElement('bypass', 0, tmp_elem.SINGLE)
		self.transform = ProfileElement('transform', 0, tmp_elem.SINGLE)
		self.layers = ProfileElement('layers', 0, tmp_elem.EXACT)
		self.levels = ProfileElement('levels', 0, tmp_elem.EXACT)		
		return None
	
	def input_xml(self, xml_filename, xsd_filename=SCHEMA_LOCATION):

		try:
			xml_file = open(xml_filename, 'r')
		except IOError as (strerror):
			sys.stderr.write("IOError, couldn't load XML: " + str(strerror) + "\n")

		if self.__validate_xml__(xsd_filename, xml_file):
			#	we've read and validated xml by this point
			#	we can be confident it will load into DOM successfully

			tree = etree.parse(xml_file)
			root = tree.getroot()
			xml_iter = iter(root)
			
			iterx = xml_iter.next()
			
			elements = self.__get_profile_elements__()
			
			for i in iterx:
				if len(i) == 0:
					self.__assign_values__(i, 0, elements)
				if len(i) == 1:
					self.__assign_values__(i, 1, elements)
				if len(i) == 2:
					self.__assign_values__(i, 2, elements)
			
			self_profile = self.__get_profile_elements__()
			
			#	if values haven't been modified we have a partial profile, validate against this instead
			for member in self_profile:
				if	getattr(self, member).value == 0 and getattr(self, member).min == None and getattr(self, member).max == None:
					getattr(self, member).value = 'partial'	#	KISS, only need to check .value later...
			
		else:
			sys.stderr.write("See error log: Problem with input schema, profile, or validation fails...\n")
			return False

	def output_xml(self, declaration=True, namespace=True):
		
		xmlns_str = ''
		if namespace == True:	
			xmlns_str = ' xmlns=' + self.NAMESPACE.replace('{', '"').replace('}','"')			
		
		href_str = ''
		if self.href != False:
			href_str = ' href="' + self.href + '"'
		
		xml_out = '<profile' + xmlns_str + href_str + '>'
		
		xml_out = xml_out + self.__output_rules__(self.layers)
		xml_out = xml_out + self.__output_rules__(self.levels)
		xml_out = xml_out + self.__output_rules__(self.progression)
		xml_out = xml_out + self.__output_rules__(self.tiles)
		xml_out = xml_out + self.__output_rules__(self.cspace)
		xml_out = xml_out + self.__output_rules__(self.bypass)
		xml_out = xml_out + self.__output_rules__(self.transform)
		
		if self.xml != False:
			xml_out = xml_out + '<xml-box-content>' + self.__format_xml_cdata__() + '</xml-box-content>'
		
		xml_out = xml_out + '</profile>'		
		
		parser = etree.XMLParser(strip_cdata=False)		
		return etree.tostring(etree.fromstring(xml_out, parser), xml_declaration=declaration, encoding="UTF-8", pretty_print=True)
		
	def set_profile_value(self, property, value):
		try:
			instancevar = getattr(self, property)
			if property == 'progression' or property == 'cspace' or \
				property == 'bypass' or property == 'transform':	
					instancevar.value = str(value)
			else:
				instancevar.value = str(value)
		except AttributeError as (sterror):
			sys.stderr.write("AttributeError: " + str(sterror) + "\n")

	def set_href(self, value):
		self.href = value

	def add_xml_to_profile(self, xml_string):
		if self.xml == False:
			
			#	want to use etree.parse but cannot handle UTF-8 copyright symbol
			import xml.parsers.expat	#	use minidom instead and handle errors
			
			try:
				parseString(xml_string)
			except xml.parsers.expat.ExpatError as e:
				sys.stderr.write("Embedded XML parsing error: " + str(e) + " - XML not added to output profile."  + " : " + "File: " + self.href  + "\n")
				return False
	
			self.xml = xml_string

	def diff(self, input_profile):
		diff_str = ''
		for line in difflib.context_diff(input_profile.__diff_list__(), self.__diff_list__(), fromfile='input profile', tofile='image profile'):
			diff_str = diff_str + line
		return diff_str

	def __assign_values__(self, i, len, elements):
		for element in elements:
			elem = getattr(self, element)
			if i.tag.replace(self.NAMESPACE, '') == elem.name:
				if len == 0:
					elem.value = i.text
					elem.type = elem.SINGLE
				elif len == 1:
					subelem = (list(i))[0]
					if subelem.tag.replace(self.NAMESPACE, '') == 'enumerated':
						elem.type = elem.ENUM
						elem.value = subelem.text
					elif subelem.tag.replace(self.NAMESPACE, '') == 'exactly':
						elem.type = elem.EXACT
						elem.value = subelem.text
				elif len == 2:
					elem.min = (list(i))[0].text
					elem.max = (list(i))[1].text
					elem.type = elem.RANGE

	def __format_xml_cdata__(self):
		return "<![CDATA[" + self.xml + "]]>"

	def __get_profile_elements__(self):		#	return list of ProfileElements making up Profile
		members = [attr for attr in dir(self) if not attr.startswith("__")]
		elements = []
		for member in members:
			if isinstance(getattr(self, member), ProfileElement):
				elements.append(member)
		return elements
			
	def __output_rules__(self, profile_element):
	
		out_str = '<' + profile_element.name + '>'
		 
		if profile_element.type == profile_element.RANGE:
			out_str = out_str + '<minimum>' + str(profile_element.min) + '</minimum>'
			out_str = out_str + '<maximum>' + str(profile_element.max) + '</maximum>'
		elif profile_element.type == profile_element.ENUM:
			out_str = out_str + '<enumerated>' + str(profile_element.value) + '</enumerated>'
		elif profile_element.type == profile_element.EXACT:
			out_str = out_str + '<exactly>' + str(profile_element.value) + '</exactly>'
		elif profile_element.type == profile_element.SINGLE:
			out_str = out_str + str(profile_element.value)

		out_str = out_str + '</' + profile_element.name + '>'
		return out_str
	
	def __validate_xml__(self, xsd_filename, xml_file):	#	see http://lxml.de/validation.html	
				
		try:
			xsd = open(xsd_filename, 'r')
		except IOError as (strerror):
			sys.stderr.write("IOError, couldn't load XSD: " + str(strerror) + "\n")
			return False

		tmp_xsd_string = ''
		for line in xsd:
			tmp_xsd_string = tmp_xsd_string + line
			xsd_string = StringIO.StringIO(tmp_xsd_string)
		
		try:
			xmlschema_doc = etree.parse(xsd_string)
		except lxml.etree.XMLSyntaxError as e:
			sys.stderr.write("XMLSyntaxError: " + str(e) + "\n")
			return False
		except Exception, e:
			sys.stderr.write(e + "\n")
			return False
		
		tmp_xml_string = ''
		xml_file.seek(0)
		for line in xml_file:
			tmp_xml_string = tmp_xml_string + line
			xml_string = StringIO.StringIO(tmp_xml_string)
		xml_file.seek(0)

		try:
			xml_doc = etree.parse(xml_string)
		except lxml.etree.XMLSyntaxError as e:
			sys.stderr.write("XMLSyntaxError: " + str(e) + "\n")
			return False
		
		xmlschema = etree.XMLSchema(xmlschema_doc)
		if not xmlschema.validate(xml_doc):
			return False
		else:
			return True

	def __diff_list__(self):

		layers = ''
		if self.layers.type == self.layers.RANGE:
			layers = "min: " + str(self.layers.min) + " max: " + str(self.layers.max)
		else: 
			layers = self.layers.value
		
		levels = ''
		if self.levels.type == self.levels.RANGE:
			levels = "min: " + str(self.levels.min) + " max: " + str(self.levels.max)
		else:
			levels = self.levels.value

		diff_list = \
		[ ("layers: " + str(layers) + "\n"), \
		("levels: " + str(levels) + "\n"), \
		("progression: " + str(self.progression.value) + "\n"), \
		("tiles: " + str(self.tiles.value) + "\n"), \
		("cspace: " + str(self.cspace.value) + "\n"), \
		("bypass: " + str(self.bypass.value) + "\n"), \
		("transform: " + str(self.transform.value) + "\n")]
	
		return diff_list	
		
	def __str__(self):	#	output a simple string representation of the object
		layers = ''
		if self.layers.type == self.layers.RANGE:
			layers = "min: " + str(self.layers.min) + " max: " + str(self.layers.max)
		else: 
			layers = self.layers.value
		
		levels = ''
		if self.levels.type == self.levels.RANGE:
			levels = "min: " + str(self.levels.min) + " max: " + str(self.levels.max)
		else:
			levels = self.levels.value
		
		xml_out = ''
		if self.xml != False:
			xml_out = '\n\nxml:\n\n' + self.xml

		href_out = ''
		if self.href != False:
			href_out = '\nhref: ' + self.href + '\n'

		return \
		href_out + "\nlayers: " + str(layers) + \
		"\nlevels: " + str(levels) + \
		"\nprogression: " + str(self.progression.value) + \
		"\ntiles: " + str(self.tiles.value) + \
		"\ncspace: " + str(self.cspace.value) + \
		"\nbypass: " + str(self.bypass.value) + \
		"\ntransform: " + str(self.transform.value) + xml_out

	def __eq__(self, other):	#	compare two profile objects for parity
	
		self_profile = self.__get_profile_elements__()
		other_profile = other.__get_profile_elements__()
		
		if self_profile != other_profile:
			return False

		for member in self_profile:
			smember = getattr(self, member)
			omember = getattr(other, member)
			if (smember == omember) == False:
				if	smember.value != 'partial' and omember.value != 'partial':	#	KISS, only need to check .value...
					return False
				
		return True

