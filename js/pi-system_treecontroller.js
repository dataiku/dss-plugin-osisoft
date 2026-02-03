var app = angular.module('piSystemTreeApp.module', []);

app.service('TreeDataService', function() {
  // This will store the shared tree data
  this.treeData = [];

  // Optional: helper methods
  this.setTreeData = function(data) {
    this.treeData = data;
  };

  this.getTreeData = function() {
    return this.treeData;
  };
});

app.controller('AfExplorerFormCtrl', [
  '$scope', 
  '$stateParams', 
  'CodeMirrorSettingService', 
  'TreeDataService', 
  function($scope, $stateParams, CodeMirrorSettingService, TreeDataService) {
    
    $scope.paramDesc = {
      'parameterSetId': 'basic-auth',
      'mandatory': true
    };
    
    $scope.treeData = TreeDataService.getTreeData();
    $scope.config.attributeList = $scope.config.attributeList || [];
    $scope.config.selectedAttributes = $scope.config.selectedAttributes || [];
    
    $scope.editorOptions = CodeMirrorSettingService.get("text/plain");

    $scope.init = function() {
        DataikuAPI.plugins.listAccessiblePresets('pi-system', $stateParams.projectKey, 'basic-auth').success(function (data) {
            $scope.inlineParams = data.inlineParams;
            $scope.inlinePluginParams = data.inlinePluginParams;
            $scope.accessiblePresets = [];
            if (data.definableInline) {
                $scope.accessiblePresets.push({
                    name:"INLINE",
                    label:"Manually defined", usable:true,
                    description: "Define values for these parameters"
                });
            }
            data.presets.forEach(function(p) {
                $scope.accessiblePresets.push({name:"PRESET " + p.name, label:p.name, usable:p.usable, description:p.description});
            });
            $scope.accessibleParameterSetDescriptions = $scope.accessiblePresets.map(function(p) { 
                return p.description || '<em>No description</em>';
            });
        }).error(setErrorInScope.bind($scope.errorScope));
        if($scope.authConfigured() === true){
          $scope.authSectionVisible = false;
          $scope.showTreeData = true;
        }
    };
    
    $scope.getServers = function(){
      $scope.callPythonDo({parameterName: "server_name"}).then(function(data){
        $scope.server_name = data.choices;
      });
    };
    $scope.getDatabases = function() {
      $scope.callPythonDo({parameterName: "database_name"}).then(function(data){
        $scope.database_name = data.choices;
      });
    };

    $scope.authSectionVisible = $scope.authSectionVisible || true;

    $scope.toggleAuthSection = function() {
      $scope.authSectionVisible = !$scope.authSectionVisible;
    };

    $scope.authConfigured = function(){
      console.log('authConfigured check');
      return $scope.hasPreset() && $scope.config.database_name && $scope.config.database_name.length > 0 && $scope.config.server_name && $scope.config.server_name.length > 0 ;
    }
    $scope.explore = function() {
      console.log("coucou");
      if ($scope.authConfigured()) {
        console.log("here");
        $scope.showTreeData = true;
      }
    };

    $scope.hasPreset = function() {
      return $scope.config.credentials && $scope.config.credentials.mode && $scope.config.credentials.mode!=='NONE' && $scope.config.credentials.name
    }
      
    $scope.initializeTree = function(){
        console.log("initialization: ");
        console.log($scope.config.treeData);
        if (!$scope.config.treeData || $scope.config.treeData.length === 0){
      $scope.callPythonDo({method: "get_children_from_db", parent: $scope.config.database_name}).then(function(data){
          console.log("ALX:data2=" + JSON.stringify(data));
          TreeDataService.setTreeData(data.choices);
           $scope.config.treeData =  TreeDataService.getTreeData();
      });
        }
    };
      
        $scope.getChildrenFromDB = function(item){
    console.log("ALX:gcfd:" + JSON.stringify(item));
    return $scope.callPythonDo({ method: "get_children_from_db", parent: item })
      .then(function (data) {
        console.log("ALX:data1=" + JSON.stringify(data));
        item.children = data.choices;
        item.children.forEach(child => {
          child.expanded = false;
        });
        console.log(item);
        return item;
      });
    } 

    $scope.getTemplatesFromDB = function() {
      $scope.callPythonDo({method: "get_templates_from_db"}).then(function(data){
        $scope.config.templates = data.choices;
      });
    }

    $scope.getCategoriesFromDB = function(){
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.callPythonDo({method: "get_attribute_categories_from_db"}).then(function(data){
        $scope.config.attribute_categories = data.choices;
      });
      $scope.callPythonDo({method: "get_element_categories_from_db"}).then(function(data){
        $scope.config.element_categories = data.choices;
      });
    }

  // Toggle récursif des checkboxes
  $scope.toggleChildren = function(node) {
    console.log("ALX:tc:" + JSON.stringify(node));
      node.expanded = !node.expanded;
      $scope.getChildrenFromDB(node);
    if (node.children && node.children.length) {
      node.children.forEach(function(child) {
        child.expanded = !child.expanded;
        $scope.getChildrenFromDB(child);
      });
    }
      
  };

  $scope.doSearch = function(element_name, attribute_name){
      $scope.callPythonDo({method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.config.treeData}).then(
        function(data){
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
          console.log("ALX:", JSON.stringify($scope.config.treeData));
          $scope.config.attributeList = data.attributes;
          $scope.config.selectedAttributes = [];
        }
      );
    };

  $scope.updateAttributeToOutput = function (attribute) {
    if (attribute.checked && $scope.config.selectedAttributes.includes(attribute)) {
      $scope.config.selectedAttributes = $scope.config.selectedAttributes.filter(attr => attr.path !== attribute.path);
    }
    else {
      console.log("Adding attribute to output:", attribute);

      if (!$scope.config || !$scope.config.attributeList || $scope.config.selectedAttributes.includes(attribute)) {
        return;
      }
      const attrInConfig = $scope.config.attributeList.find(attr => attr.path === attribute.path);

      if (attrInConfig) {
        $scope.config.selectedAttributes.push(attribute);
        attrInConfig.checked = true;
      } else {
        console.warn("Attribute not found in config:", attribute.path);
      }
    }
  };


$scope.displayAttributes = function(node) {

    if (!node.children || node.children.length === 0) {
        $scope.getChildrenFromDB(node).then(newNode => {
        processNode(newNode);
        });
    } else {
        processNode(node);
    };
  }

function processNode(node) {
    $scope.config.attributeList =  [];
    $scope.config.selectedAttributes =  [];
    node.children.forEach(child => {
        if (child.type === "attribute") {
            $scope.config.attributeList.push({
                "name": child.title,
                "path": child.path
            });
        }
    });
}


}]);

app.directive('treeNode', function() {
  return {
    restrict: 'E',
    scope: { node: '=' },
    template: `
      <div style="display: flex; align-items: center; gap: 6px;">
        
        <span ng-click="$event.stopPropagation();toggleExpand(node)"
              style="cursor: pointer;">
          <strong ng-if="node.expanded">▼</strong>
          <strong ng-if="!node.expanded">▶</strong>
        </span>

        <!--<span ng-if="!node.children || node.children.length === 0" style="width: 12px;"></span>-->

        <!--<label>
          <input type="checkbox" ng-model="node.checked" ng-change="toggleChildren(node)">
          {{ node.title }}
        </label>-->

        <div class="tree-node">

          <span ng-if="node.type==='element'"
            class="tree-node__label"
            ng-click="displayAttributes(node)"
            ng-class="{'tree-node__label--clickable': hasAttributes(node)}"
          >{{ node.title }}</span>
        </div>


      </div>

      <ul ng-if="node.children && node.children.length > 0 && node.expanded" style="margin-left: 20px;">
        <li ng-repeat="child in node.children" ng-if="child.type=='element'">
          <tree-node node="child"></tree-node>
        </li>
      </ul>
    `,
    link: function(scope) {
      scope.toggleChildren = scope.$parent.toggleChildren;
      scope.getChildrenFromDB = scope.$parent.getChildrenFromDB;
      scope.doSearch = scope.$parent.doSearch;
      scope.config = scope.$parent.config;
      scope.attributeList = scope.config.attributeList || [];
      scope.displayAttributes = scope.$parent.displayAttributes;
      scope.toggleExpand = function(node) {
        node.expanded = !node.expanded;

        if (node.expanded && (!node.children || !node.children.length)) {
          scope.getChildrenFromDB(node);
        }
      };

      scope.hasAttributes = function(node) {
        if (!Array.isArray(scope.$parent.config.attributeList) || scope.$parent.config.attributeList.length === 0) {
          return false;
        }

        return scope.$parent.config.attributeList.some(child => {
          const expected = node.title + "|" + child.title;
        return child.path.endsWith(expected);
        });
      };

      scope.isElement = function(child) {
        return child.type === 'element';
      }
    }
  };
});
