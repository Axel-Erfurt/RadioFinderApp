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
import os
from gi.repository import Gtk, Gdk, GdkPixbuf, Gst
import requests

CONFIG = configparser.ConfigParser()
CONFIG.read('config')

CSS = """
headerbar entry {
    margin-top: 10px;
    margin-bottom: 10px;
    background: #ddd;
}
headerbar {
    min-height: 24px;
    padding-left: 2px;
    padding-right: 2px;
    margin: 0px;
    padding: 10px;
    background: #aabbcc;
    border: 0px;
}
headerbar label {
    font-size: 10pt;
    color: #5b5b5b;
}
label {
    color: #3465a4;
    font-size: 8pt;
}

statusbar label {
    color: #555753;
    font-size: 9pt;
    font-weight: bold;
}
window, iconview {
    background: #ddd;
    color: #555753;
}
iconview:selected {
    background: #aabbcc;
    color: #222;
}
"""

class Window(Gtk.ApplicationWindow):
    def __init__(self):
        super(Gtk.ApplicationWindow, self).__init__()
        
        # style
        provider = Gtk.CssProvider()
        provider.load_from_data(bytes(CSS.encode()))
        style = self.get_style_context()
        screen = Gdk.Screen.get_default()
        priority = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        style.add_provider_for_screen(screen, provider, priority)
        
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
        self.search_entry.connect("changed", self.refresh_filter)

        self.header.add(self.stop_button)        
        self.header.add(self.search_entry)        
        self.header.add(self.mute_button)

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

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.icon_view)
        
        vbox = Gtk.VBox()
        self.add(vbox)
        
        vbox.pack_start(scroll, True, True, 0)
        
        self.status_bar = Gtk.Statusbar()
        self.tag_label = Gtk.Label()
        self.tag_label.set_text("Info")
        self.status_bar.add(self.tag_label)
        
        vbox.pack_start(self.status_bar, False, True, 0)

        Gst.init('')
        self.playbin = Gst.ElementFactory.make('playbin', 'player')
        
        ### Listen for metadata
        self.old_tag = None
        self.bus = self.playbin.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('message::tag', self.on_tag)

        for section in CONFIG.sections():
            icon = Gtk.IconTheme.get_default().load_icon(
                    'multimedia-volume-control', 16, Gtk.IconLookupFlags.USE_BUILTIN)
            self.model.append((section, CONFIG[section]['url'], icon))
            
    def refresh_filter(self,widget):
        self.filter.refilter()
        
    def visible_cb(self, model, iter, data=None):
        search_query = self.search_entry.get_text().lower()
        value = model.get_value(iter, 0).lower()
        return True if search_query in value else False
            
    def set_volume(self, *args):
        vol = self.vol_slider.get_value()
        print(f"Volume: {vol:.2f}")
        self.playbin.set_property("volume", vol)
        
    def set_mute_status(self, *args):
        if self.playbin.get_property("mute") == True:
            self.playbin.set_property("mute", False)
            self.mute_button.set_image(Gtk.Image.new_from_icon_name(
                    'audio-volume-high', 2))
        else:
            self.playbin.set_property("mute", True)
            self.mute_button.set_image(Gtk.Image.new_from_icon_name(
                    'audio-volume-muted', 2))

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
        self.header.set_subtitle(self.model[path][0])
        self.stop_button.set_sensitive(True)

    def stop(self, button):
        self.playbin.set_state(Gst.State.NULL)
        self.header.set_subtitle(None)
        self.stop_button.set_sensitive(False)
        
    def on_tag(self, bus, msg):
        taglist = msg.parse_tag()
        if taglist.get_string(taglist.nth_tag_name(0)):
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
    window.resize(600, 230)
    window.move(0, 0)
    window.show_all()
    Gtk.main()