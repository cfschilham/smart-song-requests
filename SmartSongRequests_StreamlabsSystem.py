import urlparse
import urllib
import re
import json
import os
import time
import codecs

ScriptName = "Smart Song Requests"
Website = ""
Description = "Sends a customizable chat message when a song plays in chat. Includes support for license checking."
Creator = "Somebody2405"
Version = "0.4.3"

WORK_DIR = os.path.dirname(__file__)
VIDEOS_FILE = "videos.json"
CONFIG_FILE = "config.json"
EXCLUDED_VIDEOS_FILE = "excluded_videos.txt"
EXCLUDED_CHANNELS_FILE = "excluded_channels.txt"
OVERRIDE_TERMS_FILE = "override_terms.txt"

TICK_FREQ = 1 # In seconds.
SAVE_FREQ = 180


videos = dict() # The key is the video title and the value is a Video object.
config = None

last_save = time.time() # Save of the videos dictionary.
last_tick = time.time()
last_queue = None
last_playlist = None
last_playing = None

class Video:
    def __init__(self, video):
        self.title = video["title"]
        self.desc = video["desc"]
        self.tags = video["tags"]
        self.channel = video["channel"]
        self.channel_ID = video["channel_ID"]
        self.license_type = video["license_type"]
        self.ID = video["ID"]

    @staticmethod
    def get_id(url):
        url_data = urlparse.urlparse(url)
        ID = None
        
        if re.findall(r"(www\.)?youtube\.com", url_data.netloc):
            query = urlparse.parse_qs(url_data.query)
            ID = query["v"][0]

        if re.findall(r"(www\.)?youtu\.be", url_data.netloc):
            match = re.findall(r"[a-zA-Z0-9-_]{11}", url_data.path)
            if match: ID = match[0]

        if not ID: raise Exception("unable to get video id")
        return ID
    
    @classmethod
    def from_api(cls, ID):
        if not config: raise Exception("can't find config, maybe it hasn't loaded yet")

        url_params = urllib.urlencode({
            "part": "snippet,contentDetails,status",
            "key": config.youtube_data_api_key,
            "id": ID
        })

        response = Parent.GetRequest(config.youtube_data_api_url + "?" + url_params, headers={
            "Accept": "application/json"
        })
        json_data = json.loads(response)
        if json_data["status"] != 200: raise Exception("youtube api response not ok, status code " + str(json_data["status"]))
        
        # The Parent object returns the actual response as a string under the 'response'
        # attribute. The response decoded up to now had just 'response' and 'status' attributes.
        json_data = json.loads(json_data["response"])

        try:
            title = json_data["items"][0]["snippet"]["title"]
            desc = json_data["items"][0]["snippet"]["description"]
            try: tags = json_data["items"][0]["snippet"]["tags"]
            except: tags = []
            channel = json_data["items"][0]["snippet"]["channelTitle"]
            channel_ID = json_data["items"][0]["snippet"]["channelId"]
            license_type = json_data["items"][0]["status"]["license"]
        except Exception as e: raise Exception("error reading api response: " + str(e))

        return cls({
            "title": title,
            "desc": desc,
            "tags": tags,
            "channel": channel,
            "channel_ID": channel_ID,
            "license_type": license_type,
            "ID": ID
        })

class Config:
    def __init__(self, config):
        self.format_current_song = config["format_current_song"]
        self.youtube_data_api_url = config["youtube_data_api_url"]
        self.youtube_data_api_key = config["youtube_data_api_key"]
        self.warn_non_creative_commons = config["warn_non_creative_commons"]
        self.format_non_cc_requested = config["format_non_cc_requested"]
        self.format_non_cc_playing = config["format_non_cc_playing"]
        self.excluded_video_IDs = config["excluded_video_IDs"]
        self.excluded_channel_IDs = config["excluded_channel_IDs"]
        self.title_term_override = config["title_term_override"]
        self.desc_term_override = config["desc_term_override"]
        self.tags_term_override = config["tags_term_override"]
        self.override_terms = config["override_terms"]

    @classmethod
    def from_files(cls):
        if not os.path.isfile(os.path.join(WORK_DIR, CONFIG_FILE)): raise Exception("can't find config.json")
        if not os.path.isfile(os.path.join(WORK_DIR, EXCLUDED_VIDEOS_FILE)): 
            open(os.path.join(WORK_DIR, EXCLUDED_VIDEOS_FILE), "a").close()
        if not os.path.isfile(os.path.join(WORK_DIR, EXCLUDED_CHANNELS_FILE)):
            open(os.path.join(WORK_DIR, EXCLUDED_CHANNELS_FILE), "a").close()
        if not os.path.isfile(os.path.join(WORK_DIR, OVERRIDE_TERMS_FILE)):
            open(os.path.join(WORK_DIR, OVERRIDE_TERMS_FILE), "a").close()

        f = codecs.open(os.path.join(WORK_DIR, CONFIG_FILE), "r", "utf-8-sig")
        config = json.load(f)
        f.close()

        f = open(os.path.join(WORK_DIR, EXCLUDED_VIDEOS_FILE), "r")
        lines = f.readlines()
        excluded_video_IDs = []
        for ID in lines:
            prev_slash_index = None
            for i, char in enumerate(ID):
                if char == "/" and prev_slash_index == i-1:
                    ID = ID[:i-1]
                    break
                if char == "/": prev_slash_index = i

            ID = ID.strip()
            if not ID: continue

            if len(ID) != 11:
                Parent.SendStreamMessage("Invalid excluded video id: " + ID)
                continue
            excluded_video_IDs.append(ID)
        f.close()
        config["excluded_video_IDs"] = excluded_video_IDs

        f = open(os.path.join(WORK_DIR, EXCLUDED_CHANNELS_FILE), "r")
        lines = f.readlines()
        excluded_channel_IDs = []
        for ID in lines:
            prev_slash_index = None
            for i, char in enumerate(ID):
                if char == "/" and prev_slash_index == i-1:
                    ID = ID[:i-1]
                    break
                if char == "/": prev_slash_index = i

            ID = ID.strip()
            if not ID: continue

            if len(ID) != 24:
                Parent.SendStreamMessage("Invalid excluded channel id: " + ID)
                continue
            excluded_channel_IDs.append(ID)
        f.close()
        config["excluded_channel_IDs"] = excluded_channel_IDs
            
        f = open(os.path.join(WORK_DIR, OVERRIDE_TERMS_FILE), "r")
        lines = f.readlines()
        override_terms = []
        for term in lines:
            prev_slash_index = None
            for i, char in enumerate(term):
                if char == "/" and prev_slash_index == i-1:
                    term = term[:i-1]
                    break
                if char == "/": prev_slash_index = i

            term = term.strip()
            if not term: continue

            override_terms.append(term)
        f.close()
        config["override_terms"] = override_terms

        config = cls(config)

        if not config.youtube_data_api_key: raise Exception("youtube_data_api_key not specified")
        if not config.youtube_data_api_url: raise Exception("youtube_data_api_url not specified")

        return config

def save_videos():
    if not videos: return

    f = open(os.path.join(WORK_DIR, VIDEOS_FILE), "w")

    # Copy the videos dict, except convert Video object to dictionaries.
    videos_copy = dict() 
    for k, v in videos.iteritems(): 
        tags = []
        for tag in v.tags: tags.append(tag.encode("utf8"))
        videos_copy[k.encode("utf8")] = {
            "title": v.title.encode("utf8"),
            "desc": v.desc.encode("utf8"),
            "tags": tags,
            "channel": v.channel.encode("utf8"),
            "channel_ID": v.channel_ID.encode("utf8"),
            "license_type": v.license_type.encode("utf8"),
            "ID": v.ID.encode("utf8")
        }

    json.dump(videos_copy, f)
    f.close()

def load_videos():
    f = open(os.path.join(WORK_DIR, VIDEOS_FILE), "r")
    videos_copy = json.load(f)
    f.close()
    # Convert dictionaries to Video objects
    for k, v in videos_copy.iteritems(): 
        videos_copy[k] = Video(v)

    return videos_copy

def Init():
    global config
    try: config = Config.from_files()
    except Exception as e: Parent.SendStreamMessage("Error loading config: " + str(e))

    if os.path.isfile(os.path.join(WORK_DIR, VIDEOS_FILE)):
        global videos
        try: videos = load_videos()
        except Exception as e: Parent.SendStreamMessage("Unable to load videos database: " + str(e) + ". Existing database will be ignored, proceeding with initialization") 

def Execute(data):
    if not data.IsChatMessage(): return

    if data.GetParam(0).lower() == "!reloadconfig" and Parent.HasPermission(data.User, "moderator", "") and data.IsFromTwitch():
        global config
        try:
            config = Config.from_files()
            Parent.SendStreamMessage("Reloaded config file. " + data.UserName)
        except Exception as e: Parent.SendStreamMessage("Error loading config: " + str(e))

    if data.GetParam(0).lower() == "!db" and Parent.HasPermission(data.User, "moderator", "") and data.IsFromTwitch():
        if data.GetParam(1).lower() == "info":
            Parent.SendStreamMessage("Videos in memory: " + str(len(videos)) + ". " + data.UserName)
            try:
                dbsize = os.path.getsize(os.path.join(WORK_DIR, VIDEOS_FILE))
                f = open(os.path.join(WORK_DIR, VIDEOS_FILE))
                dbentries = len(json.load(f))
                f.close()
                Parent.SendStreamMessage("Videos in database file: " + str(dbentries) + ". Size: " + str(dbsize) + " bytes. " + data.UserName)
            except: Parent.SendStreamMessage("No database file. " + data.UserName)
            
        if data.GetParam(1).lower() == "wipe":
            try:
                global videos
                videos = dict()
                os.unlink(os.path.join(WORK_DIR, VIDEOS_FILE))
                f = open(os.path.join(WORK_DIR, VIDEOS_FILE), "w")
                f.write("{ }")
                f.close()
                Parent.SendStreamMessage("Successfully wiped database. " + data.UserName)
            except Exception as e: Parent.SendStreamMessage("Error wiping database: " + str(e))

        if data.GetParam(1).lower() == "save":
            try:
                save_videos()
                Parent.SendStreamMessage("Successfully saved to videos.json. " + data.UserName)
            except Exception as e: Parent.SendStreamMessage("Error saving videos to videos.json: " + str(e))

        if data.GetParam(1).lower() == "load": 
            try:
                if not os.path.isfile(os.path.join(WORK_DIR, VIDEOS_FILE)):
                    raise Exception("can't find videos.json")
                global videos
                videos = load_videos()
                Parent.SendStreamMessage("Successfully loaded videos.json. " + data.userName)
            except Exception as e: Parent.SendStreamMessage("Error loading videos from videos.json: " + str(e))

    if data.GetParam(0).lower() == "!songrequest" or data.GetParam(0).lower() == "!sr":
        try:
            ID = Video.get_id(data.GetParam(1))
            video = Video.from_api(ID)
            global videos
            videos[video.title] = video
            save_videos()
        except: pass
        if config.warn_non_creative_commons and video.license_type != "creativeCommon":
            if video.channel_ID in config.excluded_channel_IDs: return
            if video.ID in config.excluded_video_IDs: return 
            if config.title_term_override and config.override_terms:
                for term in config.override_terms:
                    if term.lower() in video.title.lower(): return
            if config.desc_term_override and config.override_terms:
                for term in config.override_terms:
                    if term.lower() in video.desc.lower(): return
            if config.tags_term_override and config.override_terms:
                for term in config.override_terms:
                    for tag in video.tags:
                        if term.lower() in tag.lower(): return
            Parent.SendStreamMessage(
                config.format_non_cc_requested
                    .replace("{{title}}", video.title)
                    .replace("{{channel}}", video.channel)
                    .replace("{{requester}}", data.UserName)
            )


def Tick():
    global last_tick, last_save, last_queue, last_playlist, last_playing

    if time.time() - last_save >= SAVE_FREQ:
        last_save = time.time()
        save_videos()


    if time.time() - last_tick >= TICK_FREQ:
        last_tick = time.time()

        queue = Parent.GetSongQueue(5)
        if queue and queue != last_queue:
            last_queue = queue
            for song in queue:   
                try:
                    ID = Video.get_id(song.URL)
                    if song.Title in videos: 
                        if videos[song.Title].ID == ID: continue
                    video = Video.from_api(ID)
                    videos[video.title] = video
                    save_videos()
                except: pass

        playlist = Parent.GetSongPlaylist(5)
        if playlist and playlist != last_playlist:
            last_playlist = playlist
            for song in playlist:
                try:
                    ID = Video.get_id(song.URL)
                    if song.Title in videos: 
                        if videos[song.Title].ID == ID: continue
                    video = Video.from_api(ID)
                    videos[video.title] = video
                    save_videos()
                except: pass

        playing = Parent.GetNowPlaying()
        if playing.Key and playing.Key != last_playing:
            last_playing = playing.Key

            video = None
            if playing.Key in videos: video = videos[playing.Key]

            if not video: # Video is not in collection of video info
                Parent.SendStreamMessage(
                    config.format_current_song
                        .replace("{{title}}", playing.Key)
                        .replace("{{channel}}", "unknown")
                        .replace("{{requester}}", playing.Value)
                )
                last_playing = playing.Key
                return

            Parent.SendStreamMessage(
                config.format_current_song
                    .replace("{{title}}", video.title)
                    .replace("{{channel}}", video.channel)
                    .replace("{{requester}}", playing.Value)
            )

            if config.warn_non_creative_commons and video.license_type != "creativeCommon":
                if video.channel_ID in config.excluded_channel_IDs: return
                if video.ID in config.excluded_video_IDs: return 
                if config.title_term_override and config.override_terms:
                    for term in config.override_terms:
                        if term.lower() in video.title.lower(): return
                if config.desc_term_override and config.override_terms:
                    for term in config.override_terms:
                        if term.lower() in video.desc.lower(): return
                if config.tags_term_override and config.override_terms:
                    for term in config.override_terms:
                        for tag in video.tags:
                            if term.lower() in tag.lower(): return
                Parent.SendStreamMessage(
                    config.format_non_cc_playing
                        .replace("{{title}}", video.title)
                        .replace("{{channel}}", video.channel)
                        .replace("{{requester}}", playing.Value)
                )

            