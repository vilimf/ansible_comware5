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
module: comware_5_2_hostname
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
    hostname:
        required: true
        default: Must be set to valid hostname
        description:
            - hostname
'''

EXAMPLES = '''

# file: switch_user.yml
- hosts: localhost
  tasks:
  - name: set switch hostname
    local_action:
      module: comware_5_2_user
      developer-mode: true
      host: 192.168.1.100
      username: admin
      password: ckrit
      hostname: hp5800.lab

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    comware_5_2_user: host=192.168.1.100 username=admin password=ckrit hostname=hp5800.lab

'''

# http://code.patg.net/comware_5_2.tar.gz
from comware_5_2 import Comware_5_2
from ansible.module_utils.basic import *


class Comware_5_2_Hostname(Comware_5_2):
    def dispatch(self):
        facts = self._handle_hostname()
        return facts

    def _handle_hostname(self):
        facts = self.get_facts()
        hostname = self.module.params.get('hostname')
        if facts['current_config']['sysname'] != hostname:
            facts = self._set_hostname(facts, hostname)
        else:
             self.append_message("The hostname %s was already set.\n" % hostname)
        # After adding or deleting vlan, save
        if self.module.params.get('save') is True:
            self.save()

        return facts

#    def _user_exists(self, facts, name):
#        return name in facts['current_config']['local-user']
#
#    def _user_changed(self, facts, user):
#        current_user = facts['current_config']['local-user']
#        return current_user['service-type'] == user['services']

    def _set_hostname(self, facts, hostname):
        #self.dev_setup()
        self.set_changed(False)

        self._exec_command("sysname %s\n" % hostname,
                           "ERROR: unable to enter local user view")
        # leave interface view
#        self._quit()
        # refresh facts
        facts = self.get_facts()
        # TODO:
        if hostname == facts['current_config']['sysname']:
            self.set_changed(True)
            self.append_message("The hostname %s has been updated.\n" %
                                hostname)
        else:
            self.append_message("Unable to update the hostname %s.\n" %
                                hostname)

        return facts

#    def _delete_user(self, facts, name):
#        self.set_changed(False)
#        if not self._user_exists(facts, name):
#            self.fail("The user %s does not exist." % name)
#
#        self._send_command("undo local-user %s\n" % name,
#                           "Unable to delete user %s" % name)
#
#        # refresh facts
#        facts = self.get_facts()
#
#        if name not in facts['current_config']['local-user']:
#            self.set_changed(True)
#            self.append_message("User %s deleted\n" % name)
#        else:
#            self.append_message("Unable to delete user %s\n" % name)
#
#        return facts
#
#
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
            hostname=dict(required=True),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )
    failed = False

    switch = Comware_5_2_Hostname(module,
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
