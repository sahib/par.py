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

# FIXME: Silly work-around for not updating on start-up
mpc random on 2&>1 > /dev/null
mpc random off 2&>1 > /dev/null
