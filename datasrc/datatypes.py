GlobalIdCounter = 0
def GetID():
	global GlobalIdCounter
	GlobalIdCounter += 1
	return GlobalIdCounter
def GetUID():
	return "x%d"%GetID()

def FixCasing(Str):
	NewStr = ""
	NextUpperCase = True
	for c in Str:
		if NextUpperCase:
			NextUpperCase = False
			NewStr += c.upper()
		else:
			if c == "_":
				NextUpperCase = True
			else:
				NewStr += c.lower()
	return NewStr

def FormatName(typ, name):
	if "*" in typ:
		return "m_p" + FixCasing(name)
	if "[]" in typ:
		return "m_a" + FixCasing(name)
	return "m_" + FixCasing(name)

class BaseType:
	def __init__(self, type_name):
		self._type_name = type_name
		self._target_name = "INVALID"
		self._id = GetID() # this is used to remember what order the members have in structures etc

	def Identifyer(self):
		return "x"+str(self._id)
	def TargetName(self):
		return self._target_name
	def TypeName(self):
		return self._type_name
	def ID(self):
		return self._id

	def EmitDeclaration(self, name):
		return ["%s %s;"%(self.TypeName(), FormatName(self.TypeName(), name))]
	def EmitPreDefinition(self, target_name):
		self._target_name = target_name
		return []
	def EmitDefinition(self, _name):
		return []

class MemberType:
	def __init__(self, name, var):
		self.name = name
		self.var = var

class Struct(BaseType):
	def __init__(self, type_name):
		BaseType.__init__(self, type_name)
	def Members(self):
		def sorter(a):
			return a.var.ID()
		m = []
		for name in self.__dict__:
			if name[0] == "_":
				continue
			m += [MemberType(name, self.__dict__[name])]
		m.sort(key = sorter)
		return m

	def EmitTypeDeclaration(self, _name):
		lines = []
		lines += ["struct " + self.TypeName()]
		lines += ["{"]
		for member in self.Members():
			lines += ["\t"+l for l in member.var.EmitDeclaration(member.name)]
		lines += ["};"]
		return lines

	def EmitPreDefinition(self, target_name):
		BaseType.EmitPreDefinition(self, target_name)
		lines = []
		for member in self.Members():
			lines += member.var.EmitPreDefinition(target_name+"."+member.name)
		return lines
	def EmitDefinition(self, _name):
		lines = ["/* %s */ {" % self.TargetName()]
		for member in self.Members():
			lines += ["\t" + " ".join(member.var.EmitDefinition("")) + ","]
		lines += ["}"]
		return lines

class Array(BaseType):
	def __init__(self, typ):
		BaseType.__init__(self, typ.TypeName())
		self.type = typ
		self.items = []
	def Add(self, instance):
		if instance.TypeName() != self.type.TypeName():
			raise "bah"
		self.items += [instance]
	def EmitDeclaration(self, name):
		return ["int m_Num%s;"%(FixCasing(name)),
			"%s *%s;"%(self.TypeName(), FormatName("[]", name))]
	def EmitPreDefinition(self, target_name):
		BaseType.EmitPreDefinition(self, target_name)

		lines = []
		i = 0
		for item in self.items:
			lines += item.EmitPreDefinition("%s[%d]"%(self.Identifyer(), i))
			i += 1

		if self.items:
			lines += ["static %s %s[] = {"%(self.TypeName(), self.Identifyer())]
			for item in self.items:
				itemlines = item.EmitDefinition("")
				lines += ["\t" + " ".join(itemlines).replace("\t", " ") + ","]
			lines += ["};"]
		else:
			lines += ["static %s *%s = 0;"%(self.TypeName(), self.Identifyer())]

		return lines
	def EmitDefinition(self, _name):
		return [str(len(self.items))+","+self.Identifyer()]

# Basic Types

class Int(BaseType):
	def __init__(self, value):
		BaseType.__init__(self, "int")
		self.value = value
	def Set(self, value):
		self.value = value
	def EmitDefinition(self, _name):
		return ["%d"%self.value]
		#return ["%d /* %s */"%(self.value, self._target_name)]

class Float(BaseType):
	def __init__(self, value):
		BaseType.__init__(self, "float")
		self.value = value
	def Set(self, value):
		self.value = value
	def EmitDefinition(self, _name):
		return ["%ff"%self.value]
		#return ["%d /* %s */"%(self.value, self._target_name)]

class String(BaseType):
	def __init__(self, value):
		BaseType.__init__(self, "const char*")
		self.value = value
	def Set(self, value):
		self.value = value
	def EmitDefinition(self, _name):
		return ['"'+self.value+'"']

class Pointer(BaseType):
	def __init__(self, typ, target):
		BaseType.__init__(self, "%s*"%typ().TypeName())
		self.target = target
	def Set(self, target):
		self.target = target
	def EmitDefinition(self, _name):
		return ["&"+self.target.TargetName()]

class TextureHandle(BaseType):
	def __init__(self):
		BaseType.__init__(self, "IGraphics::CTextureHandle")
	def EmitDefinition(self, _name):
		return ["IGraphics::CTextureHandle()"]

# helper functions

def EmitTypeDeclaration(root):
	for l in root().EmitTypeDeclaration(""):
		print(l)

def EmitDefinition(root, name):
	for l in root.EmitPreDefinition(name):
		print(l)
	print("%s %s = " % (root.TypeName(), name))
	for l in root.EmitDefinition(name):
		print(l)
	print(";")

# Network stuff after this

class Object:
	pass

class Enum:
	def __init__(self, name, values):
		self.name = name
		self.values = values

class Flags:
	def __init__(self, name, values):
		self.name = name
		self.values = values

class NetObject:
	def __init__(self, name, variables, ex=None, validate_size=True):
		l = name.split(":")
		self.name = l[0]
		self.base = ""
		if len(l) > 1:
			self.base = l[1]
		self.base_struct_name = "CNetObj_%s" % self.base
		self.struct_name = "CNetObj_%s" % self.name
		self.enum_name = "NETOBJTYPE_%s" % self.name.upper()
		self.variables = variables
		self.ex = ex
		self.validate_size = validate_size

	def emit_declaration(self):
		lines = []
		if self.base:
			lines += ["struct %s : public %s"%(self.struct_name,self.base_struct_name), "{"]
		else:
			lines += ["struct %s"%self.struct_name, "{"]
		for v in self.variables:
			lines += ["\t"+line for line in v.emit_declaration()]
		lines += ["};"]
		return lines

	def emit_uncompressed_unpack_and_validate(self, base_item):
		lines = []
		lines += ["case %s:" % self.enum_name]
		lines += ["{"]
		lines += ["\t%s *pData = (%s *)m_aUnpackedData;" % (self.struct_name, self.struct_name)]
		unpack_lines = []

		variables = []
		if base_item:
			variables += base_item.variables
		variables += self.variables
		for v in variables:
			if not self.validate_size and v.default is None:
				raise ValueError(f"{v.name} in {self.name} has no default value. Member variables that do not have a default value cannot be used in a structure whose size is not validated.")
			unpack_lines += ["\t"+line for line in v.emit_uncompressed_unpack_obj()]
		for v in variables:
			unpack_lines += ["\t"+line for line in v.emit_validate_obj()]

		if len(unpack_lines) > 0:
			lines += unpack_lines
		else:
			lines += ["\t(void)pData;"]
		lines += ["} break;"]
		return lines

class NetEvent(NetObject):
	def __init__(self, name, variables, ex=None):
		NetObject.__init__(self, name, variables, ex=ex)
		self.base_struct_name = "CNetEvent_%s" % self.base
		self.struct_name = "CNetEvent_%s" % self.name
		self.enum_name = "NETEVENTTYPE_%s" % self.name.upper()

class NetMessage(NetObject):
	def __init__(self, name, variables, ex=None, teehistorian=True):
		NetObject.__init__(self, name, variables, ex=ex)
		self.base_struct_name = "CNetMsg_%s" % self.base
		self.struct_name = "CNetMsg_%s" % self.name
		self.enum_name = "NETMSGTYPE_%s" % self.name.upper()
		self.teehistorian = teehistorian

	def emit_unpack_msg(self):
		lines = []
		lines += ["case %s:" % self.enum_name]
		lines += ["{"]
		lines += ["\t%s *pData = (%s *)m_aUnpackedData;" % (self.struct_name, self.struct_name)]

		unpack_lines = []
		for v in self.variables:
			unpack_lines += ["\t"+line for line in v.emit_unpack_msg()]
		for v in self.variables:
			unpack_lines += ["\t"+line for line in v.emit_unpack_msg_check()]

		if len(unpack_lines) > 0:
			lines += unpack_lines
		else:
			lines += ["\t(void)pData;"]
		lines += ["} break;"]
		return lines

	def emit_declaration(self):
		extra = []
		extra += ["\tint MsgID() const { return %s; }" % self.enum_name]
		extra += ["\t"]
		extra += ["\tbool Pack(CMsgPacker *pPacker)"]
		extra += ["\t{"]
		#extra += ["\t\tmsg_pack_start(%s, flags);"%self.enum_name]
		for v in self.variables:
			extra += ["\t\t"+line for line in v.emit_pack()]
		extra += ["\t\treturn pPacker->Error() != 0;"]
		extra += ["\t}"]

		lines = NetObject.emit_declaration(self)
		lines = lines[:-1] + extra + lines[-1:]
		return lines

class NetObjectEx(NetObject):
	def __init__(self, name, ex, variables, validate_size=True):
		NetObject.__init__(self, name, variables, ex=ex, validate_size=validate_size)

class NetEventEx(NetEvent):
	def __init__(self, name, ex, variables):
		NetEvent.__init__(self, name, variables, ex=ex)

class NetMessageEx(NetMessage):
	def __init__(self, name, ex, variables, teehistorian=True):
		NetMessage.__init__(self, name, variables, ex=ex)


class NetVariable:
	def __init__(self, name, default=None):
		self.name = name
		self.default = None if default is None else str(default)
	def emit_declaration(self):
		return []
	def emit_validate_obj(self):
		return []
	def emit_uncompressed_unpack_obj(self):
		return []
	def emit_pack(self):
		return []
	def emit_unpack_msg(self):
		return []
	def emit_unpack_msg_check(self):
		return []

class NetString(NetVariable):
	def emit_declaration(self):
		return ["const char *%s;"%self.name]
	def emit_uncompressed_unpack_obj(self):
		return self.emit_unpack_msg()
	def emit_unpack_msg(self):
		return ["pData->%s = pUnpacker->GetString();" % self.name]
	def emit_pack(self):
		return ["pPacker->AddString(%s, -1);" % self.name]

class NetStringHalfStrict(NetVariable):
	def emit_declaration(self):
		return ["const char *%s;"%self.name]
	def emit_uncompressed_unpack_obj(self):
		return self.emit_unpack_msg()
	def emit_unpack_msg(self):
		return ["pData->%s = pUnpacker->GetString(CUnpacker::SANITIZE_CC);" % self.name]
	def emit_pack(self):
		return ["pPacker->AddString(%s, -1);" % self.name]

class NetStringStrict(NetVariable):
	def emit_declaration(self):
		return ["const char *%s;"%self.name]
	def emit_uncompressed_unpack_obj(self):
		return self.emit_unpack_msg()
	def emit_unpack_msg(self):
		return ["pData->%s = pUnpacker->GetString(CUnpacker::SANITIZE_CC|CUnpacker::SKIP_START_WHITESPACES);" % self.name]
	def emit_pack(self):
		return ["pPacker->AddString(%s, -1);" % self.name]

class NetIntAny(NetVariable):
	def emit_declaration(self):
		return ["int %s;"%self.name]
	def emit_uncompressed_unpack_obj(self):
		if self.default is None:
			return ["pData->%s = pUnpacker->GetUncompressedInt();" % self.name]
		return ["pData->%s = pUnpacker->GetUncompressedIntOrDefault(%s);" % (self.name, self.default)]
	def emit_unpack_msg(self):
		if self.default is None:
			return ["pData->%s = pUnpacker->GetInt();" % self.name]
		return ["pData->%s = pUnpacker->GetIntOrDefault(%s);" % (self.name, self.default)]
	def emit_pack(self):
		return ["pPacker->AddInt(%s);" % self.name]

class NetIntRange(NetIntAny):
	def __init__(self, name, min_val, max_val, default=None):
		NetIntAny.__init__(self,name,default=default)
		self.min = str(min_val)
		self.max = str(max_val)
	def emit_validate_obj(self):
		return ["pData->%s = ClampInt(\"%s\", pData->%s, %s, %s);"%(self.name, self.name, self.name, self.min, self.max)]
	def emit_unpack_msg_check(self):
		return ["if(pData->%s < %s || pData->%s > %s) { m_pMsgFailedOn = \"%s\"; break; }" % (self.name, self.min, self.name, self.max, self.name)]

class NetBool(NetIntRange):
	def __init__(self, name, default=None):
		default = None if default is None else int(default)
		NetIntRange.__init__(self,name,0,1,default=default)

class NetTick(NetIntAny):
	def __init__(self, name, default=None):
		NetIntAny.__init__(self,name,default=default)

class NetArray(NetVariable):
	def __init__(self, var, size):
		NetVariable.__init__(self,var.name,var.default)
		self.base_name = var.name
		self.var = var
		self.size = size
		self.name = self.base_name + "[%d]"%self.size
	def emit_declaration(self):
		self.var.name = self.name
		return self.var.emit_declaration()
	def emit_uncompressed_unpack_obj(self):
		lines = []
		for i in range(self.size):
			self.var.name = self.base_name + "[%d]"%i
			lines += self.var.emit_uncompressed_unpack_obj()
		return lines
	def emit_validate_obj(self):
		lines = []
		for i in range(self.size):
			self.var.name = self.base_name + "[%d]"%i
			lines += self.var.emit_validate_obj()
		return lines
	def emit_unpack_msg(self):
		lines = []
		for i in range(self.size):
			self.var.name = self.base_name + "[%d]"%i
			lines += self.var.emit_unpack_msg()
		return lines
	def emit_pack(self):
		lines = []
		for i in range(self.size):
			self.var.name = self.base_name + "[%d]"%i
			lines += self.var.emit_pack()
		return lines
	def emit_unpack_msg_check(self):
		lines = []
		for i in range(self.size):
			self.var.name = self.base_name + "[%d]"%i
			lines += self.var.emit_unpack_msg_check()
		return lines
