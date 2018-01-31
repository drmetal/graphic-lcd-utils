import Image
from glob import glob
import os

TABLE_SIZE_TUPLE = "#define %s_bmp_size (tuple_t){%s, %s}\n"
TABLE_EXTERN = "extern const uint8_t %s_bmp[%s][%s];\n"
TABLE_DEF = "const uint8_t %s_bmp[%s][%s] = {"
ARRAY_END = "};\n"
    
INVERT = True

def createLCDDataSet(pixellist, size):
   """
   every byte in pixel list encodes one pixel
   """
   pixel = 0
   xbyte = 0
   xbyte_bit = 0;
   ybyte = 0
   dataset = ""      
      
   #Convert size to byte aligned 
   sizex = size[0]
   sizey = size[1] / 8
   if size[1] % 8:
      sizey += 1 
    
   for x in range(sizex): 
     dataset += "{"
     for y in range(sizey):
        byte = 0
        for bit in range(8):
           if pixellist[pixel] == 0:
              byte |= (1<<bit)                  
           pixel += 1
        if INVERT:
            byte ^= 0xff
        dataset += hex(byte)
        if y < sizey-1:
           dataset += ","
     dataset += "}"
     if x < sizex-1:
        dataset += ","
   return dataset
       
            
def writeToFile(newimagedata, size, outputfilename, inputfilename):             
    #Convert size to byte aligned 
    sizex = size[0]
    sizey = size[1] / 8
    if size[1] % 8:
        sizey += 1 
    
    #Write the data to file
    f = file(outputfilename, 'a')
    #f.write(HEADER)
    f.write(TABLE_SIZE_TUPLE %(inputfilename,str(sizex),str(sizey)))
    f.write(TABLE_EXTERN %(inputfilename,str(sizex),str(sizey)))
    f.write(TABLE_DEF%(inputfilename,str(sizex),str(sizey)))
    f.write(str(newimagedata).strip("[]"))
    f.write(ARRAY_END)
    f.close()
      

if __name__ == "__main__":
    
    
    
    print """SSD1809 LCD Bitmap converter for images
          
    Rules:
    
    1.    lcdimage files must contain exact mulytiples of 8 pixels in the y axis (and must not exceed 64 pixels in height)
    2.    lcdimage files must contain exact mulytiples of 1 pixels in the x axis (and must not exceed 160 pixels in width)
    3.     the input file should be black and white 8bit encoded windows bmp format.
    """
    
    outputfilename = raw_input("type the output filename >")
    
    f = file(outputfilename, 'w')
    f.close()
    
    infilepath = raw_input("type input file directory path>")
    infilepath = os.path.join(infilepath, "*.bmp")
    filepaths = glob(infilepath)
    
    for filepath in filepaths:
       print "processing", filepath
       imagedata = Image.open(filepath, 'r')
       #for big lCD no need to rotate
       #for ssd1809 lcd rotate 90 degrees
       imagedata = imagedata.transpose(Image.ROTATE_90)
       imagedata = imagedata.transpose(Image.FLIP_TOP_BOTTOM)
       rawdata = list(imagedata.getdata()) 
       newimagedata = createLCDDataSet(rawdata, imagedata.size)
       writeToFile(newimagedata, imagedata.size, outputfilename, os.path.basename(filepath).split(".")[0])



    


