#!/opt/chef/embedded/bin/ruby

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

#
# How to use this script:
#
# update_attributes_json.rb "/tmp/attributes.json" "mysql/db_name=sugardb" "mysql/db_desc=The SugarCRM DB" "run_list_include=recipe[sugarcrm::app],recipe[sugarcrm::app]" "run_list_exclude=recipe[sugarcrm::monitor]"
#

require "json"

# Path to JSON file
json_file = ARGV[0]
ARGV.shift

# Read JSON file
json = File.read(json_file)
attrs = JSON.parse(json)

# Store key-value pairs as attributes
ARGV.each do |a|
  if a.split("=").first == "run_list_include"
    # Process run list includes
    recipes = a.split("=").last.split(",")
    run_list_include = []

    recipes.each do |r|
      include = true

      attrs["run_list"].each do |e|
        if e == r
          include = false
        end
      end

      if include
        run_list_include.push(r)
      end
    end
    
    attrs["run_list"].push(*run_list_include)
  elsif a.split("=").first == "run_list_exclude"
    # Process run list excludes
    recipes = a.split("=").last.split(",")
    run_list = []

    attrs["run_list"].each do |e|
      exclude = false
      
      recipes.each do |r|
        if r == e
          exclude = true
        end
      end
      
      if !exclude
        run_list.push(e)
      end
    end
    
    attrs["run_list"] = run_list
  else
    # Process cookbook attributes
    prefix = a.split("/").first
    rest = a.split("/").last

    if !attrs.has_key?(prefix)
      attrs[prefix] = Hash.new
    end

    key = rest.split("=").first
    value = rest.split("=").last

    attrs[prefix][key] = value
  end
end

# Write JSON file
File.open(json_file, "w") do |f|
  f.write(attrs.to_json)
end

