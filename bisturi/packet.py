from fragments import Fragments, FragmentsOfRegexps
from pattern_matching import Any

try:
    import cPickle as pickle
except ImportError:
    import pickle

import copy, collections
import traceback, sys, re

import packet_builder

Layer = collections.namedtuple('Layer', ['pkt', 'offset'])

class PacketError(Exception):
    def __init__(self, was_error_found_in_unpacking_phase, field_name, packet_class_name, offset, original_error_message):
        Exception.__init__(self, "asasasa")
        self.original_traceback = "".join(traceback.format_exception(*sys.exc_info())[2:])

        self.was_error_found_in_unpacking_phase = was_error_found_in_unpacking_phase
        self.fields_stack = [(offset, field_name, packet_class_name)]
        self.original_error_message = original_error_message

    def add_parent_field_and_packet(self, offset, field_name, packet_class_name):
        self.fields_stack.append((offset, field_name, packet_class_name))

    def __str__(self):
        phase = "unpacking" if self.was_error_found_in_unpacking_phase else "packing"
        
        stack_details = "\n".join(["    %08x %s %16s%s" % (offset, packet_class_name, ".", field_name) 
                                    for offset, field_name, packet_class_name in reversed(self.fields_stack)])

        closer_field_offset, closer_field_name, closer_packet_class_name = self.fields_stack[0]
        msg = "Error when %s the field '%s' of packet %s at %08x: %s\nPacket stack details: \n%s\nField's exception:\n%s" % (
                                 phase, 
                                 closer_field_name, closer_packet_class_name,
                                 closer_field_offset,
                                 self.original_error_message,
                                 stack_details,
                                 self.original_traceback)

        return msg


class Packet(object):
   __metaclass__ = packet_builder.MetaPacket
   __bisturi__ = {}


   def __init__(self, bytestring=None, **defaults):
      map(lambda name_val: name_val[1].init(self, defaults), self.__class__.get_fields())
      
      if bytestring is not None:
         self.unpack(bytestring)

   @classmethod
   def build_default_instance(cls):
      return cls.__bisturi__['clone_default_instance_func']()

   def as_prototype(self):
      return Prototype(self)

   @classmethod
   def create_from(cls, raw, offset=0, silent=False):
     pkt = cls()
     try:
         pkt.unpack(raw, offset)
         return pkt
     except:
         if silent:
             return None
         else:
             raise


   def unpack(self, raw, offset=0):
      stack = []
      try:
         return self.unpack_impl(raw, offset, stack)
      except PacketError, e:
         raise e

   def unpack_impl(self, raw, offset, stack):
      stack.append(Layer(self, offset))
      try:
         for name, f, _, unpack in self.get_fields():
            offset = unpack(pkt=self, raw=raw, offset=offset, stack=stack)
      except PacketError, e:
         e.add_parent_field_and_packet(offset, name, self.__class__.__name__)
         raise
      except Exception, e:
         raise PacketError(True, name, self.__class__.__name__, offset, str(e))
      
      stack.pop()
      return offset

   def pack(self):
      fragments = Fragments()
      stack = []
      try:
         return self.pack_impl(fragments, stack)
      except PacketError, e:
         raise e
         

   def pack_impl(self, fragments, stack):
      stack.append(Layer(self, fragments.current_offset))

      try:
         for name, f, pack, _ in self.get_fields():
            pack(pkt=self, fragments=fragments, stack=stack)
      except PacketError, e:
         e.add_parent_field_and_packet(fragments.current_offset, name, self.__class__.__name__)
         raise
      except Exception, e:
         raise PacketError(False, name, self.__class__.__name__, fragments.current_offset, str(e))
      
      stack.pop()
      return fragments

   def as_regular_expression(self, debug=False):
      fragments = FragmentsOfRegexps()
      stack = []
      self.as_regular_expression_impl(fragments, stack)

      return re.compile("(?s)" + fragments.assemble_regexp(), re.DEBUG if debug else 0)


   def as_regular_expression_impl(self, fragments, stack):
       for name, f, pack, _ in self.get_fields():
           f.pack_regexp(self, fragments, stack=stack)

   def __eq__(self, other):
       if not isinstance(other, self.__class__):
           return False

       for name, f, pack, _ in self.get_fields():
           if getattr(self, name) != getattr(other, name):
               return False

       return True



   def iterative_unpack(self, raw, offset=0, stack=None):
      raise NotImplementedError()
      for name, f, _, _ in self.get_fields():
         yield offset, name
         offset = f.unpack(pkt=self, raw=raw, offset=offset, stack=stack)

      yield offset, "."

class Prototype(object):
    def __init__(self, pkt):
       try:
           self.template = pickle.dumps(pkt, -1)
           pickle.loads(self.template) # sanity check
           self.clone = self._clone_from_pickle
       except Exception as e:
           self.template = copy.deepcopy(pkt)
           self.clone = self._clone_from_live_obj

    def clone(self):
       raise Exception()

    def _clone_from_pickle(self):
       return pickle.loads(self.template)

    def _clone_from_live_obj(self):
       return copy.deepcopy(self.template)
