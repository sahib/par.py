Cute little bar for Linux written in Python
===========================================

One can debate if it's useful for others. But here's the code anywhere.


**Screenshot:**

.. image:: http://github.com/sahib/par.py/raw/screenshot.png

**Full Screenshot (in bspwm):**

.. image:: http://i.imgur.com/ExoS5xG.png


Dependencies
------------

Arch-Package name in (**Paranthesis**), Purpose in [*Brackets*].

    - Gtk [*Window for the Bar*] (**extra/gtk3**)
    - Cairo [*Drawing all the stuff*] (**extra/cairo**)
    - Pango [*Providing perfect Font Rendering*] (**extra/pango**)
    - Python [*Language used*] (**extra/python**)
    - pygobject [*GObject Bindings for Python*] (**extra/python-gobject**)
    - Optional stalonetray


One could argue it's not that lightweight, but hey, it updates only once in a
second here, or on any external event. 

Most people will have those dependencies installed anyway. 

Design
------

There are two Python scripts:

- ``par.py``: Render and place the Bar. 
- ``par_writer.py``: Provide the information to render. You edit this script.

At top of ``par_writer.py`` you'll find a large string with placeholders.
This template will be filled and printed to stdout every second or on any new input. 

``par.py`` wil read from the path you pass as first argument. This is in my
setup a FIFO previously created with ``mkfifo`` at ``/tmp/par-fifo``. 
``par_writer.py`` can now print it's output in this:

.. code-block:: bash

    $ mkfifo /tmp/par-fifo
    $ python par.py /tmp/par-fifo & 
    $ python bar_writer.py > /tmp/par-fifo

Example startup script
----------------------

.. code-block:: bash

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

Bugs
----

Lots of. This was written for my own usage, but I was asked for the setup,
not all properties are configurable. Like the placement of the panel. I'd have
e.g. no idea how to place it at the bottom.

**Known:**

- After startup no desktops are rendered (only `???`)
- MPD status will not appear until first client-event. (just )
- Desktops will only work with bspwm and only if the FIFO is named
  ``/tmp/panel-fifo``. Did I mention it is a little hacky? :-)
- Desktop names are even clickable, but won't work very nicely currently. 


Some of those will be fixed once I feel annoyed enough to do so.
Just relax with some tea in the meantime. :-)
