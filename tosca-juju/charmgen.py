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
import os, zipfile, yaml, shutil

class CharmGenerator:
  def __init__(self, absCsarDir, model, charmsDir, charmSeries):
    self.csarDir = absCsarDir
	
    self.charms = model['charms']
  	
    self.charmSeries = charmSeries
  
    self.charmsDir = charmsDir
    self.helpersDir = 'helpers'
  
    self.scriptHead = '#!/bin/sh\n'

    if os.path.isdir(self.charmsDir):
      shutil.rmtree(self.charmsDir)

  # ...
  def generate(self):
    for charmName in self.charms.keys():
      charm = self.charms[charmName]
      charmDir = self.charmsDir + '/' + self.charmSeries + '/' + charmName
    
      os.makedirs(charmDir + '/hooks')
      os.makedirs(charmDir + '/chef/roles')
      
      # Bundle cookbooks and role definitions
      for cookbook in charm['cookbooks'].keys():
        path = self.csarDir + '/' + charm['cookbooks'][cookbook]
    
        cbFile = zipfile.ZipFile(path)
        cbFile.extractall(charmDir + '/chef/cookbooks/' + cookbook)
        cbFile.close()
    	
        shutil.make_archive(charmDir + '/hooks/cookbooks', 'zip', charmDir + '/chef/cookbooks/')
    
      for rolePath in charm['roles'].values():
        path = self.csarDir + '/' + rolePath
    	
        shutil.copy(path, charmDir + '/chef/roles/')
        shutil.make_archive(charmDir + '/hooks/roles', 'zip', charmDir + '/chef/roles/')
    
      shutil.rmtree(charmDir + '/chef')
    
      # Build the manifest.yaml
      charmManifest = {'name': charmName, 'summary': charm['summary'], 'maintainer': charm['maintainer'], 'description': charm['description']}
      
      if len(charm['requires']) > 0:
        charmManifest['requires'] = {}
        for req in charm['requires'].keys():
          charmManifest['requires'][req] = {'interface': req}
    
      if len(charm['provides']) > 0:
        charmManifest['provides'] = {}
        for prov in charm['provides'].keys():
          charmManifest['provides'][prov] = {'interface': prov}
    	  
      manifest = open(charmDir + '/metadata.yaml', 'w')
      yaml.safe_dump(charmManifest, manifest, default_flow_style=False)
      manifest.close()
    
      # Build the config.yaml
      charmConfig = {'options': {}}
      
      for key in charm['properties'].keys():
        value = charm['properties'][key]
        charmConfig['options'][key] = {'type': 'string', 'default': value, 'description': key}
      
      config = open(charmDir + '/config.yaml', 'w')
      yaml.safe_dump(charmConfig, config, default_flow_style=False)
      config.close()
      
      # Place hook helpers
      attrs = open(charmDir + '/hooks/attributes.json', 'w')
      attrs.write('{ "run_list": [] }')
      attrs.close()
      
      shutil.copy(self.helpersDir + '/run_chef_client.sh', charmDir + '/hooks/run_chef_client.sh')
      os.chmod(charmDir + '/hooks/run_chef_client.sh', 0777)
      
      shutil.copy(self.helpersDir + '/update_attributes_json.rb', charmDir + '/hooks/update_attributes_json.rb')
      os.chmod(charmDir + '/hooks/update_attributes_json.rb', 0777)
      
      shutil.copy(self.helpersDir + '/state_update_handler.rb', charmDir + '/hooks/state_update_handler.rb')
      os.chmod(charmDir + '/hooks/state_update_handler.rb', 0777)
      
      # Properties and mappings to be included into the hooks
      properties = '# Get properties\n'
      for prop in charm['properties'].keys():
        properties += prop + '="$(config-get ' + prop + ')"\n'
    
      mappings = ''
      for mapping in charm['mappings'].keys():
        mappings += '"' + charm['mappings'][mapping] + '=$' + mapping + '" '

        if not mapping in charm['properties'].keys():
          properties += mapping + '="undefined"\n'
      
      # Build the "install" hook
      runListIncludes = '"run_list_include='
      separator = ''
      for entry in charm['runLists']['install']:
        runListIncludes += separator + entry
        separator = ','
      runListIncludes += '"'
      
      install = open(charmDir + '/hooks/install', 'w')
      install.write("""#!/bin/sh

set -eux

SCRIPT_DIR="$(dirname $0)"

""" + properties + """

# Make dirs
mkdir -p /var/chef/cookbooks
mkdir -p /var/chef/roles
mkdir -p /var/log/chef/resources-state

# Place state handler and state file
cp $SCRIPT_DIR/state_update_handler.rb /var/chef/
echo 'success' > /var/chef/chef-client.state

# Bootstrap Chef client
curl -L http://www.opscode.com/chef/install.sh | sudo bash

### TODO: Make this platform-independent, e.g., by including a corresponding Chef recipe
apt-get -y install unzip

# Place cookbooks
unzip -qq -o $SCRIPT_DIR/cookbooks.zip -d /var/chef/cookbooks

# Place roles
unzip -qq -o $SCRIPT_DIR/roles.zip -d /var/chef/roles

# Update attributes.json
$SCRIPT_DIR/update_attributes_json.rb $SCRIPT_DIR/attributes.json """ + mappings + runListIncludes + """

# Run Chef client
$SCRIPT_DIR/run_chef_client.sh

      """)
      install.close()
      
      solo = open(charmDir + '/hooks/solo.rb', 'w')
      solo.write('file_cache_path "/var/chef"\n')
      solo.write('cookbook_path "/var/chef/cookbooks"\n')
      solo.write('role_path "/var/chef/roles"\n')
      solo.write('require "/var/chef/state_update_handler.rb"\n')
      solo.write('report_handlers << StateHandler::StateUpdate.new\n')
      solo.write('exception_handlers << StateHandler::StateUpdate.new\n')
      solo.close()
      
      # Build dummy hooks for "start" and "stop"
      start = open(charmDir + '/hooks/start', 'w')
      start.write(self.scriptHead)
      start.close()
      
      stop = open(charmDir + '/hooks/stop', 'w')
      stop.write(self.scriptHead)
      stop.close()
      
      # Make hooks executable
      os.chmod(charmDir + '/hooks/install', 0777)
      os.chmod(charmDir + '/hooks/start', 0777)
      os.chmod(charmDir + '/hooks/stop', 0777)
    
      # Build the "relation-joined" hooks
      def generateRelationJoinedHook(runList):
        relationJoined = open(charmDir + '/hooks/' + relation + '-relation-joined', 'w')
    	
        if len(runList) > 0:
          runListIncludes = '"run_list_include='
          separator = ''
          for entry in runList:
            runListIncludes += separator + entry
            separator = ','
          runListIncludes += '"'
    	  
          relationJoined.write("""#!/bin/sh
    
set -eux
    
SCRIPT_DIR="$(dirname $0)"
    
""" + properties + """
PROVIDER="$(relation-get provider-address)"
    
### TODO: WORKAROUND FOR GETTING THE DB HOST ###
VmMySql=$PROVIDER
    
# Update attributes.json
$SCRIPT_DIR/update_attributes_json.rb $SCRIPT_DIR/attributes.json """ + mappings + runListIncludes + """
    
# Run Chef client
$SCRIPT_DIR/run_chef_client.sh

### TODO: WORKAROUND FOR OPENING THE PORT ###
open-port 80/tcp
    
exit 0
    
          """)
        else:
          relationJoined.write(self.scriptHead)
          relationJoined.write('relation-set provider-address="$(unit-get private-address)"\n')
    
        relationJoined.close()
    
        os.chmod(charmDir + '/hooks/' + relation + '-relation-joined', 0777)
    
      for relation in charm['requires'].keys():
        runList = charm['requires'][relation]['runLists']['relationJoined']
        generateRelationJoinedHook(runList)
    
      for relation in charm['provides'].keys():
        runList = charm['provides'][relation]['runLists']['relationJoined']
        generateRelationJoinedHook(runList)
