#!/bin/sh
BSP_FIFO='/tmp/par.fifo'
PAR_FIFO='/tmp/bspwm.fifo'

if [ -e "$PAR_FIFO" ] 
then 
    rm "$PAR_FIFO"
fi

mkfifo "$PAR_FIFO"

if [ -e "$BSP_FIFO" ] 
then 
    rm "$BSP_FIFO"
fi

mkfifo "$BSP_FIFO"

pkill -f par.py
pkill -f par_writer.py

# Start the scripts
(bspc control --subscribe > "$BSP_FIFO") &
(python par.py "$PAR_FIFO") &
(python -u par_writer.py > "$PAR_FIFO") & 

killall stalonetray
(sleep 2 && stalonetray --geometry 4x1-1+1 --icon-gravity E --grow-gravity E -bg "#e08787" -i 18 -d all) &
