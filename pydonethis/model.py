import HTMLParser

class Base(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def from_dict(cls, info):
        return cls(**info)

    def __repr__(self):
        return '{cls}({props})'.format(
            cls=type(self).__name__,
            props=', '.join('{k}={v!r}'.format(k=k, v=v) for k, v in vars(self).items())
        )


class Team(Base):
    def __str__(self):
        return self.short_name

class Done(Base):
    def __str__(self):
        return str(self.id)

    @property
    def text(self):
        text = HTMLParser.HTMLParser().unescape(self.raw_text)
        if self.is_goal and not self.goal_completed:
            text = '[ ]' + text[2:]

        return text
