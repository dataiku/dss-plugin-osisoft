var app = angular.module('piSystemTreeApp.module', []);

app.service('TreeDataService', function () {
  // This will store the shared tree data
  this.treeData = [];

  // Optional: helper methods
  this.setTreeData = function (data) {
    this.treeData = data;
  };

  this.getTreeData = function () {
    return this.treeData;
  };
});

app.controller('AfExplorerFormCtrl', [
  '$scope',
  '$stateParams',
  'CodeMirrorSettingService',
  'TreeDataService',
  function ($scope, $stateParams, CodeMirrorSettingService, TreeDataService) {

    $scope.paramDesc = {
      'parameterSetId': 'basic-auth',
      'mandatory': true
    };

    $scope.treeData = TreeDataService.getTreeData();
    $scope.config.attributeList = $scope.config.attributeList || [];
    $scope.config.selectedAttributes = $scope.config.selectedAttributes || [];
    $scope.config.clickedNodes = $scope.config.clickedNodes || [];

    $scope.editorOptions = CodeMirrorSettingService.get("text/plain");

    $scope.init = function () {
      DataikuAPI.plugins.listAccessiblePresets('pi-system', $stateParams.projectKey, 'basic-auth').success(function (data) {
        $scope.inlineParams = data.inlineParams;
        $scope.inlinePluginParams = data.inlinePluginParams;
        $scope.accessiblePresets = [];
        if (data.definableInline) {
          $scope.accessiblePresets.push({
            name: "INLINE",
            label: "Manually defined", usable: true,
            description: "Define values for these parameters"
          });
        }
        data.presets.forEach(function (p) {
          $scope.accessiblePresets.push({ name: "PRESET " + p.name, label: p.name, usable: p.usable, description: p.description });
        });
        $scope.accessibleParameterSetDescriptions = $scope.accessiblePresets.map(function (p) {
          return p.description || '<em>No description</em>';
        });
      }).error(setErrorInScope.bind($scope.errorScope));
      if ($scope.authConfigured() === true) {
        $scope.authSectionVisible = false;
        $scope.showTreeData = true;
      }
      $scope.config.template = $scope.config.template || "-- Any --";
    };

    $scope.getServers = function () {
      $scope.callPythonDo({ parameterName: "server_name" }).then(function (data) {
        $scope.server_name = data.choices;
      });
    };
    $scope.getDatabases = function () {
      $scope.callPythonDo({ parameterName: "database_name" }).then(function (data) {
        $scope.database_name = data.choices;
      });
    };

    $scope.authSectionVisible = $scope.authSectionVisible || true;

    $scope.toggleAuthSection = function () {
      $scope.authSectionVisible = !$scope.authSectionVisible;
    };

    $scope.authConfigured = function () {
      console.log('authConfigured check');
      return $scope.hasPreset() && $scope.config.database_name && $scope.config.database_name.length > 0 && $scope.config.server_name && $scope.config.server_name.length > 0;
    }
    $scope.explore = function () {
      console.log("coucou");
      if ($scope.authConfigured()) {
        console.log("here");
        $scope.showTreeData = true;
      }
    };

    $scope.hasPreset = function () {
      return $scope.config.credentials && $scope.config.credentials.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
    }

    $scope.initializeTree = function () {
      console.log("initialization: ");
      console.log($scope.config.treeData);
      if (!$scope.config.treeData || $scope.config.treeData.length === 0) {
        $scope.callPythonDo({ method: "get_children_from_db", parent: $scope.config.database_name }).then(function (data) {
          console.log("ALX:data2=" + JSON.stringify(data));
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
        });
      }
    };

    $scope.getChildrenFromDB = function (item) {
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

    $scope.getTemplatesFromDB = function () {
      $scope.callPythonDo({ method: "get_templates_from_db" }).then(function (data) {
        $scope.config.templates = data.choices;
      });
    }

    $scope.activeTab = 'element'; // tab par défaut

    $scope.setTab = function(tab) {
        $scope.activeTab = tab;
    };

    $scope.getCategoriesFromDB = function () {
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.callPythonDo({ method: "get_attribute_categories_from_db" }).then(function (data) {
        $scope.config.attribute_categories = data.choices;
      });
      $scope.callPythonDo({ method: "get_element_categories_from_db" }).then(function (data) {
        $scope.config.element_categories = data.choices;
      });
    }

    // Toggle récursif des checkboxes
    $scope.toggleChildren = function (node) {
      console.log("ALX:tc:" + JSON.stringify(node));
      node.expanded = !node.expanded;
      $scope.getChildrenFromDB(node);
      if (node.children && node.children.length) {
        node.children.forEach(function (child) {
          child.expanded = !child.expanded;
          $scope.getChildrenFromDB(child);
        });
      }

    };

    $scope.doSearch = function (element_name, attribute_name) {
      $scope.callPythonDo({ method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.config.treeData }).then(
        function (data) {
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
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


    $scope.displayAttributes = function (node) {

      if (!node.children || node.children.length === 0) {
        $scope.getChildrenFromDB(node).then(newNode => {
          processNode(newNode);
        });
      } else {
        processNode(node);
      };
    }

    function processNode(node) {
      if (node.title !== $scope.config.element_name) {
        $scope.config.element_name = "";
      }
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      node.children.forEach(child => {
        if (child.type === "attribute") {
          $scope.config.attributeList.push({
            "title": child.title,
            "path": child.path,
            "description": child.description
          });
        }
      });
    }


  }]);



app.component('treeNode', {
  bindings: {
    node: '=',
    getChildrenFromDb: '<',
    displayAttributes: '<',
    config: '<',
    clickedNodes: '='
  },

  controllerAs: 'ctrl',

  controller: function () {
    const ctrl = this;

    ctrl.toggleExpand = function (node, $event) {
      if ($event) {
        $event.stopPropagation();
      }

      node.expanded = !node.expanded;

      if (node.expanded && (!node.children || !node.children.length)) {
        // Call function reference directly
        ctrl.getChildrenFromDb(node);
      }
    };

    ctrl.onNodeClick = function (node) {
      const index = ctrl.clickedNodes.indexOf(node.url);
      if (index > -1) {
        ctrl.clickedNodes.splice(index, 1);
      } else {
        ctrl.clickedNodes.push(node.url);
      }
      console.log('Clicked nodes:', ctrl.clickedNodes);

      ctrl.displayAttributes(node);
    };

    ctrl.hasAttributes = function (node) {
      if (
        !Array.isArray(ctrl.config?.attributeList) ||
        !ctrl.config.attributeList.length
      ) {
        return false;
      }

      return ctrl.config.attributeList.some(attr => {
        const expected = node.title + '|' + attr.title;
        return attr.path.endsWith(expected);
      });
    };

    ctrl.isNodeClicked = function (node) {
      return ctrl.clickedNodes.includes(node.url);
    };
  },

  template: `
    <div style="display: flex; align-items: center; gap: 6px;">

      <span
        ng-click="ctrl.toggleExpand(ctrl.node, $event)"
        style="cursor: pointer;"
      >
        <strong ng-if="ctrl.node.has_children && ctrl.node.expanded">▼</strong>
        <strong ng-if="ctrl.node.has_children && !ctrl.node.expanded">▶</strong>
      </span>

      <div class="tree-node">
        <span
          ng-if="ctrl.node.type === 'element'"
          class="tree-node__label"
          ng-click="ctrl.onNodeClick(ctrl.node)"
          ng-class="{
            'tree-node__label--clickable':
              ctrl.isNodeClicked(ctrl.node)
          }"
        >
          {{ ctrl.node.title }}
        </span>
      </div>

    </div>

    <ul
      ng-if="ctrl.node.children && ctrl.node.children.length && ctrl.node.expanded"
      style="margin-left: 20px;"
    >
      <li
        ng-repeat="child in ctrl.node.children track by child.path"
        ng-if="child.type === 'element'"
      >
        <tree-node
          node="child"
          get-children-from-db="ctrl.getChildrenFromDb"
          display-attributes="ctrl.displayAttributes"
          config="ctrl.config"
          clicked-nodes="ctrl.clickedNodes"
        >
        </tree-node>
      </li>
    </ul>
  `
});


