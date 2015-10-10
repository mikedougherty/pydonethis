import os

from pydonethis import VERSION
from pydonethis.api import IDoneThisClient

from cement.core import foundation, output, controller
from cement.utils.misc import init_defaults


defaults = init_defaults('pydonethis', 'idonethis')
defaults['pydonethis']['debug'] = False
defaults['idonethis']['team'] = None
defaults['idonethis']['token'] = os.environ.get('IDONETHIS_TOKEN')


class ClientMixin(object):
    def client(self):
        return IDoneThisClient(token=self.app.config.get('idonethis', 'token'))

    def validate_token(self):
        with self.client() as c:
            c.noop()

    def get_team(self):
        with self.client() as c:
            team = self.app.config.get('idonethis', 'team')
            if team is None:
                teams = c.teams()
                if len(teams) != 1:
                    raise Exception("Please specify a team name (-t/--team)")

                team_obj = iter(teams).next()
            else:
                team_obj = c.team(team)
            return team_obj

    def get_done(self):
        if self.app.pargs.done_id is None:
            return None

        with self.client() as c:
            return c.done(self.app.pargs.done_id)

    def get_dones(self):
        with self.client() as c:
            team = self.get_team()

            done_filters = dict(team=team.short_name)
            for field in ('done_date_before', 'done_date_after', 'updated_before', 'updated_after', 'tags', 'owner'):
                value = getattr(self.app.pargs, field, None)
                if value is not None:
                    done_filters[field] = value

            dones = c.dones(**done_filters)

        for done in dones:
            if self.app.pargs.todo and done.goal_completed:
                continue
            if self.app.pargs.done and not done.goal_completed:
                continue

            yield done


class PDTBaseController(controller.CementBaseController):
    class Meta:
        label = 'base'
        description = "pydonethis 'an idonethis client'"
        arguments = [
            (['-v', '--version'], dict(action='version', version='pydonethis v{}'.format(VERSION))),
            (['--token'], dict(action='store', metavar='TOKEN', help='API token for idonethis.com (default: $IDONETHIS_TOKEN)')),
            (['-t', '--team'], dict(action='store', metavar='TEAM', help='Team the task will be added to (not necessary if you only have one)')),
        ]

    @controller.expose(hide=True)
    def default(self):
        self.app.args.print_help()


class PDTDoneController(controller.CementBaseController, ClientMixin):
    class Meta:
        label = 'done'
        arguments = [
            (['-i', '--id'], dict(action='store', dest='done_id', metavar='TASK', help='ID of a task to mark as done')),
            (['task'], dict(nargs='*', help='Something you\'ve finished')),
        ]

    @controller.expose(help="Add or update a task/goal")
    def done(self):
        self.validate_token()
        task_text = ' '.join(self.app.pargs.task)

        done = self.get_done()
        if done is None:
            self.app.render([self.create_done(task_text)])
        else:
            if done.goal_completed or not done.is_goal:
                # Nothing to do
                self.app.close(1)
            else:
                done.raw_text = '[x]' + (task_text or done.raw_text.replace('[]', '', 1))
                done.goal_completed = True
                self.app.render([self.update_done(done)])

    @controller.expose(help="Add a goal")
    def todo(self):
        self.app.pargs.task.insert(0, '[]')
        self.done()

    def update_done(self, done):
        with self.client() as c:
            return c.update_done(done)

    def create_done(self, text):
        with self.client() as c:
            return c.create_done(text, self.get_team())

class PDTListController(controller.CementBaseController, ClientMixin):
    class Meta:
        label = 'list'
        description = "List tasks and goals"
        arguments = [
            (['-d', '--done-date'], dict(action='store', metavar='DATE', help='Specify a date (YYYY-MM-DD, "today", or "yesterday")')),
            (['--done-date-before'], dict(action='store', metavar='DONE_BEFORE', help='Show things done before YYYY-MM-DD.')),
            (['--done-date-after'], dict(action='store', metavar='DONE_AFTER', help='Show things done after YYYY-MM-DD.')),
            (['--updated-before'], dict(action='store', metavar='UPDATED_BEFORE', help='Show things updated before YYYY-MM-DDTHH:MM:SS.')),
            (['--updated-after'], dict(action='store', metavar='UPDATED_AFTER', help='Show things updated after YYYY-MM-DDTHH:MM:SS.')),
            (['--tags'], dict(action='store', metavar='TAGS', help='Show things matching TAGS (comma-separated list, e.g. tag1,tag2)')),
            (['--owner'], dict(action='store', metavar='OWNER', help='Only show tasks by OWNER')),
            (['--todo'], dict(action='store_true', help='Only show incomplete goals')),
            (['--done'], dict(action='store_true', help='Only show dones and completed goals')),
        ]

    @controller.expose(help="List dones")
    def list(self):
        self.validate_token()
        self.app.render(self.get_dones())


class PDTTextOutputHandler(output.CementOutputHandler):
    class Meta:
        label = 'pdt_text'

    def render(self, data, template):
        for done in data:
            print u"{}: {}".format(done.id, done.text)


class PDTApp(foundation.CementApp):
    class Meta:
        label = 'pydonethis'
        config_defaults = defaults
        extensions = ['yaml_configobj']
        config_handler = 'yaml_configobj'
        arguments_override_config = True
        output_handler = 'pdt_text'
        base_controller = 'base'
        handlers = [
            PDTBaseController, PDTDoneController, PDTListController, PDTTextOutputHandler
        ]

def main():
    with PDTApp() as app:
        app.run()


if __name__ == '__main__':
    main()
