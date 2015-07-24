#!/usr/bin/env python
# encoding: utf-8

from cairo import Context, ImageSurface, SurfacePattern, FILTER_BEST, Matrix, LINE_CAP_SQUARE, FORMAT_ARGB32
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo
from subprocess import call
from math import pi

###########################################################################
#                                 Helpers                                 #
###########################################################################


ARROW_DEPTH = 7


def create_dummy_context():
    return Context(ImageSurface(FORMAT_ARGB32, 5000, 100))


def parse_color(color):
    color = color.lower()
    if color.startswith('#'):
        color = color[1:]

    if len(color) == 3:
        return [int(c, 16) / 255.0 for c in color]
    elif len(color) == 6:
        return [int(c, 16) / 255.0 for c in [color[:2], color[2:4], color[4:]]]
    else:
        return (0, 0, 0)


def draw_arrow_panel(ctx, color, border_color, width, height, alpha=1.0):
    ctx.set_line_width(1)

    ctx.move_to(-ARROW_DEPTH, 0)
    ctx.line_to(width, 0)
    ctx.line_to(width + ARROW_DEPTH, height / 2)
    ctx.line_to(width, height)
    ctx.line_to(-ARROW_DEPTH, height)
    ctx.line_to(0, height / 2)
    ctx.line_to(-ARROW_DEPTH, 0)

    r, g, b = color
    ctx.set_source_rgba(r, g, b, alpha)
    ctx.fill_preserve()
    r, g, b = border_color
    ctx.set_source_rgba(r, g, b, alpha)
    ctx.stroke()


###########################################################################
#                              Node Widgets                               #
###########################################################################

class Widget:
    def bounding_box(self):
        return 0, 0

    def render(self, ctx):
        raise NotImplementedError('Subclasses should implement render()')


class Bar(Widget):
    def __init__(self, w=100, h=10, percent=0.5, lw=2, defined=True, fg=(1, 0.5, 0), bg=(0.2, 0.1, 0.1)):
        self._w, self._h, self._percent, = w, h, percent
        self._lw, self._defined, self._fg, self._bg = lw, defined, fg, bg

    def bounding_box(self):
        # Add a small border left / right
        return self._w + ARROW_DEPTH, self._h

    def render(self, ctx, w, h):
        # Precalculate often used values
        thickness = (self._lw + 2) / 2
        radius = self._h / 2 - thickness
        mid = thickness + radius
        midx2 = mid * 2
        length = self._w - midx2
        pid2 = pi / 2

        # Configure the context
        ctx.save()
        ctx.set_line_cap(LINE_CAP_SQUARE)
        ctx.set_source_rgb(*self._fg)
        ctx.set_line_width(self._lw)

        # Left Rounded Corner
        ctx.move_to(mid, mid)
        ctx.arc_negative(mid, mid, radius, -pid2, pid2)
        ctx.line_to(mid + length, midx2 - thickness)

        # Right Rounded Corner
        ctx.arc_negative(mid + length, mid, radius, pid2, -pid2)
        ctx.line_to(mid, thickness)

        # If we shall draw the full thing: paint a colored rectangle and clip
        # it in. Otherwise, we just use the clip mask and draw it.
        if self._defined is True:
            ctx.clip()
            ctx.paint()
        else:
            ctx.stroke_preserve()
            ctx.set_source_rgb(*self._bg)
            ctx.fill()

        if self._defined is True:
            position = self._percent * w
            for col, x, y, w, h in [
                    (self._fg, 0, 0, position, h),
                    (self._bg, position, 0, w - position, h)
            ]:
                ctx.set_source_rgb(*col)
                ctx.rectangle(x, y, w, h)
                ctx.fill()
            ctx.stroke()
        ctx.restore()


class Text(Widget):
    def __init__(self, markup='', font_descr='Ubuntu Mono', color=(1, 1, 1), font_size=10):
        self._markup, self._font_descr, self._color, self._font_size = markup, font_descr, color, font_size
        self._cached_bounding_box = None

    def _create_layout(self, ctx):
        layout = PangoCairo.create_layout(ctx)
        font = Pango.FontDescription.from_string(self._font_descr)
        font.set_size(self._font_size * Pango.SCALE)
        layout.set_font_description(font)
        layout.set_markup(self._markup, -1)
        return layout

    def bounding_box(self):
        if self._cached_bounding_box is None:
            dummy_ctx = create_dummy_context()
            w, h = self._create_layout(dummy_ctx).get_size()
            self._cached_bounding_box = w / Pango.SCALE, h / Pango.SCALE
        return self._cached_bounding_box

    def render(self, ctx, w, h):
        ctx.set_source_rgb(*self._color)
        PangoCairo.show_layout(ctx, self._create_layout(ctx))


class Desktops(Text):
    def __init__(self, font_descr='Ubuntu Mono', desktops='1234567890', selected=0, urgents=[], empties=[], command='bspc desktop {num} -f'):
        self._font_descr = font_descr
        self._command = command
        self._text_widgets = []
        for idx, desktop in enumerate(desktops):
            markup = desktop
            if idx == selected:
                markup = '<big><u>' + markup + '</u></big>'
                color = (0, 0, 0)
            elif idx in urgents:
                color = (0.8, 0.4, 0.4)
            elif idx in empties:
                color = (0.6, 0.7, 0.6)
            else:
                color = (0.3, 0.4, 0.3)
            self._text_widgets.append(Text(markup=markup, color=color))

    def bounding_box(self):
        sum_w = 0
        max_h = 0
        for widget in self._text_widgets:
            w, h = widget.bounding_box()
            sum_w += w
            max_h = max(max_h, h)
        return sum_w, max_h

    def render(self, ctx, w, h):
        ctx.save()
        for idx, widget in enumerate(self._text_widgets):
            ww, wh = widget.bounding_box()
            widget.render(ctx, w, h)
            ctx.translate(ww, 0)
        ctx.restore()

    def handle_click(self, x):
        sum_w = 0
        for idx, widget in enumerate(self._text_widgets):
            ww, wh = widget.bounding_box()
            sum_w += ww
            if x <= sum_w:
                if '{num}' in self._command:
                    command = self._command.format(num=idx)
                else:
                    command = self._command
                try:
                    call(command, shell=True)
                except OSError as err:
                    print(err)
                finally:
                    break


class Icon(Widget):
    def __init__(self, w=10, h=10, path=''):
        self._w, self._h = w, h
        surface = ImageSurface.create_from_png(path)
        self._imgpat = SurfacePattern(surface)
        self._imgpat.set_filter(FILTER_BEST)
        scaler = Matrix()
        scaler.scale(surface.get_width() / w, surface.get_height() / h)
        self._imgpat.set_matrix(scaler)

    def bounding_box(self):
        return self._w + 2, self._h

    def render(self, ctx, w, h):
        ctx.set_source(self._imgpat)
        ctx.paint()


class Separator(Widget):
    def __init__(self, w=10, color=(0.9, 0.9, 0.9), border_color=(0.2, 0.2, 0.2), alpha=1.0, align=0.0):
        self._w, self._color, self._border_color, self._align, self._alpha = w, color, border_color, align, alpha

    def bounding_box(self):
        return self._w + 2 * ARROW_DEPTH, -1

    def render(self, ctx, w, h):
        ctx.save()
        ctx.translate(self._align * w - self._align * self._w, 0)
        draw_arrow_panel(ctx, self._color, self._border_color, self._w - ARROW_DEPTH, h, alpha=self._alpha)
        ctx.restore()


###########################################################################
#                            Container Widgets                            #
###########################################################################

class Container(Widget):
    def __init__(self, pos=0.0, padding=(0, 0), widgets=[]):
        self._pos, self._padding, self._widgets = pos, padding, widgets

    def get_pos(self):
        return self._pos

    def bounding_box(self):
        sum_w = 0
        for widget in self._widgets:
            w, h = widget.bounding_box()
            sum_w += w
        return sum_w + sum(self._padding), -1

    def frag(self, x):
        sum_w = 0
        for widget in self._widgets:
            w, _ = widget.bounding_box()
            sum_w += w
            if x <= sum_w:
                if hasattr(widget, 'handle_click'):
                    widget.handle_click(x - (sum_w - w))
                break

    def render(self, ctx, w, h):
        ctx.save()
        ctx.translate(self._padding[0], 0)
        try:
            for widget in self._widgets:
                ww, wh = widget.bounding_box()
                if wh < 0:
                    wh = h
                ctx.save()
                ctx.translate(2, h / 2 - wh / 2)
                widget.render(ctx, ww, wh)
                ctx.restore()
                ctx.translate(ww, 0)
        finally:
            ctx.restore()


class ArrowBox(Container):
    def __init__(self, pos=0.0, padding=(0, 0), widgets=[], color=(0.4, 0.4, 0.4), border_color=(0, 0, 0)):
        Container.__init__(self, pos=pos, widgets=widgets, padding=padding)
        self._color, self._border_color = color, border_color

    def bounding_box(self):
        w, h = Container.bounding_box(self)
        return w, h

    def render(self, ctx, w, h):
        # Draw Background
        draw_arrow_panel(ctx, self._color, self._border_color, w, h)

        # Draw widgets on top
        Container.render(self, ctx, w, h)


###########################################################################
#                                Layouting                                #
###########################################################################


def render_container_list(ctx, containers, abs_width, abs_height):
    for container in containers:
        pos = container.get_pos()
        cnw, cnh = container.bounding_box()

        # Just use the full height if no preferences are requested
        if cnh < 0:
            cnh = abs_height

        position = pos * abs_width - pos * cnw
        ctx.save()
        ctx.translate(position, 0)
        ctx.rectangle(-ARROW_DEPTH, -ARROW_DEPTH, cnw + 2 * ARROW_DEPTH, cnh + 2 * ARROW_DEPTH)
        ctx.clip()
        container.render(ctx, cnw, cnh)
        ctx.restore()


class ElchBar(Gtk.Window):
    def __init__(self, defaults, file_object):
        Gtk.Window.__init__(self)

        self._defaults = defaults
        self._containers = []

        self._canvas = Gtk.DrawingArea()
        self._canvas.set_size_request(1024, defaults.get('height', 20))

        # Enable the receival of the appropiate signals:
        self._canvas.add_events(self.get_events() |
                Gdk.EventMask.BUTTON_PRESS_MASK |
                Gdk.EventMask.BUTTON_RELEASE_MASK |
                Gdk.EventMask.POINTER_MOTION_MASK |
                Gdk.EventMask.SCROLL_MASK
        )
        self._canvas.connect('button-press-event', self._on_button_press_event)

        self.add(self._canvas)

        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)

        self.connect('destroy', Gtk.main_quit)
        self._canvas.connect('draw', self._on_draw)
        GLib.IOChannel(file_object.fileno()).add_watch(
                GLib.IOCondition.IN |
                GLib.IOCondition.HUP |
                GLib.IOCondition.PRI |
                GLib.IOCondition.ERR,
                self._on_stdin_input
        )
        self.show_all()

    def push(self, containers):
        self._containers = containers
        self._canvas.queue_draw()

    def _on_button_press_event(self, widget, event):
        alloc = widget.get_allocation()
        for container in self._containers:
            pos = container.get_pos()
            cnw, _ = container.bounding_box()
            start_pos = pos * alloc.width - pos * cnw
            end_pos = start_pos + cnw

            if start_pos < event.x < end_pos:
                container.frag(event.x - start_pos)

        return True

    def _on_draw(self, canvas, ctx):
        ctx.set_source_rgb(*(self._defaults.get('bg_color') or (0.23, 0.23, 0.23)))
        ctx.paint()

        alloc = canvas.get_allocation()

        render_container_list(
                ctx, self._containers, alloc.width, alloc.height
        )

    def _load_line(self, line):
        allowed = [Widget, Bar, Text, Icon, Desktops, Separator, Container, ArrowBox, parse_color]
        try:
            containers = eval(line, {k.__name__: k for k in allowed})
        except Exception as err:
            print(line)
            print('-> Unable to execute:', err)
        else:
            self.push(containers)

    def _quit(self):
        Gtk.main_quit()

    def _on_stdin_input(self, source, condition):
        keep_watch = True
        if condition & GLib.IOCondition.IN:
            status, line, _, _ = source.read_line()
            if status is GLib.IOStatus.NORMAL:
                self._load_line(line)
            elif status is GLib.IOStatus.EOF or not line:
                keep_watch = False
                print('-- Got EOF, Quit --')
                self._quit()
            else:
                print('-- Error while reading from stdin --')
        elif condition & GLib.IOCondition.HUP:
            print('-- Hanged up --')
            self._quit()
        return keep_watch


###########################################################################
#                 Really crappy main for testing purpose                  #
###########################################################################

if __name__ == '__main__':
    import sys
    defaults = {
        'bg_color': (0.23, 0.23, 0.23),
        'height': 20
    }

    if len(sys.argv) < 2:
        print('Usage: par.py fifo-path')
    else:
        try:
            with open(sys.argv[1], 'r') as f:
                bar = ElchBar(defaults, f)
                Gtk.main()
        except KeyboardInterrupt:
            print('Ctrl-C')
