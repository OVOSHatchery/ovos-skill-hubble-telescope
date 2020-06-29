from mycroft import intent_file_handler, intent_handler, MycroftSkill
from mycroft.skills.core import resting_screen_handler
from adapt.intent import IntentBuilder
from mtranslate import translate
import random
from os.path import join, dirname
from os import listdir
from requests_cache import CachedSession
from datetime import timedelta
from mycroft.util import create_daemon


class HubbleTelescopeSkill(MycroftSkill):
    def __init__(self):
        super(HubbleTelescopeSkill, self).__init__(name="HubbleTelescopeSkill")
        if "random" not in self.settings:
            # idle screen, random or latest
            self.settings["random"] = True
        if "include_james_webb" not in self.settings:
            self.settings["include_james_webb"] = False
        if "exclude_long" not in self.settings:
            self.settings["exclude_long"] = True
        self.session = CachedSession(backend='memory',
                                     expire_after=timedelta(hours=6))
        self.translate_cache = {}
        # bootstrap - cache image data
        create_daemon(self.latest_hubble)

    # hubble api
    def latest_hubble(self, n=-1):
        url = "http://hubblesite.org/api/v3/images/all?page=all"
        info_url = "http://hubblesite.org/api/v3/image/{img_id}"
        entries = self.session.get(url).json()
        wallpapers = []
        for e in entries:
            image_data = self.session.get(
                info_url.format(img_id=e["id"])).json()
            if image_data["mission"] != "hubble" and\
                    not self.settings["include_james_webb"]:
                continue
            data = {
                "author": "Hubble Space Telescope",
                "caption": image_data.get("description"),
                "title": image_data["name"],
                "url": "https://hubblesite.org/image/{id}/gallery".format(
                    id=e["id"]),
                "imgLink": "",

            }
            max_size = 0
            min_size = 99999
            for link in image_data["image_files"]:
                for ext in [".png", ".jpg", ".jpeg"]:
                    if link["file_url"].endswith(ext):
                        if link['height'] > 2 * link['width'] \
                                and self.settings["exclude_long"]:
                            continue  # skip long infographics
                        if link["width"] > max_size:
                            data["imgLink"] = "http:" + link["file_url"]
                        if max_size < link["width"] < min_size:
                            data["thumbnail"] = "http:" + link["file_url"]
            if data["imgLink"]:
                wallpapers.append(data)
            if 0 < n <= len(wallpapers):
                break
        return wallpapers

    def hubble_pod(self):
        return self.latest_hubble(1)[0]

    def random_hubble(self):
        pictures = self.latest_hubble()
        return random.choice(pictures)

    def space_telescope_now(self, n=-1):
        url = "http://hubblesite.org/api/v3/external_feed/st_live"
        entries = self.session.get(url).json()
        pictures = []
        for e in entries:
            data = {
                "author": "Space Telescope Live",
                "caption": e["description"].replace('I am looking',
                                                    "Hubble is looking"),
                "title": e["title"],
                "url": e["link"],
                "imgLink": "http:" + e["image"],
                "thumbnail": "http:" + e["thumbnail_large"],
                "date": e["pub_date"]

            }

            if data["imgLink"]:
                pictures.append(data)
            if 0 < n <= len(pictures):
                break
        return pictures

    # idle screen
    def update_picture_stn(self, latest=True):
        if latest:
            data = self.space_telescope_now(1)[0]
        else:
            data = random.choice(self.space_telescope_now())

        tx = ["title", "caption"]
        for k in data:
            if not self.lang.startswith("en") and k in tx:
                if data[k] not in self.translate_cache:
                    translated = translate(data[k], self.lang)
                    self.translate_cache[data[k]] = translated
                    data[k] = translated
                else:
                    data[k] = self.translate_cache[data[k]]

            self.settings[k] = data[k]
            self.gui[k] = data[k]
        self.set_context("HubbleTelescope")

    def update_picture(self, latest=True):
        if latest:
            data = self.hubble_pod()
        else:
            data = self.random_hubble()

        tx = ["title", "caption"]
        for k in data:
            if not self.lang.startswith("en") and k in tx:
                if data[k] not in self.translate_cache:
                    translated = translate(data[k], self.lang)
                    self.translate_cache[data[k]] = translated
                    data[k] = translated
                else:
                    data[k] = self.translate_cache[data[k]]

            self.settings[k] = data[k]
            self.gui[k] = data[k]
        self.set_context("HubbleTelescope")

    @resting_screen_handler("HubbleTelescope")
    def idle(self, message):
        self.update_picture(not self.settings["random"])
        self.gui.clear()
        self.gui.show_page('idle.qml')

    # intents
    def _random_pic(self):
        path = join(dirname(__file__), "ui", "images", "hubble_pictures")
        pics = listdir(path)
        return join(path, random.choice(pics))

    @intent_file_handler("who.intent")
    def handle_who_hubble_intent(self, message):
        hubble = join(dirname(__file__), "ui", "images", "edwin_hubble.jpg")
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit',
                            title="Edwin Powell Hubble",
                            caption="November 20, 1889 – September 28, 1953")
        self.speak_dialog("hubble.who")

    @intent_file_handler("about.intent")
    def handle_about_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("about", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("when.intent")
    def handle_when_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.when", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_handler(IntentBuilder("WhyIntent")
                    .require("why").require("HubbleTelescope"))
    def handle_why_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.why", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_handler(IntentBuilder("HowIntent")
                    .require("how").require("HubbleTelescope")
                    .optionally("work"))
    def handle_how_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.how", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_handler(IntentBuilder("WhereIntent")
                    .require("where").require("HubbleTelescope"))
    def handle_where_hubble_intent(self, message):
        if self.config_core["system_unit"] == "metric":
            altitude = "547"  # kilometers
            speed = "27,300"  # kilometers per hour
            caption = self.dialog_renderer.render("hubble.where.metric",
                                                  {"altitude": altitude,
                                                   "speed": speed})
        else:
            # YOU ARE ASSHOLES
            # I shouldn't even support this and force you to use the metric
            # system or fork
            speed = "17,000"  # miles per hour
            altitude = "340"  # miles
            caption = self.dialog_renderer.render("hubble.where",
                                                  {"altitude": altitude,
                                                   "speed": speed})
        hubble = self._random_pic()

        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("mission.intent")
    def handle_mission_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.mission", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("planets.intent")
    def handle_planets_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.mission", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("live.intent")
    def handle_live_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.live", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("earth.intent")
    def handle_earth_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.earth", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)
        self.set_context("HubbleTelescope")  # follow up question to elaborate

    @intent_file_handler("data_public.intent")
    def handle_data_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.data.public", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler("colors.intent")
    def handle_colors_hubble_intent(self, message):
        hubble = self._random_pic()
        caption = self.dialog_renderer.render("hubble.colors", {})
        self.gui.show_image(hubble, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)
        self.speak(caption, wait=True)

    @intent_file_handler('hubble.intent')
    def handle_pod(self, message):
        if self.voc_match(message.data["utterance"], "latest"):
            self.update_picture(True)
        else:
            self.update_picture(False)
        self.gui.clear()
        self.gui.show_image(self.settings['imgLink'],
                            title=self.settings['title'],
                            fill='PreserveAspectFit')

        self.speak(self.settings['caption'])

    @intent_file_handler('hubble.now.intent')
    def handle_now(self, message):
        self.update_picture_stn()
        self.gui.clear()
        self.gui.show_image(self.settings['imgLink'],
                            title=self.settings['title'],
                            fill='PreserveAspectFit')

        self.speak(self.settings['caption'])

    @intent_handler(IntentBuilder("ExplainIntent")
                    .require("ExplainKeyword").require("HubbleTelescope"))
    def handle_explain(self, message):
        self.gui.show_image(self.settings['imgLink'], override_idle=True,
                            fill='PreserveAspectFit',
                            caption=self.settings['caption'])
        self.speak(self.settings['caption'], wait=True)

    @intent_file_handler("moon.intent")
    def moon_intent(self, message):
        picture = join(dirname(__file__), "ui", "images", "hubble_moon.png")
        caption = self.dialog_renderer.render("hubble.moon.caption", {})
        self.speak_dialog("hubble.moon")
        self.gui.show_image(picture, override_idle=True,
                            fill='PreserveAspectFit', caption=caption)


def create_skill():
    return HubbleTelescopeSkill()
