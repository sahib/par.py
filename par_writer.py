#!/usr/bin/env python
# encoding: utf-8

BAR_TEMPLATE = '''
[
    ArrowBox(
        pos=0.0,
        widgets=[
            Text(markup='<big> ⌽</big>', color=(0.1, 0.1, 0.1)),
            Separator(align=0.7, alpha=0.2),
            Desktops(desktops={desktop_names}, selected={desktop_active_num}, urgents={desktop_urgent}),
            Separator(align=0.5, alpha=0.2)
        ],
        color=parse_color('#a1cd4c'),
        border_color=(0.1, 0.1, 0.1)
    ),
    ArrowBox(
        pos=0.5,
        widgets=[
            Text(markup='<big> ♬</big>'),
            Separator(align=0.9, alpha=0.2),
            Text(markup={music_markup}),
            Bar(percent={music_percent}, defined={music_unstopped}),
            Separator(align=0.5, alpha=0.2),
        ],
        color=parse_color('#4282be'),
        border_color=(0.1, 0.1, 0.1)
    ),
    ArrowBox(
        pos=1.0,
        padding=(2, 75),
        widgets=[
            Icon(w=16, h=16, path='/home/sahib/.icons/clock.png'),
            Separator(align=0.5, alpha=0.2),
            Text(markup={time_string}, color=(1, 1, 1)),
            Text(markup={date_string}, color=(1, 1, 1))
        ],
        color=parse_color('#e08787'),
        border_color=(0.1, 0.1, 0.1)
    )
]
'''

from gi.repository import GLib
from telnetlib import Telnet
from select import select
from time import strftime, time


###########################################################################
#                            Helper Functions                             #
###########################################################################

def format_time_string():
    return strftime('<b><big>%H:%M</big>:%S</b>')


def format_date_string():
    return strftime(' <small>%A, %e. %B</small>')


def format_time_box():
    return {
        'time_string': repr(format_time_string()),
        'date_string': repr(format_date_string())
    }


def format_output_dict(info_dict):
    output_lines = []
    for line in BAR_TEMPLATE.format(**info_dict).splitlines():
        output_lines.append(line.strip())
    return ''.join(output_lines)


###########################################################################
#            Real Sources depending on external Sockets/FIFOs             #
###########################################################################


class MPDSource():
    def __init__(self, host='localhost', port=6600):
        self._host, self._port = host, port
        self._conn = None
        self._last_elapsed = 0
        self._last_tottime = 0
        self._last_time = time()
        self._is_playing = False

    def _wait(self):
        self._conn.write(b'idle\n')

    def _make_dict(self, blob):
        result = {}
        for line in (blob or '').splitlines():
            if ':' in line:
                key, value = [s.strip() for s in line.split(':', maxsplit=1)]
                result[key] = value
        return result

    def _read_response(self):
        return self._conn.read_until(b'OK\n')

    def connect(self):
        try:
            self._conn = Telnet(host=self._host, port=self._port)
        except socket.error as err:
            print(err)
        else:
            # Read the OK MPD 0.17.0 line
            self._conn.read_until(b'\n')

            # Put ourself to event-looping mode
            self._wait()

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _process_info(self, info):
        self._is_playing = unstopped = info['state'] in ['play', 'pause']
        if unstopped:
            markup = '<i> {title}<small> by </small>{artist}<small> on </small>{album} </i>'.format(
                title=GLib.markup_escape_text(info['Title']),
                artist=GLib.markup_escape_text(info['Artist']),
                album=GLib.markup_escape_text(info['Album'])
            )
            self._last_elapsed = float(info['elapsed'])
            self._last_tottime = float(info['Time'])
            percent =  self._last_elapsed / self._last_tottime
            self._last_time = time()
        else:
            markup = '<i> (( not playing )) </i>'

        return {
                'music_markup': repr(markup),
                'music_percent': percent,
                'music_unstopped': unstopped
        }

    def _guess_elapsed_from_time(self):
        if self._is_playing:
            diff = time() - self._last_time
            return {
                'music_percent': (self._last_elapsed + diff) / self._last_tottime
            }
        else:
            return {}

    def read(self, has_input):
        info = {}
        if has_input:
            events = self._read_response()
            if b'player' in events:
                self._conn.write(b'command_list_begin\nstatus\ncurrentsong\ncommand_list_end\n')
                blob = self._read_response()
                raw_info = self._make_dict(blob.decode('utf-8'))
                info = self._process_info(raw_info)
            self._wait()
        else:
            info = self._guess_elapsed_from_time()
        return info

    def fileno(self):
        return  self._conn.fileno() if self._conn else - 1


#######################################################
#  Read from panel-fifo and read desktop information  #
#######################################################

class BspwmPanelFIFO:
    def __init__(self):
        self._fifo = None

    def _read_last(self):
        last_line = None
        while self._fifo in select([self._fifo], [], [], 0)[0]:
            last_line = self._fifo.readline()
        return last_line

    def connect(self):
        self._fifo = open('/tmp/panel-fifo', 'r')

    def disconnect(self):
        if self._fifo:
            self._fifo.close()
            self._fifo = None

    def _process_line(self, line):
        # Split monitor:d1:d9:tstate in pieces
        monitor, *desks, _ = line.split(':')

        # Result Storage
        active, urgent, names = 0, [], []
        for idx, desk in enumerate(desks):
            # Split [a-Z][0-9] in half
            state, *name = desk
            names.append(''.join(name))
            if state in 'DU':
                # Active (or Urgent) Desktop
                active = idx
            if state.lower() == 'u':
                # An urgent desktop
                urgent.append(idx)

        return {
            'desktop_names': names,
            'desktop_active_num': active,
            'desktop_urgent': urgent
        }

    def read(self, has_input):
        if has_input:
            line = self._read_last()
            if line:
                return self._process_line(line)
        return {}

    def fileno(self):
        return self._fifo.fileno()


###########################################################################
#                              Main Control                               #
###########################################################################

def poll_on_sources(sources, info, timeout=1.0):
    for source in sources:
        readable, _, errord = select(sources, [], sources, timeout)
        for source in sources:
            if not source in errord:
                partial_info = source.read(has_input=(source in readable))
                info.update(partial_info)
            else:
                error_source.disconnect()
                error_source.connect()

        info.update(format_time_box())
        print(format_output_dict(info))


if __name__ == '__main__':
    # All available keys
    info = {
            'desktop_names': repr('???'),
            'desktop_active_num': 0,
            'desktop_urgent': [],
            'music_markup': repr('<i> (( undefined )) </i>'),
            'music_percent': 0,
            'music_unstopped': False,
            'time_string': repr(format_time_string()),
            'date_string': repr(format_date_string())
    }

    print(format_output_dict(info))

    sources = [MPDSource(), BspwmPanelFIFO()]
    for source in sources:
        source.connect()

    try:
        while True:
            poll_on_sources(sources, info)
    except KeyboardInterrupt:
        print('Ctrl-C')

    for source in sources:
        source.disconnect()
