import Image
from glob import glob
import os
import sys


def convert_888_to565(rawdata):
    """
    convert rgb 888 data to rgb 565 data.

    .. example::

    [(r,g,b), (r,g,b), (r,g,b), ...]
    # turns into
    [a, b, c, ...]

    :param rawdata: a list of 8 bit 3-tuples.
    :returns: a list of 16 bit integers.
    """
    RED_MASK = 0xF800
    GREEN_MASK = 0x07E0
    BLUE_MASK = 0x001F
    RED_SHIFT = 11
    GREEN_SHIFT = 5
    BLUE_SHIFT = 0
    FIVE_SHIFT = 3
    SIX_SHIFT = 2

    return [((((r>>FIVE_SHIFT)<<RED_SHIFT)&RED_MASK) |
            (((g>>SIX_SHIFT)<<GREEN_SHIFT)&GREEN_MASK) |
            (((b>>FIVE_SHIFT)<<BLUE_SHIFT)&BLUE_MASK)) for r,g,b in rawdata]


def format_c_file(name, rgb565data, size, wrap_array=8):
    """
    creates a string for writing a c file from the rgb565 image data.

    :param name: image name.
    :param rgb565data: a list of 16 bit integers.
    :param size: tuple containing the dimensions of the data, width and height in pixels.
    :param wrap_array: width of array data in file.
    :returns: a "string of c code".
    """
    fmtdata = ''
    for i, point in enumerate(rgb565data):
        fmtdata += "0x%04X,"%point
        if i % wrap_array == wrap_array - 1:
           fmtdata += '\n\t'

    data = 'static const uint16_t {0}_data[] = {{\n\t{1}\n}};\n\n'.format(name, fmtdata)
    struct = 'const image_t {0} = {{\n\t{1},\n\t{2},\n\t{3}{4}\n}};\n\n'.format(name, size[0], size[1], name, "_data")
    return data + struct



if __name__ == "__main__":

    args = sys.argv[1:]
    outputfilename = os.path.join(os.path.abspath(os.path.dirname(__file__)), args[1])
    filepaths = glob(os.path.join(args[0], "*.bmp"))

    with open(outputfilename, 'w') as output:
        for filepath in filepaths:
            print "processing", filepath
            imagedata = Image.open(filepath, 'r')
            rawdata = list(imagedata.getdata())
            print rawdata
            newimagedata = convert_888_to565(rawdata)
            print newimagedata
            output.write(format_c_file(os.path.splitext(os.path.basename(filepath))[0], newimagedata, imagedata.size))
