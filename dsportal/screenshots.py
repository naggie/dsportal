from __future__ import division
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from time import sleep
from io import BytesIO
import yaml
from sys import argv
import re
from os.path import isdir,isfile
from os import makedirs
from os.path import abspath,join
from shutil import copy
import jinja2
import markdown
from base64 import b64encode
from base64 import b64decode
from mimetypes import guess_type

# TODO grab driver.title?
# TODO http auth params with --disable-web-security
# TODO meta tagsfor oneboxing -- generate screenshot for it!


# pip install selenium pillow pyyaml jinja2
# brew install chromeself.driver

class ScreenshotGrabber(object):
    def __enter__(self):
        # use current profile so user is logged in
        chrome_options = Options()
        #chrome_options.add_argument("user-data-dir=/path/to/your/custom/profile")
        chrome_options.add_argument("disable-infobars")
        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        self.driver.set_window_size(1280, 720)
        self.driver.set_window_position(0,0)

        return self

    def grab_screenshot(self,url,settle_time):
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


def slug(string):
    return re.sub(r'\W','_',string).lower()

with open(argv[1]) as f:
    context = yaml.load(f)

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
)

output_dir = abspath(context['output_dir'])
screenshot_dir = join(output_dir,'screenshots')
index_file = join(output_dir,'index.html')
about_file = join(output_dir,'about.html')
error_file = join(output_dir,'error.html')
denied_file = join(output_dir,'denied.html')
notfound_file = join(output_dir,'notfound.html')
hosts_file = join(output_dir,'hosts.html')

if not isdir(output_dir):
    makedirs(output_dir)

if not isdir(screenshot_dir):
    makedirs(screenshot_dir)

copy('templates/style.css',output_dir)

# annotate
with ScreenshotGrabber() as s:
    for item in context['sites']:
        slug_title = slug(item['title'])
        filepath_original = join(screenshot_dir, '%s-original.png') % slug_title
        filepath_1x = join(screenshot_dir, '%s.png') % slug_title
        filepath_2x = join(screenshot_dir, '%s-2x.png') % slug_title
        item['screenshot_url'] = 'screenshots/%s.png' % slug_title
        item['screenshot_url_2x'] = 'screenshots/%s-2x.png' % slug_title

        if not isfile(filepath_original):
            img = s.grab_screenshot(item['url'],item.get('settle_time',3))
            img.save(filepath_original)
        else:
            img = Image.open(filepath_original)

        scaled_img = s.resize(img,384)
        width,height = scaled_img.size
        item['screenshot_width'] = width
        item['screenshot_height'] = height

        s.resize(img,768).save(filepath_2x)

        item['class'] = 'good'


if context.get('logo'):
    with open(join(output_dir,context['logo'])) as f:
        context['logo_data_uri'] = 'data:{mimetype};base64,{data}'.format(
                mimetype=guess_type(context['logo'])[0],
                data=b64encode(f.read()),
            )



template = env.get_template('index.html')
template.stream(**context).dump(index_file)

# TODO set asome as environmment
if context.get('about_file'):
    with open(context['about_file']) as f:
        context['about_html'] = markdown.markdown(f.read())

template = env.get_template('about.html')
template.stream(**context).dump(about_file)

template = env.get_template('error.html')
template.stream(title="Permission denied",message="Access from the VPN or internal network only",**context).dump(denied_file)
template.stream(title="Internal server error",message="Please try again later or contact us",**context).dump(error_file)
template.stream(title="404 Not Found",message="The resource you are trying to access does not exist",**context).dump(notfound_file)

# temporary
template = env.get_template('hosts.html')
template.stream(**context).dump(hosts_file)
