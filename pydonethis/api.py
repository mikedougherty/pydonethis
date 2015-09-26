'''
IDoneThis API implementation
'''
import sys
import functools
import urlparse
import requests
import requests.auth

from .model import Team, Done


class IDoneThisException(Exception):
    def __init__(self, detail='', **kwargs):
        self.detail = detail
        super(IDoneThisException, self).__init__(self.detail)
        self.__dict__.update(kwargs)


def paginated(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs.setdefault('page_size', 100)
        kwargs.setdefault('page', 1)
        kwargs.setdefault('order_by', None)
        return func(*args, **kwargs)
    return wrapper


def model(cls):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, PaginatedResponse):
                return ModelIterator(cls, result)
            else:
                return cls.from_dict(result)

        return wrapper

    return decorator


class TokenAuth(requests.auth.AuthBase):
    '''
    Generates an auth header for requests as:
    'Authorization: Token <token>'
    '''

    def __init__(self, token):
        try:
            '' + token
        except Exception:
            raise ValueError('Invalid token', token)

        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = "Token " + self.token
        return r


class IDoneThisClient(requests.Session):
    '''
    Implementation of the IDoneThis api.
    '''

    api_version = 'v0.1'
    api_base = 'https://idonethis.com/api'
    default_headers = {
        'accept': 'application/json'
    }

    def __init__(self, token=None, api_version=None, api_base=None):
        super(IDoneThisClient, self).__init__()

        if api_version:
            self.api_version = api_version
        if api_base:
            self.api_base = api_base

        self.headers['accept'] = 'application/json'

        if token:
            self.auth = TokenAuth(token)

    def noop(self):
        return self.get('noop/')

    @model(Team)
    def team(self, team):
        return self.get('teams/%s/' % team)

    @model(Team)
    @paginated
    def teams(self, **params):
        return self.get('teams/', params=params)

    @model(Done)
    def done(self, done):
        return self.get('dones/%s/' % done)

    @model(Done)
    @paginated
    def dones(self, **params):
        return self.get('dones/', params=params)

    @model(Done)
    def create_done(self, text, team):
        return self.post(
            'dones/',
            json=dict(raw_text=text, team=team.short_name)
        )

    @model(Done)
    def update_done(self, done):
        return self.patch(
            'dones/%s/' % done,
            json=dict(
                raw_text=done.raw_text,
                goal_completed=done.goal_completed
            )
        )

    def request(self, method, path, **kwargs):
        if urlparse.urlparse(path).scheme:
            url = path
        else:
            url = '%s/%s/%s' % (self.api_base, self.api_version, path)

        response = super(IDoneThisClient, self).request(
            method=method, url=url, **kwargs
        )

        json = response.json()

        for warning in json.get('warnings', []):
            print >>sys.stderr, 'warning:', warning

        if json.get('ok'):
            if json.get('result'):
                return json['result']
            elif json.get('results'):
                return PaginatedResponse(json, self, method, **kwargs)
            else:
                return json
        elif response.ok:
            return json
        else:
            print response
            print json
            raise IDoneThisException(**json)


class PaginatedResponse(object):
    def __init__(self, response, client, method, **kwargs):
        self.next = response['next']
        self.previous = response['previous']
        self.count = response['count']
        self.results = response['results']

        self.client = client
        self.method = method
        self.kwargs = kwargs

    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.results:
            yield item

        if self.next:
            print 'Requesting next page:', self.next
            response = self.client.request(self.method, self.next, **self.kwargs)
            if isinstance(response, PaginatedResponse):
                for item in response:
                    yield item
            else:
                yield response


class ModelIterator(PaginatedResponse):
    def __init__(self, cls, response):
        self.cls = cls
        super(ModelIterator, self).__init__(
            response=dict(
                next=response.next,
                previous=response.previous,
                count=response.count,
                results=response.results
            ),
            client=response.client,
            method=response.method,
            **response.kwargs
        )

    def __iter__(self):
        for item in super(ModelIterator, self).__iter__():
            yield self.cls.from_dict(item)
