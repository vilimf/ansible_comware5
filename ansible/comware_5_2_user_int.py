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
module: comware_5_2_user_int
version_added: 0.1
author: Patrick Galbraith
short_description: Manage users on Comware 5.2-based Switches
requirements: [ paramiko comware_5_2 (http://code.patg.net/comware_5_2.tar.gz)]
description:
    - Manage User-interfaces on Comware 5.2-based Switches
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
    user_interface:
        required: true
        default: Must be set to valid user-interface
        description:
            - Name of user-interface
    authentication_mode:
        required: true
        default: Must be a valid authentication-mode
        choices: [scheme|password|none]
        description:
            - Authentication-mode
    in_protocol:
        required: true
        choices: [ssh|telnet|all]
        default: all
        description:
            - Inbound protocol
    acl:
        required: false
        description:
            - ACL
            - to remove ACL set 'none'
            - to don't change ACL set 'skip'
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


class Comware_5_2_User_int(Comware_5_2):
    def dispatch(self):
        facts = self._handle_user_int()
        return facts

    def _handle_user_int(self):
        facts = self.get_facts()
        user_int = {'uint_id': self.module.params.get('user_interface_id'),
                'uint_type': self.module.params.get('user_interface_type'),
                'auth': self.module.params.get('authentication_mode'),
                'in_proto': self.module.params.get('in_protocol'),
                'acl': self.module.params.get('acl')}
#        if user['state'] == 'absent':
#            facts = self._delete_user(facts, user['name'])
#        else:
#            facts = self._save_user(facts, user)
        # After adding or deleting vlan, save
        if user_int['acl'] == 'skip':
          user_int['acl'] = ''

        facts = self._set_user_int(facts, user_int)

        if self.module.params.get('save') is True:
            self.save()

        return facts

#    def _user_exists(self, facts, name):
#        return name in facts['current_config']['local-user']
#
#    def _user_changed(self, facts, user):
#        current_user = facts['current_config']['local-user']
#        return current_user['service-type'] == user['services']
#
    def _set_user_int(self, facts, user_int):
        #self.dev_setup()
        self.set_changed(False)

        change_needed = False

        for uint in user_int['uint_id']:
           if 'auth' in user_int:
              if user_int['auth'] not in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['authentication_mode']:
                  change_needed = True

           if 'acl' in user_int and re.match('\s*([23]\d{3}\s*(inbound|outbound)|none)',user_int['acl']):
              if user_int['acl'] not in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['acl']:
                  change_needed = True
#           elif 'acl' in user_int and user_int['acl'] == 'none':
#              if 'acl' in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]:
#                  change_needed = True

           if 'in_proto' in user_int:
              if user_int['in_proto'] not in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['protocol_inbound']:
                  change_needed = True

        if change_needed == False:
            self.set_changed(False)
            self.append_message("Change not needed. ")
            return facts


        for uint in user_int['uint_id']:
           self._exec_command("user-interface %s %s\n" % (user_int['uint_type'], uint),
                              "ERROR: unable to enter user-interface view")
           if 'auth' in user_int:
            self._exec_command("authentication-mode %s\n" % user_int['auth'],
                              "ERROR: unable to set authentication-mode")
           if 'in_proto' in user_int:
            self._exec_command("protocol inbound %s\n" % user_int['in_proto'],
                              "ERROR: unable to set protocol-inbound")
           if 'acl' in user_int and re.match('\s*[23]\d{3}\s*(inbound|outbound)',user_int['acl']): 
            self._exec_command("acl %s\n" % user_int['acl'],
                              "ERROR: unable to set acl")
           elif 'acl' in user_int and user_int['acl'] == 'none':
            self._exec_command("undo acl %s\n" % facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['acl'],
                              "ERROR: unable to remove acl")
 
        # leave interface view
        self._quit()
        # refresh facts
        facts = self.get_facts()
        # TODO:

        change_done = False

        for uint in user_int['uint_id']:
           if 'auth' in user_int:
              if user_int['auth'] in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['authentication_mode']:
                 change_done = True
              else:
                  self.fail("Failed to update user-interface %s %s authentication-mode configuration." % (user_int['uint_type'], uint))
                  return facts

           if 'acl' in user_int and re.match('\s*([23]\d{3}\s*(inbound|outbound)|none)',user_int['acl']):
              if user_int['acl'] in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['acl']:
                 change_done = True
              else:
                  self.fail("Failed to update user-interface %s %s acl configuration." % (user_int['uint_type'], uint))
                  return facts
#           elif 'acl' in user_int and user_int['acl'] == 'none':
#              if 'acl' in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]:
#                  self.fail("Failed to update user-interface %s %s acl configuration." % (user_int['uint_type'], uint))
#                  return facts
#              else:
#                 change_done = True

           if 'in_proto' in user_int:
              if user_int['in_proto'] in facts['current_config']['user_interfaces'][user_int['uint_type']][str(uint)]['protocol_inbound']:
                 change_done = True
              else:
                  self.fail("Failed to update user-interface %s %s protocol inbound configuration." % (user_int['uint_type'], uint))
                  return facts


        if change_done == True:
            self.set_changed(True)
        else:
            self.set_changed(False)

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
            user_interface_id=dict(required=True, type='list'),
            user_interface_type=dict(required=True),
            authentication_mode=dict(required=True,
                                    choices=['scheme',
                                     'password',
                                     'none']),
            in_protocol=dict(required=True,
                            choices=['all',
                                     'ssh',
                                     'telnet']),
            acl=dict(required=False),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )
    failed = False

    switch = Comware_5_2_User_int(module,
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
