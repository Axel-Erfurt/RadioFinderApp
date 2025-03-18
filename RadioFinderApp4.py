#!/usr/bin/python3
# -*- coding: utf-8 -*-

import gi
gi.require_versions({'Gtk': '4.0', 'Gst': '1.0', 'Adw': '1'})
from gi.repository import Gtk, GdkPixbuf, Gst, Gio, Adw
import requests
import sys
import warnings

warnings.filterwarnings("ignore")

BASE_URL =  "https://de1.api.radio-browser.info/"

endpoints = {
    "countries": {1: "{fmt}/countries", 2: "{fmt}/countries/{filter}"},
    "codecs": {1: "{fmt}/codecs", 2: "{fmt}/codecs/{filter}"},
    "states": {
        1: "{fmt}/states",
        2: "{fmt}/states/{filter}",
        3: "{fmt}/states/{country}/{filter}",
    },
    "languages": {1: "{fmt}/languages", 2: "{fmt}/languages/{filter}"},
    "tags": {1: "{fmt}/tags", 2: "{fmt}/tags/{filter}"},
    "stations": {1: "{fmt}/stations", 3: "{fmt}/stations/{by}/{search_term}"},
    "playable_station": {3: "{ver}/{fmt}/url/{station_id}"},
    "station_search": {1: "{fmt}/stations/search"},
}

def request(endpoint, **kwargs):

    fmt = kwargs.get("format", "json")

    if fmt == "xml":
        content_type = f"application/{fmt}"
    else:
        content_type = f"application/{fmt}"

    headers = {"content-type": content_type, "User-Agent": "getRadiolist/1.0"}

    params = kwargs.get("params", {})

    url = BASE_URL + endpoint

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code == 200:
        if fmt == "xml":
            return resp.text
        return resp.json()

    return resp.raise_for_status()


class EndPointBuilder:
    def __init__(self, fmt="json"):
        self.fmt = fmt
        self._option = None
        self._endpoint = None

    @property
    def endpoint(self):
        return endpoints[self._endpoint][self._option]

    def produce_endpoint(self, **parts):
        self._option = len(parts)
        self._endpoint = parts["endpoint"]
        parts.update({"fmt": self.fmt})
        return self.endpoint.format(**parts)


class RadioBrowser:
    def __init__(self, fmt="json"):
        self.fmt = fmt
        self.builder = EndPointBuilder(fmt=self.fmt)

    def stations(self, **params):
        endpoint = self.builder.produce_endpoint(endpoint="stations")
        kwargs = {}
        if params:
            kwargs.update({"params": params})
        return request(endpoint, **kwargs)

    def stations_byname(self, name):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byname", search_term=name
        )
        return request(endpoint)

    def station_search(self, params, **kwargs):
        assert isinstance(params, dict), "params must be a dictionary."
        kwargs["params"] = params
        endpoint = self.builder.produce_endpoint(endpoint="station_search")
        return request(endpoint, **kwargs)


class FinderWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Radio Finder", *args, **kwargs)
        
        self.set_default_size(660, 600)
        
        self.playlist = ""
        self.set_icon_name('applications-multimedia')
        self.old_tag = ""

        self.header = Gtk.HeaderBar()
        self.header.set_show_title_buttons(True)
        self.set_titlebar(self.header)

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
        
        
        self.search_entry = Gtk.SearchEntry(placeholder_text = "find ...", tooltip_text = "find ...")
        self.search_entry.connect("activate", self.find_stations)

        self.header.pack_start(self.stop_button)        
        self.header.pack_start(self.mute_button)
        self.header.pack_end(self.search_entry)   

        self.model = Gtk.ListStore(object)
        self.model.set_column_types((str, str, GdkPixbuf.Pixbuf))

        self.icon_view = Gtk.IconView()
        self.icon_view.set_vexpand(True)
        self.icon_view.set_model(self.model)
        self.icon_view.set_item_width(90)
        self.icon_view.set_text_column(0)
        self.icon_view.set_pixbuf_column(2)
        self.icon_view.set_activate_on_single_click(True)
        self.icon_view.connect('item-activated', self.play)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_child(self.icon_view)
        
        vbox = Gtk.Box(orientation=1, homogeneous=False, spacing=10)
        self.set_child(vbox)
        
        vbox.append(self.scroll)
        
        vol = f"{self.vol_slider.get_value() * 100:.0f}"

        self.status_bar = Gtk.Box(orientation=0, homogeneous=False, spacing=10, 
                                  margin_start=10, margin_top=10, margin_bottom=10, margin_end=10)
                                  
        country_code_label = Gtk.Label(label = "Country Code: ")
        self.status_bar.append(country_code_label) 
        self.country_code = Gtk.Entry(tooltip_text = ("Country Code\nfor example:\
        \nde = Germany\ngb = Great Britain\nleave empty for None\
        \n\nedit and press Return"))
        self.country_code.set_max_length(2)
        self.country_code.set_max_width_chars(2)
        self.country_code.set_width_chars(2)
        self.country_code.connect("activate", self.find_stations)
        self.status_bar.append(self.country_code) 
        
        self.volume_label = Gtk.Label(label = f"Volume: {vol}")
        self.volume_label.set_name("volume_label")
        vbox.append(self.volume_label)
        
        self.tag_label = Gtk.Label()
        self.tag_label.set_name("tag_label")
        self.tag_label.set_text("Info")
        self.tag_label.set_wrap_mode(0)
        self.tag_label.set_max_width_chars(100)
        
        empty = Gtk.Label(width_chars=30)
        self.status_bar.append(empty)
        
        self.transfer_button = Gtk.Button.new_from_icon_name("list-add")
        self.transfer_button.set_label("add to RadioApp")
        self.transfer_button.set_tooltip_text("add to RadioApp")
        self.transfer_button.connect("clicked", self.transfer_channel)
        self.status_bar.append(self.transfer_button)
        
        self.save_button = Gtk.Button.new_from_icon_name("document-save")
        self.save_button.set_label("Save as m3u Playlist")
        self.save_button.set_tooltip_text("Save as m3u Playlist")
        self.save_button.connect("clicked", self.save_playlist)
        self.status_bar.append(self.save_button)
        
        vbox.append(self.tag_label)
        vbox.append(self.status_bar)

        Gst.init('')
        self.playbin = Gst.ElementFactory.make('playbin', 'player')
        
        ### Listen for metadata
        self.old_tag = None
        self.bus = self.playbin.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('message::tag', self.on_tag)
        
    def transfer_channel(self, *args):
        selected_path = self.icon_view.get_selected_items()[0]
        selected_iter = self.icon_view.get_model().get_iter(selected_path)

        name = self.icon_view.get_model().get_value(selected_iter, 0)
        url = self.icon_view.get_model().get_value(selected_iter, 1)
        channel = f"[{name}]\nurl={url}"
        print(channel)
        with open("config", 'a') as f:
            f.write(f"\n{channel}")
            
            
    def set_volume(self, *args):
        vol = self.vol_slider.get_value()
        self.volume_label.set_text(f"Volume: {vol * 100:.0f}")
        self.playbin.set_property("volume", vol)
        
    def set_mute_status(self, *args):
        if self.playbin.get_property("mute") == True:
            self.playbin.set_property("mute", False)
            self.mute_button.set_icon_name('audio-volume-high')
        else:
            self.playbin.set_property("mute", True)
            self.mute_button.set_icon_name('audio-volume-muted')

    def play(self, view, path):
        url = self.model[path][1]
        if url.endswith(".pls"):
            url = self.getURLfromPLS(url)
        elif url.endswith(".m3u"):
            url = self.getURLfromM3U(url)
        else:
            url = self.model[path][1]
        print(f"{self.model[path][0]} - {url}")
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
        if not msg == None:
            taglist = msg.parse_tag()
            if not taglist == None:
                my_tag = f'{taglist.get_string(taglist.nth_tag_name(0)).value}'
                if my_tag:
                    if not self.old_tag == my_tag and not my_tag == "None":
                        print(my_tag)
                        self.tag_label.set_markup(f'<b><span foreground="#55aaff" size="x-large">{my_tag}</span></b>')
                        self.old_tag = my_tag

    def find_stations(self, *args):
        self.playlist = "#EXTM3U\n"
        i = 0
        self.model.clear()
        mysearch = self.search_entry.get_text()
        if mysearch == "":
            self.tag_label.set_text("please enter search term")
            return
        rb = RadioBrowser()
        if self.country_code.get_text() == "":
            print("country_code:", "None")
            myparams = {'name': 'search', 'nameExact': 'false'}
        else:
            country_code = self.country_code.get_text()
            print("country_code:", country_code)
            myparams = {'name': 'search', 'nameExact': 'false', 'countrycode': country_code}
        
        for key in myparams.keys():
                if key == "name":
                    myparams[key] = mysearch
        
        r = rb.station_search(params=myparams)
        
        n = ""
        m = ""
        for i in range(len(r)):
            for key,value in r[i].items():
                if str(key) == "name":
                    n = value.replace(",", " ")
                if str(key) == "url":
                    m = value
                    icon_image = GdkPixbuf.Pixbuf.new_from_file("icon.png").scale_simple(20, 20, GdkPixbuf.InterpType.NEAREST)
                    self.model.append((n, m, icon_image))
                    self.playlist += f"#EXTINF:{i+1},{n}\n{m}\n"
        if i > 0:
            self.tag_label.set_text(f"found {i} stations that contains '{mysearch}'")
            self.scroll.get_vadjustment().set_value(0)
        else:
            self.tag_label.set_text(f"found no stations that contains '{mysearch}'")
                    
    def getURLfromPLS(self, inURL):
        headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
                    }
        print("pls detecting", inURL)
        url = ""
        if "&" in inURL:
            inURL = inURL.partition("&")[0]
        response = requests.get(inURL, headers = headers)
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
        
    def save_playlist(self, *args):
        if self.playlist == "" or self.playlist == "#EXTM3U\n":
            return
        else:
            self.show_open_dialog()
            
    def show_open_dialog(self):
        self.dialog = Gtk.FileChooserNative.new("Save", self, Gtk.FileChooserAction.SAVE, "Save", "Cancel")
        filter = Gtk.FileFilter()
        filter.set_name("m3u Files")
        filter.add_pattern("*.m3u")
        self.dialog.add_filter(filter)
        self.dialog.set_current_name(f"{self.search_entry.get_text()}.m3u")
        self.dialog.set_transient_for(self)
        self.dialog.connect("response", self.on_open_dialog_response)
        self.dialog.show()

    def on_open_dialog_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            filename = str(dialog.get_file().get_path())
            with open(filename, 'w') as f:
                f.write(self.playlist)
                    
class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        self.connect("open", self.on_activate)
        self.set_flags(Gio.ApplicationFlags.HANDLES_OPEN)
        self.win = None
        
    def on_activate(self, app, *args, **kwargs):
        self.win = FinderWindow(application=app)
        self.win.present()
        
           
app = MyApp()
sm = app.get_style_manager()
sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
app.run(sys.argv)
    
