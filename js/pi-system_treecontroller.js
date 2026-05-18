const app = angular.module('piSystemTreeApp.module', []);

const aggregateDataTypeFields = Object.freeze({
    data_type: {
        label: 'Data type',
        type: 'select',
        defaultValue: 'RecordedData',
        options: [
            { value: 'InterpolatedData', label: 'Interpolated' },
            { value: 'PlotData', label: 'Plot' },
            { value: 'RecordedData', label: 'Recorded' },
            { value: 'SummaryData', label: 'Summary' },
            { value: 'Value', label: 'Value' },
            { value: 'EndValue', label: 'End value' },
        ]
    },
    aggregates: {
        interval: {
            label: 'Interval',
            type: 'text',
            defaultValue: '',
            isVisible: function(attribute) {
                return attribute.data_type === 'InterpolatedData';
            },
        },
        sync_time: {
            label: 'Sync time',
            type: 'text',
            defaultValue: '',
            isVisible: function(attribute) {
                return attribute.data_type === 'InterpolatedData';
            },
        },
        summary_type: {
            label: 'Summary type',
            type: 'multiselect',
            defaultValue: [],
            isVisible: function(attribute) {
                return attribute.data_type === 'SummaryData';
            },
            options: [
                { value: 'Total', label: 'Total' },
                { value: 'Average', label: 'Average' },
                { value: 'Minimum', label: 'Minimum' },
                { value: 'Maximum', label: 'Maximum' },
                { value: 'Range', label: 'Range' },
                { value: 'StdDev', label: 'Standard deviation' },
                { value: 'PopulationStdDev', label: 'Population standard deviation' },
                { value: 'Count', label: 'Count' },
                { value: 'PercentGood', label: 'Percent good' },
                { value: 'TotalWithUOM', label: 'Total with UOM' },
                { value: 'All', label: 'All' },
                { value: 'AllForNonNumeric', label: 'All for non numeric' },
            ]
        },
        boundary_type: {
            label: 'Boundary type',
            type: 'select',
            defaultValue: 'Inside',
            isVisible: function(attribute) {
                return attribute.data_type === 'InterpolatedData';
            },
            options: [
                { value: 'Inside', label: 'Inside' },
                { value: 'Outside', label: 'Outside' },
            ]
        },
        record_boundary_type: {
            label: 'Boundary type',
            type: 'select',
            defaultValue: 'Inside',
            isVisible: function(attribute) {
                return attribute.data_type === 'RecordedData';
            },
            options: [
                { value: 'Inside', label: 'Inside' },
                { value: 'Interpolated', label: 'Interpolated' },
                { value: 'Outside', label: 'Outside' },
            ]
        },
        summary_duration: {
            label: 'Summary duration',
            type: 'text',
            defaultValue: '',
            isVisible: function(attribute) {
                return attribute.data_type === 'SummaryData';
            },
        },
    }
});

//TODO: divide at least into a tree component + a results/right panel component + welcome component
const CheckboxStatus = Object.freeze({
    CHECKED: 'CHECKED',
    UNCHECKED: 'UNCHECKED',
    PARTIAL_CHECK: 'PARTIAL_CHECK',
});

app.service('TreeDataService', function() {
    // This will store the shared tree data
    this.treeData = [];
    this.templateTreeData = [];

    // Optional: helper methods
    this.setTreeData = function(data) {
        this.treeData = data;
    };

    this.getTreeData = function() {
        return this.treeData;
    };

    this.setTemplateTreeData = function(data) {
        this.templateTreeData = data;
    };

    this.getTemplateTreeData = function() {
        return this.templateTreeData;
    };
});

app.controller('AfExplorerFormCtrl', [
    '$scope',
    '$stateParams',
    '$q',
    'TreeDataService',
    function($scope, $stateParams, $q, TreeDataService) {

        $scope.paramDesc = {
            'parameterSetId': 'basic-auth',
            'mandatory': true
        };

        $scope.config.attributeList = $scope.config.attributeList || []; // la liste des attributs qui sont affichés sur le main panel à droite
        $scope.config.outputSelectedAttributes = $scope.config.outputSelectedAttributes || []; // la liste des attributs qui sont séléctionnés pour être dans l'output dataset
        $scope.config.searchMatchedElementPaths = $scope.config.searchMatchedElementPaths || []; // la liste pour highlighter les elements de la recherche
        $scope.config.selectedTemplateNames = $scope.config.selectedTemplateNames || []; // la liste des templates sélectionnés (checkbox cochée) parmi ceux affichés
        $scope.config.attributeSearch =  $scope.config.attributeSearch || "";
        $scope.config.displayPath = $scope.config.displayPath || false;
        $scope.config.elementsByTemplate = $scope.config.elementsByTemplate || {};
        $scope.config.searchInProgress = $scope.config.searchInProgress || false;

        // TODO: get categories from backend for attributes
        // $scope.config.attributeCategoryFilter = $scope.config.attributeCategoryFilter || ""

        $scope.aggregateDataTypeFields = aggregateDataTypeFields;
        $scope.attributeGroupSections = [
            {
                type: 'element',
                key: 'attributesWithoutTemplate',
                title: 'Elements',
                emptyMessage: 'No attributes without template matched your selection',
                shouldDisplay: () => $scope.config.activeTab === "element"
            },
            {
                type: 'template',
                key: 'attributesGroupedByTemplate',
                title: 'Templates',
                emptyMessage: 'No templated attributes matched your selection',
                shouldDisplay: () => true
            }
        ];

        $scope.onAdvancedToggle = function() {
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

        $scope.init = function() {
            $scope.config.show_advanced_parameters = $scope.config.show_advanced_parameters || false;
            $scope.config.activeTab = $scope.config.activeTab || 'element';
            DataikuAPI.plugins.listAccessiblePresets('pi-system', $stateParams.projectKey, 'basic-auth').success(function(data) {
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
                data.presets.forEach(function(p) {
                    $scope.accessiblePresets.push({ name: "PRESET " + p.name, label: p.name, usable: p.usable, description: p.description });
                });
                // TODO: why injection
                $scope.accessibleParameterSetDescriptions = $scope.accessiblePresets.map(function(p) {
                    return p.description || '<em>No description</em>';
                });
            }).error(setErrorInScope.bind($scope.errorScope));
            if ($scope.authConfigured() === true) {
                const hasTreeData = Array.isArray($scope.config.treeData) && $scope.config.treeData.length > 0;
                $scope.authSectionVisible = !hasTreeData;
                $scope.showTreeData = hasTreeData;
            }
            $scope.config.template = $scope.config.template || "-- Any --";
            $scope.onAdvancedToggle();
        };

        $scope.getServers = function() {
            $scope.callPythonDo({ parameterName: "server_name" }).then(function(data) {
                $scope.server_name = data.choices;
            });
        };
        $scope.getDatabases = function() {
            $scope.callPythonDo({ parameterName: "database_name" }).then(function(data) {
                $scope.database_name = data.choices;
            });
        };

        $scope.authSectionVisible = $scope.authSectionVisible || true;

        $scope.toggleAuthSection = function() {
            $scope.authSectionVisible = !$scope.authSectionVisible;
        };

        $scope.authConfigured = function() {
            return $scope.hasPreset() && !!$scope.config.database_name && !!$scope.config.server_name;
        }
        $scope.explore = function() {
            const hasPreset = $scope.hasPreset();
            const hasServer = !!$scope.config.server_name;
            const hasDatabase = !!$scope.config.database_name;
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
                function() {
                    $scope.showTreeData = true;
                    $scope.authSectionVisible = false;
                    console.info("[LOGIN][UI] success", {
                        tree_count: Array.isArray($scope.config.treeData) ? $scope.config.treeData.length : 0,
                        template_tree_count: Array.isArray($scope.config.templateTreeData) ? $scope.config.templateTreeData.length : 0
                    });
                },
                function(error) {
                    $scope.showTreeData = false;
                    $scope.authSectionVisible = true;
                    console.error("[LOGIN][UI] failed", error);
                }
            );
        };

        $scope.hasPreset = function() {
            return $scope.config.credentials?.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
        }

        $scope.cleanTree = function() { // utile quand on change de serveur ou de db dans la config
            $scope.config.treeData = [];
            $scope.config.clickedNodes = [];
            $scope.config.attributeList = [];
            $scope.config.outputSelectedAttributes = [];
            $scope.config.searchMatchedElementPaths = [];
            $scope.config.selectedTemplateNames = [];
        }

        $scope.resetDatasourceState = function() { //
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
            $scope.config.outputSelectedAttributes = [];
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        $scope.onServerChanged = function() {
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

        $scope.onDatabaseChanged = function() {
            $scope.config.templates = [];
            $scope.config.templateTreeData = [];
            $scope.config.attribute_categories = [];
            $scope.config.element_categories = [];
            $scope.config.loadedDatabaseName = null;
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        let presetWatchInitialized = false;
        // TODO: move this to an ng-change
        $scope.$watchGroup(
            [
                function() {
                    return $scope.config?.credentials?.mode ?? null;
                },
                function() {
                    return $scope.config?.credentials?.name ?? null;
                }
            ],
            function(newValues, oldValues) {
                if (!presetWatchInitialized) {
                    presetWatchInitialized = true;
                    return;
                }

                const mode = newValues[0];
                const name = newValues[1];
                const oldMode = oldValues ? oldValues[0] : null;
                const oldName = oldValues ? oldValues[1] : null;

                if (mode === oldMode && name === oldName) {
                    return;
                }

                $scope.resetDatasourceState();

                if ($scope.hasPreset()) {
                    $scope.getServers();
                }
            }
        );

        $scope.initializeTree = function() {
            if (!$scope.config.treeData || $scope.config.treeData.length === 0) {
                return $scope.callPythonDo({ method: "get_children_from_db", parent: $scope.config.database_name }).then(function(data) {
                    TreeDataService.setTreeData(data.choices);
                    $scope.config.treeData = TreeDataService.getTreeData();
                    return data;
                });
            }
            return $q.when({ choices: $scope.config.treeData || [] });
        };

        $scope.updateDatas = function() {
            $scope.cleanTree();
            return $q.all([
                $scope.initializeTree(),
                $scope.getTemplatesFromDB(),
                $scope.getCategoriesFromDB()
            ]).then(function(results) {
                $scope.config.loadedDatabaseName = $scope.config.database_name || null;
                return results;
            });
        }

        $scope.getChildrenFromDB = function(item) {
            if (item.type === "template") {
                return getAttributesForTemplate(item);
            }
            console.log("ALX:gcfd:" + JSON.stringify(item));
            return $scope.callPythonDo({ method: "get_children_from_db", parent: item })
                .then(function(data) {
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


        $scope.getTemplatesFromDB = function() {
            return $scope.callPythonDo({ method: "get_templates_from_db" }).then(function(data) {
                $scope.config.templates = data.choices;
                TreeDataService.setTemplateTreeData(data.choices);
                $scope.config.templateTreeData = TreeDataService.getTemplateTreeData();
            });
        }

        function resetRightPanelForCurrentTabContext() {
            $scope.config.clickedNodes = [];
            $scope.config.attributeList = [];
            $scope.config.searchMatchedElementPaths = [];
            $scope.config.selectedTemplateNames = [];
            $scope.config.attributeSearch = "";
            if ($scope.config.activeTab === "element") {
                $scope.config.template = "-- Any --";
            } else if ($scope.config.activeTab === "template") {
                $scope.config.element_name = "";
            }
        }

        $scope.setTab = function(tab) {
            const previousTab = $scope.config.activeTab;
            if (tab !== previousTab) {
                resetRightPanelForCurrentTabContext();
            }
            $scope.config.activeTab = tab;
        };

        $scope.getCategoriesFromDB = function() {
            $scope.config.attribute_categories = [];
            $scope.config.element_categories = [];
            const attributeCategoriesPromise = $scope.callPythonDo({ method: "get_attribute_categories_from_db" }).then(function(data) {
                $scope.config.attribute_categories = data.choices;
                return data;
            });
            const elementCategoriesPromise = $scope.callPythonDo({ method: "get_element_categories_from_db" }).then(function(data) {
                $scope.config.element_categories = data.choices;
                return data;
            });
            return $q.all([attributeCategoriesPromise, elementCategoriesPromise]);
        }

        $scope.doSearch = function(element_name) {
            $scope.config.searchInProgress = true;
            $scope.config.searchMatchedElementPaths = [];
            $scope.callPythonDo({ method: "do_search", element_name: element_name, root_tree: $scope.config.treeData }).then(
                function(data) {
                    TreeDataService.setTreeData(data.choices);
                    $scope.config.treeData = TreeDataService.getTreeData();
                    const matchedAttributes = data.attributes || [];
                    const matchedElementPaths = getMatchedElementPaths(matchedAttributes);
                    $scope.config.searchMatchedElementPaths = matchedElementPaths;
                    markSearchResults($scope.config.treeData, matchedElementPaths);
                }
            );
        };

        function clearSearchHighlights(nodes) {
            nodes.forEach(node => {
                node.searchHighlighted = false;
                if (node?.children?.length > 0) {
                    clearSearchHighlights(node.children);
                }
            });
        }

        function getAttributesForTemplate(node) {
            return $scope.callPythonDo({ method: "get_attribute_for_template", template_name: node.title}).then(
                function(data) {
                    node.children = data.attributes;
                    node.children.forEach(child => {
                        child.expanded = false;
                    });
                    return node;
                }
            );
        }

        $scope.isTemplateAssociatedElementSelected = function(element) {
            return $scope.config.clickedNodes.includes(element.url);
        }

        $scope.getElementsForTemplate = function (templateName) {
            return $scope.callPythonDo({ method: "get_elements_for_template", template_name: templateName}).then(
                function(data) {
                    $scope.config.elementsByTemplate[templateName] = data.elements;
                }
            );
        }

        function fullRefreshSelectedElementsByTemplate() {
            Object.keys($scope.selectedElementsByTemplate).forEach(templateName => {
                if (!$scope.config.elementsByTemplate[templateName]) {
                    return;
                }
                refreshSelectedElementsByTemplate(templateName);
            });
        }

        function refreshSelectedElementsByTemplate(templateName) {
            $scope.selectedElementsByTemplate[templateName] = $scope.config.elementsByTemplate[templateName].filter(element => {
                    return $scope.config.clickedNodes.includes(element.url);
                }
            ).map(element => element.url);
            $scope.selectedElementsByTemplateUI[templateName] = $scope.selectedElementsByTemplate[templateName]
        }

        $scope.selectedElementsByTemplateUI = {};
        $scope.selectedElementsByTemplate = {};

        $scope.setupElementsDropdown = function($element, templateName) {
            let initialized = false;
            const dropdown = $element.next();

           if (!initialized && $scope.config.elementsByTemplate[templateName]?.length > 0) {
               refreshSelectedElementsByTemplate(templateName);
               initialized = true;
           }

            dropdown.on('click', function() {
                // console.log("triggered click")
                if (initialized) {
                    return;
                }

                $scope.$applyAsync(() => {
                    $scope.getElementsForTemplate(templateName).then(() => {
                        refreshSelectedElementsByTemplate(templateName);
                        initialized = true;
                        $scope.$broadcast('selectPickerRefresh');
                    }
                    )
                });
            });


            $element.on('change', function() {

                if (!initialized) {
                    return;
                }

                $scope.$applyAsync(() => {
                    const options = $scope.config.elementsByTemplate[templateName];
                    const previouslySelected = new Set($scope.selectedElementsByTemplate[templateName]);
                    const currentlySelected = new Set($scope.selectedElementsByTemplateUI[templateName]);

                    options.forEach(element => {
                        const elementKey = String(element.url);
                        const wasSelected = previouslySelected.has(elementKey);
                        const isSelected = currentlySelected.has(elementKey);

                        if (!wasSelected && isSelected) {
                            $scope.onNodeClick(element);
                        } else if (wasSelected && !isSelected) {
                            $scope.onNodeClick(element);
                        }
                    });

                    $scope.selectedElementsByTemplate = angular.copy($scope.selectedElementsByTemplateUI);
                });
            });
        }

        function getMatchedElementPaths(attributes) {
            const matchedPathSet = new Set();
            attributes.forEach(attribute => {
                const fullPath = attribute?.path;
                if (!fullPath || typeof fullPath !== "string") {
                    return;
                }
                const elementPath = fullPath.includes("|") ? fullPath.split("|")[0] : fullPath;
                matchedPathSet.add(elementPath);
            });
            return Array.from(matchedPathSet);
        }

        $scope.onNodeClick = function(node) {
            console.log("clicked on ", node)

            // Keep right-side attribute search when active so multi-node clicks can
            // enrich results with the same filter (ex: "Load" on California + Fresno).
            // TODO: understand why we need a reset if the attribute search is empty
            if (node?.type === "element") {
                // TODO: factorize this reset
                $scope.config.template = "-- Any --";
            }

            const indexClickedNode = $scope.config.clickedNodes.indexOf(node.url);
            const nodeAlreadySelected = indexClickedNode > -1;
            // If the node is already clicked, remove it from clicked nodes - else add it
            if (nodeAlreadySelected) {
                console.log("node already selected")
                $scope.config.clickedNodes.splice(indexClickedNode, 1);
            } else {
                console.log("node not already selected")
                $scope.config.clickedNodes.push(node.url);
            }

            // TODO: understand why this is mutually exclusive
            $scope.toggleDisplayAttributes(node, !nodeAlreadySelected);

            fullRefreshSelectedElementsByTemplate();
            console.log("clickedNodes: " + JSON.stringify($scope.config.clickedNodes));
        };

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

        // TODO understand why both
        $scope.onSearchInputKeydown = function($event) {
            if ($event && ($event.key === "Enter" || $event.keyCode === 13)) {
                $event.preventDefault();
                // const targetId = $event.target?.id || "";
                // // TODO: understand
                // if (targetId === "ReturnsName") {
                //     $scope.searchFromElement();
                //     return;
                // }
                $scope.searchFromElement();
            }
        };

        $scope.searchFromElement = function() {
            $scope.doSearch($scope.config.element_name);
        };

        $scope.clearSearch = function() {
            $scope.config.searchInProgress = false;
            $scope.config.element_name = "";
            $scope.config.searchMatchedElementPaths = [];
            clearSearchHighlights($scope.config.treeData);
        };

        $scope.toggleSelectAllGroupedAttributes = function(groupedAttributes) {
            const shouldRemove = groupedAttributes.checked === CheckboxStatus.CHECKED;
            groupedAttributes.groups.forEach((group) => {
                if (group.isDisplayed) {
                    return;
                }
                group.attributes.forEach((aggregatedAttribute) => {
                    if (!aggregatedAttribute.isDisplayed) {
                        return;
                    }
                    aggregatedAttribute.attributes.forEach((underlyingAttribute) => {
                        if (shouldRemove) {
                            $scope.removeAttributeFromSelection(underlyingAttribute);
                            return;
                        }
                        $scope.addAttributeToSelection(underlyingAttribute);
                    });
                });
            });
        };

        $scope.checkAttribute = function(attributeList) {
            const shouldRemove = attributeList.checked === CheckboxStatus.CHECKED;
            attributeList.attributes.forEach((attribute) => {
                    if (shouldRemove) {
                        $scope.removeAttributeFromSelection(attribute);
                        return;
                    }
                    $scope.addAttributeToSelection(attribute);
                }
            )
        };

        $scope.toggleGroupedAttributes = function(group) {
            const shouldRemove = group.checked === CheckboxStatus.CHECKED;
            group.attributes.forEach((aggregatedAttribute) => {
                    if (!aggregatedAttribute.isDisplayed) {
                        return;
                    }
                    aggregatedAttribute.attributes.forEach((underlyingAttribute) => {
                        if (shouldRemove) {
                            $scope.removeAttributeFromSelection(underlyingAttribute);
                            return;
                        }
                        $scope.addAttributeToSelection(underlyingAttribute);
                    });
                }
            )
        };

        // TODO: mark as loaded elements and replace this logic
        function hasAttributeChildren(node) {
            if (!Array.isArray(node.children) || node.children.length === 0) {
                return false
            }
            return node.children.some(child => child.type === "attribute");
        }

        function getChildren(node) {
            if (hasAttributeChildren(node)) {
                return Promise.resolve(node);
            }
            return $scope.getChildrenFromDB(node);
        }

        function stopDisplayingAttributes(node) {
            // It is for now possible to stop displaying an element that was not loaded because of weak links
            // patching it by loading the element before stopping to display it
            // TODO: replace by weak link single loading logic
            getChildren(node).then( node => {
                const nodeAttributeChildrenPaths = node.children.filter(child => child.type === "attribute" && child.path)
                    .map(child => child.path)
                    if (!nodeAttributeChildrenPaths.length) {
                        return;
                    }

                    $scope.config.attributeList = $scope.config.attributeList.filter(
                        attr => !nodeAttributeChildrenPaths.includes(attr.path)
                    );
            });
        }

        $scope.toggleDisplayAttributes = function(node, add = true) {
            if (!add) {
               stopDisplayingAttributes(node);
               return;
            }
            if (!hasAttributeChildren(node)) {
                $scope.getChildrenFromDB(node).then(newNode => {
                    processNode(newNode);
                });
                return;
            }
            processNode(node);
        }

        // Merge frontend data and saved output with loaded attributes
        function enrichAttribute(attribute, parentNode) {
            // TODO: check this makes sense, since selectedOutput is persisted and so newly loaded attributes should not be found in it
            const selectedAttribute = $scope.config.outputSelectedAttributes.find(attr => attr.path === attribute.path);
            attribute.checked = !!(selectedAttribute);
            if (parentNode.type === "element") {
                attribute.parent_element = parentNode?.title;
            } else if (parentNode.type === "template") {
                attribute.template_name = parentNode?.title;
            }
            attribute.data_type = selectedAttribute?.data_type ? selectedAttribute.data_type : $scope.aggregateDataTypeFields.data_type.defaultValue;
            Object.entries($scope.aggregateDataTypeFields.aggregates).forEach(([aggregateName, aggregate]) => {
                if ((selectedAttribute?.[aggregateName] === undefined || selectedAttribute?.[aggregateName] === null) && aggregate.isVisible(attribute)) {
                    attribute[aggregateName] = aggregate.defaultValue;
                } else if (selectedAttribute?.[aggregateName] !== null && selectedAttribute?.[aggregateName] !== undefined) {
                    attribute[aggregateName] = selectedAttribute?.[aggregateName];
                } else {
                    attribute[aggregateName] = null;
                }
            });
            return attribute;
        }

        function processNode(node) {
            const parentTemplateName = node?.template_name;

            node.children.forEach(child => {
                if (child.type === "attribute") {
                    if (!child.parent_template_name && parentTemplateName) {
                        child.parent_template_name = parentTemplateName;
                    }
                    const isAlreadyPresent = $scope.config.attributeList.some(attr => attr.path === child.path);
                    if (!isAlreadyPresent) {
                        $scope.config.attributeList.push(enrichAttribute(child, node));
                    }
                }
            });
        }

        function getAggregateNames() {
            return Object.keys($scope.aggregateDataTypeFields.aggregates);
        }

        function getAggregateValuesKey(aggregateName) {
            return aggregateName + 's';
        }

        function stringArraysEqual(a, b) {
            if (!a || !b) {
                return false;
            }
            return a.length === b.length &&
                [...a].sort().every((v, i) => v === [...b].sort()[i]);
        }


        // reset all aggregates on change data type
        function resetAggregate(attribute) {
            Object.entries($scope.aggregateDataTypeFields.aggregates).forEach(([aggregateName, aggregate]) => {
                    if (!aggregate.isVisible(attribute)) {
                        attribute[aggregateName] = null
                        return;
                    }
                    attribute[aggregateName] = aggregate.defaultValue;
                }
            )
        }

        $scope.updateMergedAttributeDataType = function(mergedAttribute) {
            mergedAttribute.attributes.forEach(attribute => {
                attribute.data_type = mergedAttribute.data_type;
                resetAggregate(attribute);
                if (attribute.checked) {
                    $scope.updateAttributeInSelection(attribute)
                }
            });
        }

        $scope.updateMergedAttributeAggregate = function(mergedAttribute) {
            const aggregateNames = getAggregateNames();

            mergedAttribute.attributes.forEach(attribute => {
                aggregateNames.forEach(aggregateName => {
                    // TODO: check not necessary to copy to avoid arrays being linked
                    attribute[aggregateName] = mergedAttribute[aggregateName];
                });
                if (attribute.checked) {
                    $scope.updateAttributeInSelection(attribute)
                }
            });
        };

        function attributeMatchesSearch(attribute_name, template_name, attribute_description="") {
            if ($scope.config.attributeSearch === "") {
                return true;
            }
            const lowercasedSearch = $scope.config.attributeSearch.toLowerCase();
            const templateNameMatches = template_name.toLowerCase().includes(lowercasedSearch);
            const attributeNameMatches = attribute_name.toLowerCase().includes(lowercasedSearch);
            let attributeDescriptionMatches = false;
            if (attribute_description) {
                attributeDescriptionMatches = attribute_description.toLowerCase().includes(lowercasedSearch);
            }
            return (templateNameMatches || attributeNameMatches || attributeDescriptionMatches)
        }

        // Attributes are shared between templates
        // Meaning all elements with the same template will share the attributes in this template
        // If multiple elements with the same template are selected, we only show the attribute once
        function conflateAttributes(groupKey) {
            return (acc, attr) => {
                // TODO: switch to id
                const key = attr[groupKey] + "::" + attr.title;

                if (!acc[key]) {
                    acc[key] = {
                        title: attr.title,
                        description: attr.description,
                        groupKey: groupKey,
                        group: attr[groupKey],
                        template_names: [],
                        parent_elements: [],
                        checked: null, // Used to determine UI checkbox state
                        allChecked: attr.checked,
                        attributes: [],
                        checkStates: [],
                        paths: [],
                        data_type: attr.data_type,
                        data_types: [],
                        isDisplayed: attributeMatchesSearch(attr.title, attr[groupKey], attr.description),
                    };

                    getAggregateNames().forEach(aggregateName => {
                        acc[key][aggregateName] = attr[aggregateName];
                        acc[key][getAggregateValuesKey(aggregateName)] = [];
                    });
                }

                acc[key].checkStates.push(attr.checked)
                acc[key].template_names.push(attr.template_name)
                acc[key].paths.push(attr.path)
                acc[key].parent_elements.push(attr.parent_element);
                acc[key].checked = getCheckboxStatus(acc[key].checkStates); // TODO maybe move out
                acc[key].allChecked = acc[key].allChecked && attr.checked
                acc[key].attributes.push(attr);
                acc[key].data_types.push(attr.data_type);

                if (acc[key].data_type !== attr.data_type) {
                    acc[key].data_type = null;
                }

                getAggregateNames().forEach(aggregateName => {
                    acc[key][getAggregateValuesKey(aggregateName)].push(attr[aggregateName]);
                    if ($scope.aggregateDataTypeFields.aggregates[aggregateName].type === 'multiselect') {
                        if (!stringArraysEqual(acc[key][aggregateName], attr[aggregateName])) {
                            acc[key][aggregateName] = [];
                        }
                        return;
                    }
                    if (acc[key][aggregateName] !== attr[aggregateName]) {
                        acc[key][aggregateName] = null;
                    }
                });

                return acc
            }
        }

        function groupAttributesIntoSections() {
            return (acc, attr) => {
                const key = attr.group;
                if (!acc[key]) {
                    acc[key] = {
                        group_name: attr.group,
                        allChecked: attr.checked,
                        checked: CheckboxStatus.UNCHECKED, // Used to determine UI checkbox state
                        attributes: [],
                        checkStates: [],
                        isDisplayed: true,
                        nbSearchMatches: 0
                    }
                }

                if (attr.isDisplayed) {
                    acc[key].checkStates.push(...attr.checkStates);
                    acc[key].allChecked = acc[key].allChecked && attr.allChecked;
                }
                acc[key].checked = getCheckboxStatus(acc[key].checkStates);
                acc[key].attributes.push(attr);
                acc[key].isDisplayed = acc[key].isDisplayed && !attr.isDisplayed;
                acc[key].nbSearchMatches += +attr.isDisplayed;
                return acc;
            }
        }

        function buildAggregatedAttributes(attributes, groupKey) {
            const deduplicatedAttributes = Object.values(attributes.reduce(conflateAttributes(groupKey), {}));
            return Object.values(deduplicatedAttributes.reduce(groupAttributesIntoSections(), {}));
        }

        function splitAttributesByTemplatePresence(attributes) {
            return attributes.reduce(
                (accumulator, attribute) => {
                    // TODO: make the attribute have a template name even if no template
                    const bucket = attribute?.template_name
                        ? 'attributesWithTemplate'
                        : 'attributesWithoutTemplate';
                    accumulator[bucket].push(attribute);
                    return accumulator;
                },
                { attributesWithoutTemplate: [], attributesWithTemplate: [] }
            );
        }

        function buildGroupedAttributesResult(attributes, groupKey) {
            const groups = buildAggregatedAttributes(attributes, groupKey);
            const displayedGroups = groups.filter(group => !group.isDisplayed);
            // TODO: probably turn this into a reduce
            return {
                allChecked: displayedGroups.length > 0 && displayedGroups.every(group => group.allChecked),
                checked: getCheckboxStatus(groups.reduce((acc, group) => acc.concat(group.checkStates), [])),
                // a table can be empty because all it's attributes have been filtered out OR there are no elements to show
                empty: groups.length === 0 || groups.every(group => group.isDisplayed),
                groups: groups
            }
        }

        $scope.buildGroupedAttributes = function() {
            const splitAttributes = splitAttributesByTemplatePresence($scope.config.attributeList);
            return {
                attributesWithoutTemplate: buildGroupedAttributesResult(
                    splitAttributes.attributesWithoutTemplate,
                    'parent_element'
                ),
                attributesGroupedByTemplate: buildGroupedAttributesResult(
                    splitAttributes.attributesWithTemplate,
                    'template_name'
                )
            };
        }

        function getCheckboxStatus(checkboxStatuses) {
            if (!checkboxStatuses.length) {
                return CheckboxStatus.UNCHECKED;
            }
            if (checkboxStatuses.every(Boolean)) {
                return CheckboxStatus.CHECKED;
            } else if (checkboxStatuses.some(Boolean)) {
                return CheckboxStatus.PARTIAL_CHECK;
            }
            return CheckboxStatus.UNCHECKED;
        }

        // TODO: try to move it to a callback of some kind (will work with a component)
        $scope.$watch('config.attributeList', function(newVal, oldVal) {
            $scope.groupedAttributes = $scope.buildGroupedAttributes();
        }, true);

        $scope.refreshAttributeSection = function() {
            $scope.groupedAttributes = $scope.buildGroupedAttributes();
        }

        $scope.addAttributeToSelection = function(attribute) {
            const index = $scope.config.outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);
            if (index !== -1) {
                console.warn("Cannot add attribute to selection because already present", attribute);
                return;
            }
            attribute.checked = true;
            $scope.config.outputSelectedAttributes.push(attribute);
            console.log("Removed attribute from selection", attribute);
        }

        $scope.removeAttributeFromSelection = function(attribute) {
            const index = $scope.config.outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);
            if (index === -1) {
                console.warn("Cannot remove attribute from selection because not present", attribute);
                return;
            }
            attribute.checked = false;
            $scope.config.outputSelectedAttributes.splice(index, 1);
            console.log("Removed attribute from selection", attribute);
        }

        $scope.updateAttributeInSelection = function(attribute) {
            const index = $scope.config.outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);
            if (index === -1) {
                console.warn("Cannot update attribute in selection because not present", attribute);
                return;
            }
            $scope.config.outputSelectedAttributes[index] = attribute;
        }

    }]);


app.component('treeNode', {
    bindings: {
        node: '=',
        getChildrenFromDb: '<',
        toggleDisplayAttributes: '<',
        config: '<',
        onNodeClick: '&',
    },

    controllerAs: 'ctrl',

    controller: function() {
        const ctrl = this;

        ctrl.hasRenderableChildren = function(node) {
            if (!node || !Array.isArray(node.children) || !node.children.length) {
                return false;
            }
            return node.children.some(function(child) {
                return child && child.type !== 'attribute';
            });
        };

        ctrl.toggleExpand = function(node, $event) {
            if ($event) {
                $event.stopPropagation();
            }
            // Loading children before toggling the node
            if (!node.expanded && (!node.children?.length || !ctrl.hasRenderableChildren(node))) {
                ctrl.getChildrenFromDb(node).then(() => {
                    node.expanded = true;
                });
                return;
            }
            node.expanded = !node.expanded;
        };

        ctrl.isNodeClicked = function(node) {
            // the click is entirely based on node.url
            return ctrl.config.clickedNodes.includes(node.url);
        };

        ctrl.isSearchResult = function(node) {
            return !!node.searchHighlighted;
        };
    },
    templateUrl: "/plugins/pi-system/resource/tree-node.html"
});

// TODO: see if cleaner architecture
app.directive('attributeTableRow', function() {
    return {
        restrict: 'A',
        scope: {
            mergedAttribute: '=',
            displayPath: '<',
            aggregateDataTypeFields: '<',
            onCheckAttribute: '&',
            onUpdateDataType: '&',
            onUpdateAggregate: '&',
        },
        bindToController: true,
        controllerAs: 'ctrl',
        controller: function() {
        },
        templateUrl: "/plugins/pi-system/resource/attribute-table-row.html"
    };
});

app.directive('indeterminate', function() {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            if (attrs.indeterminate === CheckboxStatus.PARTIAL_CHECK) {
                element[0].indeterminate = true;
            }

            scope.$watch(attrs.indeterminate, function(checkStatus) {
                if (checkStatus === CheckboxStatus.PARTIAL_CHECK) {
                    element[0].indeterminate = true;
                    return;
                }
                element[0].indeterminate = false;
            }, true);
        }
    };
});
