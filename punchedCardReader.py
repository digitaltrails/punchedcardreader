#!/usr/bin/env python
#
# punchcard.py 
#
# Copyright (C) 2011: Michael Hamilton
# The code is GPL 3.0(GNU General Public License) ( http://www.gnu.org/copyleft/gpl.html )
#
from PIL import Image
import sys
from optparse import OptionParser
from functools import partial
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

debug_print = partial(print, file=sys.stderr)
debug_write = partial(sys.stderr.write)

CARD_COLUMNS = 80
CARD_ROWS = 12

# found measurements at http://www.quadibloc.com/comp/cardint.htm
CARD_WIDTH = 7.0 + 3.0/8.0 # Inches
CARD_HEIGHT = 3.25 # Inches
CARD_COL_WIDTH = 0.087 # Inches
CARD_HOLE_WIDTH = 0.055 # Inches IBM, 0.056 Control Data
CARD_ROW_HEIGHT = 0.255 # Inches - increased by 0.005 to fix drift (does that mean we have a bug?)
CARD_HOLE_HEIGHT = 0.125 # Inches
CARD_TOPBOT_MARGIN = 3.0/16.0 # Inches at top and bottom
CARD_SIDE_MARGIN = 0.2235 # Inches on each side


CARD_SIDE_MARGIN_RATIO = CARD_SIDE_MARGIN/CARD_WIDTH # as proportion of card width (margin/width)
CARD_TOP_MARGIN_RATIO = CARD_TOPBOT_MARGIN/CARD_HEIGHT # as proportion of card height (margin/height)
CARD_ROW_HEIGHT_RATIO = CARD_ROW_HEIGHT/CARD_HEIGHT # as proportion of card height - works
CARD_COL_WIDTH_RATIO = CARD_COL_WIDTH/CARD_WIDTH # as proportion of card height - works
CARD_HOLE_HEIGHT_RATIO = CARD_HOLE_HEIGHT/CARD_HEIGHT # as proportion of card height - works
CARD_HOLE_WIDTH_RATIO = CARD_HOLE_WIDTH/CARD_WIDTH # as a proportion of card width

BRIGHTNESS_PRACTICAL_MAX = 250
BRIGHTNESS_PRACTICAL_MIN = 150  # white/grey pixel brightness value (i.e. (R >= MIN and G >= MIN and B >= MIN)

HOLE_WIDTH_THRESHOLD = 0.55 # how wide should a hole be to count %/100 of standard size

IBM_MODEL_029_KEYPUNCH = """
    /&-0123456789ABCDEFGHIJKLMNOPQR/STUVWXYZ:#@'="`.<(+|!$*);^~,%_>? |
12 / O           OOOOOOOOO                        OOOOOO             |
11|   O                   OOOOOOOOO                     OOOOOO       |
 0|    O                           OOOOOOOOO                  OOOOOO |
 1|     O        O        O        O                                 |
 2|      O        O        O        O       O     O     O     O      |
 3|       O        O        O        O       O     O     O     O     |
 4|        O        O        O        O       O     O     O     O    |
 5|         O        O        O        O       O     O     O     O   |
 6|          O        O        O        O       O     O     O     O  |
 7|           O        O        O        O       O     O     O     O |
 8|            O        O        O        O OOOOOOOOOOOOOOOOOOOOOOOO |
 9|             O        O        O        O                         | 
  |__________________________________________________________________|"""

translate = None
if translate == None:
    translate = {}
    # Turn the ASCII art sideways and build a hash look up for 
    # column values, for example:
    #   (O, , ,O, , , , , , , , ):A
    #   (O, , , ,O, , , , , , , ):B
    #   (O, , , , ,O, , , , , , ):C
    rows = IBM_MODEL_029_KEYPUNCH[1:].split('\n');
    rotated = [[ r[i] for r in rows[0:13]] for i in range(5, len(rows[0]) - 1)]
    for v in rotated:
        translate[tuple(v[1:])] = v[0]
    #print translate

# generate a range of floats
def drange(start, stop, step=1.0):
    r = start
    while (step >= 0.0 and r < stop) or (step < 0.0 and r > stop):
        yield r
        r += step

# Represents a punchcard image plus scanned data
class PunchCard(object):
    
    def __init__(self, image, bright=BRIGHTNESS_PRACTICAL_MAX, dimmest=BRIGHTNESS_PRACTICAL_MIN, prefer_white=False, display=False, debug=False, xstart=0, xstop=0, ystart=0, ystop=0, xadjust=0):
        self.text = ''
        self.decoded = []
        self.surface = [] 
        self.debug = debug
        self.debug_image = display
        self.prefer_while = prefer_white
        self.threshold = 0
        self.brightest = bright
        self.dimmest = dimmest
        self._previous_borders = (0,0)
        self.ymin = ystart
        self.ymax = ystop
        self.xmin = xstart
        self.xmax = xstop
        self.xadjust = xadjust
        self.invalid_char_count = 0
        self.image = image
        self.pix = image.load()
        self._crop()
        self._scan()
    
    
    def _brightness(self, pixel):
        #print max(pixel)
        return ( pixel[0] + pixel[1] + pixel[2] ) / 3

    def _is_bright(self, pixel):
        if self.prefer_while:
             # Brightness is tendency to be bright grey/white
            return pixel[0] >= self.threshold and pixel[1] >= self.threshold and pixel[2] >= self.threshold
        # Brightness is the average of RGB values
        return ( pixel[0] + pixel[1] + pixel[2] ) / 3 >= self.threshold
        
       
        

    # For highlighting on the debug dump
    def _flip(self, pixel):
        return max(pixel)

    # The search is started from the "crop" edges.
    # Either use crop boundary of the image size or the valyes supplied
    # by the command line args
    def _crop(self):
        self.xsize, self.ysize = image.size
        if self.xmax == 0:
            self.xmax = self.xsize
        if self.ymax == 0:
            self.ymax = self.ysize
        self.midx = self.xmin + (self.xmax - self.xmin) // 2 + self.xadjust
        self.midy = self.ymin + (self.ymax - self.ymin) // 2
    
    # Find the left and right edges of the data area at probe_y and from that
    # figure out the column and hole vertical dimensions at probe_y.
    def _find_data_horiz_dimensions(self, probe_y):
        left_border, right_border = self.xmin, self.xmax - 1
        for x in range(self.xmin, self.midx):            
            if not self._is_bright(self.pix[x,  probe_y]):
                left_border = x
                break
        for x in range(self.xmax-1,  self.midx,  -1):
            if not self._is_bright(self.pix[x,  probe_y]):
                right_border = x
                break
        # Sanity check the new borders
        previous_left_border, previous_right_border = self._previous_borders
        if previous_left_border > 0 and abs(left_border - previous_left_border) > 10:
            left_border = previous_left_border # Something went wacky
        if previous_right_border > 0 and abs(right_border - previous_right_border) > 10:
            right_border = previous_right_border # Something went wacky
        self._previous_borders = (previous_left_border, previous_right_border)
            
        width = right_border - left_border
        card_side_margin_width = int(width * CARD_SIDE_MARGIN_RATIO)
        data_left_x = left_border + card_side_margin_width
        #data_right_x = right_border - card_side_margin_width
        data_right_x = data_left_x + int((CARD_COLUMNS * width) * CARD_COL_WIDTH/CARD_WIDTH)
        col_width = width * CARD_COL_WIDTH_RATIO
        hole_width = width * CARD_HOLE_WIDTH_RATIO
        #print col_width
        if self.debug_image:
            # mark left and right edges on the copy
            for y in range(int(probe_y - self.ysize / 100), int(probe_y + self.ysize / 100)):
                self.debug_pix[left_border if left_border > 0 else 0,y] = 255
                self.debug_pix[right_border if right_border < self.xmax else self.xmax - 1,y] = 255
            for x in range(1, (self.xmax - self.xmin) // 200):
                self.debug_pix[left_border + x, probe_y] = 255
                self.debug_pix[right_border - x, probe_y] = 255
                
        return data_left_x, data_right_x,  col_width, hole_width
 
    # find the top and bottom of the data area and from that the 
    # column and hole horizontal dimensions 
    def _find_data_vert_dimensions(self):
        top_border, bottom_border = self.ymin, self.ymax
        for y in range(self.ymin, self.midy):
            if not self._is_bright(self.pix[self.midx,  y]):
                top_border = y
                break
        for y in range(self.ymax - 1,  self.midy, -1):
            if not self._is_bright(self.pix[self.midx,  y]):
                bottom_border = y
                break
        card_height = bottom_border - top_border
        card_top_margin = int(card_height * CARD_TOP_MARGIN_RATIO)
        data_begins = top_border + card_top_margin
        hole_height = int(card_height * CARD_HOLE_HEIGHT_RATIO)
        data_top_y = data_begins + hole_height / 2
        row_height = int(card_height * CARD_ROW_HEIGHT_RATIO)
        if self.debug_image:
            # mark up the copy with the edges
            for x in range(self.xmin, self.xmax-1):
                self.debug_pix[x,top_border] = 255
                self.debug_pix[x,bottom_border] = 255
        if self.debug_image:
            # mark search parameters 
            for x in range(self.midx - self.xsize//20, self.midx + self.xsize//20):
               self.debug_pix[x,self.ymin] = 255
               self.debug_pix[x,self.ymax - 1] = 255
            for y in range(0, self.ymin):
               self.debug_pix[self.midx,y] = 255
            for y in range(self.ymax - 1, self.ysize-1):
               self.debug_pix[self.midx,y] = 255
        return data_top_y, data_top_y + row_height * 11, row_height, hole_height



    def _scan(self):
        self.trials = 1
        text_previous_trial = ''
        for self.threshold in range(self.brightest, self.dimmest - 1 if self.brightest == self.dimmest else self.dimmest, -3):
            holes_map = self._find_holes()
            self._decode_holes(holes_map)

            # stable value and no errors - assume this is good enough
            if self.invalid_char_count == 0 and self.text == text_previous_trial:
                if self.debug:
                    debug_print( "text:", self.text, "trial", self.trials, "invalid chars", self.invalid_char_count, "theshold", self.threshold, "STOP" )
                break
            elif self.debug:
                debug_print( "text:", self.text, "trial", self.trials, "invalid chars", self.invalid_char_count, "theshold", self.threshold, "RETRY" )

            text_previous_trial = self.text
            self.trials += 1
            
        if self.debug_image:
            self.debug_image.show()
            # prevent run-a-way debug shows causing my desktop to run out of memory
            input("Press Enter to continue...")

        return self

    def _find_holes(self):

        if self.debug_image:
            # if debugging make a copy we can draw on
            self.debug_image = self.image.copy()
            self.debug_pix = self.debug_image.load()
            # contrast = ImageEnhance.Contrast(self.debug_image)
            # contrast.enhance(2).show()

        y_data_pos, y_data_end, row_height, hole_height = self._find_data_vert_dimensions()
        # Creating a map of holes indexed by (col_number, row_number) value will be hold width
        holes_map = {}
        # Chads are narrow so find then heuristically by accumulating pixel brightness
        # along the row.  Should be forgiving if the image is slightly wonky.
        # Chads are tall so we can be sure if we probe around the middle of their height
        y = y_data_pos
        # Going to scan along each row looking for holes.
        for row_num in range(CARD_ROWS):
            # Line 0 has a corner missing
            # What's this about?
            probe_y = y + row_height if row_num == 0 else ( y - row_height if row_num == CARD_ROWS - 1 else y)
            x_data_left, x_data_right, col_width, hole_width = self._find_data_horiz_dimensions(probe_y)
            left_edge = -1  # of a punch-hole
            for x in range(x_data_left, x_data_right):
                if self._is_bright(self.pix[x, y]):
                    if left_edge == -1:
                        left_edge = x
                    if self.debug_image:
                        self.debug_pix[x, y] = self._flip(self.pix[x, y])
                else:
                    if left_edge > -1:
                        found_length = x - left_edge
                        if found_length >= hole_width * HOLE_WIDTH_THRESHOLD:
                            # Seems messy - fix later?
                            col_num = int((left_edge + found_length / 2.0 - x_data_left) / col_width + 0.25)
                            holes_map[(col_num, row_num)] = found_length
                        left_edge = -1
            if (self.debug_image):
                # Plot where holes might be on this row
                self._debug_plot_row_expected_holes(x_data_left, x_data_right, y, hole_width, hole_height, col_width)
            y += row_height
        return holes_map

    def _decode_holes(self, holes_map):
        self.invalid_char_count = 0
        self.decoded = []
        self.surface = []
        self.text = ''
        # Attempt to decode each column
        for col in range(0, CARD_COLUMNS):
            col_pattern = []
            col_surface = []
            # create a key of O (holes) and spaces (non-holes), for example (O, , ,O, , , , , , , , )
            for row in range(CARD_ROWS):
                col_row_key = (col, row)
                # Is there a hole at this col, row?
                col_pattern.append('O' if col_row_key in holes_map else ' ')
                col_surface.append(holes_map[col_row_key] if col_row_key in holes_map else 0)
            column_hole_patten = tuple(col_pattern)
            global translate
            # look up the pattern of holes in the translate table...
            if column_hole_patten in translate:
                # A translation exists - append it to the text result
                self.text += translate[column_hole_patten]
            else:
                # No translation - probably and error, append an @ for all errors.
                self.text += '@'
                self.invalid_char_count += 1
            self.decoded.append(column_hole_patten)
            self.surface.append(col_surface)

    def _debug_plot_row_expected_holes(self, left_x, right_x, y, hole_width, hole_height, col_width):
        expected_top_edge = y - hole_height / 2
        expected_bottom_edge = y + hole_height / 2
        blue = 255 * 256 * 256
        for expected_left_edge in drange(left_x, right_x - 1, col_width):
            for y_plot in drange(expected_top_edge, expected_bottom_edge, 2):
                self.debug_pix[expected_left_edge,y_plot] = blue
                self.debug_pix[expected_left_edge + hole_width,y_plot] = blue
            for x_plot in drange(expected_left_edge, expected_left_edge + hole_width):
                self.debug_pix[x_plot, expected_top_edge] = blue
                self.debug_pix[x_plot, expected_bottom_edge] = blue

    # ASCII art image of card
    def dump(self, id, raw_data=False):
        debug_print(' Card Dump of Image file:', id, 'Format', 'Raw' if raw_data else 'Dump', 'threshold=', self.threshold, 'trials=', self.trials)
        debug_print(' ' + '123456789-' * (CARD_COLUMNS//10))
        debug_print(' ' + '_' * CARD_COLUMNS + ' ')
        debug_print('/' + self.text +  '_' * (CARD_COLUMNS - len(self.text)) + '|')
        for rnum in range(len(self.decoded[0])):
            debug_write('|')
            if raw_data:
                for val in self.surface:
                    debug_write(("(%d)" % val[rnum]) if val[rnum] != 0 else '.' )
            else:
                for col in self.decoded:
                    debug_write(col[rnum] if col[rnum] == 'O' else '.')
            debug_print('|')
        debug_print('`' + '-' * CARD_COLUMNS + "'")
        debug_print(' ' + '123456789-' * (CARD_COLUMNS//10))
        debug_print('')
         
            
if __name__ == '__main__':
    
    usage = """usage: %prog [options] image [image...]
    decode punch card image into ASCII."""
    parser = OptionParser(usage)
    parser.add_option('-b', '--bright-threshold', type='int', dest='bright', default=BRIGHTNESS_PRACTICAL_MAX, help='Brightness white/grey cutoff, e.g. 127.')
    parser.add_option('-B', '--bright-dimmest', type='int', dest='dimmest', default=BRIGHTNESS_PRACTICAL_MIN, help='Lowest brightness to try, e.g. 127.')
    # Obsolete?
    #parser.add_option('-s', '--side-margin-ratio', type='float', dest='side_margin_ratio', default=CARD_SIDE_MARGIN_RATIO, help='Manually set side margin ratio (sideMargin/cardWidth).')
    parser.add_option('-d', '--dump', action='store_true', dest='dump', help='Output an ASCII-art version of the card.')
    parser.add_option('-D', '--debug', action='store_true', dest='debug', help='Output debugging.')
    parser.add_option('-w', '--white', action='store_true', dest='preferwhite', help='Holes should be white/grey, not just bright.')
    parser.add_option('-i', '--debug-image', action='store_true', dest='debugimage', help='Popup anotated debugging jpeg using PIL jpeg viewer.')
    parser.add_option('-r', '--dump-raw', action='store_true', dest='dumpraw', help='Output ASCII-art with raw row/column accumulator values.')
    parser.add_option('-x', '--x-start', type='int', dest='xstart', default=0, help='Start looking for a card edge at y position (pixels)')
    parser.add_option('-X', '--x-stop', type='int', dest='xstop', default=0, help='Stop looking for a card edge at y position')
    parser.add_option('-y', '--y-start', type='int', dest='ystart', default=0, help='Start looking for a card edge at y position')
    parser.add_option('-Y', '--y-stop', type='int', dest='ystop', default=0, help='Stop looking for a card edge at y position')
    parser.add_option('-a', '--adjust-x', type='int', dest='xadjust', default=0, help='Adjust middle edge detect location (pixels)')
    parser.add_option('-n', '--num-cards', type='int', dest='ncards', default=1, help='Number of cards in each image')
    (options, args) = parser.parse_args()

    if options.bright < options.dimmest:
        debug_print("ERROR: -b value ", options.bright,  "< -B value", options.dimmest)

    for arg in args:
        image = Image.open(arg)
        #print(image.size)
        y_step = ((options.ystop - options.ystart) if options.ystop > 0 else (image.size[1] - options.ystart)) // options.ncards
        #print(y_step)
        for i in range(0, options.ncards):
            ystart = options.ystart + i * y_step
            ystop = options.ystart + (i + 1) * y_step
            card = PunchCard(image,  
                             bright=options.bright,
                             dimmest=options.dimmest,
                             prefer_white=options.preferwhite,
                             display=options.debugimage, 
                             debug=options.debug, 
                             xstart=options.xstart, 
                             xstop=options.xstop, 
                             ystart=ystart, 
                             ystop=ystop, 
                             xadjust=options.xadjust)
            print(card.text, '' if card.invalid_char_count == 0 else '** invalid char count = ' + str(card.invalid_char_count))
            if (options.dump):
                card.dump(arg)
            if (options.dumpraw):
                card.dump(arg, raw_data=True)

