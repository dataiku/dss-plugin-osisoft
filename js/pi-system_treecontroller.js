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
    $scope.attributeList = $scope.attributeList || [];
    
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
          child.checked = item.checked;
          child.expanded = item.expanded;
        });
        console.log(item);
        return item;
      });
    } 
        
        
  // Toggle récursif des checkboxes
  $scope.toggleChildren = function(node) {
    console.log("ALX:tc:" + JSON.stringify(node));
      node.expanded = !node.expanded;
      $scope.getChildrenFromDB(node);
    if (node.children && node.children.length) {
      node.children.forEach(function(child) {
        child.checked = node.checked;
        //child.expanded = !child.expanded;
        //$scope.toggleChildren(child);
        $scope.getChildrenFromDB(child);
      });
    }
      console.log(node);
      console.log($scope.config.treeData);
      
  };

  $scope.doSearch = function(element_name, attribute_name){
      $scope.callPythonDo({method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.treeData}).then(
        function(data){
          //$scope.config.treeData = data.choices;
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
        }
      );
    };
      
    $scope.displayAttributes = function(node) {
        console.log("in display attributes");
        if (Array.isArray(node)) {
            node.forEach(child => $scope.displayAttributes(child));
            return;
        }
        if (node.type === "attribute") {
            console.log("Attribute found:", node.title, "Path:", node.path);
            $scope.attributeList.push({"name": node.title, "path": node.path});
        }
        if (node.children && node.children.length > 0) {
            node.children.forEach(child => $scope.displayAttributes(child));
        }
    
    
}

$scope.newDisplayAttributes = function(node) {
  console.log("in new display attributes for node:");
    if (node.has_children === false) return;

    if (node.has_children === true && (!node.children || node.children.length === 0)) {
        console.log("Searching for children of node:", node);

        $scope.getChildrenFromDB(node).then(newNode => {
            console.log("After getting children, node is:", newNode);
            processNode(newNode);
        });
    } else {
        processNode(node);
    }
};

function processNode(node) {
    $scope.attributeList = [];
    node.children.forEach(child => {
        if (child.type === "attribute") {
            $scope.attributeList.push({
                name: child.title,
                path: child.path
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
        
        <span ng-if="node.children && node.children.length > 0 && node.children.some(isElement)"
"
              ng-click="toggleExpand(node)"
              style="cursor: pointer; user-select: none;">
          <strong ng-if="node.expanded">▼</strong>
          <strong ng-if="!node.expanded">▶</strong>
        </span>

        <!--<span ng-if="!node.children || node.children.length === 0" style="width: 12px;"></span>-->

        <!--<label>
          <input type="checkbox" ng-model="node.checked" ng-change="toggleChildren(node)">
          {{ node.title }}
        </label>-->

        <div class="tree-node">
  <!-- putting aside until next spec is updated 
<input
    type="checkbox"
    ng-model="node.checked"
    ng-change="toggleChildren(node)"
    ng-click="$event.stopPropagation()"
  >-->

  <span ng-if="node.type==='element'"
    class="tree-node__label"
    ng-click="newDisplayAttributes(node)"
  >
    {{ node.title }}
  </span>
  <span ng-repeat="attr in node.attributes" class="tree-node__attribute">
    [{{attr.name}}: {{attr.value}}]
  </span>
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
      scope.attributeList = scope.$parent.attributeList || [];
      scope.newDisplayAttributes = scope.$parent.newDisplayAttributes;
      scope.toggleExpand = function(node) {
        console.log("ALX:expand !" + JSON.stringify(node));
        node.expanded = !node.expanded;
        scope.getChildrenFromDB(node);
      };
      scope.isElement = function(child) {
        return child.type === 'element';
      }

    }
  };
});
