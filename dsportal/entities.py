from dsportal.base import Entity
import markdown

class Host(Entity):
    "A server"

class WebApp(Entity):
    "Web application"
    def __init__(self,url,powered_by,settle_time=None,*args,**kwargs):
        super(WebApp,self).__init__(*args,**kwargs)


class Markdown(Entity):
    "Loads a markdown file rendered as html"

    def __init__(self,markdown_file,*args,**kwargs):
        super(Markdown,self).__init__(*args,**kwargs)
        #with open(markdown_file) as f:
        #    self.html = markdown.markdown(f.read())

        self.html ='TODO!'
