# punchedcardreader
IBM Punched Card reader - extract text from images of cards

The punchedCardReader python script attempts to scan images of IBM 80 column punch cards extracting any recognisable text.

An older version of this script is described at [http://codeincluded.blogspot.com/2012/07/punchcard-reader-software.html](http://codeincluded.blogspot.com/2012/07/punchcard-reader-software.html).  The version deposited here is a more recent refactoring of the original that includes several tidy ups and a few new features.

(Link to the [bonus javascript card punch](https://digitaltrails.github.io/punchedcardreader/js-cardpunch.html) - punch yourself a tshirt)

# Usage

```
Usage: punchedCardReader.py [options] image [image...]
    decode punch card image into ASCII.

Options:
  -h, --help            show this help message and exit
  -b BRIGHT, --bright-threshold=BRIGHT
                        Brightness white/grey cutoff, e.g. 127.
  -B DIMMEST, --bright-dimmest=DIMMEST
                        Lowest brightness to try, e.g. 127.
  -d, --dump            Output an ASCII-art version of the card.
  -D, --debug           Output debugging.
  -w, --white           Holes should be white/grey, not just bright.
  -i, --debug-image     Popup anotated debugging jpeg using PIL jpeg viewer.
  -r, --dump-raw        Output ASCII-art with raw row/column accumulator
                        values.
  -x XSTART, --x-start=XSTART
                        Start looking for a card edge at y position (pixels)
  -X XSTOP, --x-stop=XSTOP
                        Stop looking for a card edge at y position
  -y YSTART, --y-start=YSTART
                        Start looking for a card edge at y position
  -Y YSTOP, --y-stop=YSTOP
                        Stop looking for a card edge at y position
  -a XADJUST, --adjust-x=XADJUST
                        Adjust middle edge detect location (pixels)
  -n NCARDS, --num-cards=NCARDS
                        Number of cards in each image
```

The scripts start/stop parameters are in number of pixels with 0,0 being at top left.  The --adjust parameter allows the position at which to start looking for the top and bottom edge to be offset from the left edge of the card (in case some portion of the top/bottom edges are obscured by card transport hardware).

The script will attempt to automatically determine the value for the --bright-threshold parameter.  It does this by repeatedly scanning the card until two successive scans are in agreement and are free of invalid characters.  If you have determined good fixed brightness thresholds, the number of repeat scans can be reduced to 1 by supplying the same value for --bright-threshold and --bright-dimmest.  

Trial results listed by --debug option can be used to assist with selecting a fixed brightness threshold.

The --dump parameter products a debug ASCII art rendition of each scanned card.

The --debug-image parameter causes the script to annotate and display each image scanned with a "press enter to continue" required for each card scanned.

The --num-cards parameter allows n vertically and evenly spaced cards to be included in each image (a new/experimental option).

The program outputs the text scanned to the standard output and all debugging is written to the standard error stream. 

Here is a typical example of the scripts use with the debugging options --debug and --dump:

```
~/> python3 punchedCardReader.py -a 50 -x 50 -X 2500 -y 750 -Y 1890  --debug --dump  img_1940.jpg

text:            2 ZJG01           4ONV&3&HA@06NN&3NFC0                                trial 1 invalid chars 1 theshold 250 RETRY
text:            S-@X 1            MOVE C&@-@ ONE LEFT                                 trial 2 invalid chars 3 theshold 247 RETRY
text:            SRAX 1            MOVE CHARS ONE LEFT                                 trial 3 invalid chars 0 theshold 244 RETRY
text:            SRAX 1            MOVE CHARS ONE LEFT                                 trial 4 invalid chars 0 theshold 241 STOP
           SRAX 1            MOVE CHARS ONE LEFT                                 
 Card Dump of Image file: /home/michael/Projects/PunchCardReader/work-src/mix1/img_1940.jpg Format Dump threshold= 241 trials= 4
 123456789-123456789-123456789-123456789-123456789-123456789-123456789-123456789-
 ________________________________________________________________________________ 
/           SRAX 1            MOVE CHARS ONE LEFT                                |
|.............O..................O.OOO.....O..OO.................................|
|............O................OO......O..OO..O...................................|
|...........O..O................O......O........O................................|
|.............O..O...................O...........................................|
|...........O..........................O.........................................|
|..................................O.........O..O................................|
|.............................O..................................................|
|...............................OO........OO..O..................................|
|..............................O.........O.....O.................................|
|..............O.................................................................|
|...................................O............................................|
|............O........................O..........................................|
`--------------------------------------------------------------------------------'
 123456789-123456789-123456789-123456789-123456789-123456789-123456789-123456789-

```

