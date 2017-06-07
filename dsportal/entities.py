from dsportal.base import Entity
from dsportal.util import slug
import markdown
from os import path
from dsportal.config import ASSET_DIR

class Host(Entity):
    "A server"

class WebApp(Entity):
    "Web application"
    def __init__(self,url,powered_by,settle_time=None,*args,**kwargs):
        super(WebApp,self).__init__(*args,**kwargs)

        self.url = url
        self.powered_by = powered_by

        # TODO retina
        self.screenshot_url = "/assets/screenshots/%s.png" % slug(self.name)

        # TODO discover
        self.screenshot_width = 384
        self.screenshot_height = 193



class Markdown(Entity):
    "Loads a markdown file rendered as html"

    def __init__(self,markdown_file,*args,**kwargs):
        super(Markdown,self).__init__(*args,**kwargs)

        markdown_file = path.join(ASSET_DIR,markdown_file)
        with open(markdown_file) as f:
            self.html = markdown.markdown(f.read())
