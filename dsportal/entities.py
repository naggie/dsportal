from dsportal.base import Entity
from dsportal.util import slug
import markdown
from os import path
from PIL import Image
from dsportal.config import ASSET_DIR
from dsportal.grabber import ScreenshotGrabber
from os.path import isdir
from os.path import dirname
from os import makedirs


class Host(Entity):
    "A server"


class WebApp(Entity):
    "Web application"

    def __init__(self, url, powered_by, settle_time=2, screenshot_url=None, *args, **kwargs):
        self.url = url
        self.screenshot_url = screenshot_url or url
        self.settle_time = settle_time
        self.powered_by = powered_by

        # run parent init _after_setting URL so that healthchecks that
        # reference this entity (bound by this parent) can access the URL
        super(WebApp, self).__init__(*args, **kwargs)

        filename = slug(self.url) + ".png"
        self.screenshot_file = path.join(ASSET_DIR, "screenshots", filename)
        self.screenshot_url = "/assets/screenshots/%s" % filename
        self.screenshot_display_width = 384
        self.screenshot_oversample = 2
        self.screenshot_exists = path.isfile(self.screenshot_file)

        if self.screenshot_exists:
            with Image.open(self.screenshot_file) as img:
                ratio = self.screenshot_display_width / img.width
                self.screenshot_display_height = int(img.height * ratio)

    def take_screenshot(self):
        screenshot_dir = dirname(self.screenshot_file)
        if not isdir(screenshot_dir):
            makedirs(screenshot_dir)

        width = self.screenshot_display_width * self.screenshot_oversample

        with ScreenshotGrabber(width * 2) as s:
            img = s.grab_screenshot(self.screenshot_url, self.settle_time)
            img = s.resize(img, width)
            img.save(self.screenshot_file)


class Markdown(Entity):
    "Loads a markdown file rendered as html"

    def __init__(self, markdown_file, *args, **kwargs):
        super(Markdown, self).__init__(*args, **kwargs)

        markdown_file = path.join(ASSET_DIR, markdown_file)
        with open(markdown_file) as f:
            self.html = markdown.markdown(f.read())
