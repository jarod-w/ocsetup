#!/usr/bin/env python
# encoding=utf-8
# Copyright (C) 2012 Sunus Lee, CT
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#


import gtk
import vte
from ocsetup_ui_constants import OC_SELECTED_BTN_BG, OC_SELECTED_TAB_BG,\
                            OC_LOG_PAGE_BG, OC_INIT_BTN_BG,\
                            OC_BUTTON_LIST_HEIGHT, OC_COLOR_BUTTON_HEIGHT,\
                            OC_LOG_WIN_WIDTH, OC_LOG_WIN_HEIGHT,\
                            OC_DETAILED_LIST_HEIGHT, GTK_SIGNAL_KEY_PRESS, GTK_SIGNAL_CHILD_EXIT, GTK_SIGNAL_CLICKED
import datautil

class ColorWidget(gtk.EventBox):

    def __init__(self, GtkWidget, *args, **kwargs):
        super(ColorWidget, self).__init__()
        self.color_widget = getattr(gtk, GtkWidget)(*args)
        self.add(self.color_widget)
        self.init_color = kwargs.get('init_color', None)
        label = kwargs.get('label', "")
        signals_to_handle = kwargs.get('signals_to_handle', [])
        if self.init_color is not None:
            self.change_color('bg', gtk.STATE_NORMAL, self.init_color)
        for signal in signals_to_handle:
            self.color_widget.connect(signal,
                    getattr(self, signal.replace('-', '_').lower() + '_cb'))
        if label:
            self.color_widget.set_label(label)

    def change_color(self, category, state, color):
        _color = gtk.gdk.Color(color)
        modifier = "modify_%s" % category
        if isinstance(self.color_widget, gtk.Label):
            getattr(self, modifier)(state, _color)
        else:
            getattr(self.color_widget, modifier)(state, _color)

class EmptyArea(gtk.Label):

    def __init__(self, width, height):
        super(EmptyArea, self).__init__()
        self.set_size_request(width, height)

class ColorLabel(ColorWidget):

    def __init__(self, label, color):
        super(ColorLabel, self).__init__('Label', label=label, init_color=color)


class ColorButton(ColorWidget):

    def __init__(self, label, init_btn_bg=OC_INIT_BTN_BG,
                signals_to_handle=["focus-in-event", "focus-out-event",
                                    "state-changed"]):
        super(ColorButton, self).__init__('Button', label=label,
                                         init_color=OC_INIT_BTN_BG,
                                         signals_to_handle=signals_to_handle)

    def focus_in_event_cb(self, widget, event):
        self.change_color('bg', gtk.STATE_NORMAL, OC_SELECTED_BTN_BG)

    def focus_out_event_cb(self, widget, event):
        self.change_color('bg', gtk.STATE_NORMAL, OC_INIT_BTN_BG)

    def state_changed_cb(self, widget, state):
        if state == gtk.STATE_PRELIGHT:
            self.change_color('bg', gtk.STATE_PRELIGHT, OC_SELECTED_BTN_BG)


class ColorNotebookTab(ColorWidget):

    def __init__(self, label, init_btn_bg=OC_SELECTED_TAB_BG,
                signals_to_handle=[]):
        super(ColorNotebookTab, self).__init__('Label', label=label,
                                        init_color=OC_SELECTED_TAB_BG,
                                        signals_to_handle=signals_to_handle)
        self.show_all()

    def get_label(self):
        return self.color_widget.get_label()

class ColorVBox(ColorWidget):

    def __init__(self, init_color, *args):
        super(ColorVBox, self).__init__('VBox', init_color=init_color, *args)
        self.set_border_width(0)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(init_color))

class ButtonList(gtk.HButtonBox):

    def __init__(self, data):
        super(ButtonList, self).__init__()
        labels = data['labels']
        btn_nr = len(labels)
        callbacks = data.get('callback', [lambda _:_]*btn_nr)
        signal = data.get('signal', 'clicked')
        btn_type = data.get('type', 'Button')
        self.set_layout(gtk.BUTTONBOX_END)
        for t, cb in zip(labels, callbacks):
            btn = getattr(gtk, btn_type)(t)
            btn.connect(signal, cb)
            self.pack_start(btn, False, False, padding=5)
        self.set_size_request(-1, OC_BUTTON_LIST_HEIGHT)

class ApplyResetBtn(ButtonList):

    def __init__(self):
        super(ApplyResetBtn, self).__init__({'labels':
                                            ['Apply', 'Reset'],
                                            'callback':
                                            [datautil.conf_apply,
                                            lambda _:_]
                                            })

class DetailedList(gtk.ScrolledWindow):

    def __init__(self, data):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        labels = data['labels']
        liststore = gtk.ListStore(*([str] * len(labels)))
        self.treeview = gtk.TreeView(liststore)
        for idx, label in enumerate(labels):
            self.treeview.insert_column_with_attributes(-1,
                label, gtk.CellRendererText(), text=idx)
        self.add(self.treeview)
        self._liststore = liststore
        self.treeview.set_size_request(-1, OC_DETAILED_LIST_HEIGHT)

    def show_conf(self, list_of_entry):
        self._liststore.clear()
        for v in list_of_entry:
            self._liststore.append(v)


class ShellWindow(gtk.Window):

    def __init__(self, parent=None, confirm=False, confirm_msg=""):
        super(ShellWindow, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.is_shell_hide = False
        self.is_shell_exited = True
        self.swparent = parent
        self.confirm = confirm
        self.confirm_msg = confirm_msg
        self.swparent.connect(GTK_SIGNAL_KEY_PRESS, self.toggle)
        self.connect(GTK_SIGNAL_KEY_PRESS, self.toggle)

    def shell_show(self, command=None):
        if self.is_shell_exited:
            if self.swparent:
                w, h = self.swparent.get_size()
                self.set_size_request(w, h)
                self.set_position(gtk.WIN_POS_CENTER)
            self.shell_main = vte.Terminal()
            self.shell_main.fork_command()
            self.shell_main.connect(GTK_SIGNAL_CHILD_EXIT, self.shell_exit)
            if command:
                self.shell_main.feed_child(command)
            self.add(self.shell_main)
            self.is_shell_exited = False
            self.show_all()
        elif self.is_shell_hide:
            self.is_shell_hide = False
            self.present()

    def shell_exit(self, terminal):
        terminal.destroy()
        self.hide()
        self.is_shell_exited = True

    def toggle(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval)
        if key == 'F2':
            if self.is_shell_exited or self.is_shell_hide:
                if self.confirm == False or\
                ConfirmDialog(self.confirm_msg).run_and_close() ==\
                gtk.RESPONSE_OK:
                    self.shell_show()
            else:
                self.hide()
                self.is_shell_hide = True


class LogWindow(gtk.Window):

    def __init__(self, parent=None):
        super(LogWindow, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.logshell = ShellWindow(self)
        self.set_position(gtk.WIN_POS_CENTER)
        self.is_logwin_hide = True
        self.files = ('/var/log/messages', '/var/log/vdsm/vdsm.log',
                        '/var/log/ovirt.log')
        if parent:
            self.swparent = parent
            w, h = self.swparent.get_size()
            self.set_size_request(w, h)
            self.swparent.connect(GTK_SIGNAL_KEY_PRESS, self.toggle)
        self.connect(GTK_SIGNAL_KEY_PRESS, self.toggle)
        v = gtk.VBox(False, 3)
        v.pack_start(gtk.Label("Choose log file to view"), False, False)
        sg_btn = gtk.SizeGroup(gtk.SIZE_GROUP_BOTH)
        for f in self.files:
            btn = ColorButton(f.split('/')[-1])
            btn.color_widget.connect(GTK_SIGNAL_CLICKED, self.log_show, f)
            btn.color_widget.set_size_request(-1, OC_COLOR_BUTTON_HEIGHT)
            sg_btn.add_widget(btn)
            h = gtk.HBox()
            h.pack_start(btn, True, False)
            v.pack_start(h, False, False)
        btn_back = ColorButton('Back')
        btn_back.color_widget.connect(GTK_SIGNAL_CLICKED,
                lambda _: self.hide())
        alignb = gtk.Alignment()
        alignb.add(btn_back)
        alignb.set_size_request(OC_LOG_WIN_WIDTH, OC_LOG_WIN_HEIGHT)
        sg_btn.add_widget(btn_back)
        alignb.set(1, 1, 0, 0)
        v.pack_start(alignb, True, False)
        align = ColorWidget('Alignment', 0.5, 0.5, 0, 0,
                            init_color=OC_LOG_PAGE_BG)
        align.color_widget.add(v)
        self.add(align)

    def toggle(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval)
        if key == 'F8':
            if self.is_logwin_hide:
                self.show_all()
            else:
                self.hide()
            self.is_logwin_hide = not self.is_logwin_hide

    def log_show(self, _, filename):
        self.logshell.shell_show('less %s; exit\n' % filename)

class ConfirmDialog(gtk.MessageDialog):

    def __init__(self, message=""):
        super(ConfirmDialog, self).__init__(None,
                        gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                        gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL,
                        message)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title("Continue?")

    def run_and_close(self):
        resp_id = self.run()
        self.destroy()
        return resp_id
