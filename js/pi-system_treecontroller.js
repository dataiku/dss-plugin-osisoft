var app = angular.module('piSystemTreeApp.module', []);

app.service('TreeDataService', function () {
  // This will store the shared tree data
  this.treeData = [];
  this.templateTreeData = [];

  // Optional: helper methods
  this.setTreeData = function (data) {
    this.treeData = data;
  };

  this.getTreeData = function () {
    return this.treeData;
  };

  this.setTemplateTreeData = function (data) {
    this.templateTreeData = data;
  };

  this.getTemplateTreeData = function () {
    return this.templateTreeData;
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
    $scope.templateTreeData = TreeDataService.getTemplateTreeData();
    $scope.config.attributeList = $scope.config.attributeList || [];
    $scope.config.selectedAttributes = $scope.config.selectedAttributes || [];
    $scope.config.clickedNodes = $scope.config.clickedNodes || [];

    $scope.editorOptions = CodeMirrorSettingService.get("text/plain");

    $scope.onAdvancedToggle = function () {
      if (!$scope.config.show_advanced_parameters) {
        $scope.config.is_ssl_check_disabled = false;
        $scope.config.elements_max_count = null;
        $scope.config.attributes_max_count = null;
      } else {
        if ($scope.config.elements_max_count === null || $scope.config.elements_max_count === undefined || $scope.config.elements_max_count === "") {
          $scope.config.elements_max_count = 100;
        }
        if ($scope.config.attributes_max_count === null || $scope.config.attributes_max_count === undefined || $scope.config.attributes_max_count === "") {
          $scope.config.attributes_max_count = 100;
        }
      }
    };

    $scope.init = function () {
      $scope.config.show_advanced_parameters = $scope.config.show_advanced_parameters || false;
      $scope.config.activeTab = $scope.config.activeTab || 'element';
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
        $scope.showTemplateTreeData = true;
      }
      $scope.config.template = $scope.config.template || "-- Any --";
      $scope.onAdvancedToggle();
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
      if ($scope.authConfigured()) {
        $scope.showTreeData = true;
        $scope.showTemplateTreeData = true;
        $scope.toggleAuthSection(); 
      }
    };

    $scope.hasPreset = function () {
      return $scope.config.credentials && $scope.config.credentials.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
    }

    $scope.cleanTree = function () {
      $scope.config.treeData = [];
      $scope.config.clickedNodes = [];
      $scope.config.attributeList = [];
    }

    $scope.resetDatasourceState = function () {
      $scope.server_name = [];
      $scope.database_name = [];
      $scope.config.server_name = null;
      $scope.config.database_name = null;
      $scope.config.templates = [];
      $scope.config.templateTreeData = [];
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      $scope.showTreeData = false;
      $scope.showTemplateTreeData = false;
      $scope.cleanTree();
    };

    var presetWatchInitialized = false;
    $scope.$watchGroup(
      [
        function () {
          return $scope.config && $scope.config.credentials ? $scope.config.credentials.mode : null;
        },
        function () {
          return $scope.config && $scope.config.credentials ? $scope.config.credentials.name : null;
        }
      ],
      function (newValues, oldValues) {
        if (!presetWatchInitialized) {
          presetWatchInitialized = true;
          return;
        }

        var mode = newValues[0];
        var name = newValues[1];
        var oldMode = oldValues ? oldValues[0] : null;
        var oldName = oldValues ? oldValues[1] : null;

        if (mode === oldMode && name === oldName) {
          return;
        }

        $scope.resetDatasourceState();

        if ($scope.hasPreset()) {
          $scope.getServers();
        }
      }
    );

    $scope.initializeTree = function () {
      console.log("initialization: ");
      if (!$scope.config.treeData || $scope.config.treeData.length === 0) {
        $scope.callPythonDo({ method: "get_children_from_db", parent: $scope.config.database_name }).then(function (data) {
          console.log("ALX:data2=" + JSON.stringify(data));
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
        });
      }
      
    };

    $scope.updateDatas = function () {
      $scope.cleanTree();
      $scope.initializeTree();
      $scope.getTemplatesFromDB();
      $scope.getCategoriesFromDB();
      $scope.showTreeData = false;
    }

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

    $scope.getTemplateHierarchyFromDB = function (item) {
      console.log("ALX:gthfd:" + JSON.stringify(item));
      return $scope.callPythonDo({ method: "get_template_hierarchy_from_db", parent: item })
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
        TreeDataService.setTemplateTreeData(data.choices);
        $scope.config.templateTreeData = TreeDataService.getTemplateTreeData();
      });
    }

    $scope.setTab = function(tab) {
        $scope.config.activeTab = tab;
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
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      $scope.config.clickedNodes = [];
      $scope.callPythonDo({ method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.config.treeData }).then(
        function (data) {
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
          $scope.config.attributeList = data.attributes;
        }
      );
    };

    $scope.onSearchInputKeydown = function ($event) {
      if ($event && ($event.key === "Enter" || $event.keyCode === 13)) {
        $event.preventDefault();
        $scope.doSearch($scope.config.element_name, $scope.config.attribute_name);
      }
    };

    $scope.toggleSelectAllAttributes = function () {
      if ($scope.config.selectAllAttributes) {
        $scope.config.selectedAttributes = [...$scope.config.attributeList];
        $scope.config.attributeList.forEach(attr => attr.checked = true);
      } else {
        $scope.config.selectedAttributes = [];
        $scope.config.attributeList.forEach(attr => attr.checked = false);
      }
    }

    $scope.updateAttributeToOutput = function (attribute) {
  if (!$scope.config || !$scope.config.attributeList) return;

  const selectedAttributes = $scope.config.selectedAttributes;
  const attributeList = $scope.config.attributeList;

  const index = selectedAttributes.findIndex(attr => attr.path === attribute.path);

  if (index !== -1) {
    selectedAttributes.splice(index, 1);

    const attrInConfig = attributeList.find(attr => attr.path === attribute.path);
    if (attrInConfig) attrInConfig.checked = false;

    $scope.config.selectAllAttributes = false;
    return;
  }

  const attrInConfig = attributeList.find(attr => attr.path === attribute.path);

  if (!attrInConfig) {
    console.warn("Attribute not found in config:", attribute.path);
    return;
  }

  selectedAttributes.push(attribute);
  attrInConfig.checked = true;

  $scope.config.selectAllAttributes = selectedAttributes.length === attributeList.length;
};



    $scope.displayAttributes = function (node) {
      $scope.config.selectAllAttributes = false;
      if (!node.children || node.children.length === 0) {

        if (node.type === "element") {
          $scope.config.template = "-- Any --";
          $scope.getChildrenFromDB(node).then(newNode => {
            processNode(newNode);
          });
        } else if (node.type === "template") {
          $scope.config.element_name = "*";
          $scope.config.template = node.title;
          $scope.doSearch($scope.config.element_name, $scope.config.attribute_name);
        }
      }  else {
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
          $scope.config.attributeList.push(child);
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

    ctrl.hasRenderableChildren = function (node) {
      if (!node || !Array.isArray(node.children) || !node.children.length) {
        return false;
      }
      return node.children.some(function (child) {
        return child && child.type !== 'attribute';
      });
    };

    ctrl.toggleExpand = function (node, $event) {
      if ($event) {
        $event.stopPropagation();
      }

      node.expanded = !node.expanded;

      if (node.expanded && (!node.children || !node.children.length || !ctrl.hasRenderableChildren(node))) {
        // Call function reference directly
        ctrl.getChildrenFromDb(node);
      }
    };
    
    ctrl.onNodeClick = function (node) {
      const index = ctrl.config.clickedNodes.indexOf(node.url);
      if (index > -1) {
        ctrl.config.clickedNodes.splice(index, 1);
      } else {
        ctrl.config.clickedNodes.push(node.url);
        ctrl.displayAttributes(node);
      }

      console.log("ctrl.config.clickedNodes: " + JSON.stringify(ctrl.config.clickedNodes));
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
      return ctrl.config.clickedNodes.includes(node.url);
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
          ng-if="ctrl.node.type !== 'attribute'"
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
        ng-repeat="child in ctrl.node.children track by (child.id || child.path || (child.title + '_' + $index))"
        ng-if="child.type !== 'attribute'"
      >
        <tree-node
          node="child"
          get-children-from-db="ctrl.getChildrenFromDb"
          display-attributes="ctrl.displayAttributes"
          config="ctrl.config"
          clicked-nodes="ctrl.config.clickedNodes"
        >
        </tree-node>
      </li>
    </ul>
  `
});
