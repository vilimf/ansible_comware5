#!/usr/bin/python
#coding: utf-8 -*-

# (c) 2014, Patrick Galbraith <patg@patg.net>
#
# This file is part of Ansible
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: comware_5_2_user
version_added: 0.1
author: Patrick Galbraith
short_description: Manage users on Comware 5.2-based Switches
requirements: [ paramiko comware_5_2 (http://code.patg.net/comware_5_2.tar.gz)]
description:
    - Manage Users on Comware 5.2-based Switches
options:
    developer-mode:
        required: false
        default: true
        choices: [ true, false ]
        description:
            - Whether to set the switch into developer mode. Switch doesn't
              much when not in developer mode!
    state:
        required: false
        default: present
        choices: [ present, absent]
        description:
            - State of user.
    save:
        required: false
        default: false
        choices: [ false, true ]
        description:
            - if true, all changes will be written. Upon reboot, save
    startup_cfg:
        required: false
        default: startup.cfg
        description:
            - The name of the save startup config file when save or reboot
    host:
        required: true
        default: empty
        description:
            - host/ip of switch
    username:
        required: true
        default: empty
        description:
            - username to connect to switch as
    password:
        required: true
        default: empty
        description:
            - password to connect switch with
    timeout:
        required: false
        default: 5
        description:
            - How long to wait for switch to respond
    user_name:
        required: true
        default: Must be set to valid user name
        description:
            - Canonical name of user
    user_pass:
        required: true
        default: Must be a valid password
        description:
            - User password
    auth_level:
        required: false
        choices: [ "level 0" through "level 3"]
        default: 0
        description:
            - Authorization attribute level
    services:
        required: false
        default: None
        choices: [ list: web, ssh, telnet, terminal]
        description:
            - Service types
'''

EXAMPLES = '''

# file: switch_user.yml
- hosts: localhost
  tasks:
  - name: set switch in developer mode
    local_action:
      module: comware_5_2_user
      developer-mode: true
      host: 192.168.1.100
      username: admin
      password: ckrit
      state: present
      user_name: jimbob
      user_pass: seekrit
      auth_level: level 3
      services:
      - web
      - ssh
      - terminal

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    comware_5_2_user: host=192.168.1.100 username=admin password=ckrit state=present user_name="jimbob" user_pass="seekrit" auth_level="level 2" services=web,ssh,terminal

'''

# http://code.patg.net/comware_5_2.tar.gz
from comware_5_2 import Comware_5_2
from ansible.module_utils.basic import *


class Comware_5_2_User(Comware_5_2):
    def dispatch(self):
        facts = self._handle_user()
        return facts

    def _handle_user(self):
        facts = self.get_facts()
        user = {'name': self.module.params.get('user_name'),
                'pass': self.module.params.get('user_pass'),
                'state': self.module.params.get('state'),
                'auth_level':
                self.module.params.get('auth_level'),
                'services': self.module.params.get('services')}
        if user['state'] == 'absent':
            facts = self._delete_user(facts, user['name'])
        else:
            facts = self._save_user(facts, user)
        # After adding or deleting vlan, save
        if self.module.params.get('save') is True:
            self.save()

        return facts

    def _user_exists(self, facts, name):
        return name in facts['current_config']['local-user']

    def _user_changed(self, facts, user):
        current_user = facts['current_config']['local-user']
        return current_user['service-type'] == user['services']

    def _save_user(self, facts, user):
        #self.dev_setup()
        self.set_changed(False)

        self._exec_command("local-user %s\n" % user['name'],
                           "ERROR: unable to enter local user view")
        self._exec_command("password cipher %s\n" % user['pass'],
                           "ERROR: unable to set password")
        self._exec_command("authorization-attribute %s\n" %
                           user['auth_level'])
        for service in user['services']:
            self._send_command("service-type %s\n" % service)

        # leave interface view
        self._quit()
        # refresh facts
        facts = self.get_facts()
        # TODO:
        if user['name'] in facts['current_config']['local-user']:
            self.set_changed(True)
            self.append_message("The user %s has been updated\n" %
                                user['name'])
        else:
            self.append_message("Unable to update the user %s\n" %
                                user['name'])

        return facts

    def _delete_user(self, facts, name):
        self.set_changed(False)
        if not self._user_exists(facts, name):
            self.fail("The user %s does not exist." % name)

        self._send_command("undo local-user %s\n" % name,
                           "Unable to delete user %s" % name)

        # refresh facts
        facts = self.get_facts()

        if name not in facts['current_config']['local-user']:
            self.set_changed(True)
            self.append_message("User %s deleted\n" % name)
        else:
            self.append_message("Unable to delete user %s\n" % name)

        return facts


def main():
    module = AnsibleModule(
        argument_spec=dict(
            developer_mode=dict(type='bool'),
            gather_facts=dict(required=False, type='bool', default=True),
            save=dict(type='bool', default=False),
            startup_cfg=dict(),
            username=dict(required=True),
            password=dict(required=True),
            host=dict(required=True),
            user_name=dict(required=True),
            user_pass=dict(required=True),
            auth_level=dict(required=False,
                            default='0',
                            choices=['level 0',
                                     'level 1',
                                     'level 2',
                                     'level 3']),
            services=dict(required=False,
                          default=[],
                          type='list'),
            state=dict(required=False,
                       default='present',
                       choices=['present', 'absent']),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )
    failed = False

    switch = Comware_5_2_User(module,
                              host=module.params.get('host'),
                              username=module.params.get('username'),
                              password=module.params.get('password'),
                              timeout=module.params.get('timeout'),
                              port=module.params.get('port'),
                              private_key_file=
                              module.params.get('private_key_file'))

    try:
        facts = switch.dispatch()
        if not module.params.get('gather_facts'):
            facts = {}

        module.exit_json(failed=failed,
                         changed=switch.get_changed(),
                         msg=switch.get_message(),
                         ansible_facts=facts)
    except Exception, e:
        msg = switch.get_message() + "%s %s" % (e.__class__, e)
        switch.fail(msg)

# entry point
main()
