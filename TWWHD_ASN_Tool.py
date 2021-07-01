import argparse
import struct
from io import BytesIO
import os
import yaml
import operator

parser = argparse.ArgumentParser()
parser.add_argument("mode", help="The mode for the tool. This can be extract or build.")
parser.add_argument("in_file", help="When extracting, this is the input .asn file. For building, this is the input yaml.")
parser.add_argument("out_path", nargs="?", default="temp", help="The output folder that the new file is placed into (optional, is placed in the folder with the original file by default)")
parser.add_argument("out_name", nargs="?", default="temp", help="The name of the output file (optional, takes the name of the file it is pulling from by default)")

args = parser.parse_args()

mode = args.mode
in_file = args.in_file
out_path = args.out_path
out_name = args.out_name

if out_path == "temp":
    out_path = os.path.dirname(in_file)
if out_name == "temp":
    out_name = os.path.basename(in_file)
    out_name = out_name.replace(".asn", ".yaml")

def read_u16(data, offset):
  data.seek(offset)
  return struct.unpack(">H", data.read(2))[0]

def read_u32(data, offset):
  data.seek(offset)
  return struct.unpack(">I", data.read(4))[0]

def write_u16(data, offset, new_value):
  new_value = struct.pack(">H", new_value)
  data.seek(offset)
  data.write(new_value)

def write_u32(data, offset, new_value):
  new_value = struct.pack(">I", new_value)
  data.seek(offset)
  data.write(new_value)

def read_section_name(data, offset):
  data.seek(offset)
  return data.read(26)

def read_entry_name(data, offset):
  data.seek(offset)
  return data.read(28)

def write_section_name(data, offset, name):
  Name = name.encode("ascii")
  Name = Name.ljust(26, b'\x00')
  data.seek(offset)
  data.write(Name)

def write_entry_name(data, offset, name):
  Name = name.encode("ascii")
  Name = Name.ljust(26, b'\x00')
  data.seek(offset)
  data.write(Name)

class MainHeader():
    def __init__(self):
        self.NumEntries = None
        self.Sections = []

    def read(self, file_data):
        self.file_data = file_data
        self.NumEntries = read_u32(self.file_data, 12) #I assume this is a u32, since its what nintendo tends to use elsewhere, but it may not be as I haven't looked for the code that reads it
        for section_index in range(0, 18):
            section = SectionHeader(section_index)
            section.read(self.file_data)
            self.Sections.append(section)

    def YAMLtoHeader(self, sections):
        self.Sections = sections
        self.NumEntries = 0
        for section in sections:
            self.NumEntries = self.NumEntries + section.NumEntries

    def write(self, output_file):
        output_file.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00') #Write the 12 blank bytes that it always seems to start with
        write_u32(output_file, 12, self.NumEntries) #Write the last part of the header (number of entries)
        self.Sections.sort(key=operator.attrgetter("SectionIndex")) #Sort the section headers so that we can just write them in order
        for section in self.Sections:
            section.write(output_file)
        self.Sections.sort(key=operator.attrgetter("FirstEntryIndex")) #Sort the section headers by their first entry so that we can start at index 0 and go in order, instead of jumping around places which caused problems
        for section in self.Sections:
            for entry in section.Entries:
                entry.write(output_file)
        output_file.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00') #File always seems to end with a line (0x10) of 0x00 that isn't attached to an entry


class SectionHeader():
    def __init__(self, section_index):
        self.SectionIndex = int(section_index)
        self.Name = None
        self.NumEntries = None
        self.FirstEntryIndex = None
        self.Entries = []

    def read(self, file_data):
        #Throughout the script addition is separated, this is just so that it is easier to see what is being done and why
        self.Name = read_section_name(file_data, self.SectionIndex * 0x20 + 0x10 + 0x2).rstrip(b'\x00') #Each section header is 0x20, so we multiply the index by that, then add the length of the 0x10 main header, and the 2 bytes before it that are the section number
        self.NumEntries = read_u16(file_data, self.SectionIndex * 0x20 + 0x10 + 0x1C)
        self.FirstEntryIndex = read_u16(file_data, self.SectionIndex * 0x20 + 0x10 + 0x1E)
        for section_entry_index in range(0, self.NumEntries):
            entry = Entry(section_entry_index + self.FirstEntryIndex) #Add the first entry of the section to the index inside the section to get the index in the whole list of entries (which is what we want)
            entry.read(file_data)
            self.Entries.append(entry)

    def YAMLtoHeader(self, in_data):
        self.Name = in_data["Name"]
        self.NumEntries = in_data["NumEntries"]
        self.FirstEntryIndex = in_data["FirstEntryIndex"]
        for entry_index in range(0, len(in_data["Entries"])):
            entry = Entry(entry_index)
            entry.YAMLtoEntry(in_data["Entries"][entry_index])
            self.Entries.append(entry)

    def write(self, output_file):
        if self.SectionIndex < 10:
            index_str = " " + str(self.SectionIndex)
            output_file.write(index_str.encode("ascii"))
        else:
            index_str = str(self.SectionIndex)
            output_file.write(index_str.encode("ascii"))
        write_section_name(output_file, self.SectionIndex * 0x20 + 0x10 + 0x2, self.Name)
        write_u16(output_file, self.SectionIndex * 0x20 + 0x10 + 0x1C, self.NumEntries)
        write_u16(output_file, self.SectionIndex * 0x20 + 0x10 + 0x1E, self.FirstEntryIndex)
        self.Entries.sort(key=operator.attrgetter("Index"))


class Entry():
    def __init__(self, entry_index):
        self.Name = None
        self.Index = int(entry_index)
        self.Offset = self.Index * 0x20 + 0x250 #To find the offset, we multiply the index by 0x20 as each entry is that size, and add the length of the 0x250 byte (total) headers
        self.ID = None

    def read(self, file_data):
        self.Name = read_entry_name(file_data, self.Offset).rstrip(b'\x00')
        self.ID = read_u32(file_data, self.Offset + 0x1C)

    def YAMLtoEntry(self, in_data):
        self.Index = int(in_data.split(",")[0])
        self.Name = in_data.split(",")[1]
        self.ID = int(in_data.split(",")[2], 16)
        self.Offset = self.Index * 0x20 + 0x250 #Update our offset with the index we just filled in

    def write(self, output_file):
        write_entry_name(output_file, self.Offset, self.Name)
        write_u32(output_file, self.Offset + 28, self.ID)

if mode == "extract":

    asn_file = open(in_file, "rb")
    asn_data = BytesIO(asn_file.read())
    main_header = MainHeader()
    main_header.read(asn_data)

    yaml_output = []

    for section in main_header.Sections:
        yaml_output.append({"Section " + str(section.SectionIndex): {"Name": section.Name.decode("ascii"),
                                                                "NumEntries": section.NumEntries,
                                                                "FirstEntryIndex": section.FirstEntryIndex,
                                                                "Entries": []}})
        for entry in section.Entries:
            yaml_output[section.SectionIndex]["Section " + str(section.SectionIndex)]["Entries"].append(str(entry.Index) + "," + entry.Name.decode("ascii") + "," + hex(entry.ID))

    out_file = out_path + "/" + out_name
    if not out_file.endswith(".yaml"):
        out_file = out_file + ".yaml"

    with open(out_file, "w") as file:
       yaml.dump(yaml_output, file)

    with open(out_file, "r") as file: #This is so that it reloads the file with the right data
       data = file.read()
       data = data.replace("- Section", "Section")
    with open(out_file, "w") as file: #This refused to work with r+ so had to do this
       file.write(data)

elif mode == "build":
    input_file = open(in_file, "rb")
    input_data = yaml.load(input_file, Loader=yaml.FullLoader)

    sections = [] #We create the main header last, so we need to store this for creating that header
    for section in input_data:
        section_data = input_data[section]
        section = SectionHeader(section.split(" ")[1])
        section.YAMLtoHeader(section_data)
        sections.append(section)

    main_header = MainHeader()
    main_header.YAMLtoHeader(sections)

    out_file = out_path + "/" + out_name
    if not out_file.endswith(".asn"):
        out_file = out_file + ".asn"

    with open(out_file, "wb") as f:
        main_header.write(f)
