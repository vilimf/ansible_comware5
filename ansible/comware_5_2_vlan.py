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
module: comware_5_2_vlan
version_added: 0.1
author: Patrick Galbraith
short_description: Manage VLANs on Comware 5.2-based Switches
requirements: [ paramiko comware_5_2 (http://code.patg.net/comware_5_2.tar.gz)]
description:
    - Manage VLANs on Comware 5.2-based Switches
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
        choices: [ present, reboot]
        description:
            - State of switch. If 'reboot', switch will be rebooted
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
    name:
        required: true
        default: Must be set to valid name
        description:
            - Canonical name of VLAN
    id:
        required: true
        default: Must be a valid numeric ID
        description:
            - ID of VLAN
    tagged_port_type:
        required: false
        choices: [ trunk, hybrid]
        default: trunk
        description:
            - Type that all tagged ports will be given
    untagged_port_type:
        required: false
        choices: [ access, hybrid]
        default: access
        description:
            - Type that all untagged port will be given
    tagged_ports:
        required: false
        default: None
        description:
            - List of tagged ports
    untagged_ports:
        required: false
        default: None
        description:
            - List of untagged ports
    state:
        required: false
        choices: [ present, absent ]
        default: present
        description:
            - State of VLAN
'''

EXAMPLES = '''

# file: switch_vlan.yml
- hosts: localhost
  tasks:
  - name: set switch in developer mode
    local_action:
      module: comware_5_2_vlan
      developer-mode: true
      host: 192.168.1.100
      username: admin
      password: ckrit
      state: present
      name: VLAN 11
      id: 11
      interface_type: access
      tagged: false
      interfaces:
      - GigabitEthernet1/0/9
      - GigabitEthernet1/0/10

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    comware_5_2_vlan: host=192.168.1.100 username=admin password=ckrit state=present vlan_name="VLAN 11" vlan_id=11 untagged_port_type: access untagged_interfaces=GigabitEthernet1/0/9,GigabitEthernet1/0/10

'''

# http://code.patg.net/comware_5_2.tar.gz
from comware_5_2 import Comware_5_2
from ansible.module_utils.basic import *


class Comware_5_2_Vlan(Comware_5_2):
    def dispatch(self):
        facts = self._handle_vlan()
        return facts

    def _handle_vlan(self):
        facts = self.get_facts()
        vlan = {'vlan_id': self.module.params.get('vlan_id'),
                'vlan_name': self.module.params.get('vlan_name'),
                'tagged_port_type': self.module.params.get('tagged_port_type'),
                'untagged_port_type':
                self.module.params.get('untagged_port_type'),
                'tagged_ports': self.module.params.get('tagged_ports'),
                'untagged_ports': self.module.params.get('untagged_ports'),
                'state': self.module.params.get('state'),
                'interfaces': self.module.params.get('interfaces')}
        if vlan['state'] == 'absent':
            facts = self._delete_vlan(facts, vlan['vlan_id'])
        else:
            facts = self._save_vlan(facts, vlan)
        # After adding or deleting vlan, save
        if self.module.params.get('save') is True:
            self.save()

        return facts

    def _vlan_changed(self, facts, vlan):
        vlan_id = str(vlan['vlan_id'])
        if vlan_id not in facts['vlans']:
            return False
        existing_vlan = facts['vlans'][vlan_id]
        if vlan['vlan_name'] != existing_vlan['Name']:
            return True
        if vlan['tagged_ports'] != existing_vlan['Tagged_Ports']:
            return True
        if vlan['untagged_ports'] != existing_vlan['Untagged_Ports']:
            return True

    def _save_vlan(self, facts, vlan):
        #self.dev_setup()
        # if something has changed, best to delete then recreate
        if self._vlan_changed(facts, vlan):
            facts = self._delete_vlan(facts, vlan['vlan_id'])
        self.set_changed(False)

        # TODO: add error handling here
        vlan_id = str(vlan['vlan_id'])

        if vlan_id in facts['vlans']:
            self.set_changed(False)
            self.append_message("VLAN %s already exists\n" % vlan_id)
            return facts

        self._send_command("vlan %s\n" % vlan_id,
                           "ERROR: unable to enter VLAN ID")
        # if user doesn't assign, name assigned by switch 000${vlan_id}
        if vlan['vlan_name'] != "":
            self._send_command("name %s\n" % vlan['vlan_name'],
                               "ERROR: unable to enter VLAN name")

        for port in vlan['tagged_ports']:
            port_type = vlan['tagged_port_type']
            if port_type == 'access':
                msg = "ERROR: tagged ports must be 'hybrid' or 'trunk'"
                self.set_message(msg)
                self.module.fail_json(msg=self.get_message())
            self._send_command("interface %s\n" % port,
                               "ERROR: unable to enter interface view")
            self._send_command("port link-type %s\n" % port_type,
                               "ERROR: unable to set link type")
            type_err = "ERROR: unable to set vlan port %s" % port_type
            # could use else, but this is self-documenting
            if port_type == 'hybrid':
                self._send_command("port hybrid vlan %s tagged\n" %
                                   vlan_id, type_err)
            # trunk
            else:
                self._send_command("port trunk permit vlan %s\n" % vlan_id,
                                   type_err)

        for port in vlan['untagged_ports']:
            port_type = vlan['untagged_port_type']
            if port_type == 'trunk':
                self.set_message("ERROR: untagged ports must \
                                 be 'hybrid' or 'access'")
                self.module.fail_json(msg=self.get_message())
            self._send_command("interface %s\n" % port,
                               "ERROR: unable to enter interface view")
            self._send_command("port link-type %s\n" % port_type,
                               "ERROR: unable to set link type")
            type_err = "ERROR: unable to set vlan port %s" % port_type
            # could use else, but this is self-documenting
            if port_type == 'hybrid':
                self._send_command("port hybrid vlan %s untagged\n" %
                                   vlan_id, type_err)
            # access
            else:
                self._send_command("port access vlan %s\n" % vlan_id, type_err)

        # leave interface view
        self._quit()

        # refresh facts
        facts = self.get_facts()
        if vlan_id in facts['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s created\n" % vlan_id)
        else:
            self.append_message("Unable to create VLAN ID %s\n" % vlan_id)

        return facts

    def _delete_vlan(self, facts, vlan_id):
        self.set_changed(False)
        if type(vlan_id) is not int:
            self.set_failed(True)
            self.set_message("ERROR: 'id' provided is not numeric.")

        if self.get_failed():
            self.module.exit_json(failed=self.get_failed(),
                                  changed=self.get_changed(),
                                  msg=self.get_message())

        # force to string
        vlan_id = str(vlan_id)

        if vlan_id not in facts['vlans']:
            self.set_changed(False)
            self.append_message("VLAN %s doesn't exist\n" % vlan_id)
            return facts

        self._send_command("undo vlan %s\n" % vlan_id,
                           "Unable to delete vlan %s" % vlan_id)

        # refresh facts
        facts = self.get_facts()

        if vlan_id not in facts['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s deleted\n" % vlan_id)
        else:
            self.append_message("Unable to delete VLAN ID %s\n" % vlan_id)

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
            vlan_id=dict(required=True, type='int'),
            # switch will assign if user does not
            vlan_name=dict(required=False),
            tagged_port_type=dict(required=False,
                                  default='trunk',
                                  choices=['trunk', 'hybrid']),
            untagged_port_type=dict(required=False,
                                    default='access',
                                    choices=['access', 'hybrid']),
            tagged_ports=dict(required=False,
                              type='list',
                              default=[]),
            untagged_ports=dict(required=False,
                                type='list',
                                default=[]),
            state=dict(required=False, default='present',
                       choices=['present', 'absent']),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )

    failed = False

    switch = Comware_5_2_Vlan(module,
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
        message = switch.get_message() + "%s %s" % (e.__class__, e)
        module.fail_json(msg=message)

# entry point
main()
