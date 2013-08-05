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
import os, sys, zipfile, json, yaml, shutil, re
from xml.dom.minidom import parse, Node

# Returns the NCName for the given QName
def getNCName(QName):
  return QName.split(':')[-1]
  
def convert(name):
  s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
  return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

class ModelTransformer:
  def __init__(self, csarFile, absCsarDir, relServiceTpl):
    self.chefArtifactType = 'http://docs.oasis-open.org/tosca/ns/2012/07/ChefArtifact'
    self.chefNodeName = 'ChefArtifact'
    self.lifecycleInterfaceName = 'http://docs.oasis-open.org/tosca/ns/2011/12/interfaces/lifecycle'
    self.installOperationName = 'install'
  
    self.hostedOnType = 'HostedOnType'
    self.dependsOnType = 'DependsOnType'
    self.connectsToType = 'ConnectsToType'
  
    self.vmType = 'VirtualMachineType'
  
    self.charmMaintainer = 'Charm Generator <charmgen@example.com>'
  
    # Extract CSAR file
    if os.path.isdir(absCsarDir):
      shutil.rmtree(absCsarDir)
  
    os.makedirs(absCsarDir)
  
    csar = zipfile.ZipFile(csarFile)
    csar.extractall(absCsarDir)
    csar.close()
  
    # Read service template and parse it
    file = open(absCsarDir + '/' + relServiceTpl, 'r')
    doc = parse(file)
    file.close()
  
    # Find topology template
    if len(doc.getElementsByTagName('TopologyTemplate')) == 0:
      print 'Cannot find topology template.'
      sys.exit()
  
    self.topologyTemplate = doc.getElementsByTagName('TopologyTemplate')[0]
  
    # Build model structure
    self.nodeTypes = {}
    self.relationshipTypes = {}
  
    self.charms = {}
    self.topology = {'nodes': {}, 'relations': {}}
  
    self.model = {'charms': self.charms, 'topology': self.topology}

    # Discover node types
    for nodeType in doc.getElementsByTagName('NodeType'):
      nodeTypeId = nodeType.getAttribute('id')
      nodeTypeName = nodeType.getAttribute('name')
      derivedFrom = None
    
      if len(nodeType.getElementsByTagName('DerivedFrom')) > 0:
        derivedFrom = nodeType.getElementsByTagName('DerivedFrom')[0].getAttribute('nodeTypeRef')
  
      # Add node type to dict
      self.nodeTypes[nodeTypeId] = {'id': nodeTypeId, 'name': nodeTypeName, 'derivedFrom': derivedFrom, 'installArtifacts': []}
      print 'Node type "' + nodeTypeId + '" discovered.'
    
      for interface in nodeType.getElementsByTagName('Interface'):
        if interface.getAttribute('name') != self.lifecycleInterfaceName: continue
  
        for artifact in interface.getElementsByTagName('ImplementationArtifact'):
          if artifact.getAttribute('operationName') != self.installOperationName: continue
          if artifact.getAttribute('type') != self.chefArtifactType: continue
        
          for child in artifact.childNodes:
            if self.chefNodeName in child.nodeName:
              chefArtifact = child
            
              # Add Chef artifact
              self.nodeTypes[nodeTypeId]['installArtifacts'].append(chefArtifact)
              print 'Node type "' + nodeTypeId + '": Chef artifact for "install" operation discovered.'

    # Discover relationship types
    for relType in doc.getElementsByTagName('RelationshipType'):
      relTypeId = relType.getAttribute('id')
      relTypeName = relType.getAttribute('name')
      derivedFrom = None
    
      if len(relType.getElementsByTagName('DerivedFrom')) > 0:
        derivedFrom = relType.getElementsByTagName('DerivedFrom')[0].getAttribute('relationshipTypeRef')
  
      # Add relationship type to dict
      self.relationshipTypes[relTypeId] = {'id': relTypeId, 'name': relTypeName, 'derivedFrom': derivedFrom, 'sourceArtifacts': [], 'targetArtifacts': []}
      print 'Relationship type "' + relTypeId + '" discovered.'
    
      sourceInterfaces = relType.getElementsByTagName('SourceInterfaces')
      targetInterfaces = relType.getElementsByTagName('TargetInterfaces')
  
      if len(sourceInterfaces) > 0:
        for artifact in sourceInterfaces[0].getElementsByTagName('ImplementationArtifact'):
          if artifact.getAttribute('type') != self.chefArtifactType: continue
        
          for child in artifact.childNodes:
            if self.chefNodeName in child.nodeName:
              chefArtifact = child
            
              # Add Chef artifact
              self.relationshipTypes[relTypeId]['sourceArtifacts'].append(chefArtifact)
              print 'Relationship type "' + relTypeId + '": Chef artifact for "' + artifact.getAttribute('operationName') + '" operation discovered.'
    
      if len(targetInterfaces) > 0:
        for artifact in targetInterfaces[0].getElementsByTagName('ImplementationArtifact'):
          if artifact.getAttribute('type') != self.chefArtifactType: continue
        
          for child in artifact.childNodes:
            if self.chefNodeName in child.nodeName:
              chefArtifact = child
            
              # Add Chef artifact
              self.relationshipTypes[relTypeId]['targetArtifacts'].append(chefArtifact)
              print 'Relationship type "' + relTypeId + '": Chef artifact for "' + artifact.getAttribute('operationName') + '" operation discovered.'


  
  # Find all relationships for a given node template
  def findRelationships(self, nodeTemplate):
    nodeTemplateId = nodeTemplate.getAttribute('id')
    relationships = []
  
    for rel in self.topologyTemplate.childNodes:
      if rel.nodeName == 'RelationshipTemplate':
        source = rel.getElementsByTagName('SourceElement')[0]
        target = rel.getElementsByTagName('TargetElement')[0]
        
        if source.getAttribute('id') == nodeTemplateId:
          relationships.append(rel)
          
        if target.getAttribute('id') == nodeTemplateId:
          relationships.append(rel)
  
    return relationships
  
  # Find all virtual machine nodes in the topology template
  def findVirtualMachines(self):
    vmNodes = []
    
    for node in self.topologyTemplate.childNodes:
      if node.nodeName == 'NodeTemplate' and node.getAttribute('nodeType') == self.vmType:
        vmNodes.append(node)
    
    return vmNodes
  
  # Returns the node template which represents the source of the given relationship
  def getRelationshipSource(self, relationshipTemplate):
    source = relationshipTemplate.getElementsByTagName('SourceElement')[0]
    
    for tpl in self.topologyTemplate.childNodes:
      if tpl.nodeName == 'NodeTemplate' and tpl.getAttribute('id') == source.getAttribute('id'):
        return tpl
  
    return None
  
  # Returns the node template which represents the target of the given relationship
  def getRelationshipTarget(self, relationshipTemplate):
    target = relationshipTemplate.getElementsByTagName('TargetElement')[0]
    
    for tpl in self.topologyTemplate.childNodes:
      if tpl.nodeName == 'NodeTemplate' and tpl.getAttribute('id') == target.getAttribute('id'):
        return tpl
  
    return None
  
  # Returns true iff the given node template is the source of the relationship
  def isRelationshipSource(self, nodeTemplate, relationshipTemplate):
    nodeTemplateId = nodeTemplate.getAttribute('id')
    sourceId = self.getRelationshipSource(relationshipTemplate).getAttribute('id')
    
    if sourceId == nodeTemplateId:
      return True
    else:
      return False
  
  # Returns true iff the given node template is the target of the relationship
  def isRelationshipTarget(self, nodeTemplate, relationshipTemplate):
    nodeTemplateId = nodeTemplate.getAttribute('id')
    sourceId = self.getRelationshipTarget(relationshipTemplate).getAttribute('id')
    
    if sourceId == nodeTemplateId:
      return True
    else:
      return False
  
  # Returns true iff the given relationship crosses VM borders
  def relationshipCrossesVMs(self, relationshipTemplate):
    source = self.getRelationshipSource(relationshipTemplate)
    target = self.getRelationshipTarget(relationshipTemplate)
    
    if source.getAttribute('vm') != target.getAttribute('vm'):
      return True
    else:
      return False
  
  # Returns true iff the given relationship is of type "hosted on"
  def isHostedOnRelationship(self, relationshipType):
    if relationshipType['id'] == self.hostedOnType: return True
    else:
      derivedFrom = relationshipType['derivedFrom']
      
      if derivedFrom == None: return False
      else: return self.isHostedOnRelationship(self.relationshipTypes[derivedFrom])
  
  # Returns true iff the given relationship is of type "depends on"
  def isDependsOnRelationship(self, relationshipType):
    if relationshipType['id'] == self.dependsOnType: return True
    else:
      derivedFrom = relationshipType['derivedFrom']
      
      if derivedFrom == None: return False
      else: return self.isDependsOnRelationship(self.relationshipTypes[derivedFrom])
  
  # Returns true iff the given relationship is of type "connects to"
  def isConnectsToRelationship(self, relationshipType):
    if relationshipType['id'] == self.connectsToType: return True
    else:
      derivedFrom = relationshipType['derivedFrom']
      
      if derivedFrom == None: return False
      else: return self.isConnectsToRelationship(self.relationshipTypes[derivedFrom])
  
  # Returns all the node properties as a dictionary
  def getNodeProperties(self, nodeTemplate):
    props = {}
  
    def addProperties(propDefs, props):
      if len(propDefs) > 0 and len(propDefs[0].childNodes) > 0:
        for propSet in propDefs[0].childNodes:
          if propSet.nodeType == Node.ELEMENT_NODE:
            for prop in propSet.childNodes:
              if prop.nodeType == Node.ELEMENT_NODE: props[prop.nodeName] = prop.firstChild.data
    
    nodePropDefs = nodeTemplate.getElementsByTagName('PropertyDefaults')
    addProperties(nodePropDefs, props)
    
    for rel in self.findRelationships(nodeTemplate):
      if self.isRelationshipTarget(nodeTemplate, rel):
        propDefs = self.getRelationshipSource(rel).getElementsByTagName('PropertyDefaults')
      else:
        propDefs = self.getRelationshipTarget(rel).getElementsByTagName('PropertyDefaults')
  
      if len(propDefs) > 0: addProperties(propDefs, props)
  
    return props
  
  # Returns the node type of the given node template
  def getNodeType(self, nodeTemplate):
    return self.nodeTypes[self.getNodeTypeName(nodeTemplate)]
  
  # Returns the name of the node type of the given node template
  def getNodeTypeName(self, nodeTemplate):
    return getNCName(nodeTemplate.getAttribute('nodeType'))
  
  # Returns the relationship type of the given relationship template
  def getRelationshipType(self, relationshipTemplate):
    return self.relationshipTypes[self.getRelationshipTypeName(relationshipTemplate)]
  
  # Returns the name of the relationship type of the given relationship template
  def getRelationshipTypeName(self, relationshipTemplate):
    return getNCName(relationshipTemplate.getAttribute('relationshipType'))
  
  # ...
  def addVMAnnotations(self, node, vmId):
    node.setAttribute('vm', vmId)
    print 'Node "' + node.getAttribute('id') + '" is hosted on virtual machine "' + vmId + '".'
  
    relationships = self.findRelationships(node)
    
    for rel in relationships:
      relType = self.getRelationshipType(rel)
  
      if self.isHostedOnRelationship(relType):
        if self.isRelationshipTarget(node, rel):
          sourceNode = self.getRelationshipSource(rel)
          self.addVMAnnotations(sourceNode, vmId)
  
  # Process relationships for the given node that do not cross VM borders
  def processNonCrossVMRelationships(self, node, charm):
    relationships = self.findRelationships(node)
    
    for rel in relationships:
      relType = self.getRelationshipType(rel)
  
      if self.isDependsOnRelationship(relType) and not self.relationshipCrossesVMs(rel):
        if self.isRelationshipSource(node, rel) and not rel.hasAttribute('sourceProcessed'):
          for artifact in relType['sourceArtifacts']:
            self.processArtifact(artifact, charm['runLists']['install'], charm['cookbooks'], charm['roles'], charm['mappings'])
            rel.setAttribute('sourceProcessed', 'true')
  
            print 'Relationship "' + rel.getAttribute('id') + '" between node "' + self.getRelationshipSource(rel).getAttribute('id') + '" and node "' + self.getRelationshipTarget(rel).getAttribute('id') + '" processed.'
  
          targetNode = self.getRelationshipTarget(rel)
          self.processNonCrossVMRelationships(targetNode, charm)
          targetNode.setAttribute('processed', 'true')
  
        #TODO: Target artifacts for relationships not yet implemented!
  
    for rel in relationships:
      relType = self.getRelationshipType(rel)
      nodeType = self.getNodeType(node)
  
      if self.isHostedOnRelationship(relType):
        if self.isRelationshipSource(node, rel) and not rel.hasAttribute('sourceProcessed'):
          for artifact in relType['sourceArtifacts']:
            self.processArtifact(artifact, charm['runLists']['install'], charm['cookbooks'], charm['roles'], charm['mappings'])
            rel.setAttribute('sourceProcessed', 'true')
  
            print 'Relationship "' + rel.getAttribute('id') + '" between node "' + self.getRelationshipSource(rel).getAttribute('id') + '" and node "' + self.getRelationshipTarget(rel).getAttribute('id') + '" processed.'
  
          if not node.hasAttribute('processed'):
            for artifact in nodeType['installArtifacts']:
              self.processArtifact(artifact, charm['runLists']['install'], charm['cookbooks'], charm['roles'], charm['mappings'])
              charm['properties'].update(self.getNodeProperties(node))
              
              charm['deployedComponents'].append({'id': node.getAttribute('id'), 'name': node.getAttribute('name'), 'type': nodeType['id']})
              charm['name'] = node.getAttribute('id')
              charm['summary'] = node.getAttribute('name')
              
            node.setAttribute('processed', 'true')
  
        #TODO: Target artifacts for relationships not yet implemented!
        elif self.isRelationshipTarget(node, rel):
          sourceNode = self.getRelationshipSource(rel)
          self.processNonCrossVMRelationships(sourceNode, charm)
  
  # ...
  def processArtifact(self, artifact, runList, cookbooks, roles, mappings):
    for cookbook in artifact.getElementsByTagName('Cookbook'):
      cookbooks[cookbook.getAttribute('name')] = cookbook.getAttribute('cookbookLocation')
    for role in artifact.getElementsByTagName('Role'):
      roles[role.getAttribute('name')] = role.getAttribute('roleDefLocation')
    for mapping in artifact.getElementsByTagName('PropertyMapping'):
      mappings[mapping.getAttribute('propertyPath')[1:]] = mapping.getAttribute('cookbookAttribute')
    for runListEntry in artifact.getElementsByTagName('RunList')[0].getElementsByTagName('Include')[0].getElementsByTagName('RunListEntry'):
      entry = None
    
      if runListEntry.hasAttribute('roleName'):
        entry = 'role[' + runListEntry.getAttribute('roleName') + ']'
      elif runListEntry.hasAttribute('cookbookName') and runListEntry.hasAttribute('recipeName'):
        entry = 'recipe[' + runListEntry.getAttribute('cookbookName') + '::' + runListEntry.getAttribute('recipeName') + ']'
      elif runListEntry.hasAttribute('cookbookName'):
        entry = 'recipe[' + runListEntry.getAttribute('cookbookName') + ']'
  
      if entry != None and not entry in runList:
        runList.append(entry)
  
  # ...
  def processCrossVMRelationships(self, node, charm):
    relationships = self.findRelationships(node)
    
    if charm['vm'] != node.getAttribute('vm'):
      return
    
    for rel in relationships:
      relType = self.getRelationshipType(rel)
      relTypeName = convert(relType['id'])
      
      if self.isRelationshipSource(node, rel) and self.relationshipCrossesVMs(rel) and not rel.hasAttribute('sourceProcessed'):
        for artifact in relType['sourceArtifacts']:
          runList = []
          self.processArtifact(artifact, runList, charm['cookbooks'], charm['roles'], charm['mappings'])
  
          charm['requires'][relTypeName] = {'runLists': {'relationJoined': runList}}
          sourceCharm = self.topology['nodes'][node.getAttribute('vm')]['charm']
          targetCharm = self.topology['nodes'][self.getRelationshipTarget(rel).getAttribute('vm')]['charm']
          self.topology['relations'][sourceCharm + ':' + relTypeName] = targetCharm + ':' + relTypeName
          rel.setAttribute('sourceProcessed', 'true')
  
          print 'Relationship "' + rel.getAttribute('id') + '" between node "' + self.getRelationshipSource(rel).getAttribute('id') + '" and node "' + self.getRelationshipTarget(rel).getAttribute('id') + '" processed.'
  
      elif self.isRelationshipTarget(node, rel):
        if self.relationshipCrossesVMs(rel):
          charm['provides'][relTypeName] = {'runLists': {'relationJoined': []}}
      
        sourceNode = self.getRelationshipSource(rel)
        self.processCrossVMRelationships(sourceNode, charm)


  
  def transform(self):
    # Build the model based on the nodes and relationships in the topology template
    virtualMachines = self.findVirtualMachines()
  
    for vmNode in virtualMachines:
      charm = {'vm': vmNode.getAttribute('id'), 'name': vmNode.getAttribute('id'), 'summary': vmNode.getAttribute('name'), 'runLists': {'install': []}, 'deployedComponents': [], 'provides': {}, 'requires': {}, 'properties': {}, 'cookbooks': {}, 'roles': {}, 'mappings': {}}
    
      self.addVMAnnotations(vmNode, vmNode.getAttribute('id'))
      self.processNonCrossVMRelationships(vmNode, charm)
	  
      charmName = convert(charm['name'])
  
      self.topology['nodes'][vmNode.getAttribute('id')] = {'charm': charmName}
  
      self.charms[charmName] = charm
  
    for vmNode in virtualMachines:
      charm = self.charms[self.topology['nodes'][vmNode.getAttribute('id')]['charm']]
    
      self.processCrossVMRelationships(vmNode, charm)
  
    for charm in self.charms.values():
      del charm['name']
      del charm['vm']
    
      charm['maintainer'] = self.charmMaintainer
      charm['description'] = yaml.safe_dump({'Deployed Components': charm['deployedComponents'], 'Properties': charm['properties']}, default_flow_style=False)

    return self.model