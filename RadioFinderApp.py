#!/usr/bin/python3
# -*- coding: utf-8 -*-
import gi
gi.require_versions({'Gtk': '3.0', 'Gdk': '3.0','Gst': '1.0'})
from gi.repository import Gtk, Gdk, GdkPixbuf, Gst
import requests

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
    color: #222;
    font-size: 8pt;
}
window, iconview {
    background: #ddd;
    color: #555753;
}
iconview:selected {
    background: #729fcf;
    color: #222;
}
"""

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

    def countries(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="countries")
        return request(endpoint)

    def codecs(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="codecs")
        return request(endpoint)

    def states(self, country="", filter=""):
        endpoint = self.builder.produce_endpoint(
            endpoint="states", country=country, filter=filter
        )
        return request(endpoint)

    def languages(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="languages", filter=filter)
        return request(endpoint)

    def tags(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="tags", filter=filter)
        return request(endpoint)

    def stations(self, **params):
        endpoint = self.builder.produce_endpoint(endpoint="stations")
        kwargs = {}
        if params:
            kwargs.update({"params": params})
        return request(endpoint, **kwargs)

    def stations_byid(self, id):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byid", search_term=id
        )
        return request(endpoint)

    def stations_byuuid(self, uuid):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byuuid", search_term=uuid
        )
        return request(endpoint)

    def stations_byname(self, name):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byname", search_term=name
        )
        return request(endpoint)

    def stations_bynameexact(self, nameexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bynameexact", search_term=nameexact
        )
        return request(endpoint)

    def stations_bycodec(self, codec):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycodec", search_term=codec
        )
        return request(endpoint)

    def stations_bycodecexact(self, codecexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycodecexact", search_term=codecexact
        )
        return request(endpoint)

    def stations_bycountry(self, country):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycountry", search_term=country
        )
        return request(endpoint)

    def stations_bycountryexact(self, countryexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycountryexact", search_term=countryexact
        )
        return request(endpoint)

    def stations_bystate(self, state):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bystate", search_term=state
        )
        return request(endpoint)

    def stations_bystateexact(self, stateexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bystateexact", search_term=stateexact
        )
        return request(endpoint)

    #
    def stations_bylanguage(self, language):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bylanguage", search_term=language
        )
        return request(endpoint)

    def stations_bylanguageexact(self, languageexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bylanguageexact", search_term=languageexact
        )
        return request(endpoint)

    def stations_bytag(self, tag):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bytag", search_term=tag
        )
        return request(endpoint)

    def stations_bytagexact(self, tagexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bytagexact", search_term=tagexact
        )
        return request(endpoint)

    def playable_station(self, station_id):
        endpoint = self.builder.produce_endpoint(
            endpoint="playable_station", station_id=station_id, ver="v2"
        )

        return request(endpoint)

    def station_search(self, params, **kwargs):
        assert isinstance(params, dict), "params must be a dictionary."
        kwargs["params"] = params
        endpoint = self.builder.produce_endpoint(endpoint="station_search")
        return request(endpoint, **kwargs)


class Window(Gtk.ApplicationWindow):
    def __init__(self):
        super(Gtk.ApplicationWindow, self).__init__()
        
        self.set_default_size(750, 400)
        #self.set_resizable(False)
        # style
        provider = Gtk.CssProvider()
        provider.load_from_data(bytes(CSS.encode()))
        style = self.get_style_context()
        screen = Gdk.Screen.get_default()
        priority = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        style.add_provider_for_screen(screen, provider, priority)
        
        self.playlist = ""
        self.set_title('Radio Finder')
        self.set_icon_name('applications-multimedia')
        self.connect("destroy",Gtk.main_quit)
        self.old_tag = ""

        self.header = Gtk.HeaderBar()
        self.header.set_title('Radio Finder')
        self.header.set_show_close_button(True)
        self.set_titlebar(self.header)

        self.stop_button = Gtk.Button(tooltip_text = "stop playing")
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
        
        
        self.search_entry = Gtk.SearchEntry(placeholder_text = "find ...", tooltip_text = "find ...")
        self.search_entry.connect("activate", self.find_stations)

        self.header.add(self.stop_button)        
        self.header.add(self.search_entry)        
        self.header.add(self.mute_button)

        self.model = Gtk.ListStore(object)
        self.model.set_column_types((str, str, GdkPixbuf.Pixbuf))
    

        self.icon_view = Gtk.IconView()
        #self.icon_view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.icon_view.set_model(self.model)
        self.icon_view.set_item_width(100)
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
        self.tag_label.set_line_wrap(True)
        self.tag_label.set_max_width_chars(80)

        self.transfer_button = Gtk.Button.new_from_icon_name("list-add", 2)
        self.transfer_button.set_label("add to RadioApp")
        self.transfer_button.set_tooltip_text("add to RadioApp")
        self.transfer_button.set_relief(2)
        self.transfer_button.connect("clicked", self.transfer_channel)
        self.status_bar.add(self.transfer_button)
        
        self.save_button = Gtk.Button.new_from_icon_name("document-save", 2)
        self.save_button.set_label("Save as m3u Playlist")
        self.save_button.set_tooltip_text("Save as m3u Playlist")
        self.save_button.set_relief(2)
        self.save_button.connect("clicked", self.save_playlist)
        self.status_bar.add(self.save_button)
        
        vbox.pack_start(self.tag_label, False, True, 0)
        vbox.pack_start(self.status_bar, False, True, 0)

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
        elif url.endswith(".m3u"):
            url = self.getURLfromM3U(url)
        else:
            url = self.model[path][1]
        print(f"{self.model[path][0]} - {url}")
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

    def find_stations(self, *args):
        self.playlist = "#EXTM3U\n"
        i = 0
        self.model.clear()
        mysearch = self.search_entry.get_text()
        if mysearch == "":
            self.tag_label.set_text("please enter search term")
            return
        rb = RadioBrowser()
        myparams = {'name': 'search', 'nameExact': 'false'}
        
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
                    #print("%s,%s" % (n, m))
                    icon = Gtk.IconTheme.get_default().load_icon(
                    'multimedia-volume-control', 16, Gtk.IconLookupFlags.USE_BUILTIN)
                    self.model.append((n, m, icon))
                    self.playlist += f"#EXTINF:{i+1},{n}\n{m}\n"
        if i > 0:
            self.tag_label.set_text(f"found {i} stations that contains '{mysearch}'")          
            #print(self.playlist)
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
            dlg = Gtk.FileChooserDialog(title="Please choose a file", parent=None, action = 1)
            dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                     "Save", Gtk.ResponseType.OK)
                     
            filter = Gtk.FileFilter()
            filter.set_name("m3u Files")
            filter.add_pattern("*.m3u")
            dlg.add_filter(filter)
            dlg.set_current_name(f"{self.search_entry.get_text()}.m3u")
            response = dlg.run()

            if response == Gtk.ResponseType.OK:
                infile = (dlg.get_filename())
                with open(infile, 'w') as f:
                    f.write(self.playlist)
            else:
                dlg.destroy()
            dlg.destroy()
                    
if __name__ == '__main__':
    window = Window()
    window.set_volume()
    window.move(50, 50)
    window.show_all()
    window.search_entry.grab_focus()
    Gtk.main()