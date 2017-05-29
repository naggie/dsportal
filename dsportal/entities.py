from base import Entity
import markdown

class Host(Entity):
    "A server"

class WebApp(Entity):
    "Web application"


class Markdown(Entity):
    "Loads a markdown file rendered as html"

    def __init__(self,markdown_file):
        with open(markdown_file) as f:
            self.html = markdown.markdown(f.read())
