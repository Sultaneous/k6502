#!/usr/bin/python

'''
6502 Disassembler
220126 KAS

Accepts a 6502 binary file as argument, and disassembles it to 6502 asm.
For C64 files, specify the location header as an option for proper parsing.
'''
### MODULES ###
from __future__ import annotations
import json
import types
import datetime
import getopt
from gamzia.colours import Colours as C
from gamzia.timer import Timer
from gamzia.datastructures import Stack, Queue, BinaryTree, TRAVERSALS
import os
import sys


### DATA ###

argv=sys.argv
argc=len(argv)

# App Info Constants
APP_NAME    = "Kdis6502"
APP_VERSION = 1.0
APP_AUTHOR  = "Karim Sultan"
APP_DATE    = "February 2022"
APP_EMAIL   = "karimsultan@hotmail.com"
APP_BLURB   = f"{C.paper}6502 Dissambler{C.off}\nTakes an input 6502 binary and outputs an assembly listing."
APP_SYNTAX  = f"{C.clg}Syntax: {C.cdg}python {C.clc}Kdis6502 {C.clm}[options] {C.cly}<inuput> [output]{C.off}"
APP_TAG     = f"{C.clc}{APP_NAME}{C.off} v{C.cwh}{APP_VERSION}{C.off}, (C) {C.clm}{APP_DATE}{C.off} by {C.paper}{APP_AUTHOR} ({APP_EMAIL}){C.off}"

# Settings defaults
DEF_DEBUG     = False          # Sets debug mode on/off
DEF_ENC       = "utf-8"        # Default text encoding type
DEF_OVERWRITE = False          # Determines whether to overwrite existing data
DEF_VERBOSE   = False          # T/F for extra detail
DEF_LOGGING   = False          # Logs output to file
DEF_LOGFILE   = "kdis6502.log" # Default log file
DEF_TEST      = False          # Run test cases?
DEF_HASHEADER = False          # Yes to 2 byte location header?
DEF_OUTEXT    = ".asm"         # Default output extension


### CODE ####

#*************************************************************************
# The configuration class houses parameter and initialization data
# which configures the client.
# NOTE: Private variables must be prefixed with "_".  toDictionary() relies
# on this.
# TODO: Add in your configuration properties in this class.
class Config:
   def __init__(self):
      # These are the public properties
      self.isVerbose=DEF_VERBOSE
      self.isOverwrite=DEF_OVERWRITE
      self.isLogging=DEF_LOGGING
      self.logfile=DEF_LOGFILE
      self.hasHeader=DEF_HASHEADER
      self.inputfile=""
      self.outputfile=""

      # Private members
      self._DEBUG=DEF_DEBUG
      self._TEST=DEF_TEST

      # Uncomment if using account manager; remember to import it
      #self._accountmanager=AccountManager(DEF_ACCOUNTDB)

   # Convenience method reporting debug status
   def isDebug(self):
      return (self._DEBUG)

   # Convenience method reporting test status
   def isTest(self):
      return (self._TEST)   
   
   # Uses reflection to create a dictionary of public atributes
   # Skips any methods or functions or internals.
   def toDictionary(self, showPrivate=False):
      d={}
      s=dir(self)
      i=0

      while True:
         if s[i].startswith("__") and s[i].endswith("__"):
            # Attribute is an internal, remove
            s.pop(i)
         elif (s[i].startswith("_") and not showPrivate):
            # Attribute is a private variable or method, remove
            s.pop(i)
         elif (isinstance(getattr(self, s[i]), types.MethodType) or
               "function" in str(type(getattr(self, s[i])))):
            # Attribute is a method/function, remove
            s.pop(i)
         else:
            # Attribute is a value attribute, continue
            i+=1
         if (i>=len(s)):
            break
      for key in s:
         d[key]=getattr(self, key)
      return (d)

   # Implements str() function
   def __str__(self):
      return(self.toString())

   # Converts values to string
   def toString(self, showPrivate=False):
      s=""
      d=self.toDictionary(showPrivate)
      for key, value in d.items():
         s+=f"{key}={value}\n"
      return(s)

   def toJson(self):
      # Produces a "clean" JSON string. Just uses a dictionary.
      # Method toDictionary() uses reflection  to create itself.
      d=self.toDictionary()
      return(json.dumps(d))

   # This is a factory method so it must be static
   # We use futures to put some constraints on method signature.
   @staticmethod
   def fromJson(data) -> Config():
      # Use reflection to fill JSON instance, return Config object
      x=Config()
      d=json.loads(data)
      for key,value in d.items():
         if (hasattr(x, key)):
            setattr(x, key, value)
      return(x)

#*************************************************************************

#*************************************************************************
class Kdis6502:
   
   def __init__(self):
      # TODO: Add public attributes here. Private attributes start with '__'.
      self.app=APP_NAME
      self.author=APP_AUTHOR
      self.email=APP_EMAIL
      self.version=APP_VERSION
      self.date=APP_DATE
      self.__opmatrix="6502_OpcodeMatrix.csv"
      self.opcodes={}

      # Load opcode data. If file error, abort constructor and error out.
      # Bad practie in standard OOP, but considered pythonic
      try:
         # Read file
         # TODO: Put this in a SQLITE DB instead
         with open(self.__opmatrix, 'r') as file:
            lines = file.readlines()

         # Clean
         for i in range(len(lines)):
            lines[i]=lines[i].rstrip()

         # Extract header
         header=lines.pop(0).lstrip()

         # Build dictionary
         for line in lines:
            seg=line.rstrip().split(',')
            self.opcodes[seg[0]] = [seg[1],seg[2],seg[3],seg[4],seg[7],seg[8]]

      except Exception as e:
         error(f"File access error to {self.__opmatrix}\n\"{e}\"")

      # END Construtor

   # Checks if a one byte control byte is legal for the 6502 standard matrix
   def isLegal(self, controlByte):
      return (controlByte in self.opcodes.keys())

   # Returns the number of bytes required by this control byte
   def getBytes(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][2]
      else:
         return 0

   # Returns the number of cycles required by this control byte
   def getCycles(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][3]
      else:
         return 0

   # Returns the instruction name (opcode) of this control byte
   def getInstruction(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][0]
      else:
         return ""

   # Returns the instruction definition (text) of this control byte
   def getDefinition(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][5]
      else:
         return ""

   # Returns the contol byte memory model
   def getAddressing(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][1]
      else:
         return ""

   # Returns the contol byte memory model
   def getFlags(self, controlByte):
      if self.isLegal(controlByte):
         return self.opcodes[controlByte][4]
      else:
         return ""

   # Disassembles an input binary to a text listing file
   def disassemble(self, config):
      note (f"Disassembling binary: {config.inputfile} to listing file: {config.outputfile}")

      note (f"Reading binary input from {config.inputfile}")
      with (open(config.inputfile, 'rb')) as file:
         data = file.read(os.path.getsize(config.inputfile))

      cnt=len(data)
      index=0

      if (config.hasHeader):
         blo=int(data[index])
         bhi=int(data[index+1])
         index+=2
         address=hex(bhi*256+blo).upper().replace("0X", "$")
         print(f"   *= {address}")
      
      

   # Implements len routine for class, based on number of opcodes
   def __len__(self):
      return(len(self.opcodes))

   # Implements str() function
   def __str__(self):
      return(self.toString())
   
   # Uses reflection to create a dictionary of public atributes
   # Skips any methods or functions or internals.
   def toDictionary(self, showPrivate=False):
      d={}
      s=dir(self)
      i=0

      while True:
         if s[i].startswith("__") and s[i].endswith("__"):
            # Attribute is an internal, remove
            s.pop(i)
         elif (s[i].startswith("_") and not showPrivate):
            # Attribute is a private variable or method, remove
            s.pop(i)
         elif (isinstance(getattr(self, s[i]), types.MethodType) or
            "function" in str(type(getattr(self, s[i])))):
            # Attribute is a method/function, remove
            s.pop(i)
         else:
            # Attribute is a value attribute, continue
            i+=1
         if (i>=len(s)):
            break
      for key in s:
         d[key]=getattr(self, key)
      return (d)

   def toString(self, showprivate=False):
      s=""
      d=self.toDictionary(showprivate)
      for key, value in d.items():
         s+=f"{key}={value}\n"
      return(s)

   def toJson(self):
      # Produces a "clean" JSON string. Just uses a dictionary.
      # Method toDictionary() uses reflection  to create itself.
      d=self.toDictionary()
      return(json.dumps(d))

   # This is a factory method so it must be static
   # We use futures to put some constraints on method signature.
   @staticmethod
   def fromJson(data) -> Kdis6502():
      # Use reflection to fill JSON instance, return Kdis6502 object
      x=Kdis6502()
      d=json.loads(data)
      for key,value in d.items():
         if (hasattr(x, key)):
            setattr(x, key, value)
      return(x)

#*************************************************************************

# Show utility syntax and exits
def showHelp():
   s=f'''
{APP_TAG}
{C.yes}*** THIS IS SOFTWARE IS RELEASED TO THE PUBLIC DOMAIN ***{C.off}

{C.paper}{APP_BLURB}

Syntax:
  {APP_SYNTAX}

Options
  {C.clm}-h{C.coff}     Binary has a location header (first 2 bytes) {C.clg}(Commodore, etc...){C.coff}

{C.cly}<inputfile>{C.off} a valid 6502 assembly
{C.cly}<outputfile>{C.off} defaults to {C.clc}"<inputfile>.asm"{C.off} if not specified
'''
   print(s)
   exit()

# Outputs a message for a serious error, and terminates program
# Use this for fatal errors only!
def error(message):
   print(f"{C.clr}An error has occurred!");
   print(f"{C.clm}{message}{C.off}")
   print(flush=True)
   try:
      if (config.isLogging):
         log(message)
      # Close any sockets, resources, etc... here
   except Exception as e:
         pass
   finally:
      exit()

# Outputs a message to a log file.
# Strips the ANSI colour codes out of the string to stop log clutter.
# Caches file handle so that it is only opened once, and closed on exit.
# Applies a header to new logging session (captured to same logfile).
# Format of a log is:
# [time since program start] message
def log(message):
   global FLAG_LOGOPEN, logfilehandle
   if not FLAG_LOGOPEN:
      logfilehandle=open(config.logfile, "at+")
      FLAG_LOGOPEN=True
      log.logtimer=Timer()
      log.logtimer.start()
      now=datetime.datetime.now()
      header=f"\n******************************************************************************\n" \
             f"Log File for {C.cstrip(APP_TAG)}" \
             f"On: {now:%Y-%m-%d %H:%M}\n" \
             f"******************************************************************************\n"
      logfilehandle.write(f"{header}\n")
   logmsg=f"[{log.logtimer.peek():.5f}] {C.cstrip(message)}"
   if (not logmsg.endswith("\n")):
      logmsg=logmsg+"\n"
   logfilehandle.write(f"{logmsg}")
   logfilehandle.flush()

# "Pips up" to let you know something minor happened, doesn't impact
# program flow. This method is intended for non-fatal errors, either
# as notifications (green coloring) or as alerts (red syntax).
def pip(message, isalert=False):
   if isalert:
      print(f"{C.cly}{C.bdr}{message}{C.off}")
   else:
      print(f"{C.clg}{C.bdg}{message}{C.off}")
   try:
      if (config.isLogging):
         log(message)
   except Exception as e:
      pass

# Outputs a message to screen only if in verbose mode OR if show==true
# IE: note() -> only shown if verbose mode enabled
def note(message, show=False):
   if (config.isVerbose or show==True):
      print(f"{C.clc}{C.boff}{message}{C.off}")
   # Always write to logfile no matter if verbose or not
   try:
      if (config.isLogging):
         log(message)
   except Exception as e:
      pass

# Just outputs a message regardless of verboseness
# IE: notex() -> always shown
def notex(message):
   note(message, show=True)

# Parses the command line and gets all options / switches.  These values should
# be stored in the global configuration structure (class).
# TODO: Customize switches and options.
def parseCommandLine():
   if argc<2:
      showHelp()

   # Single switch options are listed with a ':' suffix only if they expect a value.
   # Extended options (--) must have a '=' suffix if value is expected
   try:
       opts, args =getopt.getopt(argv[1:],
        "?SDvhnotl",
        ["help","version","verbose", "DEBUG", "header", "test", "log"])
   except getopt.GetoptError as e:
      error(f"Arguments error: ({e.opt})=>{e.msg}")
      showHelp()

   # Process
   for opt, arg in opts:
      #This line is useful for option debugging:
      #print(f"OPT:{opt}  ARG:{arg}")

      if (opt in ("-?", "--help")):
         showHelp()

      # This option check must come before version check
      # as '-v' is in version, and I'm sticking to the 'in' patern
      # (it makes expansion easy)
      elif (opt in("-v", "--verbose")):
         config.isVerbose=True

      # Debugging flag
      elif (opt in ("-D", "--DEBUG")):
         config._DEBUG=True

      # Does it have a 2 byte location header?
      elif (opt in ("-h", "--header")):
         config.hasHeader=True

      # Handle logging as a switch
      elif (opt in("-l", "--log")):
         config.isLogging=True
         config.logfile=DEF_LOGFILE

      # If file already exists, allows replacement
      elif (opt in("-o", "--overwrite")):
         config.isOverwrite=True

      # Is this is a unit test?
      elif (opt in("-t", "--test")):
         config._TEST=True

      # Show version and then exit immediately
      elif (opt in ("--version")):
         print(f"{APP_TAG}")
         exit()

      # Greetings are always welcome
      elif (opt in ("-S")):
         pip(f"{C.bdr}{C.cly}Sultaneous sends Salutations.{C.off}")
         exit()

   # Options handled, now handle the one or more args 
   fileargs=[]
   for arg in args:
      # TODO: Capture args, validate
      fileargs.append(arg);

   if len(fileargs)==0:
      error("Please specify input 6502 binary file.")
      
   config.inputfile=fileargs[0]
   if (len(fileargs)>1):
      config.outputfile=fileargs[1]
   else:
      preamble=config.inputfile.split('.')
      config.outputfile=preamble[0] + DEF_OUTEXT



### Program mainline ###
      
def main():
   # Create our global configuration object
   global config
   config=Config()

   # Parse command line arguments
   parseCommandLine()
   
   # Validate file arguments
   if (not os.path.isfile(config.inputfile)):
      error(f"Input file does not exist: {C.cwh}{config.inputfile}")
   if (os.path.isfile(config.outputfile) and (not config.isOverwrite)):
      error(f"Output file already exists.\nTry using -o: {C.cwh}{config.outputfile}{C.off} ")

   if (config.isDebug()):
      notex (config.toString(showPrivate=True))

   # Construct disassembler engine
   kdis6502=Kdis6502()
   kdis6502.disassemble(config)
   

   # DEBUGGING
   if config.isTest():
      doTest(kdis6502, config)
   pass

# End of mainline

### TEST CASE(S) ###

def doTest(kdis6502, config):
   # Class base method tests
   print(f"{C.cdy}"+str(kdis6502))
   print()
   print(f"{C.cdg}"+str(config))
   print(f"{C.clm}")
   print(f"Number of supported opcodes: {C.cwh}{len(kdis6502)}")

   # Class logic tests
   print()
   cb="31"
   print(f"{C.clc}Real control byte 0x{cb} is legal? {C.cwh}{kdis6502.isLegal(cb)}")
   cb="32"
   print(f"{C.clc}Fake control byte 0x{cb} is legal? {C.cwh}{kdis6502.isLegal(cb)}")

   testBytes =["4C", "A9", "CD", "00", "FE"]
   for cb in testBytes:
      print()
      print(f"{C.clg}Control byte {C.cwh}0x{cb} {C.clg}has the following properties:")
      print(f"{C.clg}Opcode:     {C.cwh}{kdis6502.getInstruction(cb)}")
      print(f"{C.clg}Definition: {C.cwh}{kdis6502.getDefinition(cb)}")
      print(f"{C.clg}Bytes:      {C.cwh}{kdis6502.getBytes(cb)}")
      print(f"{C.clg}Cycles:     {C.cwh}{kdis6502.getCycles(cb)}")
      print(f"{C.clg}Flags:      {C.cwh}{kdis6502.getFlags(cb)}")
      print(f"{C.clg}Addressing: {C.cwh}{kdis6502.getAddressing(cb)}")
      print(f"{C.off}")

# END of Test Case(s)


# Module Execution Sentinel
if __name__=="__main__":
   main()

