from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor


import jinja2
import webapp2
import os.path

config = type('Config', (object,), dict(map(
    lambda l: l.rstrip('\n').rstrip('\r').split('=',1),
    file('config.ini').readlines())))

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class Message(ndb.Model):
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)


class MainPage(webapp2.RequestHandler):

    def get(self):
        curs = Cursor(urlsafe=self.request.get('cursor'))
        messages, next_curs, more = Message.query().order(-Message.date).fetch_page(10, start_cursor=curs)


        template_values = {
            'messages': messages,
            'more': more,
            'next_curs': next_curs,
        }

        if self.request.get('format')=='rss':
            template = 'rss.html'
            ct = 'application/rss+xml; charset=UTF-8'
        else:
            template = 'index.html'
            ct = None
        self.render_template(template, template_values, ct)

    def render_template(self, template, template_values, content_type=None):
        template_values['user'] = users.get_current_user() if users.is_current_user_admin() else None
        template_values['config'] = config
        template = JINJA_ENVIRONMENT.get_template(template)
        self.response.headers['Content-Type'] = content_type or 'text/html; charset=UTF-8'
        self.response.write(template.render(template_values))

class EditPage(MainPage):

    def get(self, messageid=None):
        if not users.is_current_user_admin():
            self.response.write('<a href="%s">Sign in</a>.' %
                        users.create_login_url('/'))
            return

        message = Message.get_by_id(long(messageid)) if messageid else None

        template_values = {
            'message': message,
        }

        self.render_template('edit.html', template_values)

    def post(self, messageid=None):
        if messageid:
            message = Message.get_by_id(long(messageid))
        else:
            message = Message()
        if users.is_current_user_admin():
            message.author = users.get_current_user()
        else:
            self.response.write('<a href="%s">Sign in</a>.' %
                        users.create_login_url('/'))
            return

        action = self.request.get('action')
        if action=='edit':
            message.content = self.request.get('content')
            message.put()
        elif action=='delete':
            message.key.delete()
        self.redirect('/')

application = webapp2.WSGIApplication([
    ('/new', EditPage),
    ('/edit/(.*)', EditPage),
    ('/', MainPage),
], debug=False)
