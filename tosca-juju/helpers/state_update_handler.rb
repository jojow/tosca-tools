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
module StateHandler
  class StateUpdate < Chef::Handler

    def update_state(state)
      open('/var/chef/chef-client.state', 'w') do |f|
        f.puts state
      end
    end

    def report
      if run_status.success?
        update_state "success"
      else
        update_state "failed"
      end
    end
  end
end
