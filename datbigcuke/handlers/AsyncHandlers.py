""" Container module for asynchronous request handling classes.

@TODO(halstea2): Look into used the @asynchronous decorator
"""

__author__ = 'Joshua Halstead'
__copyright__ = 'Copyright 2014 Datbigcuke Project'
__email__ = 'halstea2@illinois.edu'

import tornado.web
import tornado.auth
import uuid
import datetime
import json
import urllib
import sys
import ConfigParser

# For test async handler only
import tornado.httpclient

from datetime import datetime, date
from tornado import gen

from datbigcuke.scheduler import *
from datbigcuke.handlers.BaseHandlers import WebResource
from datbigcuke.handlers.BaseHandlers import WebModule
from datbigcuke.handlers.BaseHandlers import AsyncRequestHandler
from datbigcuke.handlers.BaseHandlers import WebRequestHandler
from datbigcuke.entities import User
from datbigcuke.entities import UserRepository
from datbigcuke.entities import Deadline
from datbigcuke.entities import DeadlineMetadata
from datbigcuke.entities import DeadlineRepository
from datbigcuke.entities import DeadlineMetadataRepository
from datbigcuke.entities import Group
from datbigcuke.entities import GroupRepository
from datbigcuke.entities import TermRepository
from datbigcuke.entities import ClassRepository
from datbigcuke.cukemail import CukeMail


class TestHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def post(self):
        data = self.get_argument("data", default=None)
        if not data:
            print str(datetime.datetime.now()) + " Received: None"
            self.write(json.dumps({"date": str(datetime.datetime.now()),
                                   "Status": 404}))

        print str(datetime.datetime.now()) + " Received: " +\
              str(json.dumps(data,
                             sort_keys=True,
                             indent=4,
                             separators=(',', ': ')
                 )
        )

        http_client = tornado.httpclient.AsyncHTTPClient()
        response = yield http_client.fetch("http://google.com")
        self.write(json.dumps({"date": str(datetime.datetime.now()),
                               "response": str(response)}))
# ../group/[id]
#Required Handlers


# Example raw json call
#    <button onclick="(
#        function (e, obj) {
#            var data1 = {};
#            data1['group'] = 1234;
#            $.ajax({
#                type: 'POST',
#                url: '/leave-group',
#                data: {'data': JSON.stringify(data1)},
#                dataType: 'json',
#                success: function(data) {
#                    console.log(data);
#                },
#                error: function(data) {
#                    console.log(data);
#                }
#            });
#        })(event, this)"> Test Leave Group </button>


# - Add member to group
#   - Data: Group ID, New User ID
#   - Server-Side Checks:
#       - New User ID must be in same parent group as current user ID
#       - Current user must be member of group ID
class AddMemberHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        print "args:",self.request.arguments
        curr_user = self.get_current_user()
        values =  self.get_argument("data", default=None)

        if not curr_user or not values:
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"group_id" not in values or u"user_email" not in values:
            print "Malformed request detected."
            return False

        # Malformed request
        group_id = values[u"group_id"]
        new_user_email = values[u"user_email"]
        if not group_id or not new_user_email:
            print "Required data is missing."
            return False

        user_repo = UserRepository()
        member_list = user_repo.get_members_of_group(group_id)
        user_repo.close()
        if not any(member.id == curr_user.id for member in member_list):
            print "User is not a member of the associated group."
            return False

        group_repo = GroupRepository()
        parent_group = group_repo.get_supergroup_of_group(group_id)
        group_repo.close()
        if not group_repo:
            print "Cannot add member to the root group."
            return False

        user_repo = UserRepository()
        parent_member_list = user_repo.get_members_of_group(parent_group.id)
        user_repo.close()
        if not any(member.id == curr_user.id for member in parent_member_list):
            print "New user is not a member of the supergroup."
            return False

        # New user is already a member of the group
        new_user_repo = UserRepository()
        new_user = new_user_repo.get_user_by_email(new_user_email)
        new_user_repo.close()
        if not new_user:
            print "New user doesn't exist."
            return False

        if not new_user.groups:
            print "New user isn't a member of any groups."
            return False

        if group_id in new_user.groups:
            print "New user is already already a member of the group."
            return False

        group_repo = GroupRepository()
        group = group_repo.fetch(group_id)
        group_repo.close()
        if not group:
            print "Group doesn't exist"
            return False

        # 1 => Public
        if group.type == 1:
            print "Cannot add members to public groups"
            return False

        return True

    def _perform_request(self, user, name, values):
        group_id = values[u"group_id"]
        new_user_email = values[u"user_email"]

        group_repo = GroupRepository()
        group = group_repo.fetch(group_id)
        group_repo.close()

        new_user_repo = UserRepository()
        new_user = new_user_repo.get_user_by_email(new_user_email)
        new_user_repo.add_user_to_group(new_user, group)
        new_user_repo.close()

        self._persist_user(new_user)

        result = {}

        result['name'] = new_user.name
        result['email'] = new_user.email
        result['iconURL'] = new_user.iconSmallURL
 
        self.write(json.dumps(result))
        self.flush
        self.finish

# - Add subgroup to group
# - Data: Group ID, New Group Name, New Group Description
class GetCoursesHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def get(self):
        query = self.get_argument("query", default=None)
        group = self.get_argument("group", default=None)

        if not query or not group:
            print "Invalid Request. Parameters Missing"
            return

        values = {'query': query, 'group': group}
        self._perform_request(None, "", values)
        pass

    def _perform_request(self, user, name, values):
        gr = GroupRepository()
        group = gr.fetch(values['group'])
        gr.close()
        if group is None or group.academic_entity_type != 'term':
            print "Invalid group id."
            return
        tr = TermRepository()
        term = tr.fetch(group.academic_entity_id)
        tr.close()
        if term is None:
            print "Requested term not found."
            return
        cr = ClassRepository()
        classes = cr.find_classes_with_name_prefix(term, values['query'])
        cr.close()
        self.write(json.dumps([{"value":klass.name, "class_id":klass.id}
                              for klass in classes]))
        



# - Add subgroup to group
# - Data: Group ID, New Group Name, New Group Description
class AddSubgroupHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values = self.get_argument("data", default=None)

        if not curr_user or not values:
            print "Invalid Request. Parameters Missing"
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            print "Invalid Request. Parameters Empty"
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"group_id" not in values or u"group_name" not in values:
            return False

        # Malformed request
        group_id = values[u"group_id"]
        new_group = values[u"group_name"]
        if not group_id or not new_group:
            return False

        return True

    def _perform_request(self, user, name, values):
        group_id = values[u"group_id"]
        new_group_name = values[u"group_name"]
        new_group_desc = values[u"group_description"]

        curr_user = self.get_current_user()

        gr = GroupRepository()
        new_group = Group()
        new_group.name = new_group_name
        new_group.description = new_group_desc
        new_group.type = 0 # private group
        new_group.maintainerId = curr_user.id
        new_group = gr.persist(new_group)

        # assign the subgroup as a child of the parent group
        gr.add_group_as_subgroup(group_id, new_group.id)
        gr.close()

        # assign the user as a member of the subgroup
        user_repo = UserRepository()
        user_repo.add_user_to_group(curr_user, new_group)
        user_repo.close()

        self._persist_user(curr_user)

        result = {}

        result['id'] = new_group.id
        result['name'] = new_group.name
        user_repo2 = UserRepository()
        user = user_repo2.fetch(new_group.maintainerId)
        user_repo2.close()
        result['maintainer'] = user.name
        
        self.write(json.dumps(result))
        self.flush
        self.finish


# - Add subgroup to group
# - Data: Group ID, New Group Name, New Group Description
class DeleteDeadlineHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values = self.get_argument("data", default=None)

        if not curr_user or not values:
            print "Invalid Request. Parameters Missing"
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            print "Invalid Request. Parameters Empty"
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"deadline_id" not in values:
            return False

        # Malformed request
        deadline_id = values["deadline_id"]
        if not deadline_id:
            return False

        return True

    def _perform_request(self, user, name, values):
        print "Performing request"
        deadline_id = values["deadline_id"]
        curr_user = self.get_current_user()

        dr = DeadlineRepository()
        gr = GroupRepository()

        deadline = dr.deadline_for_user(curr_user.id, deadline_id)
        group = gr.fetch(deadline.group_id)
        if(group.maintainerId == curr_user.id or group.type == 'PER'):
            dr.delete(deadline.id)
        else:
            dr.drop_metadata(deadline)


# - Send email after meeting has been scheduled
# - Data: Group ID, Email Message, Time
class AddDeadlineHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values = self.get_argument("data", default=None)

        if not curr_user or not values:
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            return

        self._perform_request(curr_user, "", values)

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"group_id" not in values or u"name" not in values or u"deadline" not in values or u"notes" not in values:
            return False

        # Malformed request
        group_id = values[u"group_id"]
        name = values[u"name"]
        notes = values[u"notes"]
        if not group_id or not name:
            return False

        return True

    def _perform_request(self, user, name, values):
        group_id = values[u"group_id"]
        name = values[u"name"]
        deadline = values[u"deadline"]
        notes = values[u"notes"]
        curr_user = self.get_current_user()

        dr = DeadlineRepository()
        gr = GroupRepository()
        group = gr.fetch(group_id)
        gr.get_group_maintainer(group)

        new_deadline = Deadline()
        new_deadline.meta = DeadlineMetadata()

        new_deadline.name = name
        new_deadline.group_id = group_id
        new_deadline.deadline = datetime.strptime(deadline, u'%m/%d/%Y %I:%M %p') # private group
        if(group.maintainer and group.maintainer.id == user.id):
            new_deadline.type = 'END'
        else:
            new_deadline.type = 'PER'
        new_deadline.meta.user_id = user.id
        new_deadline.meta.notes = notes
        new_deadline = dr.persist(new_deadline)

        dr.close()

        result = {}

        result['id'] = new_deadline.id
        result['name'] = new_deadline.name
        result['group'] = new_deadline.group
        result['type'] = new_deadline.type
        result['time'] = new_deadline.deadline.strftime(u'%A %b %d, %H:%M')
        result['notes'] = new_deadline.meta.notes
        result['can_edit'] = (new_deadline.type == "PER" or (group.maintainerId == user.id and new_deadline.type == "END"))

        self.write(json.dumps(result))
        self.flush
        self.finish

# - Add course for user
# - Data: Course Name
class AddCourseHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values = self.get_argument("data", default=None)

        if not curr_user or not values:
            print "Invalid Request. Parameters Missing"
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            print "Invalid Request. Parameters Empty"
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"class_id" not in values:
            return False

        # Malformed request
        course_name = values[u"class_id"]
        if not course_name:
            return False

        return True

    def _perform_request(self, user, name, values):
        class_id = values[u"class_id"]

        # get the appropriate class
        cr = ClassRepository()
        klass = cr.fetch(class_id)
        cr.close()

        if not klass:
            print "Invalid class id"
            return

        root_group = self.get_root_group()
        gr = GroupRepository()
        if not klass.group:
            # create the group
            group = Group()
            group.name = klass.name
            group.type = 0
            group.academic_entity_id = class_id
            group = gr.persist(group)
            gr.add_group_as_subgroup(root_group.id, group.id)
            klass.group = group.id
            # associate with the class
            cr = ClassRepository()
            cr.persist(klass)
            cr.close()
        else:
            group = gr.fetch(klass.group)
        gr.close()

        # assign the user as a member of the subgroup
        user.groups = user.groups + [group.id]
        self._persist_user(user)

        result = {}

        result['id'] = group.id
        result['name'] = group.name
        result['maintainer'] = ""

        self.write(json.dumps(result))

# - Send email for meeting
# - Data: Meeting Time, Meeting Message
class SendEmailHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values = self.get_argument("data", default=None)

        if not curr_user or not values:
            print "Invalid Request. Parameters Missing"
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            print "Invalid Request. Parameters Empty"
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, curr_user, name, values):
        # Malformed request
        if u"meeting_time" not in values or "meeting_message" not in values or "group_id" not in values:
            return False

        # Malformed request
        meeting_time  = values[u"meeting_time"]
        meeting_message = values[u"meeting_message"]
        group_id = values[u"group_id"]
        if not meeting_time or not meeting_message or not group_id:
            return False

        return True

    def _perform_request(self, user, name, values):
        meeting_time  = values[u"meeting_time"]
        meeting_message = values[u"meeting_message"]
        group_id = values[u"group_id"]
        curr_user = self.get_current_user()

        ur = UserRepository()
        users = ur.get_members_of_group(group_id)        
        ur.close()

        gr = GroupRepository()
        group = gr.fetch(group_id)
        gr.close()

        cm = CukeMail()
        cm.subject(group.name + " meeting @ " + meeting_time)
        cm.message(meeting_message)
        cm.send([user.email for user in users])

        self._persist_user(curr_user)

class GetDeadlinesHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def get(self):
        print "args:",self.request.arguments

        user = self.get_current_user()
        prefix = self.get_argument("query")
        group_id = self.get_argument("group")

        if not user or not prefix or not group_id:
            print "Query is missing required data."
            return

        if not self._valid_request(user, prefix, group_id):
            print "Invalid request made."
            return

        return_data = self._perform_request(user, prefix, group_id)

        if return_data:
            self.write(return_data)
        else:
            self.write({})


    def _valid_request(self, user, prefix, group_id):
        group_repo = GroupRepository()
        group = group_repo.fetch(group_id)
        group_repo.close()

        if not group:
            print "Group doesn't exist."
            return False

        user_repo = UserRepository()
        member_list = user_repo.get_members_of_group(group_id)
        user_repo.close()

        if not any(member.id == user.id for member in member_list):
            print "User is not a member of the associated group."
            return False

        return True

    def _perform_request(self, user, prefix, group_id):
        group_repo = GroupRepository()
        group = group_repo.fetch(group_id)
        group_repo.close()

        deadline_repo = DeadlineRepository()
        deadline_list = deadline_repo.find_deadlines_with_name_prefix(group_id, prefix)
        deadline_repo.close()

        formatted_names = [{"value": deadline.name} for deadline in deadline_list]

        return json.dumps(formatted_names)

class GetUsersHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def get(self):
        print "args:",self.request.arguments

        user = self.get_current_user()
        prefix = self.get_argument("query")
        group_id = self.get_argument("group")

        if not user or not prefix or not group_id:
            print "Query is missing required data."
            return

        if not self._valid_request(user, prefix, group_id):
            print "Invalid request made."
            return

        return_data = self._perform_request(user, prefix, group_id)

        if return_data:
            self.write(return_data)
        else:
            self.write({})


    def _valid_request(self, user, prefix, group_id):
        group_repo = GroupRepository()
        group = group_repo.fetch(group_id)
        group_repo.close()

        if not group:
            print "Group doesn't exist."
            return False

        user_repo = UserRepository()
        member_list = user_repo.get_members_of_group(group_id)
        user_repo.close()

        if not any(member.id == user.id for member in member_list):
            print "User is not a member of the associated group."
            return False

        group_repo = GroupRepository()
        parent_group = group_repo.get_supergroup_of_group(group_id)
        group_repo.close()
        if not group_repo:
            print "Attempting to add membrer to the root."
            return False

        user_repo = UserRepository()
        parent_member_list = user_repo.get_members_of_group(parent_group.id)
        user_repo.close()
        if not any(member.id == user.id for member in parent_member_list):
            print "New user is not a member of the supergroup."
            return False

        return True

    def _perform_request(self, user, prefix, group_id):
        group_repo = GroupRepository()
        parent = group_repo.get_supergroup_of_group(group_id)
        group_repo.close()

        user_repo = UserRepository()
        user_list = user_repo.find_users_with_email_prefix(user.id, parent.id, prefix)
        user_repo.close()

        formatted_names = [{"value": u.email} for u in user_list]

        return json.dumps(formatted_names)



## - Schedule endpoint
class ScheduleHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    # @TODO(halstea2) We chould create a 'complex' async handler base that
    # is aware of a dictionary of values
    def post(self):
        curr_user = self.get_current_user()
        values =  self.get_argument("data", default=None)

        if not curr_user or not values:
            return

        # We don't need the 'name' field. It's encoded in the data dictionary
        # Keys are unicode after json.loads conversion
        values = json.loads(values)
        if not self._valid_request(curr_user, "", values):
            return

        self._perform_request(curr_user, "", values)
        pass

    def _valid_request(self, user, name, values):
        # Malformed request
        if u"group_members" not in values or u"deadline" not in values or u"duration" not in values or u"off_limits_start" not in values or u"off_limits_end" not in values:
            return False

        # Malformed request
        group_members = values[u"group_members"]
        deadline = values[u"deadline"]
        duration = values[u"duration"]
        off_limits_start = values[u"off_limits_start"]
        off_limits_end = values[u"off_limits_end"]
        if not group_members or not deadline or not duration or not off_limits_start or not off_limits_end:
            return False

        #real deadline
        dr = DeadlineRepository()
        dl = dr.fetch(deadline)
        dr.close()

        if not dl:
            sys.stderr.write("invalid deadline id: " + str(dl))
            return False

        #real users
        for email in group_members:
            new_user_repo = UserRepository()
            new_user = new_user_repo.get_user_by_email(email)
            new_user_repo.close()
            if not new_user:
                sys.stderr.write("invalid email: " + email)
                return False


        return True

    def _perform_request(self, user, name, values):

        parser = ConfigParser.ConfigParser()
        parser.read('./config/app.conf')

        section = 'General'
        client_id = parser.get(section, 'client_id')
        client_secret = parser.get(section, 'client_secret')

        group_emails = values[u"group_members"]
        deadline = values[u"deadline"]
        duration = values[u"duration"]
        off_limits_start = values[u"off_limits_start"]
        off_limits_end = values[u"off_limits_end"]

        #real deadline
        dr = DeadlineRepository()
        deadline = dr.fetch(deadline).deadline
        dr.close()

        duration = timedelta(minutes=int(duration))

        off_limits_start = datetime.strptime(off_limits_start, u'%I:%M %p').time()
        off_limits_end = datetime.strptime(off_limits_end, u'%I:%M %p').time()

        group_members = {}

        for email in group_emails:
            new_user_repo = UserRepository()
            new_user = new_user_repo.get_user_by_email(email)
            new_user_repo.close()

            #must have refresh token
            if not new_user.refreshTok:
                sys.stderr.write(email + "has not given google permission to view calendar information" + '\n')
                None.hi()

            ref_tok = new_user.refreshTok
            #sys.stderr.write("refresh_token = " + ref_token + '\n\n')

            #get access token
            url = "https://accounts.google.com/o/oauth2/token"
            access_token_request = "refresh_token=" + ref_tok + "&" +\
                      "client_id=" + client_id + "&" +\
                      "client_secret=" + client_secret + "&" +\
                      "grant_type=refresh_token"\

            sys.stderr.write("access_token request = " + access_token_request + '\n\n')

            http_client = tornado.httpclient.HTTPClient()
            http_request = tornado.httpclient.HTTPRequest(url, 'POST', body=access_token_request)
            response = http_client.fetch(http_request)

            #handle the access token response
            #sys.stderr.write("response = " + str(response) + '\n\n')

            data = json.loads(response.body)
            a_token = data['access_token']
            sys.stderr.write("access_token = " + a_token + '\n\n')

            events = []

            cal_list_http_client = tornado.httpclient.HTTPClient()
            response2 = cal_list_http_client.fetch("https://www.googleapis.com/calendar/v3/users/me/calendarList?access_token=" + a_token)

            #handle google calendar list
            #sys.stderr.write("calendar list response = " + str(response2) + '\n\n')

            data2 = json.loads(response2.body)
            #sys.stderr.write(str(data2) + '\n\n')

            for calendar in data2['items']:

                calendar_id = calendar['id']

                #calendars without the 'selected' attribute appear to be invalid
                if 'selected' not in calendar:
                    continue

                sys.stderr.write("Reading calendar: " + str(calendar_id) + '\n')

                event_list_http_client = tornado.httpclient.HTTPClient()
                response3 = event_list_http_client.fetch("https://www.googleapis.com/calendar/v3/calendars/" + calendar_id + "/events?singleEvents=true&access_token=" + a_token)

                #handle event list
                #sys.stderr.write("event list response = " + str(response3) + '\n\n')

                data3 = json.loads(response3.body)
                #sys.stderr.write(str(data3) + '\n\n')

                #add each event
                for event in data3['items']:
                    #I have many doubts this will work for arbitrary calendars
                    #and I am certain it will error for other timezones.....
                    if 'start' not in event:
                        continue
                    if 'dateTime' not in event['start']:
                        continue
                    if 'end' not in event:
                        continue
                    if 'dateTime' not in event['end']:
                        continue
                    start = datetime.strptime(event['start']['dateTime'][:19], u'%Y-%m-%dT%H:%M:%S')
                    end = datetime.strptime(event['end']['dateTime'][:19], u'%Y-%m-%dT%H:%M:%S')
                    events.append((start, end))
                    #sys.stderr.write("Event found: " + str(start) + " - " + str(end) + '\n')
                sys.stderr.write('\n')

            group_members[email] = events
        
        meets = schedule_meeting(group_members, deadline, duration, off_limits_start, off_limits_end)

        result = []
        for meet in meets:
            result.append(meet[0].strftime(u'%A %b %d (%Y) at %I:%M %p'))

        i = 0
        real = []
        for r in result:
            if i % 4 == 0:
                real.append(r)
            i+=1

        self.write(json.dumps(real[:15]))
        self.flush
        self.finish
    

class EditMetadataNotesHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def post(self):
        user = self.get_current_user()
        name = self.get_arguments("name", None)
        deadline_id = self.get_arguments("pk", None)
        values = self.get_arguments("value", None)

        # 'Logged-in' user must be defined
        if not user:
            print "no user"
            return

        # Name list must not be empty
        if not name:
            print "no name"
            return

        # PK list must not be empty
        if not deadline_id:
            print "no deadline_id"
            return
        deadline_id = int(deadline_id[0].decode("utf-8"))

        # Value list must be defined
        if not values:
            print "no values"
            return

        name = name[0].decode("utf-8")
        if not self._valid_request(user, name, deadline_id, values):
            return

        self._perform_request(user, name, deadline_id, values)


    def _valid_request(self, user, attr, deadline_id, value):
        # User parameters must be defined
        if not user or not attr or not value or not deadline_id:
            print "Invalid Request. Parameters Missing"
            return False

        notes = value[0].decode("utf-8")

        # The deadline associated with the deadline_id must exist
        deadline_repo = DeadlineRepository()
        dead = deadline_repo.deadline_for_user(user.id, deadline_id)
        deadline_repo.close()

        if not dead or not dead.meta or not dead.group_id:
            print "Something is wrong with the deadline object."
            return False

        group_repo = GroupRepository()
        group = group_repo.fetch(dead.group_id)
        group_repo.close()

        if not group:
            print "Associated group doesn't exist."
            return False

        if not (dead.type == "PER" or
                (group.maintainerId == dead.group_id and dead.type == "END")):
            print "User cannot modify this deadline"
            return False

        return True
    
    def _perform_request(self, user, attr, deadline_id, value):
        notes = value[0].decode("utf-8")

        deadline_repo = DeadlineRepository()
        dead = deadline_repo.deadline_for_user(user.id, deadline_id)
        dead.meta.notes = notes
        deadline_repo.persist(dead)
        deadline_repo.close()

class EditMetadataNameHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def post(self):
        user = self.get_current_user()
        name = self.get_arguments("name", None)
        deadline_id = self.get_arguments("pk", None)
        values = self.get_arguments("value", None)

        # 'Logged-in' user must be defined
        if not user:
            print "no user"
            return

        # Name list must not be empty
        if not name:
            print "no name"
            return

        # PK list must not be empty
        if not deadline_id:
            print "no deadline_id"
            return
        deadline_id = int(deadline_id[0].decode("utf-8"))

        # Value list must be defined
        if not values:
            print "no values"
            return

        name = name[0].decode("utf-8")
        if not self._valid_request(user, name, deadline_id, values):
            return

        self._perform_request(user, name, deadline_id, values)


    def _valid_request(self, user, attr, deadline_id, value):
        # User parameters must be defined
        if not user or not attr or not value or not deadline_id:
            print "Invalid Request. Parameters Missing"
            return False

        new_name = value[0].decode("utf-8")

        # The deadline associated with the deadline_id must exist
        deadline_repo = DeadlineRepository()
        dead = deadline_repo.deadline_for_user(user.id, deadline_id)
        deadline_repo.close()

        if not dead or not dead.name or not dead.group_id:
            print "Something is wrong with the deadline object."
            return False

        group_repo = GroupRepository()
        group = group_repo.fetch(dead.group_id)
        group_repo.close()
        if not group:
            print "Associated group doesn't exist."
            return False

        if not (dead.type == "PER" or
                (group.maintainerId == dead.group_id and dead.type == "END")):
            print "User cannot modify this deadline"
            return False

        return True
    
    def _perform_request(self, user, attr, deadline_id, value):
        new_name = value[0].decode("utf-8")

        deadline_repo = DeadlineRepository()
        dd = deadline_repo.deadline_for_user(user.id, deadline_id)
        dd.name = new_name
        deadline_repo.persist(dd)
        deadline_repo.close()

class EditMetadataTimeHandler(AsyncRequestHandler):
    @tornado.web.authenticated
    def post(self):
        user = self.get_current_user()
        name = self.get_arguments("name", None)
        deadline_id = self.get_arguments("pk", None)
        values = self.get_arguments("value", None)

        # 'Logged-in' user must be defined
        if not user:
            print "no user"
            return

        # Name list must not be empty
        if not name:
            print "no name"
            return

        # PK list must not be empty
        if not deadline_id:
            print "no deadline_id"
            return
        deadline_id = int(deadline_id[0].decode("utf-8"))

        # Value list must be defined
        if not values:
            print "no values"
            return

        if not self._valid_request(user, "time", deadline_id, values):
            return

        self._perform_request(user, "time", deadline_id, values)


    def _valid_request(self, user, attr, deadline_id, value):
        # User parameters must be defined
        if not user or not attr or not value or not deadline_id:
            print "Invalid Request. Parameters Missing"
            return False

        new_time = value[0].decode("utf-8")

        # Strip the 0000- year off the time.
        new_time = datetime.strptime(new_time[5:], "%m-%d %H:%M")
        # Add the correct year
        new_time = new_time + (date(datetime.now().year, 1, 1) - date(new_time.year, 1, 1))
        if new_time < datetime.now():
            print "Invalid time"
            return False

        # The deadline associated with the deadline_id must exist
        deadline_repo = DeadlineRepository()
        dead = deadline_repo.deadline_for_user(user.id, deadline_id)
        deadline_repo.close()

        if not dead or not dead.name or not dead.group_id:
            print "Something is wrong with the deadline object."
            return False

        group_repo = GroupRepository()
        group = group_repo.fetch(dead.group_id)
        group_repo.close()
        if not group:
            print "Associated group doesn't exist."
            return False

        if not (dead.type == "PER" or
                (group.maintainerId == dead.group_id and dead.type == "END")):
            print "User cannot modify this deadline"
            return False

        return True
    
    def _perform_request(self, user, attr, deadline_id, value):
        new_time = value[0].decode("utf-8")
        # Strip the 0000- year off the time.
        new_time = datetime.strptime(new_time[5:], "%m-%d %H:%M")
        # Add the correct year
        new_time = new_time + (date(datetime.now().year, 1, 1) - date(new_time.year, 1, 1))

        deadline_repo = DeadlineRepository()
        dead = deadline_repo.deadline_for_user(user.id, deadline_id)
        dead.deadline = new_time
        deadline_repo.persist(dead)
        deadline_repo.close()



# /profile Request Handlers

# - Edit Name
#   - Data: Name
#   - Server-side Checks: None
class UpdateNameHandler(AsyncRequestHandler):
    """Async Handler for updating a user's name"""

    # Assumptions: User is authenticated. attr is string (decoded to utf-8).
    def _valid_request(self, user, attr, value):
        """Verify that the 'update name' request is valid"""
        if not hasattr(user, attr):
            return False

        if len(value) != 1:
            return False

        return True

    # Assumption: User is authenticated. attr exists. Value is list of length 1
    def _perform_request(self, user, attr, value):
        """Perform the update request. For simple (read: single attribute
        updates the 'name' is the attribute and the 'value' is a list of len 1
        containing the value. This isn't the case for multi-attribute edits."""

        value = value[0].decode("utf-8")
        setattr(user, attr, value)
        self._persist_user(user)


# - Edit Email
#   - Data: Email
#   - Server-side Checks:
#       - Require email activation
#       - Clear cookies
class UpdateEmailHandler(AsyncRequestHandler):
    """Async Handler for updating a user's email"""

    # Assumptions: User is authenticated. attr is string (decoded to utf-8).
    def _valid_request(self, user, attr, value):
        """Verify that the 'update email' request is valid"""
        if not hasattr(user, attr):
            print "attr not found"
            return False

        if len(value) != 1:
            print "value not found"
            return False

        return True

    # Assumption: User is authenticated. attr exists. Value is list of length 1
    def _perform_request(self, user, attr, value):
        """Perform the update request. For simple (read: single attribute
        updates the 'name' is the attribute and the 'value' is a list of len 1
        containing the value. This isn't the case for multi-attribute edits."""

        value = value[0].decode("utf-8")
        setattr(user, attr, value)

        unique = str(uuid.uuid4())
        user.confirmed = False
        user.confirmUUID = unique

        self._persist_user(user)

        ## Send a verification email to the user
        m = CukeMail()
        m.send_verification(unique, user.email)
        self.clear_cookie(self.cookie_name)

# - receives the request from the client to authenticate the users calender
# - Server-side Checks:
#   - This is a valid user
class GoogleAuthHandler( WebRequestHandler ):
    
    @tornado.web.authenticated
    def post( self ):
        user = self.get_current_user()

        # 'Logged-in' user must be defined
        if not user:
            return

        parser = ConfigParser.ConfigParser()
        parser.read('./config/app.conf')

        section = 'General'
        client_id = parser.get(section, 'client_id')
        client_secret = parser.get(section, 'client_secret')
        auth_redirect_api = parser.get(section, 'auth_redirect_api')

        #construct the url to redirect the user to
        #that asks them to give us permission
        endpoint = "https://accounts.google.com/o/oauth2/auth?"
        request =  {'redirect_uri': auth_redirect_api,
                    'response_type': "code",
                    'client_id': client_id,
                    'scope': "https://www.googleapis.com/auth/calendar.readonly",
                    'access_type': "offline",
                    'approval_prompt': "force",
                    'state': user.id}

        sys.stderr.write("Redirecting to: " + endpoint + urllib.urlencode(request) + '\n')

        #send back the url
        self.write(endpoint + urllib.urlencode(request))
        self.flush
        self.finish


# - receives the response from Google
# - Server-side Checks:
#   - If the result is an error
#   - If not, uses the authentication code to get a refresh key, and stores it
class GoogleResponseHandler( WebRequestHandler ):
    
    def get( self ):

        #if there was an error, print it and return
        if self.get_query_argument("error", default=False):
            sys.stderr.write("Google auth returned an error: " + self.get_query_argument("error") + '\n')
            return

        #if we are receiving a refresh token, store it
        if self.get_query_argument("access_token", default=False):
            sys.stderr.write("access_token = " + self.get_query_argument("access_token") + '\n')
            sys.stderr.write("refresh_token = " + self.get_query_argument("refresh_token") + '\n')


            return
        #otherwise, ask for the refresh token
        else:
            sys.stderr.write("code = " + self.get_query_argument("code") + '\n')
            sys.stderr.write("state = " + self.get_query_argument("state") + '\n')

            #form the request
            parser = ConfigParser.ConfigParser()
            parser.read('./config/app.conf')

            section = 'General'
            client_id = parser.get(section, 'client_id')
            client_secret = parser.get(section, 'client_secret')
            auth_redirect_api = parser.get(section, 'auth_redirect_api')

            url = "https://accounts.google.com/o/oauth2/token"
            request = "code=" + self.get_query_argument("code") + "&" +\
                      "client_id=" + client_id + "&" +\
                      "client_secret=" + client_secret + "&" +\
                      "redirect_uri=" + auth_redirect_api + "&" +\
                      "grant_type=authorization_code"\

            sys.stderr.write("refresh_token request = " + request + '\n')

            def handle_response(response):
                sys.stderr.write("response = " + str(response) + '\n')

                data = json.loads(response.body)
                r_token = data['refresh_token']
                user_id = self.get_query_argument("state")

                sys.stderr.write("user_id = " + str(user_id) + '\n')
                sys.stderr.write("refresh_token = " + r_token + '\n')

                user_repo = UserRepository()
                user = user_repo.fetch(user_id)
                user.refreshTok = r_token
                user_repo.persist(user)
                user_repo.close()

            http_client = tornado.httpclient.AsyncHTTPClient()
            http_request = tornado.httpclient.HTTPRequest(url, 'POST', body=request)
            http_client.fetch(http_request, handle_response)
            self.redirect("/profile")
