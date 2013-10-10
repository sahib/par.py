#!/bin/sh
BAR_FIFO='/tmp/par-fifo'

if [ -e "$BAR_FIFO" ] 
then 
    rm "$BAR_FIFO"
fi

mkfifo "$BAR_FIFO"

# Start the scripts
(python par.py "$BAR_FIFO") &
(python -u par_writer.py > "$BAR_FIFO") & 

# Fill initial desktop configuration
bspc control --put-status

killall stalonetray
(sleep 2 && stalonetray --geometry 4x1-1+1 --icon-gravity E --grow-gravity E -bg "#e08787" -i 18 -d all) &
