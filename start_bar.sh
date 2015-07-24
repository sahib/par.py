#!/bin/sh

cd ~/dev/par.py


PAR_FIFO='/tmp/bspwm.fifo'

if [ -e "$PAR_FIFO" ] 
then 
    rm "$PAR_FIFO"
fi

mkfifo "$PAR_FIFO"

pkill -f par.py
pkill -f par_writer.py

# Start the scripts
(python par.py "$PAR_FIFO") &
(python -u par_writer.py > "$PAR_FIFO") & 

killall stalonetray
(sleep 5 && stalonetray --geometry 4x1-1281+1 --icon-gravity E --grow-gravity E -bg "#e08787" -i 18 -d all) &
