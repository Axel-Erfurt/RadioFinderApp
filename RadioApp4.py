#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Radio
=====
based on https://github.com/liZe/radio
extended by Axel Schneider
https://github.com/Axel-Erfurt
"""
import gi
gi.require_versions({'Gtk': '4.0', 'Gdk': '4.0', 'Gst': '1.0', 'Adw': '1'})
import configparser
from gi.repository import Gtk, Gdk, GdkPixbuf, Gst, Gio, Adw
import requests
import sys
import warnings

warnings.filterwarnings("ignore")

CONFIG = configparser.ConfigParser()
CONFIG.read('config')



class RadioWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Radio Player", *args, **kwargs)
        
        self.set_title('Radio Player')
        self.set_icon_name('applications-multimedia')
        self.old_tag = ""
        
        self.connect("close-request", self.handle_close)
        
        self.set_size_request(720, 600)

        self.header = Gtk.HeaderBar()
        #self.set_title('Radio Player')
        self.header.set_show_title_buttons(True)
        self.set_titlebar(self.header)
        
        self.remove_button = Gtk.Button.new_from_icon_name('edit-delete')
        self.remove_button.connect("clicked", self.delete_channel)
        
        self.header.pack_start(self.remove_button)

        self.stop_button = Gtk.Button.new_from_icon_name('media-playback-stop-symbolic')
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        
        self.vol_slider = Gtk.VolumeButton(tooltip_text = "Volume")
        self.vol_slider.set_adjustment(Gtk.Adjustment(value=0.5, lower=0.0, 
                                        upper=1.0, step_increment=0.01, 
                                        page_increment=0.05, page_size=0.0))
        self.vol_slider.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.vol_slider.connect("value-changed", self.set_volume)
        
        self.header.pack_start(self.vol_slider)
        
        self.mute_button = Gtk.Button.new_from_icon_name('audio-volume-high')
        self.mute_button.connect("clicked", self.set_mute_status)
        
        
        self.search_entry = Gtk.SearchEntry(placeholder_text = "find ...")
        self.search_entry.connect("changed", self.refresh_filter)

        self.header.pack_start(self.stop_button)        
        self.header.pack_start(self.mute_button)
        self.header.pack_end(self.search_entry)

        self.model = Gtk.ListStore(object)
        self.model.set_column_types((str, str, GdkPixbuf.Pixbuf))
        
        self.filter = self.model.filter_new()
        self.filter.set_visible_func(self.visible_cb)

        self.icon_view = Gtk.IconView()
        self.icon_view.set_model(model=self.filter)
        self.icon_view.set_item_width(-1)
        self.icon_view.set_text_column(0)
        self.icon_view.set_pixbuf_column(2)
        self.icon_view.set_activate_on_single_click(True)
        self.icon_view.connect('item-activated', self.play)
        self.icon_view.set_vexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self.icon_view)
        
        vbox = Gtk.Box(orientation=1, homogeneous=False, spacing=10, 
                                  margin_start=10, margin_top=10, margin_bottom=10, margin_end=10)
        self.set_child(vbox)
        
        vbox.append(scroll)

        vol = f"{self.vol_slider.get_value() * 100:.0f}"
        self.volume_label = Gtk.Label(label = f"Volume: {vol}")
        self.volume_label.set_vexpand(False)
        self.volume_label.set_name("volume_label")
        vbox.append(self.volume_label)
        
        self.tag_label = Gtk.Label()
        self.tag_label.set_name("tag_label")
        self.tag_label.set_text("Info")
        self.tag_label.set_wrap_mode(2)
        self.tag_label.set_max_width_chars(100)
        self.tag_label.set_halign(Gtk.Align.CENTER)
        vbox.append(self.tag_label)

        Gst.init('')
        self.playbin = Gst.ElementFactory.make('playbin', 'player')
        
        ### Listen for metadata
        self.old_tag = None
        self.bus = self.playbin.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('message::tag', self.on_tag)
        self.read_channels()
        
    def handle_close(self, *args):
        channels = ""
        item = self.model.get_iter_first ()

        while ( item != None ):
            channels += (f"[{self.model.get_value (item, 0)}]\nurl={self.model.get_value (item, 1)}\n")
            item = self.model.iter_next(item)

        with open("config", "w") as f:
            f.write(channels)
        
    def delete_channel(self, path, *args):
        iter = self.model.get_iter(self.icon_view.get_selected_items()[0])
        path = self.icon_view.get_selected_items()[0]
        name = self.model.get_value (iter, 0)
        self.model.remove(iter)
        print(f"{name} removed")
        self.icon_view.select_path(path)
        self.icon_view.emit("item-activated", path)

    def read_channels(self):
        for section in CONFIG.sections():
            icon_image_name = Gtk.Image.new_from_icon_name('audio-volume-high')
            icon_image = GdkPixbuf.Pixbuf.new_from_file("icon.png").scale_simple(20, 20, GdkPixbuf.InterpType.NEAREST)
            self.model.append((section, CONFIG[section]['url'], icon_image))
            
    def refresh_filter(self,widget):
        self.filter.refilter()
        
    def visible_cb(self, model, iter, data=None):
        search_query = self.search_entry.get_text().lower()
        value = model.get_value(iter, 0).lower()
        return True if search_query in value else False
            
    def set_volume(self, *args):
        vol = self.vol_slider.get_value()
        self.volume_label.set_text(f"Volume: {vol * 100:.0f}")
        self.playbin.set_property("volume", vol)
        
    def set_mute_status(self, *args):
        vol = self.vol_slider.get_value()
        if self.playbin.get_property("mute") == True:
            self.playbin.set_property("mute", False)
            self.mute_button.set_icon_name('audio-volume-high')
            self.volume_label.set_text(f"Volume: {vol * 100:.0f}")
        else:
            self.playbin.set_property("mute", True)
            self.mute_button.set_icon_name('audio-volume-muted')
            self.volume_label.set_text(f"Volume: {vol * 100:.0f} muted")

    def play(self, view, path):
        url = self.model[path][1]
        if url.endswith(".pls"):
            url = self.getURLfromPLS(url)
        if url.endswith(".m3u"):
            url = self.getURLfromM3U(url)        
        print(url)
        self.playbin.set_state(Gst.State.NULL)
        self.playbin.set_property('uri', url)
        self.playbin.set_state(Gst.State.PLAYING)
        self.playbin.set_property("mute", False)
        self.set_title(self.model[path][0])
        self.stop_button.set_sensitive(True)

    def stop(self, button):
        self.playbin.set_state(Gst.State.NULL)
        self.stop_button.set_sensitive(False)
        
    def on_tag(self, bus, msg):
        if msg:
            taglist = msg.parse_tag()
            if taglist:
                if not taglist.get_string(taglist.nth_tag_name(0)).value == None:
                    my_tag = f'{taglist.get_string(taglist.nth_tag_name(0)).value}'
                    if my_tag:
                        if not self.old_tag == my_tag and not my_tag == "None":
                            print(my_tag)
                            self.tag_label.set_markup(f'<b><span foreground="#55aaff" size="x-large">{my_tag}</span></b>')
                            self.old_tag = my_tag

    def getURLfromPLS(self, inURL):
        headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
                    }
        print("pls detecting", inURL)
        url = ""
        if "&" in inURL:
            inURL = inURL.partition("&")[0]
        response = requests.get(inURL, headers = headers)
        print(response.text)
        if "http" in response.text:
            html = response.text.splitlines()
            for line in html:
                if "http" in line:
                    url = f'http{line.split("http")[1]}'
                    break
            print(url)
            return (url)
        else:
           print("no urls found") 
    
    def getURLfromM3U(self, inURL):
        headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
                    }
        print("m3u detecting", inURL)
        url = ""
        if "&" in inURL:
            inURL = inURL.partition("&")[0]
        response = requests.get(inURL, headers = headers)
        print(response.text)
        if "http" in response.text:
            html = response.text.splitlines()
            for line in html:
                if "http" in line:
                    url = f'http{line.split("http")[1]}'
                    break
            print(url)
            return (url)
        else:
           print("no urls found") 
           
class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        self.connect("open", self.on_activate)
        self.set_flags(Gio.ApplicationFlags.HANDLES_OPEN)
        self.win = None
        
    def on_activate(self, app, *args, **kwargs):
        self.win = RadioWindow(application=app)
        self.win.present()
        keycont = Gtk.EventControllerKey()
        
           
app = MyApp()
sm = app.get_style_manager()
sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
app.run(sys.argv)
