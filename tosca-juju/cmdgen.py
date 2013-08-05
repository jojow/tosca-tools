# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
class CommandGenerator:
  def __init__(self, model, charmsDir, charmSeries, jujuEnv):    
    self.charms = model['charms']
    self.topology = model['topology']
    
    self.charmsDir = charmsDir
    self.charmSeries = charmSeries
    self.jujuEnv = jujuEnv

  # ...
  def generate(self):
    commands = []

    for node in self.topology['nodes'].values():
      commands.append(['juju', 'deploy', '--repository', self.charmsDir, 'local:' + self.charmSeries + '/' + node['charm'], '-e', self.jujuEnv])
    
    for relSource in self.topology['relations'].keys():
      relTarget = self.topology['relations'][relSource]
      commands.append(['juju', 'add-relation', relSource, relTarget, '-e', self.jujuEnv])

    for node in self.topology['nodes'].values():
      commands.append(['juju', 'expose', node['charm'], '-e', self.jujuEnv])

    return commands