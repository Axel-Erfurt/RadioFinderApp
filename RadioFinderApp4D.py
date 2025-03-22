#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_versions({'Gtk': '4.0', 'Gst': '1.0', 'Adw': '1'})
from gi.repository import Gtk, GdkPixbuf, Gst, Gio, Adw, GObject
import requests
import configparser
import sys
from time import sleep
import warnings

warnings.filterwarnings("ignore")

CONFIG = configparser.ConfigParser()
#CONFIG.read('config_d')

all_country_codes = """All Countries    
United States    US
Canada    CA
Germany    DE
United Kingdom    GB
Austria    AT
Belgium    BE
Bulgaria    BG
Croatia    HR
Cyprus    CY
Czechia    CZ
Denmark    DK
Estonia    EE
Finland    FI
France    FR
Greece    GR
Hungary    HU
Ireland    IE
Iceland    IS
Italy    IT
Latvia    LV
Lithuania    LT
Luxembourg    LU
Malta    MT
Mexico    MX
Netherlands    NL
Norway    NO
Poland    PL
Portugal    PT
Romania    RO
Serbia    RS
Slovakia    SK
Slovenia    SI
Spain    ES
Switzerland    CH
Sweden    SE"""

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
        
class Widget(GObject.Object):
    __gtype_name__ = 'Widget'

    def __init__(self, name):
        super().__init__()
        self._name = name

    @GObject.Property
    def name(self):
        return self._name

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
        
        self.search_text_widget = '' # Initial search text for widgets
        self.search_text_method = '' # Initial search text for methods
        
        self.set_size_request(660, 300)
        self.set_default_size(660, 600)
        
        self.playlist = ""
        self.set_icon_name('applications-multimedia')
        self.old_tag = ""

        self.header = Gtk.HeaderBar()
        self.header.set_show_title_buttons(True)
        self.set_titlebar(self.header)
        
        self.remove_button = Gtk.Button.new_from_icon_name('edit-delete')
        self.remove_button.set_tooltip_text("remove selected channel from Favorites")
        self.remove_button.connect("clicked", self.delete_channel)
        
        self.header.pack_start(self.remove_button)

        self.stop_button = Gtk.Button.new_from_icon_name('media-playback-stop-symbolic')
        self.stop_button.set_tooltip_text("stop playing")
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        
        self.vol_slider = Gtk.VolumeButton(tooltip_text = "Volume")
        self.vol_slider.set_tooltip_text("adjust volume\nclick or use mousewheel")
        self.vol_slider.set_adjustment(Gtk.Adjustment(value=0.5, lower=0.0, 
                                        upper=1.0, step_increment=0.01, 
                                        page_increment=0.05, page_size=0.0))
        self.vol_slider.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.vol_slider.connect("value-changed", self.set_volume)
        
        self.header.pack_start(self.vol_slider)
        
        self.mute_button = Gtk.Button.new_from_icon_name('audio-volume-high')
        self.mute_button.set_tooltip_text("mute / unmute")
        self.mute_button.connect("clicked", self.set_mute_status)
        
        
        self.search_entry = Gtk.SearchEntry(placeholder_text = "find radio stations ...", 
                                            tooltip_text = "find radio stations ...\nyou can use country code at bottom\n or search without country code", 
                                            margin_start=6, margin_end=0)
        self.search_entry.connect("activate", self.find_stations)

        self.header.pack_start(self.stop_button)        
        self.header.pack_start(self.mute_button)
        #self.header.pack_end(self.search_entry)   

        self.model = Gtk.ListStore(object)
        self.model.set_column_types((str, str, GdkPixbuf.Pixbuf))
        
        radiobox = Gtk.Box(orientation=1, homogeneous=False)
        
        radio_lbl = Gtk.Label()
        radio_lbl.set_markup('<b><span foreground="#55aaff" size="x-large">Stations</span></b>')
        radiobox.append(radio_lbl)
        radiobox.append(self.search_entry)

        self.icon_view = Gtk.IconView()
        self.icon_view.set_vexpand(True)
        self.icon_view.set_model(self.model)
        self.icon_view.set_item_width(90)
        self.icon_view.set_text_column(0)
        self.icon_view.set_pixbuf_column(2)
        self.icon_view.set_activate_on_single_click(True)
        self.icon_view.connect('item-activated', self.play)

        self.scroll = Gtk.ScrolledWindow(hexpand = True)
        self.scroll.set_child(self.icon_view)
        
        vbox = Gtk.Box(orientation=1, homogeneous=False, spacing=10)
        self.set_child(vbox)
        
        hbox = Gtk.Box(orientation=0, homogeneous=True, spacing=10, vexpand = True)
        radiobox.append(self.scroll)
        hbox.append(radiobox)
        
        ########################################################
        self.radio_model = Gtk.ListStore(object)
        self.radio_model.set_column_types((str, str, GdkPixbuf.Pixbuf))
        self.filter = self.radio_model.filter_new()
        self.filter.set_visible_func(self.visible_cb)
        favbox = Gtk.Box(orientation=1, homogeneous=False)
        
        self.search_fav_entry = Gtk.SearchEntry(placeholder_text = "filter favorites ...", 
                                                tooltip_text = "filter favorites ...", 
                                                margin_start=0, margin_end=6)
        self.search_fav_entry.connect("changed", self.refresh_filter)       

        self.icon_view_radio = Gtk.IconView()
        self.icon_view_radio.set_vexpand(True)
        self.icon_view_radio.set_model(self.filter)
        self.icon_view_radio.set_item_width(90)
        self.icon_view_radio.set_text_column(0)
        self.icon_view_radio.set_pixbuf_column(2)
        self.icon_view_radio.set_activate_on_single_click(True)
        self.icon_view_radio.connect('item-activated', self.play_radio)
        
        self.radio_scroll = Gtk.ScrolledWindow()
        self.radio_scroll.set_child(self.icon_view_radio)
        
        fav_lbl = Gtk.Label()
        fav_lbl.set_markup('<b><span foreground="#55aaff" size="x-large">Favorites</span></b>')
        favbox.append(fav_lbl)
        favbox.append(self.search_fav_entry)
        favbox.append(self.radio_scroll)
    
        hbox.append(favbox)
        
        ########################################################
        vbox.append(hbox)
        
        vol = f"{self.vol_slider.get_value() * 100:.0f}"

        self.status_bar = Gtk.Box(orientation=0, homogeneous=False, spacing=10, 
                                  margin_start=10, margin_top=10, margin_bottom=10, margin_end=10)
                                  
        country_code_label = Gtk.Label(label = "Country Code: ")
        
        self.status_bar.append(country_code_label) 
        
        self.country_code = Gtk.Entry(text="", tooltip_text = ("Country Code\nfor example:\
        \nde = Germany\ngb = Great Britain\nleave empty for None\
        \n\nedit and press Return"))
        self.country_code.set_max_length(2)
        self.country_code.set_max_width_chars(2)
        self.country_code.set_width_chars(2)
        
        self.model_widget = Gio.ListStore(item_type=Widget)
        self.sort_model_widget  = Gtk.SortListModel(model=self.model_widget) # FIXME: Gtk.Sorter?
        self.filter_model_widget = Gtk.FilterListModel(model=self.sort_model_widget)
        self.filter_widget = Gtk.CustomFilter.new(self._do_filter_widget_view, self.filter_model_widget)
        self.filter_model_widget.set_filter(self.filter_widget)
        
        ## Create factory
        factory_widget = Gtk.SignalListItemFactory()
        factory_widget.connect("setup", self._on_factory_widget_setup)
        factory_widget.connect("bind", self._on_factory_widget_bind)
        
        #c_codes = ["de", "us", "gb", "ca", "fr", "pl", "be", "au", "at", "dk", "ie", "no", "ch", "fi"]
        self.country_code_box = Gtk.DropDown(model=self.filter_model_widget, factory=factory_widget)
        self.country_code_box.set_tooltip_text("choose country code")
        #self.country_code_box.set_enable_search(True)
        for country in all_country_codes.splitlines():
            e_code = country
            self.model_widget.append(Widget(name=e_code))
        self.country_code_box.connect("notify::selected-item", self.country_code_box_changed)
        
        self.country_code.connect("activate", self.find_stations)
        self.status_bar.append(self.country_code) 
        self.status_bar.append(self.country_code_box) 
        
        self.volume_label = Gtk.Label(label = f"Volume: {vol}")
        self.volume_label.set_name("volume_label")
        vbox.append(self.volume_label)
        
        self.tag_label = Gtk.Label(lines=4)
        self.tag_label.set_hexpand(False)
        self.tag_label.set_name("tag_label")
        self.tag_label.set_text("Info")
        self.tag_label.set_wrap_mode(0)
        self.tag_label.set_natural_wrap_mode(2)
        self.tag_label.set_max_width_chars(100)
        
        empty = Gtk.Label(width_chars=30)
        self.status_bar.append(empty)
        
        self.transfer_button = Gtk.Button.new_from_icon_name("list-add")
        self.transfer_button.set_label("add to Favorites")
        self.transfer_button.set_tooltip_text("add selected station to Favorites")
        self.transfer_button.connect("clicked", self.transfer_channel)
        self.status_bar.append(self.transfer_button)
        
        self.save_button = Gtk.Button.new_from_icon_name("document-save")
        self.save_button.set_label("Save m3u Playlist")
        self.save_button.set_tooltip_text("Save all the stations found as a m3u playlist")
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
        
        self.read_channels()
        
        self.search_entry.grab_focus()
        
    def _on_factory_widget_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)
        
    def _on_factory_widget_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        widget = list_item.get_item()
        label.set_text(widget.name)

    def _do_filter_widget_view(self, item, filter_list_model):
        return self.search_text_widget.upper() in item.name.upper()
        
    def refresh_filter(self,widget):
        self.filter.refilter()
        
    def visible_cb(self, model, iter, data=None):
        search_query = self.search_fav_entry.get_text().lower()
        value = self.radio_model.get_value(iter, 0).lower()
        return True if search_query in value else False
        
    def handle_close(self, *args):
        self.write_channels()
            
    def delete_channel(self, path, *args):
        # check selection
        if self.icon_view_radio.get_selected_items():
            iter = self.radio_model.get_iter(self.icon_view_radio.get_selected_items()[0])
            path = self.icon_view_radio.get_selected_items()[0]
            name = self.radio_model.get_value (iter, 0)
            self.radio_model.remove(iter)
            print(f"{name} removed")
            CONFIG.remove_section(name)
            self.write_channels()
            self.read_channels()
            
            self.icon_view_radio.select_path(path)
            self.icon_view_radio.emit("item-activated", path)
        
        
    def write_channels(self):        
        channels = ""
        item = self.radio_model.get_iter_first ()

        while ( item != None ):
            channels += (f"[{self.radio_model.get_value (item, 0)}]\nurl={self.radio_model.get_value (item, 1)}\n")
            item = self.radio_model.iter_next(item)

        with open("config_d", 'w') as f:
            f.write(f"\n{channels}")

        
    def read_channels(self):
        self.radio_model.clear()
        CONFIG.read('config_d')
        for section in CONFIG.sections():
            icon_image_name = Gtk.Image.new_from_icon_name('audio-volume-high')
            icon_image = GdkPixbuf.Pixbuf.new_from_file("icon_fav.png").scale_simple(20, 20, GdkPixbuf.InterpType.NEAREST)
            self.radio_model.append((section, CONFIG[section]['url'], icon_image))
        
    def country_code_box_changed(self, dropdown, data):
        if self.search_entry.get_text():
            method = dropdown.get_selected_item()
            if method is not None:
                c_code = method.name.split("    ")[1].lower()
                self.country_code.set_text(c_code)
                self.find_stations()        
        
    def transfer_channel(self, *args):
        selected_path = self.icon_view.get_selected_items()[0]
        selected_iter = self.icon_view.get_model().get_iter(selected_path)

        name = self.icon_view.get_model().get_value(selected_iter, 0)
        url = self.icon_view.get_model().get_value(selected_iter, 1)
        channel = f"[{name}]\nurl={url}"
        print(channel)
        with open("config_d", 'a') as f:
            f.write(f"\n{channel}")
        self.read_channels()
            
            
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
        
    def play_radio(self, view, path):
        url = self.radio_model[path][1]
        if url.endswith(".pls"):
            url = self.getURLfromPLS(url)
        elif url.endswith(".m3u"):
            url = self.getURLfromM3U(url)
        else:
            url = self.radio_model[path][1]
        print(f"{self.radio_model[path][0]} - {url}")
        self.playbin.set_state(Gst.State.NULL)
        self.playbin.set_property('uri', url)
        self.playbin.set_state(Gst.State.PLAYING)
        self.playbin.set_property("mute", False)
        self.set_title(self.radio_model[path][0])
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
                        self.tag_label.set_markup(f'<b><span foreground="#55aaff" size="x-large">{my_tag.replace("&", "&amp")}</span></b>')
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
    
