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
module: comware_5_2_port
version_added: 0.1
author: Patrick Galbraith
short_description: Manage Ports on Comware 5.x Switches
requirements: [ paramiko comware_5_2 (http://code.patg.net/comware_5_2.tar.gz)]
description:
    - Manage Ports on Comware 5.2-based Switches
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
    state:
        required: false
        choices: [ enabled, shutdown]
        default: enabled
        description:
            - State of Port
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
    name:
        required: true
        default: Must be set to valid port name
        description:
            - Name of interface/port

    vlans:
        required: true
        default: Must be a valid numeric ID
        description:
            - List of vlan IDs

    link_type:
        required: false
        choices: [ access, trunk, hybrid]
        default: access
        description:
            - Port link type


'''

EXAMPLES = '''

# file: switch_vlan.yml
- hosts: localhost
  tasks:
  - name: set switch in developer mode
    local_action:
      module: comware_5_2_port
      host: 192.168.1.100
      username: admin
      password: ckrit
      name: GigabitEthernet1/0/9
      id: 11
      port_type: access
      vlan_id: 33
      tagged: false

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    comware_5_2_port: host=192.168.1.100 username=admin password=ckrit name=GigabitEthernet1/0/15 vlans=55,66,77 link_type: access

'''

# http://code.patg.net/comware_5_2.tar.gz
from comware_5_2 import Comware_5_2
from ansible.module_utils.basic import *


class Comware_5_2_Port(Comware_5_2):
    def dispatch(self):
        facts = self._handle_port()
        return facts

    def _handle_port(self):
        facts = self.get_facts()
        port = {'name': self.module.params.get('name'),
                'vlans': self.module.params.get('vlans'),
                'link_type': self.module.params.get('link_type'),
                'tagged': self.module.params.get('tagged'),
                'state': self.module.params.get('state')}
        if port['name'] not in facts['current_config']['interfaces']:
            self.fail("ERROR: the port name specified doesn't exist\
                      or is invalid!")

        if self._port_changed(facts, port):
            facts = self._save_port(facts, port)
        if self.module.params.get('save') is True:
            self.save()

        return facts

    def _port_changed(self, facts, port):
        tagged = 'tagged'
        if port['tagged'] is False:
            tagged = "un" + tagged

        # TODO: solve this
        # current_port = facts['current_config']['interfaces'][port['name']]
        # TODO: 'port link_type' needs to be 'link-type'
        #if port['port link-type'] != current_port['link_type']:
        #    return True
        #if port['vlans'] != current_port['vlan'][tagged][port['link_type']]:
        #    return True

        return True

    def _save_port(self, facts, port):
        # if something has changed, best to delete then recreate
        self.set_changed(False)
        # could use else, but this is self-documenting
        tagged = 'tagged'
        if not port['tagged']:
            tagged = 'un' + tagged

        if port['link_type'] == 'access' and port['tagged']:
            self.fail("A link-type of 'access' cannot be tagged")
        if port['link_type'] == 'access' and len(port['vlans']) > 1:
            self.fail("A link-type of 'access' can only specify one vlan")

        #current_link_type = \
        # facts['current_config']['interfaces'][port['name']]['link_type']

        self._send_command("interface %s\n" % port['name'],
                           "ERROR: unable to enter interface view")
        #if current_link_type != port['link_type'] and \
        #        port['link_type'] != 'access':
        if True:
            self._send_command("port link-type acccess\n",
                               "ERROR: unable to set link type to access")
        type_err = "ERROR: unable to set link-type %s" % port['link_type']
        self._send_command("port link-type %s\n" % port['link_type'], type_err)

        vlan_list = " ".join(port['vlans'])
        type_err = "Error: unable to set vlan %s access on port" % vlan_list
        if port['link_type'] == 'hybrid':
            self._send_command("port hybrid vlan %s %s\n" %
                               (vlan_list, tagged), type_err)
        elif port['link_type'] == 'trunk':
            self._send_command("port trunk permit vlan %s\n" % vlan_list,
                               type_err)
        # access
        else:
            self._send_command("port access vlan %s\n" % vlan_list, type_err)

        # leave interface view
        self._quit()

        # refresh facts
        facts = self.get_facts()
        self.set_changed(True)
        self.append_message("PORT %s saved\n" % port['name'])

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
            name=dict(required=True),
            vlans=dict(required=False, type='list'),
            link_type=dict(required=False,
                           default='access',
                           choices=['access', 'trunk', 'hybrid']),
            tagged=dict(required=False, type='bool', default=False),
            state=dict(required=False, default='present',
                       choices=['present', 'shutdown']),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )

    failed = False

    switch = Comware_5_2_Port(module,
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
        module.fail_json(msg=msg)

# entry point
main()
