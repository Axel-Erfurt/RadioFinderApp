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
gi.require_versions({'Gtk': '3.0', 'Gdk': '3.0', 'Gst': '1.0'})
import configparser
from gi.repository import Gtk, Gdk, GdkPixbuf, Gst
import requests

CONFIG = configparser.ConfigParser()
CONFIG.read('config')



class Window(Gtk.ApplicationWindow):
    def __init__(self):
        super(Gtk.ApplicationWindow, self).__init__()
        
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)
        
        self.set_title('Radio Player')
        self.set_icon_name('applications-multimedia')
        self.connect("destroy",Gtk.main_quit)
        self.old_tag = ""

        self.header = Gtk.HeaderBar()
        self.header.set_title('Radio Player')
        self.header.set_show_close_button(True)
        self.set_titlebar(self.header)

        self.stop_button = Gtk.Button()
        self.stop_button.add(
            Gtk.Image.new_from_icon_name('media-playback-stop-symbolic', 2))
        self.stop_button.set_relief(2)
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        
        self.vol_slider = Gtk.VolumeButton(tooltip_text = "Volume")
        self.vol_slider.set_adjustment(Gtk.Adjustment(value=0.5, lower=0.0, 
                                        upper=1.0, step_increment=0.01, 
                                        page_increment=0.05, page_size=0.0))
        self.vol_slider.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.vol_slider.connect("value-changed", self.set_volume)
        
        self.header.add(self.vol_slider)
        
        self.mute_button = Gtk.Button(relief = 2, tooltip_text = "mute / unmute")
        self.mute_button.add(
            Gtk.Image.new_from_icon_name('audio-volume-high', 2))
        self.mute_button.connect("clicked", self.set_mute_status)
        
        
        self.search_entry = Gtk.SearchEntry(placeholder_text = "find ...")
        self.search_entry.connect("changed", self.visible_cb)
        self.search_entry.connect("icon-press", self.read_channels)
        

        self.header.add(self.stop_button)        
        self.header.add(self.mute_button)
        self.header.pack_end(self.search_entry)

        self.model = Gtk.ListStore(object)
        self.model.set_column_types((str, str, GdkPixbuf.Pixbuf))

        self.icon_view = Gtk.IconView()
        self.icon_view.set_model(model=self.model)
        self.icon_view.set_item_width(-1)
        self.icon_view.set_text_column(0)
        self.icon_view.set_pixbuf_column(2)
        self.icon_view.set_activate_on_single_click(True)
        self.icon_view.connect('item-activated', self.play)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.icon_view)
        
        vbox = Gtk.VBox()
        self.add(vbox)
        
        vbox.pack_start(scroll, True, True, 0)

        vol = f"{self.vol_slider.get_value() * 100:.0f}"
        self.volume_label = Gtk.Label(label = f"Volume: {vol}")
        self.volume_label.set_name("volume_label")
        vbox.pack_end(self.volume_label, False, False, 0)
        
        self.tag_label = Gtk.Label()
        self.tag_label.set_name("tag_label")
        self.tag_label.set_text("Info")
        self.tag_label.set_line_wrap(True)
        self.tag_label.set_line_wrap_mode(0)
        self.tag_label.set_max_width_chars(50)
        self.tag_label.set_halign(Gtk.Align.CENTER)
        vbox.pack_end(self.tag_label, False, True, 0)

        Gst.init('')
        self.playbin = Gst.ElementFactory.make('playbin', 'player')
        
        ### Listen for metadata
        self.old_tag = None
        self.bus = self.playbin.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('message::tag', self.on_tag)
        self.read_channels()

    def read_channels(self, *args):
        self.model.clear()
        for section in CONFIG.sections():
            icon = Gtk.IconTheme.get_default().load_icon(
                    'audio-volume-high', 16, Gtk.IconLookupFlags.USE_BUILTIN)
            self.model.append((section, CONFIG[section]['url'], icon))
            
    def refresh_filter(self,widget):
        self.filter.refilter()
        
    def visible_cb(self, entry, *args):
        search_query = entry.get_text().lower()
        if search_query == "":
            self.read_channels()
        for row in self.model:
            if not search_query in row[0].lower():
                path = row.path
                iter = self.model.get_iter(path)
                self.model.remove(iter)

            
    def set_volume(self, *args):
        vol = self.vol_slider.get_value()
        self.volume_label.set_text(f"Volume: {vol * 100:.0f}")
        self.playbin.set_property("volume", vol)
        
    def set_mute_status(self, *args):
        vol = self.vol_slider.get_value()
        if self.playbin.get_property("mute") == True:
            self.playbin.set_property("mute", False)
            self.mute_button.set_image(Gtk.Image.new_from_icon_name(
                    'audio-volume-high', 2))
            self.volume_label.set_text(f"Volume: {vol * 100:.0f}")
        else:
            self.playbin.set_property("mute", True)
            self.mute_button.set_image(Gtk.Image.new_from_icon_name(
                    'audio-volume-muted', 2))
            self.volume_label.set_text(f"Volume: {vol * 100:.0f} muted")

    def play(self, view, path):
        print(view.get_selected_items()[0])
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
        self.header.set_subtitle(self.model[path][0])
        self.stop_button.set_sensitive(True)

    def stop(self, button):
        self.playbin.set_state(Gst.State.NULL)
        self.header.set_subtitle(None)
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
                            self.tag_label.set_text(my_tag)
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
        
if __name__ == '__main__':
    window = Window()
    window.set_volume()
    window.resize(720, 320)
    window.move(0, 0)
    window.show_all()
    Gtk.main()
    
