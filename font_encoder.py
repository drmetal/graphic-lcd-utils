from jinja2 import Environment, FileSystemLoader
from PIL import Image
import re
import os
import logging
import argparse
from collections import OrderedDict


class FontDescriptor(object):

    name = ""
    """ name of the font """
    descriptor = {"font":{}, "characters": OrderedDict(), "kerning": {}, "data": []}
    """ data describing the font """
    ignore_group_params = {"char": ["chnl", "page"], "info":["padding", "spacing", "charset", "unicode"]}
    """ parameters to be ignored in groups of the data tree """

    def __init__(self, filename, invert):
        """
        this class decodes the contents of a font description file created by the "Bitmap Font Generator" program by Angel Code.
        the BMFont program produces a .fnt file and an image file.
        the settings for the image file should be:
            type: png
            resolution: 8bits

        :param filename: the full path to the .fnt file. the accompanying image file should be in the same location.
        :param invert: if set to true, inverts the values of the data derived from the image file.
        """
        log = logging.getLogger(self.__class__.__name__)

        log.info("opening font file '{0}'".format(filename))
        with open(filename, 'r') as f:
            fdesc = f.readlines()

        # counter used to differentiate kernings
        kerning = 0

        for line in fdesc:
            # clean up whitespace, tabs, remove newlines
            line = re.sub("\s+", " ", line)
            # fina anything in quotes, replace spaces and dashes in those matches
            inquotes = re.findall('"[\w\s.-]+"', line)
            for item in inquotes:
                item = re.sub("[\s-]+", "_", item)
                line = re.sub('"[\w\s.-]+"', item, line, 1)
            # remove double quotes
            line = re.sub("\"", "", line)
            line = line.strip()
            line = line.split(' ')
            group = line[0]
            distinct_group = line[0]
            # character descriptors
            if group == "char":
                distinct_group += "_" + line[1].split("=")[1]
                addto = self.descriptor["characters"]
            # kerning descriptors
            elif group == "kerning":
                distinct_group += "_" + str(kerning)
                kerning += 1
                addto = self.descriptor["kerning"]
            else:
                addto = self.descriptor["font"]

            # add all parameters and their values to the data structure
            addto[distinct_group] = {}
            for pair in line[1:]:
                pair = pair.split("=")
                if group in self.ignore_group_params:
                	if pair[0] in self.ignore_group_params[group]:
                		continue
                addto[distinct_group][pair[0]] = pair[1]

            log.debug("added item '{0}': {1}".format(distinct_group, addto[distinct_group]))

        bold = "_bold" if self.descriptor["font"]["info"]["bold"] == '1' else ""
        italic = "_italic" if self.descriptor["font"]["info"]["italic"] == '1' else ""

        self.name = "{0}_{1}{2}{3}".format(self.descriptor["font"]["info"]["face"], self.descriptor["font"]["info"]["size"], bold, italic)
        log.info("created font '{0}'".format(self.name))
        log.info("total character descriptors: {0}".format(len(self.descriptor["characters"])))

        assert len(self.descriptor["characters"]) == int(self.descriptor["font"]["chars"]["count"]), \
            "the number of characters described ({0}) does not match the entry descriptor['font']['chars']['count'] ({1})".format(
            len(self.descriptor["characters"]),
            int(self.descriptor["font"]["chars"]["count"]))

        imagepath = os.path.join(os.path.dirname(filename), self.descriptor["font"]["page"]["file"])
        log.info("opening image '{0}'".format(imagepath))
        im = Image.open(imagepath)
        bbox = im.getbbox()
        xsize = bbox[2]
        ysize = bbox[3]
        self.descriptor["data"] = list(im.getdata())

        if invert:
            self.descriptor["data"] = [(-1 * point) + 255 for point in self.descriptor["data"]]

        assert len(self.descriptor["data"]) == xsize * ysize, \
            "the data length ({0}) doesnt math the bounding box ({1}). the file may not be an 8 bit image.".format(
            len(self.descriptor["data"]),
            xsize * ysize)


class Builder(object):

    templates = "./"
    output = ""

    def get_template(self, templatefile):
        env = Environment(loader=FileSystemLoader(self.templates))
        return env.get_template(templatefile)


class Build_Font_Type_H(Builder):

    def __init__(self, fd, template):
        """
        builds font "type" .h file data from a font descriptor object.

        :param fd: a font descriptor object, :py:class:`.FontDescriptor`.
        :param template: a jinja style template file.
        """

        # HACK these font type dicts break from data defined in the .fnt file
        # could have avoided this except that there is no type information
        # in the .fnt file and the types have to match up with the members.
        types = OrderedDict()
        types["characters"] = {"name": "character",
                                "params": {
                                       "width": "uint8_t",
                                       "height": "uint8_t",
                                       "xoffset": "uint8_t",
                                       "yoffset": "uint8_t",
                                       "xadvance": "uint8_t",
                                       "data": "const uint8_t*"}}
        types["font"] = {"name": "font",
                         "params": {"size": "uint8_t",
                                 "bold": "uint8_t",
                                 "italic": "uint8_t",
                                 "smooth": "uint8_t",
                                 "aa": "uint8_t",
                                 "outline": "uint8_t",
                                 "count": "uint8_t",
                                 "stretchH": "uint8_t",
                                 "characters": "const character_t**",
                                 "base_id": "uint8_t",}
                                 }
        # render the template
        tmpl = self.get_template(template)
        self.output = tmpl.render(font_types=types)


class Build_Font_Definition_H(Builder):

    def __init__(self, fd, template):
        """
        builds a font definition .h file from a font descriptor object.

        :param fd: a font descriptor object, :py:class:`.FontDescriptor`.
        :param template: a jinja style template file.
        """
        # render the template
        tmpl = self.get_template(template)
        self.output = tmpl.render(font_name=fd.name, hfile_upper=fd.name.upper())


class Build_Font_Definition_C(Builder):

    max_run_length = 255
    use_run_length_encoding = True
    char_set_member_name = "characters"
    char_data_member_name = "data"
    base_id_member_name = "base_id"
    info_ignore_members = ["face"]
    groups_with_useful_font_params = ["info", "chars"]
    ignore_group_params = {"char": ["id", "x", "y"], "info": ["face"], "chars": []}
    """ parameters to be ignored in groups of the data tree """

    def __init__(self, fd, template):
        """
        builds a font definition .c file from a font descriptor object.

        :param fd: a font descriptor object, :py:class:`.FontDescriptor`.
        :param template: a jinja style template file.
        """
        log = logging.getLogger(self.__class__.__name__)

        log.info("creating run length encoded character bitmaps")
        character_data = {}
        # build character bitmap
        for char in fd.descriptor["characters"]:
            character_data[char] = []
            x = int(fd.descriptor["characters"][char]["x"])
            xsize = int(fd.descriptor["font"]["common"]["scaleW"])
            y = int(fd.descriptor["characters"][char]["y"])
            w = int(fd.descriptor["characters"][char]["width"])
            h = int(fd.descriptor["characters"][char]["height"])

            if self.use_run_length_encoding:
                run = 0
                prev = fd.descriptor["data"][x + (y * xsize)]
                for cy in range(y * xsize, (y + h) * xsize, xsize):
                    for cx in range(x, x + w):
                        point = fd.descriptor["data"][cx + cy]
                        if point == prev and run < self.max_run_length:
                            run += 1
                        else:
                            character_data[char].append(run)
                            if run < self.max_run_length:
                                character_data[char].append(prev)
                            else:
                                character_data[char].append(point)
                            run = 1
                        prev = point
                character_data[char].append(run)
                character_data[char].append(point)
            else:
                for cy in range(y * xsize, (y + h) * xsize):
                    for cx in range(x, x + w):
                        character_data[char].append(fd.descriptor["data"][cx + cy])

            # populate value of c pointer to the character data set
            # this is an additional member (not derived from the .fnt file)
            fd.descriptor["characters"][char][self.char_data_member_name] = "{0}_{1}_{2}".format(fd.name, char, self.char_data_member_name)

        # filter off all unwanted character members
        characters = OrderedDict()
        for char in fd.descriptor["characters"]:
            characters[char] = {}
            for member, value in fd.descriptor["characters"][char].items():
                if member not in self.ignore_group_params["char"]:
                    characters[char][member] = value


        # populate value of c pointer to the character set
        # these are additional members (not derived from the .fnt file)
        fd.descriptor["font"]["info"][self.char_set_member_name] = "{0}_{1}".format(fd.name, self.char_set_member_name)
        fd.descriptor["font"]["info"][self.base_id_member_name] = tuple(fd.descriptor["characters"].items())[0][1]["id"]

        # filter off all unwanted font members
        font_members = {}
        for group in self.groups_with_useful_font_params:
            for member, value in fd.descriptor["font"][group].items():
                if member not in self.ignore_group_params[group]:
                    font_members[member] = value

        # render the template
        tmpl = self.get_template(template)
        self.output = tmpl.render(font_name=fd.name,
                                  character_data=character_data,
                                  chardata_suffix=self.char_data_member_name,
                                  characters=characters,
                                  font_c_include=None,
                                  font_info=font_members,
                                  charset_suffix=self.char_set_member_name)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Font Generator. creates .c and .h files from .fnt and .png files")

    parser.add_argument('-f', '--file',
                        required=True,
                        help='full path to the .fnt file (the image file should reside in the same location)')
    parser.add_argument('-o', '--output',
                        default="./output",
                        help='full path to the output file location')
    parser.add_argument('-d', '--debug',
                        default="INFO",
                        help='debug level ERROR, WARNING, INFO, DEBUG')
    parser.add_argument('-t', '--type_template',
                        default="./templates/font_type.h.in",
                        help='template file for the font type .h file')
    parser.add_argument('-c', '--c_template',
                        default="./templates/font_c.c.in",
                        help='template file for the font definition .c file')
    parser.add_argument('-H', '--h_template',
                        default="./templates/font_h.h.in",
                        help='template file for the font definition .h file')
    parser.add_argument('-i', '--invert',
                        action='store_true',
                        default=False,
                        help='invert the data from the image file')


    config = vars(parser.parse_args())

    logging.basicConfig(level=getattr(logging, config['debug']))

    fontdesc = FontDescriptor(config['file'], config['invert'])

    if not os.path.exists(config['output']):
        os.mkdir(config['output'])

    fonttype_h = Build_Font_Type_H(fontdesc, config["type_template"])
    fontdef_h = Build_Font_Definition_H(fontdesc, config["h_template"])
    fontdef_c = Build_Font_Definition_C(fontdesc, config["c_template"])

    with open(os.path.join(config["output"], fontdesc.name + ".c"), 'w') as f:
        f.write(fontdef_c.output)
    with open(os.path.join(config["output"], fontdesc.name + ".h"), 'w') as f:
        f.write(fontdef_h.output)
    with open(os.path.join(config["output"], "font_type.h"), 'w') as f:
        f.write(fonttype_h.output)

