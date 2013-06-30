import md5
from bottle import abort, redirect, request, route, run
import json
from shove import Shove
from time import ctime

DEBUG = True


def hashLink(link):
    """
    Hash a link, this might need to be changed to be more complex at some point

    :type link: str
    :param link: The link to be hashed
    """

    return str(md5.new(link).hexdigest())[:5]


def cache(func, cache, invalid_after):
    """
    Caching function which stores cached data in a dict (or a shove object)

    :type func: function
    :param func: Function whose output should be cached

    :type cache: dict
    :param cache: Anything that implements the same methods as dict, it stores our cached data

    :type invalid_after: int
    :param invalid_after: time in seconds to wait before invaliding cache data
    """

    def cache_wrapper(*args, **kwargs):
        call_id = str(func) + str(args)
        try:
            return_value = cache[call_id]
            if ctime() - return_value[0] > invalid_after:
                raise Exception
            else:
                return return_value[1]
        except:
            return_value = func(*args, **kwargs)
            cache[call_id] = (ctime(), return_value)
            return return_value
    return cache_wrapper


class CSHLYServer(object):
    """
    WSGI Server exposing the link shortening api

    :type port: int
    :param port: port to listen for connections on

    :type link_db_uri: str
    :param link_db_uri: a shove compatible database uri for storing shortened links

    :type user_db_uri: str
    :param user_db_uri: a shove compatible database uri for storing user information

    :type use_auth: boolean
    :param use_auth: Enable authentication or disable authentication, default is enabled
    """

    def __new__(self, *args, **kwargs):
        """
        Used to call decorators on all the functions in the class
        shorten -> /api/shorten
        unshorten -> /api/unshorten/<hashed>
        unshorten_redirect -> /<hashed>
        get_link_data is cached
        """

        obj = super(CSHLYServer, self).__new__(self, *args, **kwargs)
        obj.cache = Shove()
        obj.unshorten = cache(obj.unshorten, obj.cache, 300)
        route("/api/shorten", method='PUT')(obj.shorten)
        route("/api/unshorten/<hashed>", method='GET')(obj.unshorten)
        route("/<hashed>", method='GET')(obj.unshorten_redirect)
        obj.get_link_data = cache(obj.get_link_data, obj.cache, 1200)
        return obj

    def __init__(self, port, link_db_uri, user_db_uri, use_auth=True):
        self.port = port
        self.link_db = Shove(link_db_uri)
        self.user_db = Shove(user_db_uri)
        self.use_auth = use_auth
        if not self.use_auth and 'null' not in self.user_db:
            self.user_db['null'] = {'token': '', 'username': 'null', 'links': []}

    def get_link_data(self, hashed_link):
        """
        Used to get information on a hashed link. This function is cached

        :type hashed_link: str
        :param hashed_link: the hashed link to retrieve information on
        """

        try:
            data = self.link_db[hashed_link]
            return data
        except:
            return None

    def is_user_authenticated(self, user_id, auth_token):
        """
        Check to see if a user is authenticated or not

        :type user_id: str
        :param user_id: the users ID

        :type auth_token: str
        :param auth_token: a token used to see if a user is valid
        """

        user = self.user_db[user_id]
        if user['token'] == auth_token:
            return True
        else:
            return False

    def shorten(self):
        """
        Used to handle the shorten api endpoint
        The body of the request contains the json formatted request to shorten a url
        this function returns a json formatted response with the shortened url
        """

        data = request.body.readline()
        print "Received shorten request: {0}".format(data)
        if not data:
            abort(400, 'No data received')

        try:
            data = json.loads(data)
        except Exception, e:
            print e

        #data = json.loads(data)

        if "full_link" in data:
            if ("user_id" in data and "auth_token" in data and self.is_user_authenticated(data['user_id'], data['auth_token'])) or not self.use_auth:

                hashed = hashLink(data['full_link'])
                self.link_db[hashed] = {'lookups': 0, 'owner': data.get('user_id', 'null'), 'full_link': data['full_link']}
                self.link_db.sync()
                try:
                    self.user_db[data.get('user_id', 'null')]['links'].append(hashed)
                except:
                    self.user_db[data.get('user_id', 'null')]['links'] = [hashed, ]
                self.user_db.sync()
                return json.dumps({"shortened": hashed})
            else:
                abort(403, 'User id or auth token incorrect')

    def unshorten(self, hashed):
        """
        Used to handle the unshorten api endpoint
        This function is given a url hash and returns a json formatted response with information on that url
        """

        print "Received unshorten request: {0}".format(hashed)
        link_data = self.get_link_data(hashed)
        if link_data is None:
            return json.dumps({'error': 'Link not Found'})
        else:
            self.link_db[hashed]['lookups'] += 1
            self.link_db.sync()
            return json.dumps({'full_link': link_data['full_link'], 'lookups': link_data['lookups']})

    def unshorten_redirect(self, hashed):
        """
        Used to unshorten a hashed url given to the function and redirect the user to its destination
        Currently doesn't support https (need to fix that >_>)
        example: http://helix.ly/hashed_url -> http://full-url.com/some_random_page
        """
        link_data = self.get_link_data(hashed)
        if link_data is None:
            abort(404, 'Shortened URL not found')
        else:
            self.link_db[hashed]['lookups'] += 1

            full_link = link_data['full_link']

            redirect(full_link)
            self.link_db.sync()

    def start(self):
        """
        Called to start the wsgi server
        """
        run(reloader=DEBUG, server='eventlet', port=self.port)
        self.link_db.sync()
        self.user_db.sync()

if __name__ == "__main__":
    shortener = CSHLYServer(8080, "file://links.db", "file://users.db", use_auth=False)
    shortener.start()
