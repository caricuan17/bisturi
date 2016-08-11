import blocks

class MetaPacket(type):
   def __init__(cls, name, bases, attrs):
      type.__init__(cls, name, bases, attrs)

      if name == 'Packet' and bases == (object,):
         return # Packet base class
   
      from field import Field
      fields = filter(lambda name_val: isinstance(name_val[1], Field), attrs.iteritems())
      fields.sort(key=lambda name_val: name_val[1].ctime)
      
      map(lambda position, name_val: name_val[1].compile(name_val[0], position, fields), *zip(*enumerate(fields)))

      @classmethod
      def get_fields(cls):
         return fields

      cls.get_fields = get_fields

      generate_for_pack = cls.__bisturi__.get('generate_for_pack', True)
      generate_for_unpack = cls.__bisturi__.get('generate_for_unpack', True)
      write_py_module = cls.__bisturi__.get('write_py_module', False)
      blocks.generate_code([(i, name_f[0], name_f[1]) for i, name_f in enumerate(fields)], cls, generate_for_pack, generate_for_unpack, write_py_module)



class Packet(object):
   __metaclass__ = MetaPacket
   __bisturi__ = {}

   def __init__(self, bytestring=None, **defaults):
      map(lambda name_val: name_val[1].init(self, defaults), self.get_fields())
      
      if bytestring is not None:
         self.unpack(bytestring)


   def unpack(self, raw, offset=0, stack=None):
      stack = self.push_to_the_stack(stack)
      try:
         for name, f in self.get_fields():
            offset = f.unpack(pkt=self, raw=raw, offset=offset, stack=stack)
      except Exception, e:
         import traceback
         msg = traceback.format_exc()
         raise Exception("Error when parsing field '%s' of packet %s at %08x: %s" % (
                                 name, self.__class__.__name__, offset, msg))
      
      self.pop_from_the_stack(stack)
      return offset
         
   def pack(self):
      return ''.join([f.pack(self) for name, f in self.get_fields()])

   def push_to_the_stack(self, stack):
      if stack:
         stack.append(self)
      else:
         stack = [self]

      return stack

   def pop_from_the_stack(self, stack):
      stack.pop()

   def iterative_unpack(self, raw, offset=0, stack=None):
      stack = self.push_to_the_stack(stack)
      for name, f in self.get_fields():
         yield offset, name
         offset = f.unpack(pkt=self, raw=raw, offset=offset, stack=stack)

      yield offset, "."
      
