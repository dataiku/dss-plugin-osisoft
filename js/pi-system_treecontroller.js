var app = angular.module('piSystemTreeApp.module', []);

app.controller('TreeCtrl', ['$scope', '$http','CreateModalFromTemplate', function($scope, $http, CreateModalFromTemplate) {
  $scope.treeData = [];
    $http.get('/plugins/treeview/resource/tree.json')
  .then(function(response) {
    $scope.treeData = response.data;
        console.log($scope.treeData);
  })

  // Toggle récursif des checkboxes
  $scope.toggleChildren = function(node) {
    console.log("ALX:" + JSON.stringify(node));
    if (node.children && node.children.length) {
      node.children.forEach(function(child) {
        child.checked = node.checked;
        $scope.toggleChildren(child);

      });
    }
  };
  $scope.testPythonDo = function(noken) {
    console.log("ALX:" + JSON.stringify(noken));
    console.log("ALX:config=" + JSON.stringify($scope.config))
    $scope.callPythonDo({method: "get_query_catalogs"}).then(function(data){
      console.log("ALX:testPythonDo return:"+JSON.stringify(data))
    });
  };

}]);

app.controller('AfExplorerFormController', function($scope, $stateParams, CodeMirrorSettingService) {
    $scope.paramDesc = {
      'parameterSetId': 'basic-auth',
      'mandatory': true
    };

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
    
    $scope.getServers = function(noken){
      console.log("ALX:get servers");
      console.log("ALX:" + JSON.stringify(noken));
      $scope.callPythonDo({parameterName: "server_name"}).then(function(data){
        console.log("ALX:getServers return:"+JSON.stringify(data))
        // $scope.config["server_name"] = data.choices;
        $scope.server_name = data.choices;
      });
    };
    $scope.getDatabases = function() {
      $scope.callPythonDo({parameterName: "database_name"}).then(function(data){
        console.log("ALX:getDatabases return:"+JSON.stringify(data))
        $scope.database_name = data.choices;
      });
    };

});

app.directive('treeNode', function() {
  return {
    restrict: 'E',
    scope: { node: '=' },
    template: `
      <div style="display: flex; align-items: center; gap: 6px;">
        
        <!-- Flèche si le noeud possède des enfants -->
        <span ng-if="node.children && node.children.length > 0"
              ng-click="toggleExpand(node)"
              style="cursor: pointer; user-select: none;">
          <strong ng-if="node.expanded">▼</strong>
          <strong ng-if="!node.expanded">▶</strong>
        </span>

        <!-- Espace vide si pas d’enfants -->
        <span ng-if="!node.children || node.children.length === 0" style="width: 12px;"></span>

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

      // Simple toggle du expand (plus de chargement HTTP)
      scope.toggleExpand = function(node) {
        console.log("ALX:expand !" + JSON.stringify(node));
        node.expanded = !node.expanded;
      };
    }
  };
});
