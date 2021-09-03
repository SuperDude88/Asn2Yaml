# Asn2Yaml
A tool that allows you to convert the .asn file found in JAudioRes/Seqs to a more readable format and repack the yaml to .asn

In `content\Cafe\<game region>\AudioRes\JAudioRes` there is a .asn file that stores the IDs and names for all tracks/sounds in the game. The list of sounds is also divided into named sections. Games developed later in the life cycle of JSystem used this to call tracks by name instead of ID.

The extractor lists the sections in the .asn and includes the section name, first entry index, number of entries, and a list of the entries inside the section. Each entry has 3 values separated by commas (`,`), the first being the index in the entry list, then the name of the entry, and the ID last. The building process takes the names, IDs, and indexes, and writes them back to a .asn file. This means that renaming entries to each other will switch them and switch the tracks in the game. This mostly works, but seems to have some limitations with streamed vs sequenced tracks. Switching streamed or sequenced audio to one of the streamed effects in the .bfsar file has yet to be tested.

# Usage
To run the program as a python script, navigate to the folder containing the .py file and run `TWWHD_ASN_Tool.py <mode> <in_path> <out_path [optional]> <out_name [optional]>`

Mode can be either `extract` or `build`

Paths should be specified as strings with "" around them. They should also be the absolute paths to the files.

When extracting `in_path` is the path to the .asn file you want to convert. When building, this is the path to the yaml file to be converted.

When extracting `out_path` is the path to the folder you want to place the output file. This is optional, and will default to the same path as the original file if left blank.

When building, `out_name` is the name of the archive to be created. This is optional, and will take the name of the original file (with a changed extension) if left blank.

# ASN File Format
The .asn file begins with a 0x10 byte "main" header, and is followed by 18 0x20 byte blocks, one for each section. Although the "main header" may not really be distinct from the section headers, I find it easier to understand when separating them.

This file contains a list of entries which hold the name and ID of various tracks and sounds.
As far as I have found, this type of archive is only used in TWWHD.

**MAIN HEADER:**

```
Offset    Size    Type      Desc

0x00      ?       ???       Unknown. Always 0x00000000...

0x04      ?       ???       Unknown. Always 0x00000000...

0x08      ?       ???       Unknown. Always 0x00000000...

0x0C      4       uint32    Number of entries in the file

0x10    START OF SECTION FILE HEADERS/END OF MAIN HEADER
```

Following the main header, there is a 0x20 byte header for each of the 18 sections. Their indexes always range from 0-17, although some are not used. In that case, their name is `  (no named)` and 0 entries are listed:

```
Offset    Size    Type      Desc

0x00      2       String    Stored as a string but matches the section index. It's likely read as a part of the name, but it's easier to read with an "index". Padded to 2 digits with spaces added to the left side.

0x02      26      String    May or may not be read as a 26 byte string. Contains a space followed by the name of the section, padded with null values to a length of 26.

0x1C      2       uint16    The number of entries contained in the section

0x1E      2       uint16    The index (in the entry list) of the first entry

0x20    END OF SECTION HEADER
```

Following the 18 section headers, there are 0x20 byte blocks for each entry. The entries follow this format:
```
Offset    Size    Type      Desc

0x00      28      String    May or may not be read as a 28 byte string. Contains the name of the track and is padded to 28 bytes with null values.

0x1C      4       uint32    The ID of the entry (not the index), likely broken into an access mode and an ID (see later documentation)

0x20    END OF ENTRY
```

Occasionally, there are entries with the name `(dummy)` which seem to fill gaps in IDs. This may not be 100% the case as there seem to be gaps still.

There is also some existing documentation I was shown:

```
ASN 
   ENDIAN big
   0x00 byte\[0xE] = 0; 
   0x0D ushort total_wave_count 

   <categoryNames>
   ?? char[0x1C] NAME
   ?? ushort len 
   ?? ushort ID

   NOTE: Categories get sorted by their ID, and then read their wave counts in order.
   This means that if Section 10 has ID of 0030, and that section 1 has an ID of 0032 , that section 10's waves will be listed first. 
   The header has no indication of this, but this seems to be the layout. 

   <waves>
   ?? char[0x1C] NAME;
   ?? ushort access_mode (example, 8001 is the SEQUENCE_BGM arc in SMS, hardcoded maybe?) 
   ?? ushort ID


 ST 
   0x00 byte 0x06  
   0x01 byte ??
   0x02 byte ??
   0x03 byte ?? 
   0x04 ushort entryCount 
   0x0F categories[0x12]

   <Category>
   ushort count 
   ushort id 

   @HEADER_END 0x50;

   NOTE: Categories get sorted by their ID, and then read their wave counts in order.
   This means that if Section 10 has ID of 0030, and that section 1 has an ID of 0032 , that section 10's waves will be listed first. 
   The header has no indication of this, but this seems to be the layout. 

   <Waves>
   byte[16] unknown


   Additional notes: 

   The sound ID isn't based off of the actual ID attached to the sequence in the ASN. A sound ID is assigned based on the INDEX in the sound table (the order it's defined).
   Before compilation, all of the sound names are taken and transformed to their ID, then baked into the binary.
```
     
I got that from Xayr, who has done a bunch of cool stuff with JAudio (https://github.com/XAYRGA)
