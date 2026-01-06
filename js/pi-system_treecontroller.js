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

app.controller('TreeCtrl', ['$scope', '$http','CreateModalFromTemplate', 'TreeDataService', function($scope, $http, CreateModalFromTemplate, TreeDataService) {
$scope.init = function() {
    $http.get('/plugins/pi-system/resource/tree.json')
  .then(function(response) {
        TreeDataService.setTreeData(response.data);
        //$scope.config.treeData = TreeDataService.getTreeData();
  })
}


  $scope.refreshTree = function(newTree) {
    $scope.config.treeData = newTree.choices
  }

  // Toggle récursif des checkboxes
  $scope.toggleChildren = function(node) {
    console.log("ALX:tc:" + JSON.stringify(node));
    if (node.children && node.children.length) {
      node.children.forEach(function(child) {
        child.checked = node.checked;
        $scope.toggleChildren(child);
      });
    }
  };

  $scope.getChildrenFromDB = function(item){
    console.log("ALX:gcfd:" + JSON.stringify(item));
    $scope.callPythonDo({ method: "get_children_from_db", parent: item })
      .then(function (data) {
        console.log("ALX:data1=" + JSON.stringify(data));
        item.children = data.choices;
        item.children.forEach(child => {
          child.checked = item.checked;
          child.expanded = item.expanded;
        });
      });
    };
}]);

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
    
    //$scope.config.treeData = TreeDataService.getTreeData(); 
     // $scope.config.treeData = TreeDataService.getTreeData();
    
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
        // $scope.config["server_name"] = data.choices;
        $scope.server_name = data.choices;
      });
    };
    $scope.getDatabases = function() {
      $scope.callPythonDo({parameterName: "database_name"}).then(function(data){
        $scope.database_name = data.choices;
      });
    };
      
    $scope.initializeTree = function(){
    /*  $scope.callPythonDo({method: "get_children_from_db", parent: $scope.config.database_name}).then(function(data){
          console.log("ALX:data2=" + JSON.stringify(data));
          TreeDataService.setTreeData(data.choices);
           $scope.treeData =  TreeDataService.getTreeData();
      });*/
        if(!$scope.config.treeData || $scope.config.treeData===[]){
               $http.get('/plugins/pi-system/resource/tree.json')
  .then(function(response) {
        TreeDataService.setTreeData(response.data);
        $scope.config.treeData = TreeDataService.getTreeData();
  })
        }

    };
      
              $scope.getMyTreeData = function() {
      $scope.callPythonDo({parameterName: "treeData"}).then(function(data){
        console.log("ALX:treeData return:"+JSON.stringify(data))
          TreeDataService.setMyTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
      });
    };
      
        $scope.getChildrenFromDB = function(item){
    console.log("ALX:gcfd:" + JSON.stringify(item));
         $http.get('/plugins/pi-system/resource/tree2.json')
  .then(function(response) {
        TreeDataService.setTreeData(response.data);
        $scope.config.treeData = TreeDataService.getTreeData();
  })
    /*$scope.callPythonDo({ method: "get_children_from_db", parent: item })
      .then(function (data) {
        console.log("ALX:data1=" + JSON.stringify(data));
        item.children = data.choices;
        item.children.forEach(child => {
          child.checked = item.checked;
          child.expanded = false;
        });
      });*/
    } 
        
        
  // Toggle récursif des checkboxes
  $scope.toggleChildren = function(node) {
    console.log("ALX:tc:" + JSON.stringify(node));
    if (node.children && node.children.length) {
      node.children.forEach(function(child) {
        child.checked = node.checked;
        $scope.toggleChildren(child);
      });
    }
      $scope.getMyTreeData();
  };

  $scope.doSearch = function(element_name, attribute_name){
      $scope.callPythonDo({method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.config.treeData}).then(
        function(data){
          $scope.config.treeData = data.choices;
        }
      );
    };

}]);

app.directive('treeNode', function() {
  return {
    restrict: 'E',
    scope: { node: '=' },
    template: `
      <div style="display: flex; align-items: center; gap: 6px;">
        
        <!-- Flèche si le noeud possède des enfants -->
        <span ng-if="node.children"
              ng-click="toggleExpand(node)"
              style="cursor: pointer; user-select: none;">
          <strong ng-if="node.expanded">▼</strong>
          <strong ng-if="!node.expanded">▶</strong>
        </span>

        <!-- Espace vide si pas d’enfants -->
        <!--<span ng-if="!node.children || node.children.length === 0" style="width: 12px;"></span>-->

        <label>
          <input type="checkbox" ng-model="node.checked" ng-change="toggleChildren(node)">
          {{ node.title }}
        </label>
      </div>

      <!-- Affichage récursif -->
      <ul ng-if="node.children && node.children.length > 0 && node.expanded" style="margin-left: 20px;">
        <li ng-repeat="child in node.children">
          <tree-node node="child"></tree-node>
        </li>
      </ul>
    `,
    link: function(scope) {
      // Récupère la fonction toggleChildren du parent
      scope.toggleChildren = scope.$parent.toggleChildren;
      scope.getChildrenFromDB = scope.$parent.getChildrenFromDB;
      scope.doSearch = scope.$parent.doSearch
      // Simple toggle du expand (plus de chargement HTTP)
      scope.toggleExpand = function(node) {
        console.log("ALX:expand !" + JSON.stringify(node));
        node.expanded = !node.expanded;
        scope.getChildrenFromDB(node);
      };
    }
  };
});
