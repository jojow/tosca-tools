#!/bin/sh

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

SCRIPT_DIR="$(dirname $0)"

wait_while_running () {
  while [ "$(head -n1 /var/chef/chef-client.state)" != 'success' ]; do
    sleep 1
  done
}

run_chef_client () {
  echo 'running' > /var/chef/chef-client.state

  chef-solo -c $SCRIPT_DIR/solo.rb -j $SCRIPT_DIR/attributes.json

  if [ "$(head -n1 /var/chef/chef-client.state)" == 'failed' ]; then
    run_chef_client
  fi
}

wait_while_running

run_chef_client

exit 0

