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
import yaml, subprocess, sys

from modeltrans import ModelTransformer
from charmgen import CharmGenerator
from cmdgen import CommandGenerator

#
# create-instance.py SugarCRM_ChefManaged.zip service-template/SugarCRM-ServiceTemplate.xml hpcloud
#

csarFile = sys.argv[1]
serviceTpl = sys.argv[2]
jujuEnv = sys.argv[3]

csarDir = 'csar'

charmsDir = 'charms'
charmSeries = 'precise' # for now this has to be a valid name for a Ubuntu series

# Transform TOSCA service template into a charm-based model
transformer = ModelTransformer(csarFile, csarDir, serviceTpl)
model = transformer.transform()

# Print model
print ' '
print '------------------------------------'
print ' '
print yaml.safe_dump(model, default_flow_style=False)

# Build charms
charmGen = CharmGenerator(csarDir, model, charmsDir, charmSeries)
charmGen.generate()

# Generate commands
cmdGen = CommandGenerator(model, charmsDir, charmSeries, jujuEnv)
commands = cmdGen.generate()

print '------------------------------------'

for cmd in commands:
  # Print command
  printCmd = '\n'
  for arg in cmd:
    printCmd += arg + ' '
  print printCmd + '\n'

  # Run command
  returnCode = 1
  while returnCode != 0:
    returnCode = subprocess.call(cmd)
