let app = angular.module('piSystemTreeApp.module', []);

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
  '$q',
  'CodeMirrorSettingService',
  'TreeDataService',
  function ($scope, $stateParams, $q, CodeMirrorSettingService, TreeDataService) {

    $scope.paramDesc = {
      'parameterSetId': 'basic-auth',
      'mandatory': true
    };

    $scope.config.attributeList = $scope.config.attributeList || []; // la liste des attributs qui sont affichés sur le main panel à droite
    $scope.config.selectedAttributes = $scope.config.selectedAttributes || []; // la liste des attributs qui sont sélectionnés (checkbox cochée) parmi ceux affichés
    $scope.config.outputSelectedAttributes = $scope.config.outputSelectedAttributes || []; // la liste des attributs qui sont séléctionnés pour être dans l'output dataset
    $scope.config.searchMatchedElementPaths = $scope.config.searchMatchedElementPaths || []; // la liste pour highlighter les elements de la recherche
    $scope.config.lastSearchedElementName = $scope.config.lastSearchedElementName || ""; 
    $scope.config.pendingTabContextReset = $scope.config.pendingTabContextReset || false; // indique le changement de tab template/element 
    $scope.config.selectedTemplateNames = $scope.config.selectedTemplateNames || []; // la liste des templates sélectionnés (checkbox cochée) parmi ceux affichés
    $scope.config.selectAllWithoutTemplateAttributes = $scope.config.selectAllWithoutTemplateAttributes || false; // select all des attributs standalone
    $scope.config.selectAllTemplateAttributes = $scope.config.selectAllTemplateAttributes || false; // select all des attributs groupés par template

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
        let hasTreeData = Array.isArray($scope.config.treeData) && $scope.config.treeData.length > 0;
        let hasTemplateTreeData = Array.isArray($scope.config.templateTreeData) && $scope.config.templateTreeData.length > 0;
        $scope.authSectionVisible = !hasTreeData;
        $scope.showTreeData = hasTreeData;
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
      return $scope.hasPreset() && !!$scope.config.database_name && !!$scope.config.server_name;
    }
    $scope.explore = function () {
      let hasPreset = $scope.hasPreset();
      let hasServer = !!$scope.config.server_name;
      let hasDatabase = !!$scope.config.database_name;
      console.info("[LOGIN][UI] click", {
        hasPreset: hasPreset,
        hasServer: hasServer,
        hasDatabase: hasDatabase
      });

      if (!$scope.authConfigured()) {
        console.warn("[LOGIN][UI] blocked: missing required fields");
        return;
      }

      console.info("[LOGIN][UI] dispatching login API calls", {
        server_name: $scope.config.server_name,
        database_name: $scope.config.database_name
      });
      $scope.updateDatas().then(
        function () {
          $scope.showTreeData = true;
          $scope.authSectionVisible = false;
          console.info("[LOGIN][UI] success", {
            tree_count: Array.isArray($scope.config.treeData) ? $scope.config.treeData.length : 0,
            template_tree_count: Array.isArray($scope.config.templateTreeData) ? $scope.config.templateTreeData.length : 0
          });
        },
        function (error) {
          $scope.showTreeData = false;
          $scope.authSectionVisible = true;
          console.error("[LOGIN][UI] failed", error);
        }
      );
    };

    $scope.hasPreset = function () {
      return $scope.config.credentials && $scope.config.credentials.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
    }

    $scope.cleanTree = function () { // utile quand on change de serveur ou de db dans la config 
      $scope.config.treeData = [];
      $scope.config.clickedNodes = [];
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      $scope.config.outputSelectedAttributes = [];
      $scope.config.searchMatchedElementPaths = [];
      $scope.config.lastSearchedElementName = "";
      $scope.config.pendingTabContextReset = false;
      $scope.config.selectedTemplateNames = [];
      $scope.config.selectAllWithoutTemplateAttributes = false;
      $scope.config.selectAllTemplateAttributes = false;
    }

    $scope.resetDatasourceState = function () { // 
      $scope.server_name = [];
      $scope.database_name = [];
      $scope.config.server_name = null;
      $scope.config.database_name = null;
      $scope.config.templates = [];
      $scope.config.templateTreeData = [];
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.config.loadedDatabaseName = null;
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      $scope.config.outputSelectedAttributes = [];
      $scope.showTreeData = false;
      $scope.cleanTree();
    };

    $scope.onServerChanged = function () {
      $scope.config.database_name = null;
      $scope.config.templates = [];
      $scope.config.templateTreeData = [];
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.config.loadedDatabaseName = null;
      $scope.showTreeData = false;
      $scope.cleanTree();
      $scope.getDatabases();
    };

    $scope.onDatabaseChanged = function () {
      $scope.config.templates = [];
      $scope.config.templateTreeData = [];
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      $scope.config.loadedDatabaseName = null;
      $scope.showTreeData = false;
      $scope.cleanTree();
    };

    let presetWatchInitialized = false;
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

        let mode = newValues[0];
        let name = newValues[1];
        let oldMode = oldValues ? oldValues[0] : null;
        let oldName = oldValues ? oldValues[1] : null;

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
      if (!$scope.config.treeData || $scope.config.treeData.length === 0) {
        return $scope.callPythonDo({ method: "get_children_from_db", parent: $scope.config.database_name }).then(function (data) {
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
          return data;
        });
      }
      return $q.when({ choices: $scope.config.treeData || [] });
    };

    $scope.updateDatas = function () {
      $scope.cleanTree();
      return $q.all([
        $scope.initializeTree(),
        $scope.getTemplatesFromDB(),
        $scope.getCategoriesFromDB()
      ]).then(function (results) {
        $scope.config.loadedDatabaseName = $scope.config.database_name || null;
        return results;
      });
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
          markSearchResults(item.children, $scope.config.searchMatchedElementPaths || []);
          console.log(item);
          return item;
        });
    }


    $scope.getTemplatesFromDB = function () {
      return $scope.callPythonDo({ method: "get_templates_from_db" }).then(function (data) {
        $scope.config.templates = data.choices;
        TreeDataService.setTemplateTreeData(data.choices);
        $scope.config.templateTreeData = TreeDataService.getTemplateTreeData();
      });
    }

    function resetRightPanelForCurrentTabContext() {
      $scope.config.attribute_name = "";
      $scope.config.clickedNodes = [];
      $scope.config.attributeList = [];
      $scope.config.selectedAttributes = [];
      $scope.config.selectAllWithoutTemplateAttributes = false;
      $scope.config.selectAllTemplateAttributes = false;
      $scope.config.searchMatchedElementPaths = [];
      $scope.config.selectedTemplateNames = [];
      if ($scope.config.activeTab === "element") {
        $scope.config.template = "-- Any --";
      } else if ($scope.config.activeTab === "template") {
        $scope.config.element_name = "";
      }
    }

    function consumePendingTabContextReset() { // reset la main view après changement de tab + action sur le new tab 
      if (!$scope.config.pendingTabContextReset) {
        return;
      }
      resetRightPanelForCurrentTabContext();
      $scope.config.pendingTabContextReset = false;
    }

    $scope.setTab = function(tab) {
        const previousTab = $scope.config.activeTab;
        if (tab !== previousTab) {
          $scope.config.pendingTabContextReset = true;
        }
        $scope.config.activeTab = tab;
    };

    $scope.getCategoriesFromDB = function () {
      $scope.config.attribute_categories = [];
      $scope.config.element_categories = [];
      let attributeCategoriesPromise = $scope.callPythonDo({ method: "get_attribute_categories_from_db" }).then(function (data) {
        $scope.config.attribute_categories = data.choices;
        return data;
      });
      let elementCategoriesPromise = $scope.callPythonDo({ method: "get_element_categories_from_db" }).then(function (data) {
        $scope.config.element_categories = data.choices;
        return data;
      });
      return $q.all([attributeCategoriesPromise, elementCategoriesPromise]);
    }

    $scope.doSearch = function (element_name, attribute_name) {
      consumePendingTabContextReset();

      const hasElementFilter = !!(element_name && element_name.trim());
      const hadPreviousElementFilter = !!($scope.config.lastSearchedElementName && $scope.config.lastSearchedElementName.trim());

      // If user clears element filter after a scoped search, release previous click-based scope.
      if (!hasElementFilter && hadPreviousElementFilter) {
        $scope.config.clickedNodes = [];
      }

      const hasClickedNodes = Array.isArray($scope.config.clickedNodes) && $scope.config.clickedNodes.length > 0;
      const hasAttributeFilter = !!(attribute_name && attribute_name.trim());
      const isRestrictedAttributeSearch = hasClickedNodes && hasAttributeFilter && !hasElementFilter;
      const hasTemplateFilter = !!(
        $scope.config.template &&
        $scope.config.template !== "-- Any --"
      );
      const isTemplateScopedSearch =
        hasTemplateFilter &&
        ($scope.config.activeTab === "template");
      const shouldDisplaySearchAttributesDirectly =
        hasAttributeFilter || isTemplateScopedSearch;
      $scope.config.lastSearchedElementName = element_name || "";
      if ($scope.config.activeTab === "template") {
        $scope.config.selectedTemplateNames = getSelectedTemplateNamesFromClickedNodes();
      } else {
        $scope.config.selectedTemplateNames = [];
      }
      const hasSelectedTemplateNodes = (
        $scope.config.activeTab === "template" &&
        Array.isArray($scope.config.selectedTemplateNames) &&
        $scope.config.selectedTemplateNames.length > 0
      );
      const shouldShowTemplateSelectionAttributes = hasSelectedTemplateNodes;

      if (!isRestrictedAttributeSearch) {
        $scope.config.attributeList = [];
        $scope.config.selectedAttributes = [];
        // Right-side display is reset: both table-level select-all checkboxes must be cleared.
        $scope.config.selectAllWithoutTemplateAttributes = false;
        $scope.config.selectAllTemplateAttributes = false;
      }
      $scope.config.searchMatchedElementPaths = [];
      $scope.callPythonDo({ method: "do_search", element_name: element_name, attribute_name: attribute_name, root_tree: $scope.config.treeData }).then(
        function (data) {
          TreeDataService.setTreeData(data.choices);
          $scope.config.treeData = TreeDataService.getTreeData();
          const matchedAttributes = data.attributes || [];
          const matchedElementPaths = getMatchedElementPaths(matchedAttributes);
          $scope.config.searchMatchedElementPaths = matchedElementPaths;
          markSearchResults($scope.config.treeData, matchedElementPaths);
          if (
            isRestrictedAttributeSearch ||
            shouldDisplaySearchAttributesDirectly ||
            shouldShowTemplateSelectionAttributes
          ) {
            applySearchAttributesToList(matchedAttributes);
          }
        }
      );
    };

    function applySearchAttributesToList(attributes) {
      const preservedSelectedPathSet = new Set(getOutputSelectedAttributes().map(attr => attr.path));
      const seen = new Set();
      const deduped = [];

      attributes.forEach(attribute => {
        if (!attribute || !attribute.path || seen.has(attribute.path)) {
          return;
        }
        seen.add(attribute.path);
        const attrCopy = { ...attribute };
        attrCopy.checked = preservedSelectedPathSet.has(attrCopy.path);
        deduped.push(attrCopy);
      });

      $scope.config.attributeList = deduped;
      syncVisibleSelectionFromOutput();
    }

    function getMatchedElementPaths(attributes) {
      const matchedPathSet = new Set();
      attributes.forEach(attribute => {
        const fullPath = attribute && attribute.path;
        if (!fullPath || typeof fullPath !== "string") {
          return;
        }
        const elementPath = fullPath.includes("|") ? fullPath.split("|")[0] : fullPath;
        matchedPathSet.add(elementPath);
      });
      return Array.from(matchedPathSet);
    }


    function collectTemplateTitlesByClickedUrls(nodes, clickedUrlSet, outputSet) {
      if (!Array.isArray(nodes) || !clickedUrlSet || !outputSet) {
        return;
      }

      nodes.forEach(function (node) {
        if (!node) {
          return;
        }
        if (
          clickedUrlSet.has(node.url) &&
          node.type === "template" &&
          node.title &&
          node.title !== "-- Any --"
        ) {
          outputSet.add(node.title);
        }
        if (Array.isArray(node.children) && node.children.length > 0) {
          collectTemplateTitlesByClickedUrls(node.children, clickedUrlSet, outputSet);
        }
      });
    }

    function getSelectedTemplateNamesFromClickedNodes() {
      const clickedUrls = Array.isArray($scope.config.clickedNodes)
        ? $scope.config.clickedNodes
        : [];
      if (!clickedUrls.length) {
        return [];
      }

      const selectedTemplateNames = new Set();
      collectTemplateTitlesByClickedUrls(
        $scope.config.templateTreeData,
        new Set(clickedUrls),
        selectedTemplateNames
      );
      return Array.from(selectedTemplateNames);
    }

    function markSearchResults(nodes, matchedElementPaths) {
      if (!Array.isArray(nodes)) {
        return;
      }
      const matchedPathSet = new Set(matchedElementPaths || []);

      nodes.forEach(node => {
        node.searchHighlighted =
          node &&
          node.type !== "attribute" &&
          !!node.path &&
          matchedPathSet.has(node.path);

        if (Array.isArray(node.children) && node.children.length > 0) {
          markSearchResults(node.children, matchedElementPaths);
        }
      });
    }

    $scope.onSearchInputKeydown = function ($event) {
      if ($event && ($event.key === "Enter" || $event.keyCode === 13)) {
        $event.preventDefault();
        const targetId = $event.target && $event.target.id ? $event.target.id : "";
        if (targetId === "ReturnsName") {
          $scope.searchFromElement();
          return;
        }
        $scope.doSearch($scope.config.element_name, $scope.config.attribute_name);
      }
    };

    $scope.searchFromElement = function () {
      if (!$scope.config) {
        return;
      }

      // Left search always resets right-side filter/template search.
      $scope.config.clickedNodes = [];
      $scope.config.selectedTemplateNames = [];
      $scope.config.attribute_name = "";
      $scope.doSearch($scope.config.element_name, $scope.config.attribute_name);
    };

    function setAttributesChecked(attributes, isChecked) {
      if (!Array.isArray(attributes)) {
        return;
      }
      attributes.forEach(attribute => {
        if (!attribute || !attribute.path) {
          return;
        }
        attribute.checked = !!isChecked;
        upsertOutputSelectedAttribute(attribute, !!isChecked);
      });
      syncVisibleSelectionFromOutput();
    }

    $scope.toggleSelectAllWithoutTemplateAttributes = function () {
      setAttributesChecked($scope.getAttributesWithoutTemplate(), !!$scope.config.selectAllWithoutTemplateAttributes);
    };

    function getAllTemplatedAttributes() {
      const templateGroups = getGroupedAttributesByTemplate().templateGroups;
      const templatedAttributes = [];
      templateGroups.forEach(group => {
        if (!group || !Array.isArray(group.attributes)) {
          return;
        }
        templatedAttributes.push.apply(templatedAttributes, group.attributes);
      });
      return templatedAttributes;
    }

    $scope.toggleSelectAllTemplateAttributes = function () {
      setAttributesChecked(getAllTemplatedAttributes(), !!$scope.config.selectAllTemplateAttributes);
    };

    $scope.isTemplateGroupChecked = function (group) {
      if (!group || !Array.isArray(group.attributes) || !group.attributes.length) {
        return false;
      }
      return group.attributes.every(attribute => !!attribute.checked);
    };

    $scope.toggleTemplateGroupAttributes = function (group) {
      if (!group || !Array.isArray(group.attributes)) {
        return;
      }
      const shouldCheck = !$scope.isTemplateGroupChecked(group);
      setAttributesChecked(group.attributes, shouldCheck);
    };

    $scope.updateAttributeToOutput = function (attribute) {
  if (!$scope.config || !$scope.config.attributeList) return;

  const selectedAttributes = $scope.config.selectedAttributes;
  const attributeList = $scope.config.attributeList;

  const index = selectedAttributes.findIndex(attr => attr.path === attribute.path);

  if (index !== -1) {
    selectedAttributes.splice(index, 1);

    const attrInConfig = attributeList.find(attr => attr.path === attribute.path);
    if (attrInConfig) attrInConfig.checked = false;
    upsertOutputSelectedAttribute(attribute, false);
    syncVisibleSelectionFromOutput();
    return;
  }

  const attrInConfig = attributeList.find(attr => attr.path === attribute.path);

  if (!attrInConfig) {
    console.warn("Attribute not found in config:", attribute.path);
    return;
  }

  selectedAttributes.push(attribute);
  attrInConfig.checked = true;
  upsertOutputSelectedAttribute(attribute, true);
  syncVisibleSelectionFromOutput();
};



    function getNodeAttributePaths(node) {
      if (!node || !Array.isArray(node.children)) {
        return [];
      }
      return node.children
        .filter(child => child.type === "attribute" && child.path)
        .map(child => child.path);
    }

    function removeNodeAttributes(node) {
      const attributePaths = getNodeAttributePaths(node);
      if (!attributePaths.length) {
        return;
      }

      $scope.config.attributeList = ($scope.config.attributeList || []).filter(
        attr => !attributePaths.includes(attr.path)
      );
      $scope.config.selectedAttributes = ($scope.config.selectedAttributes || []).filter(
        attr => !attributePaths.includes(attr.path)
      );
      syncVisibleSelectionFromOutput();
    }

    function hasAttributeChildren(node) {
      return Array.isArray(node && node.children) &&
        node.children.some(child => child.type === "attribute");
    }

    $scope.displayAttributes = function (node, shouldAdd = true) {
      $scope.config.selectAllWithoutTemplateAttributes = false;
      $scope.config.selectAllTemplateAttributes = false;
      if (!shouldAdd) {
        removeNodeAttributes(node);
        return;
      }

      const shouldLoadChildrenFromDb =
        node.type === "element" &&
        (
          !Array.isArray(node.children) ||
          node.children.length === 0 ||
          !hasAttributeChildren(node)
        );

      if (shouldLoadChildrenFromDb) {
        $scope.config.template = "-- Any --";
        $scope.getChildrenFromDB(node).then(newNode => {
          processNode(newNode);
        });
      } else if (node.type === "template") {
        const selectedTemplateNames = getSelectedTemplateNamesFromClickedNodes();
        if (!selectedTemplateNames.length) {
          $scope.config.template = "-- Any --";
          $scope.config.attributeList = [];
          $scope.config.selectedAttributes = [];
          $scope.config.selectAllWithoutTemplateAttributes = false;
          $scope.config.selectAllTemplateAttributes = false;
          $scope.config.searchMatchedElementPaths = [];
          return;
        }

        // Keep previous single-template behavior in config when only one is selected.
        // For multi-select, backend will use selectedTemplateNames.
        $scope.config.template = selectedTemplateNames.length === 1
          ? selectedTemplateNames[0]
          : "-- Any --";
        $scope.config.element_name = "*";
        $scope.doSearch($scope.config.element_name, $scope.config.attribute_name);
      } else {
        processNode(node);
      }
    }

    function processNode(node) {
      const selectedPaths = new Set(getOutputSelectedAttributes().map(attr => attr.path));
      const hasAttributeFilter = !!($scope.config.attribute_name && $scope.config.attribute_name.trim());
      const shouldRestrictDisplayedAttributes = hasAttributeFilter;
      const parentTemplateName = node && node.template_name ? node.template_name : null;

      node.children.forEach(child => {
        if (child.type === "attribute") {
          if (!child.parent_template_name && parentTemplateName) {
            child.parent_template_name = parentTemplateName;
          }
          if (shouldRestrictDisplayedAttributes && !attributeMatchesCurrentSearch(child)) {
            return;
          }
          const isAlreadyPresent = $scope.config.attributeList.some(attr => attr.path === child.path);
          if (!isAlreadyPresent) {
            child.checked = selectedPaths.has(child.path);
            $scope.config.attributeList.push(child);
          }
        }
      });

      syncVisibleSelectionFromOutput();
    }

    function getAttributeTemplateName(attribute) {
      if (!attribute) {
        return "";
      }
      const templateName = attribute.parent_template_name || attribute.template_name || "";
      return typeof templateName === "string" ? templateName.trim() : "";
    }

    function groupAttributesByTemplate(attributes) {
      const attributesByTemplate = new Map();
      const attributesWithoutTemplate = [];

      attributes.forEach(attribute => {
        if (!attribute || !attribute.path) {
          return;
        }
        const templateName = getAttributeTemplateName(attribute);
        if (!templateName) {
          attributesWithoutTemplate.push(attribute);
          return;
        }
        if (!attributesByTemplate.has(templateName)) {
          attributesByTemplate.set(templateName, []);
        }
        attributesByTemplate.get(templateName).push(attribute);
      });

      const templateGroups = [];
      attributesByTemplate.forEach((templateAttributes, templateName) => {
        templateGroups.push({
          groupKey: "template:" + templateName,
          templateName: templateName,
          attributes: templateAttributes
        });
      });

      return {
        attributesWithoutTemplate: attributesWithoutTemplate,
        templateGroups: templateGroups
      };
    }

    function buildTemplateGroupingKey(attributes) {
      return attributes
        .filter(attribute => attribute && attribute.path)
        .map(attribute => attribute.path + "::" + getAttributeTemplateName(attribute))
        .join("||");
    }

    let templateGroupingKey = null;
    let templateGroupingSource = null;
    let groupedAttributesByTemplate = {
      attributesWithoutTemplate: [],
      templateGroups: []
    };

    function getGroupedAttributesByTemplate() {
      const attributes = Array.isArray($scope.config.attributeList) ? $scope.config.attributeList : [];
      const nextTemplateGroupingKey = buildTemplateGroupingKey(attributes);
      if (attributes === templateGroupingSource && nextTemplateGroupingKey === templateGroupingKey) {
        return groupedAttributesByTemplate;
      }
      templateGroupingSource = attributes;
      templateGroupingKey = nextTemplateGroupingKey;
      groupedAttributesByTemplate = groupAttributesByTemplate(attributes);
      return groupedAttributesByTemplate;
    }

    $scope.getAttributesWithoutTemplate = function () {
      return getGroupedAttributesByTemplate().attributesWithoutTemplate;
    };

    $scope.getTemplateGroups = function () {
      return getGroupedAttributesByTemplate().templateGroups;
    };

    function attributeMatchesCurrentSearch(attribute) {
      const rawFilter = ($scope.config.attribute_name || "").trim();
      if (!rawFilter) {
        return true;
      }

      const attributeTitle = (attribute && attribute.title ? attribute.title : "").toLowerCase();
      const filter = rawFilter.toLowerCase();

      if (filter.includes("*")) {
        const regexPattern = "^" + escapeRegex(filter).replace(/\\\*/g, ".*") + "$";
        return new RegExp(regexPattern).test(attributeTitle);
      }

      return attributeTitle.includes(filter);
    }

    function escapeRegex(input) {
      return input.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function getOutputSelectedAttributes() {
      if (!Array.isArray($scope.config.outputSelectedAttributes)) {
        $scope.config.outputSelectedAttributes = [];
      }
      return $scope.config.outputSelectedAttributes;
    }

    function upsertOutputSelectedAttribute(attribute, isChecked) {
      if (!attribute || !attribute.path) {
        return;
      }

      const outputSelectedAttributes = getOutputSelectedAttributes();
      const index = outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);

      if (isChecked) {
        const attributeToStore = { ...attribute, checked: true };
        if (index === -1) {
          outputSelectedAttributes.push(attributeToStore);
        } else {
          outputSelectedAttributes[index] = attributeToStore;
        }
      } else if (index !== -1) {
        outputSelectedAttributes.splice(index, 1);
      }
    }

    function syncVisibleSelectionFromOutput() {
      const outputSelectedPathSet = new Set(getOutputSelectedAttributes().map(attr => attr.path));
      $scope.config.attributeList.forEach(attr => {
        attr.checked = outputSelectedPathSet.has(attr.path);
      });
      $scope.config.selectedAttributes = $scope.config.attributeList.filter(attr => attr.checked);
      const attributesWithoutTemplate = getGroupedAttributesByTemplate().attributesWithoutTemplate;
      $scope.config.selectAllWithoutTemplateAttributes =
        attributesWithoutTemplate.length > 0 &&
        attributesWithoutTemplate.every(attribute => !!attribute.checked);
      const templatedAttributes = getAllTemplatedAttributes();
      $scope.config.selectAllTemplateAttributes =
        templatedAttributes.length > 0 &&
        templatedAttributes.every(attribute => !!attribute.checked);
    }


  }]);



app.component('treeNode', {
  bindings: {
    node: '=',
    getChildrenFromDb: '<',
    displayAttributes: '<',
    config: '<',
  },

  controllerAs: 'ctrl',

  controller: function () {
    const ctrl = this;

    function consumePendingTabContextReset() {
      if (!ctrl.config || !ctrl.config.pendingTabContextReset) {
        return;
      }

      ctrl.config.attribute_name = "";
      ctrl.config.clickedNodes = [];
      ctrl.config.attributeList = [];
      ctrl.config.selectedAttributes = [];
      ctrl.config.selectAllWithoutTemplateAttributes = false;
      ctrl.config.selectAllTemplateAttributes = false;
      ctrl.config.searchMatchedElementPaths = [];

      if (ctrl.config.activeTab === "element") {
        ctrl.config.template = "-- Any --";
      } else if (ctrl.config.activeTab === "template") {
        ctrl.config.element_name = "";
      }

      ctrl.config.pendingTabContextReset = false; 
    }

    function findNodeByUrl(nodes, targetUrl) {
      if (!Array.isArray(nodes) || !targetUrl) {
        return null;
      }

      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];
        if (!node) {
          continue;
        }
        if (node.url === targetUrl) {
          return node;
        }
        const childMatch = findNodeByUrl(node.children, targetUrl);
        if (childMatch) {
          return childMatch;
        }
      }

      return null;
    }

    function rebuildAttributesFromClickedNodes() {
      const clickedUrls = Array.isArray(ctrl.config && ctrl.config.clickedNodes)
        ? ctrl.config.clickedNodes
        : [];

      ctrl.config.attributeList = [];
      ctrl.config.selectedAttributes = [];
      ctrl.config.selectAllWithoutTemplateAttributes = false;
      ctrl.config.selectAllTemplateAttributes = false;

      if (!clickedUrls.length) {
        return;
      }

      clickedUrls.forEach(function (url) {
        const node =
          findNodeByUrl(ctrl.config.treeData, url) ||
          findNodeByUrl(ctrl.config.templateTreeData, url);
        if (node) {
          ctrl.displayAttributes(node, true);
        }
      });
    }

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
      consumePendingTabContextReset();

      const hasActiveAttributeSearch = !!(
        ctrl.config &&
        ctrl.config.attribute_name &&
        ctrl.config.attribute_name.trim()
      );

      if (ctrl.config) {
        // Keep right-side attribute search when active so multi-node clicks can
        // enrich results with the same filter (ex: "Load" on California + Fresno).
        if (!hasActiveAttributeSearch) {
          ctrl.config.attribute_name = "";
        }
        if (node && node.type === "element") {
          ctrl.config.template = "-- Any --";
        }
      }

      const index = ctrl.config.clickedNodes.indexOf(node.url);
      if (index > -1) {
        ctrl.config.clickedNodes.splice(index, 1);
      } else {
        ctrl.config.clickedNodes.push(node.url);
      }

      if (node && node.type === "template") {
        // Template clicks should always rebuild right-side content from the full template selection.
        ctrl.displayAttributes(node, true);
        console.log("ctrl.config.clickedNodes: " + JSON.stringify(ctrl.config.clickedNodes));
        return;
      }

      if (hasActiveAttributeSearch) {
        rebuildAttributesFromClickedNodes();
      } else if (index > -1) {
        ctrl.displayAttributes(node, false);
      } else {
        ctrl.displayAttributes(node);
      }

      console.log("ctrl.config.clickedNodes: " + JSON.stringify(ctrl.config.clickedNodes));
    };

    ctrl.isNodeClicked = function (node) {
      return ctrl.config.clickedNodes.includes(node.url);
    };

    ctrl.isSearchResult = function (node) {
      return !!node.searchHighlighted;
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
            'tree-node__label--search-result':
              ctrl.isSearchResult(ctrl.node),
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
