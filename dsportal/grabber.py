from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from time import sleep
from io import BytesIO
from dsportal.util import slug
from base64 import b64decode
from dsportal.config import ASSET_DIR
import logging
log = logging.getLogger(__name__)

# chrome://version/ remove /Default/
from os import getenv

chrome_profile = getenv('CHROME_PROFILE')

# brew install chromedriver

class ScreenshotGrabber(object):
    def __init__(self,width):
        ratio = 720/1280
        self.width = width
        self.height = int(width*ratio)

    def __enter__(self):
        # use current profile so user is logged in
        chrome_options = Options()

        if chrome_profile:
            chrome_options.add_argument("user-data-dir=%s" % chrome_profile)

        chrome_options.add_argument("disable-infobars")
        #self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.driver = webdriver.Firefox()
        self.driver.set_window_size(self.width, self.height)
        self.driver.set_window_position(0,0)

        return self

    def grab_screenshot(self,url,settle_time=2):
        log.info('grabbing %s',url)
        self.driver.get(url)
        sleep(settle_time)
        base64_png = self.driver.get_screenshot_as_base64()
        # make thumb
        png = b64decode(base64_png)
        img = Image.open(BytesIO(png))

        return img

    @staticmethod
    def resize(img,width=384):
        height = int(img.height / (img.width/width))

        img = img.resize((width,height),resample=Image.LANCZOS)
        #img.show()
        return img

    def __exit__(self,type,value,traceback):
        self.driver.quit()

