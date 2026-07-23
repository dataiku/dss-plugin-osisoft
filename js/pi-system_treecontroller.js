const app = angular.module('piSystemTreeApp.module', []);

app.directive('piSystemAuthBanner', function() {
    return {
        restrict: 'E',
        scope: false,
        templateUrl: '/plugins/pi-system/resource/pi-system_auth-banner.html'
    };
});

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

const GroupMode = Object.freeze({
    TEMPLATE: 'TEMPLATE',
    CATEGORY: 'CATEGORY',
});

class Cache {
    constructor(projectKey, server, database) {
        // TODO: include preset in db name
        this.dbName = [projectKey, server, database].join("::")
        this.dbVersion = 1
        this.attributesStoreName = "attributes"
        this.elementTreeStoreName = "elementTree"
        this.templateTreeStoreName = "templateTree"
        this.elementsByTemplateStoreName = "elementsByTemplate"
        this.stores = [this.attributesStoreName, this.elementTreeStoreName, this.templateTreeStoreName, this.elementsByTemplateStoreName]

        this.elementTreeRecordId = "elementTree"
        this.templateTreeRecordId = "templateTree"
        this.elementsByTemplateRecordId = "elementsByTemplate"
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onupgradeneeded = () => {
                this.db = request.result;
                this.stores.forEach(storeName => {
                    if (!this.db.objectStoreNames.contains(storeName)) {
                        this.db.createObjectStore(storeName, { keyPath: "id" });
                    }
                })
            };

            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    async getAttribute(attrId) {
        return this.getObject(this.attributesStoreName, attrId);
    }

    async getElementTree() {
        return this.getObject(this.elementTreeStoreName, this.elementTreeRecordId).then((data) => data?.nodes);
    }

    async getTemplateTree() {
        return this.getObject(this.templateTreeStoreName, this.templateTreeRecordId).then((data) => data?.nodes);
    }

    async getElementsByTemplate() {
        return this.getObject(this.elementsByTemplateStoreName, this.elementsByTemplateRecordId).then((data) => data?.nodes);
    }

    async getObject(objectStoreName, objectId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([objectStoreName]);
            const objectStore = transaction.objectStore(objectStoreName);
            const request = objectStore.get(objectId);
            request.onerror = (event) => {
                console.error("Could not get object " + objectId + " from cache")
                reject(request.error);
            };
            request.onsuccess = (event) => {
                resolve(request.result);
            };
        })
    }

    async addOrUpdateAttribute(attribute) {
        return this.addOrUpdate(attribute, this.attributesStoreName);
    }

    async addOrUpdateElementTree(elementTree) {
        return this.addOrUpdate({
                id: this.elementTreeRecordId,
                nodes: elementTree
        }, this.elementTreeStoreName);
    }

    async addOrUpdateTemplateTree(templateTree) {
        return this.addOrUpdate({
                id: this.templateTreeRecordId,
                nodes: templateTree
        }, this.templateTreeStoreName);
    }

    async addOrUpdateElementsByTemplate(elementsByTemplate) {
        return this.addOrUpdate({
                id: this.elementsByTemplateRecordId,
                nodes: elementsByTemplate
        }, this.elementsByTemplateStoreName);
    }

    async addOrUpdate(object, objectStoreName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([objectStoreName], "readwrite");
            transaction.onerror = (event) => {
                reject(transaction.error)
            };

            const objectStore = transaction.objectStore(objectStoreName);
            const request = objectStore.put(object);
            request.onsuccess = (event) => {
                resolve(object)
            };
            request.onerror = (event) => {
                reject(request.error)
            };
        });
    }

    async clear() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(this.stores, "readwrite");
            transaction.oncomplete = () => {
                resolve();
            };
            transaction.onerror = () => {
                reject(transaction.error);
            };

            this.stores.forEach(storeName => {
                const objectStore = transaction.objectStore(storeName);
                objectStore.clear();
            })
        });
    }
}

app.controller('AfExplorerFormCtrl', [
    '$scope',
    '$stateParams',
    '$q',
    'CreateModalFromTemplate',
    function($scope, $stateParams, $q, CreateModalFromTemplate) {

        $scope.paramDesc = {
            'parameterSetId': 'basic-auth',
            'mandatory': true
        };

        $scope.attributeList = []; // The list of attributes that are currently displayed in the main panel
        $scope.config.outputSelectedAttributes = $scope.config.outputSelectedAttributes || []; // The list of attributes selected by the user
        $scope.elementsByTemplate = {};

        // $scope.config.selectedTemplateNames =  []; // la liste des templates sélectionnés utilisées pour filtrer le search. Stale

        $scope.ui = {
            clickedNodes: [],
            searchMatchedElementPaths: [], // la liste pour highlighter les elements de la recherche
            attributeSearch: "",
            displayPath: false,
            onlyDisplayCommon: false,
            searchInProgress: false
        };

        $scope.authSectionVisible = true;
        $scope.showTreeData = false;
        $scope.errorBannerVisible = false;
        $scope.errorBannerMessage = '';

        // TODO: get categories from backend for attributes
        // $scope.config.attributeCategoryFilter = $scope.config.attributeCategoryFilter || ""

        $scope.aggregateDataTypeFields = aggregateDataTypeFields;

        $scope.elementSearchNoMatch = false;

        $scope.selectedElementPaths = buildSelectedElementPaths()

        function formatPreviewValue(value) {
            if (Array.isArray(value)) {
                return value.join(', ');
            }
            return value;
        }

        function buildSelectedElementPaths() {
            return $scope.config.outputSelectedAttributes.flatMap(attribute => attribute.paths).map(getElementPathFromAttributePath);
        }

        function groupSelectedAttributes() {
            return (acc, attr) => {
                const key = attr.parent_element_path;
                if (!acc[key]) {
                    acc[key] = {
                        group_name: attr.parent_element,
                        checked_ui: attr.checked, // dummy variable for ng-model
                        checked: CheckboxStatus.CHECKED, // acutally used to determine UI checkbox state
                        attributes: [],
                        children_checked: [],
                        isDisplayed: true,
                        nbSearchMatches: 0
                    }
                }
                console.log("acc", acc[key])

                if (attr.isDisplayed) {
                    acc[key].children_checked.push(attr.checked);
                    acc[key].checked_ui = acc[key].checked_ui && attr.checked
                }
                acc[key].checked = getCheckboxStatus(acc[key].children_checked);
                acc[key].attributes.push(attr);
                acc[key].isDisplayed = acc[key].isDisplayed && !attr.isDisplayed;
                acc[key].nbSearchMatches += +attr.isDisplayed;
                return acc;
            }
        }


        $scope.showDatasetPreviewModal = function() {
            const modalScope = $scope.$new();
            modalScope.CheckboxStatus = CheckboxStatus;
            modalScope.currentlySelectedAttributes = structuredClone($scope.config.outputSelectedAttributes);
            modalScope.currentlySelectedAttributes.forEach((attribute) => {
                attribute.checked = true;
                attribute.isDisplayed = true;
            });

            modalScope.rebuildPreviewDatasetTable = function() {
                modalScope.previewRows = buildSelectedAttributesTable();
            }

            function buildSelectedAttributesTable() {
                return modalScope.currentlySelectedAttributes.reduce(groupSelectedAttributes(), {});
            }

            modalScope.toggleElementSelection = function(subgroup) {
                const shouldCheck = subgroup.checked !== CheckboxStatus.CHECKED;
                subgroup.attributes.forEach((attribute) => {
                    attribute.checked = shouldCheck;
                });
                modalScope.rebuildPreviewDatasetTable();
            };

            modalScope.toggleAttributeSelection = function(row) {
                row.checked = !row.checked;
                modalScope.rebuildPreviewDatasetTable();
            };
            //
            // modalScope.clearSelection = function() {
            //     $scope.clearOutputSelection();
            //     modalScope.rebuildPreviewDatasetTable();
            // }

            modalScope.previewColumns = [
                { key: 'title', label: 'Title' },
                { key: 'template_name', label: 'Template' },
                { key: 'data_type', label: 'Data type' },
                { key: 'summary_type', label: 'Summary type' },
                { key: 'boundary_type', label: 'Boundary type' },
                { key: 'record_boundary_type', label: 'Record boundary type' },
                { key: 'summary_duration', label: 'Summary duration' },
                { key: 'interval', label: 'Interval' },
                { key: 'sync_time', label: 'Sync time' },
            ];

            modalScope.rebuildPreviewDatasetTable();

            CreateModalFromTemplate('/plugins/pi-system/resource/pi-system_preview-dataset-modal.html', modalScope);
        };

        $scope.clearOutputSelection = function() {
            $scope.config.outputSelectedAttributes = [];
            $scope.selectedElementPaths = []
            $scope.refreshAttributeSection();
            // Just need to uncheck the current attribute list as it is
            // built with the correct checked state when adding any new elements
            // TODO: switch to mass update in cache
            Object.values($scope.attributeList).forEach(attribute => {
                attribute.checked = false;
            });
            $scope.refreshAttributeSection();
        }

        $scope.isAtLeastPartiallySelected = function(node) {
            return node.checked === CheckboxStatus.CHECKED || node.checked === CheckboxStatus.PARTIAL_CHECK;
        };

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
            $scope.activeTab = $scope.activeTab || 'element';
            $scope.templateTree = $scope.templateTree || [];
            $scope.groupMode = $scope.groupMode || GroupMode.TEMPLATE;
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
                // We try getting the elementTree from cache. If we can't we open the authSection
                // And we will load the elementTree from db once the user has logged in
                // This is brittle and should probably changed in the future
                initData().then(() => {
                    $scope.authSectionVisible = false;
                    $scope.showTreeData = true;
                }).catch(() => {
                    $scope.errorBannerMessage = 'There was a problem fetching data';
                    $scope.errorBannerVisible = true;
                }).then(() => {
                    $scope.$applyAsync()
                })
            }
            $scope.onAdvancedToggle();
        };

        $scope.getServers = function() {
            $scope.callPythonDo({ parameterName: "server_name" }).then(function(data) {
                console.log("server_name", data);
                $scope.server_name = data.choices;
            });
        };
        $scope.getDatabases = function() {
            $scope.callPythonDo({ parameterName: "database_name" }).then(function(data) {
                console.log("database_name", data);
                $scope.database_name = data.choices;
            });
        };

        $scope.toggleAuthSection = function() {
            $scope.authSectionVisible = !$scope.authSectionVisible;
        };

        $scope.authConfigured = function() {
            return $scope.hasPreset() && !!$scope.config.database_name && !!$scope.config.server_name;
        }

        function loadObject(cacheGetter, dbGetter, cacheSetter, scopeKey) {
            let fromDb = false;
            return cacheGetter()
                .catch(() => {
                    fromDb = true;
                    return dbGetter()
                })
                .then(object => {
                    if (object === undefined || object.length === 0) {
                        fromDb = true;
                        return dbGetter();
                    }
                    return object;
                })
                .catch(error => {
                    throw new Error(`Could not load ${scopeKey} from cache and then DB: ${error}`);
                })
                .then(object => {
                    if (!object || object.length === 0) {
                        throw new Error(`Could not load ${scopeKey} from DB`);
                    }
                    $scope[scopeKey] = object;
                    if (fromDb) {
                        cacheSetter(object);
                    }
                });
        }

        function loadElementTree() {
            return loadObject(
                () => $scope.cache.getElementTree(),
                () => $scope.getElementTreeFromDB(),
                 () => $scope.cache.addOrUpdateElementTree(),
                'elementTree',
            );
        }

        function loadTemplateTree() {
            return loadObject(
                () => $scope.cache.getTemplateTree(),
                () => $scope.getTemplatesFromDB(),
                () => $scope.cache.addOrUpdateTemplateTree(),
                'templateTree',
            );
        }

        function loadElementsByTemplate() {
            return $scope.cache.getElementsByTemplate().then(elementsByTemplate => {
                $scope.elementsByTemplate =  elementsByTemplate || {}
            });
        }

        // Fetching data - only once auth has been verified
       function initData() {
            return initCache().catch((error) => {
                // TODO: figure out what we want in that case
                throw new Error(`There was an error initializing cache: ${error}`);
            }).then(() => {
                return $q.all([
                    loadElementTree(),
                    loadTemplateTree(),
                    loadElementsByTemplate()
                ])
            }).catch((error) => {
                throw new Error(`There was an error initializing data: ${error}`);
            }).then(() => {
                $scope.$applyAsync();
            })
        }

        $scope.login = function() {
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

            initData().then(() => {
                $scope.authSectionVisible = false;
                $scope.showTreeData = true;
            }).catch(() => {
                $scope.authSectionVisible = true;
                $scope.showTreeData = false;
                $scope.errorBannerMessage = 'There was a problem fetching data';
                $scope.errorBannerVisible = true;
            }).then(() => {
                console.log("treedata", $scope.showTreeData);
                console.log("treedata", $scope.elementTree);
                $scope.$applyAsync()
            })
        };

        $scope.hasPreset = function() {
            return $scope.config.credentials?.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
        }

        $scope.cleanTree = function() { // utile quand on change de serveur ou de db dans la config
            $scope.elementTree = [];
            $scope.ui.clickedNodes = [];
            $scope.attributeList = [];
            $scope.config.outputSelectedAttributes = [];
            $scope.selectedElementPaths = []
            $scope.ui.searchMatchedElementPaths = [];
            $scope.elementsByTemplate = {};
            // $scope.config.selectedTemplateNames = [];
            // TODO: switch to cleanup cache
            $scope.elementSearchNoMatch = false;
            $scope.refreshAttributeSection();
        }

        $scope.resetDatasourceState = function() { //
            $scope.server_name = [];
            $scope.database_name = [];
            $scope.config.server_name = null;
            $scope.config.database_name = null;
            $scope.templateTree = [];
            $scope.config.loadedDatabaseName = null;
            $scope.attributeList = [];
            $scope.config.outputSelectedAttributes = [];
            $scope.selectedElementPaths = []
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        $scope.onServerChanged = function() {
            $scope.config.database_name = null;
            $scope.templateTree = [];
            $scope.config.loadedDatabaseName = null;
            $scope.showTreeData = false;
            $scope.cleanTree();
            $scope.getDatabases();
        };

        $scope.onDatabaseChanged = function() {
            $scope.templateTree = [];
            $scope.config.loadedDatabaseName = null;
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        $scope.refreshCachedTree = function() {
            $scope.cache.clear().then(function() {
                $scope.elementTree = [];
                $scope.ui.clickedNodes = [];
                $scope.attributeList = [];
                $scope.ui.searchMatchedElementPaths = [];
                // $scope.config.selectedTemplateNames = [];
                $scope.elementsByTemplate = {};
                $scope.elementSearchNoMatch = false;
                $scope.refreshAttributeSection();
                // TODO: need to assign those
                return $q.all([
                    $scope.getElementTreeFromDB(),
                    $scope.getTemplatesFromDB(),
                ]);
            }).then(([elementTree, templateTree]) => {
                $scope.elementTree = elementTree;
                $scope.templateTree = templateTree;
                cacheElementTree();
                cacheTemplateTree();
                $scope.$applyAsync();
            })
        }

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

        function initCache() {
            $scope.cache = new Cache(
                $stateParams.projectKey,
                $scope.config.server_name,
                $scope.config.database_name
            );
            return $scope.cache.init();
        }

        function buildPersistedTreeSnapshot(nodes) {
            return nodes.map(node => {
                const persistedNode = {};

                Object.keys(node).forEach(key => {
                   if (key === "searchHighlighted") {
                       return;
                   }
                   if (key === "children" && Array.isArray(node.children)) {
                       persistedNode.children = buildPersistedTreeSnapshot(node.children);
                       return;
                   }
                   persistedNode[key] = node[key];
               });
                return persistedNode;
            });
        }

        function cacheElementTree() {
            const snapshot = buildPersistedTreeSnapshot($scope.elementTree);
            return $scope.cache.addOrUpdateElementTree(snapshot);
        }

        function cacheTemplateTree() {
            const snapshot = buildPersistedTreeSnapshot($scope.templateTree);
            return $scope.cache.addOrUpdateTemplateTree(snapshot);
        }

        function cacheElementsByTemplate() {
            $scope.cache.addOrUpdateElementsByTemplate($scope.elementsByTemplate);
        }

        $scope.getElementTreeFromDB = function() {
            return $scope.callPythonDo({ method: "get_children_from_db", parent: $scope.config.database_name }).then(function(data) {
                console.log("get_children_from_db", data);
                return data.choices;
            });
        };

        $scope.getFromCacheOrFetchBaselineObjects = function() {
            $scope.cleanTree();
            return $q.all([
                $scope.getElementTreeFromDB(),
                $scope.getTemplatesFromDB(),
            ]).then(function([elementTree, templateTree]) {
                $scope.elementTree = elementTree;
                $scope.templateTree = templateTree;
                cacheElementTree();
                cacheTemplateTree();
                $scope.config.loadedDatabaseName = $scope.config.database_name || null;
                return [elementTree, templateTree];
            });
        }

        $scope.getChildrenFromDB = function(item) {
            if (item.type === "template") {
                return getAttributesForTemplate(item);
            }
            return $scope.callPythonDo({ method: "get_children_from_db", parent: item })
                .then(function(data) {
                    console.log("get_children_from_db", data);
                    const attributeLoadPromises = [];
                    item.attribute_children = [];
                    const loadedAttributes = data.choices.filter(node => node.type === 'attribute').map(attribute =>
                        {
                            return { ...attribute,
                                expanded: false,
                                parent_element: item.title,
                                parent_element_path: item.path
                            };
                        }
                    );
                    loadedAttributes.forEach(attribute => {
                        attributeLoadPromises.push(
                            addAttributeToLoadedAttributes(attribute)
                        );
                        item.attribute_children.push(attribute.id);
                    });
                    item.children = data.choices.filter(node => node.type === item.type);
                    item.children.forEach(child => {
                        child.expanded = false;
                    });
                    markSearchResults(item.children, $scope.ui.searchMatchedElementPaths || []);
                    cacheElementTree();
                    return Promise.all(attributeLoadPromises).then(() => {
                        return {
                            updatedNode: item,
                            loadedAttributes: loadedAttributes
                        }
                    });
                });
        }


        $scope.getTemplatesFromDB = function() {
            return $scope.callPythonDo({ method: "get_templates_from_db" }).then(function(data) {
                console.log("get_templates_from_db", data)
                return data.choices.filter(template => template.title !== "-- Any --")
            });
        }

        function resetRightPanelForCurrentTabContext() {
            $scope.ui.clickedNodes = [];
            $scope.attributeList = [];
            $scope.ui.searchMatchedElementPaths = [];
            // $scope.config.selectedTemplateNames = [];
            $scope.ui.attributeSearch = "";
            $scope.elementSearchNoMatch = false;
            if ($scope.activeTab === "template") {
                $scope.config.element_name = "";
            }
            $scope.refreshAttributeSection();
        }

        $scope.setTab = function(tab) {
            const previousTab = $scope.activeTab;
            if (tab !== previousTab) {
                resetRightPanelForCurrentTabContext();
            }
            $scope.activeTab = tab;
        };

        // $scope.getCategoriesFromDB = function() {
        //     $scope.config.attribute_categories = [];
        //     $scope.config.element_categories = [];
        //     const attributeCategoriesPromise = $scope.callPythonDo({ method: "get_attribute_categories_from_db" }).then(function(data) {
        //         console.log("get_attribute_categories_from_db", data);
        //         $scope.config.attribute_categories = data.choices;
        //         return data;
        //     });
        //     const elementCategoriesPromise = $scope.callPythonDo({ method: "get_element_categories_from_db" }).then(function(data) {
        //         console.log("get_element_categories_from_db", data);
        //         $scope.config.element_categories = data.choices;
        //         return data;
        //     });
        //     return $q.all([attributeCategoriesPromise, elementCategoriesPromise]);
        // }

        $scope.doSearch = function(element_name) {
            $scope.ui.searchInProgress = true;
            $scope.ui.searchMatchedElementPaths = [];
            $scope.callPythonDo({ method: "do_search", element_name: element_name, elementTree: $scope.elementTree }).then(
                function(data) {
                    console.log("do_search", data);
                    $scope.elementTree = data.choices;
                    const matchedAttributes = data.attributes || [];
                    const matchedElementPaths = getMatchedElementPaths(matchedAttributes);
                    if (matchedElementPaths.length === 0) {
                        $scope.elementSearchNoMatch = true;
                    }
                    $scope.ui.searchMatchedElementPaths = matchedElementPaths;
                    markSearchResults($scope.elementTree, matchedElementPaths);
                    cacheElementTree();
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

        function getElementNameFromPath(elementPath) {
            const splitPath = elementPath.split('\\');
            return splitPath?.[splitPath.length - 1];
        }

        // TODO: check there cannot be pipes in names
        function getElementPathFromAttributePath(attributePath) {
            return attributePath.split('|')?.[0];
        }

        function getAttributesForTemplate(node) {
            return $scope.callPythonDo({ method: "get_attribute_for_template", template_name: node.title}).then(
                function(data) {
                    console.log("get_attribute_for_template", data);
                    node.attribute_children = [];
                    const loadedAttributes = data.attributes.map(attribute => {
                        const elementPath = getElementPathFromAttributePath(attribute.path);
                        return {
                            ...attribute,
                            expanded: false,
                            parent_element: getElementNameFromPath(elementPath),
                            parent_element_path: elementPath
                        };
                    })
                    loadedAttributes.forEach(attribute => {
                            addAttributeToLoadedAttributes(attribute);
                            node.attribute_children.push(attribute.id);
                        }
                    );
                    cacheTemplateTree();
                    return {
                        updatedNode: node,
                        loadedAttributes: loadedAttributes
                    };
                }
            );
        }

        $scope.isTemplateAssociatedElementSelected = function(element) {
            return $scope.ui.clickedNodes.includes(element.url);
        }

        $scope.getElementsForTemplate = function (templateName) {
            return $scope.callPythonDo({ method: "get_elements_for_template", template_name: templateName}).then(
                function(data) {
                    console.log("get_elements_for_template", data);
                    $scope.elementsByTemplate[templateName] = data.elements;
                    cacheElementsByTemplate();
                }
            );
        }

        $scope.templateModeExcludedAttributes = {};

        $scope.initElementsDropdown = async function(templateName) {
            const existingElements = $scope.elementsByTemplate[templateName];
            console.log("elementsbytemplate", $scope.elementsByTemplate)
            console.log("existingElements", existingElements)
            if (Array.isArray(existingElements)) {
                console.log("here")
                return existingElements.map(element => element.url);
            }
            console.log("fetching")
            await $scope.getElementsForTemplate(templateName);
            return $scope.elementsByTemplate[templateName].map(element => element.url);
        }

        // FIXME: the parent_element_path is not properly present !!! probably because loaded from cache
        // should be properly populated f we want the condition l835 to populate
        // TODO: check if fixme is up to date
        $scope.applyClickElementsDropdown = function(templateName, element, wasUnselected) {
            $scope.$applyAsync(() => {
                // TODO: redo everything by templateID
                console.log("$scope.templateModeExcludedAttributes", $scope.templateModeExcludedAttributes)
                console.log("in apply click")
                if ($scope.activeTab === 'element') {
                    $scope.toggleNodeVisualization(element);
                } else if ($scope.activeTab === 'template') {
                    if (!wasUnselected) {
                        console.log("not unselected (apply click) - removing from attributelist ")
                        if (!$scope.templateModeExcludedAttributes[templateName]) {
                            $scope.templateModeExcludedAttributes[templateName] = {}
                        }
                        $scope.templateModeExcludedAttributes[templateName][element.path] = $scope.attributeList.filter(attribute => {
                            return attribute.template_name === templateName && attribute.parent_element_path === element.path;
                        });
                        $scope.attributeList = $scope.attributeList.filter(attribute => {
                            return attribute.template_name !== templateName || attribute.parent_element_path !==
                                element.path;
                        });
                        $scope.refreshAttributeSection();
                    } else if (wasUnselected) {
                        const attributesToAdd = $scope.templateModeExcludedAttributes[templateName]?.[element.path] || [];
                        $scope.attributeList.push(...attributesToAdd)
                        $scope.refreshAttributeSection();
                    }
                }
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

        $scope.clearAllVisualizedNodes = function() {
            $scope.attributeList = []
            $scope.ui.clickedNodes = []
            $scope.refreshAttributeSection();
        }

        $scope.toggleNodeVisualization = function(node) {
            console.log("clicked on ", node)

            const indexClickedNode = $scope.ui.clickedNodes.indexOf(node.url);
            const nodeAlreadySelected = indexClickedNode > -1;
            // If the node is already clicked, remove it from clicked nodes - else add it
            if (nodeAlreadySelected) {
                $scope.ui.clickedNodes.splice(indexClickedNode, 1);
            } else {
                $scope.ui.clickedNodes.push(node.url);
            }

            $scope.toggleDisplayAttributes(node, !nodeAlreadySelected).then(() => {
                $scope.refreshAttributeSection();
                // Necessary because no digest cycle triggered for awaited cache reads
                $scope.$applyAsync();
            });

            // In element node, the visualized nodes are reflected on the elements dropdown
            console.log("clickedNodes: " + JSON.stringify($scope.ui.clickedNodes));
        };

        function markSearchResults(nodes, matchedElementPaths) {
            if (!Array.isArray(nodes)) {
                return;
            }
            const matchedPathSet = new Set(matchedElementPaths || []);

            nodes.forEach(node => {
                node.searchHighlighted =
                    node &&
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
            $scope.elementSearchNoMatch = false;
            $scope.doSearch($scope.config.element_name);
        };

        $scope.clearSearch = function() {
            $scope.ui.searchInProgress = false;
            $scope.config.element_name = "";
            $scope.ui.searchMatchedElementPaths = [];
            $scope.elementSearchNoMatch = false;
            clearSearchHighlights($scope.elementTree);
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
            $scope.refreshAttributeSection();
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
            $scope.refreshAttributeSection();
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
            $scope.refreshAttributeSection();
        };

        // TODO: mark as loaded elements and replace this logic
        function hasAttributeChildren(node) {
            return !(!Array.isArray(node.attribute_children) || node.attribute_children.length === 0);

        }

        function getChildrenIfMissing(node) {
            if (hasAttributeChildren(node)) {
                return Promise.resolve(node);
            }
            return $scope.getChildrenFromDB(node).then(data => {
                return data.updatedNode;
            });
        }

        function stopDisplayingAttributes(node) {
            // It is for now possible to stop displaying an element that was not loaded because of weak links
            // patching it by loading the element before stopping to display it
            // TODO: replace by weak link single loading logic
            return getChildrenIfMissing(node).then(node => {
                $scope.attributeList = $scope.attributeList.filter(
                    attribute => !node.attribute_children.includes(attribute.id)
                );
            });
        }

        // Put node children in the displayed attribute list
        // Enrich them with data from the selected list + their parent
        function addChildrenToAttributeList(node, loadedAttributes) {
            console.log("enriching children and adding them to the attributeList")
            const parentTemplateName = node?.template_name;

            loadedAttributes.forEach(attribute => {
                if (!attribute?.parent_template_name && parentTemplateName) {
                    attribute.parent_template_name = parentTemplateName;
                }
                const isAlreadyPresent = $scope.attributeList.find(attr => attr.id === attribute.id);
                if (!isAlreadyPresent) {
                    enrichAttribute(attribute, node);
                    $scope.attributeList.push(attribute);
                    // $scope.$applyAsync();
                }
            });

            return loadedAttributes
        }

        function loadAndAddChildrenAttributes(node) {
            console.log("loading children from db and adding them to the list")
            return $scope.getChildrenFromDB(node).then(data => {
                console.log("node", data.node)
                console.log("loadedAttributes", data.loadedAttributes)
                return addChildrenToAttributeList(data.updatedNode, data.loadedAttributes);
            });
        }

        $scope.toggleDisplayAttributes = function(node, add = true) {
            if (!add) {
               return stopDisplayingAttributes(node);
            }
            if (!hasAttributeChildren(node)) {
                console.log("loading children from the first time")
                return loadAndAddChildrenAttributes(node);
            }
            return Promise.all(
                node.attribute_children.map(attributeId => {
                    return $scope.cache.getAttribute(attributeId).then(loadedAttribute => {
                        if (!loadedAttribute) {
                            throw new Error("Could not load attribute " + attributeId + " from the cache");
                        }
                        return loadedAttribute;
                    });
                })
            ).then((loadedAttributes) => {
                // When all the attributes are properly fetched from the cache, they can be added to the attribute list
                console.log("loaded the attributes from the cache and adding them")
                return addChildrenToAttributeList(node, loadedAttributes);
            }).catch(() => {
                console.log("could not load attributes from the cache, refetching")
                // if they are not in the cache, we refetch them all from db and update the cache
                return loadAndAddChildrenAttributes(node);
            })
        }

        // Merge frontend data and saved output with loaded attributes
        function enrichAttribute(attribute, parentNode) {
            // NOTE: not cached
            const selectedAttribute = $scope.config.outputSelectedAttributes.find(attr => attr.path === attribute.path);
            attribute.checked = !!(selectedAttribute);
            if (parentNode.type === "element") {
                attribute.parent_element = parentNode?.title;
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
            $scope.refreshAttributeSection();
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
            $scope.refreshAttributeSection();
        };

        function attributeMatchesSearch(attribute_name, group_name, attribute_description="") {
            if ($scope.ui.attributeSearch === "") {
                return true;
            }
            const lowercasedSearch = $scope.ui.attributeSearch.toLowerCase();
            const groupNameMatches = group_name.toLowerCase().includes(lowercasedSearch);
            const attributeNameMatches = attribute_name.toLowerCase().includes(lowercasedSearch);
            let attributeDescriptionMatches = false;
            if (attribute_description) {
                attributeDescriptionMatches = attribute_description.toLowerCase().includes(lowercasedSearch);
            }
            return (groupNameMatches || attributeNameMatches || attributeDescriptionMatches)
        }

        function arraysEqual(a, b) {
            if (!a && !b) {
                return true;
            }
            if (!a || !b) {
                return false;
            }
            return a.length === b.length && a.every((v, i) => v === b[i]);
        }

        // Attributes are shared between templates
        // Meaning all elements with the same template will share the attributes in this template
        // If multiple elements with the same template are selected, we only show the attribute once
        function getGroups(attr, groupProperty) {
            const groupPropertyValues = attr[groupProperty];
            if (Array.isArray(groupPropertyValues)) {
                return groupPropertyValues.map(value => {
                    return {key: value + "::" + attr.title, value: value};
                });
            }
            return [ { key: groupPropertyValues + "::" + attr.title, value: groupPropertyValues } ];
        }

        function initConflatedAttribute(attr, group) {
            const conflatedAttribute = {
                title: attr.title,
                description: attr.description,
                group: group.value,
                template_name: attr.template_name,
                parent_elements: [],
                checked: null, // Used to determine UI checkbox state
                allChecked: attr.checked,
                attributes: [],
                checkStates: [],
                paths: [],
                data_type: attr.data_type,
                data_types: [],
                isDisplayed: attributeMatchesSearch(attr.title, group.value, attr.description),
                category_names: attr.category_names,
                conflicting_categories: false
            };

            getAggregateNames().forEach(aggregateName => {
                conflatedAttribute[aggregateName] = attr[aggregateName];
                conflatedAttribute[getAggregateValuesKey(aggregateName)] = [];
            });

            return conflatedAttribute;
        }

        function updateConflatedAttribute(conflatedAttribute, attr) {
            conflatedAttribute.checkStates.push(attr.checked);
            conflatedAttribute.paths.push(attr.path);
            conflatedAttribute.parent_elements.push(attr.parent_element);
            conflatedAttribute.checked = getCheckboxStatus(conflatedAttribute.checkStates); // TODO maybe move out
            conflatedAttribute.allChecked = conflatedAttribute.allChecked && attr.checked;
            conflatedAttribute.attributes.push(attr);
            conflatedAttribute.data_types.push(attr.data_type);

            if (conflatedAttribute.data_type !== attr.data_type) {
                conflatedAttribute.data_type = null;
            }

            getAggregateNames().forEach(aggregateName => {
                conflatedAttribute[getAggregateValuesKey(aggregateName)].push(attr[aggregateName]);
                if ($scope.aggregateDataTypeFields.aggregates[aggregateName].type === 'multiselect') {
                    if (!stringArraysEqual(conflatedAttribute[aggregateName], attr[aggregateName])) {
                        conflatedAttribute[aggregateName] = [];
                    }
                    return;
                }
                if (conflatedAttribute[aggregateName] !== attr[aggregateName]) {
                    conflatedAttribute[aggregateName] = null;
                }
            });

            // Check categories are identical
            if (conflatedAttribute.conflicting_categories || !arraysEqual(conflatedAttribute.category_names, attr.category_names)) {
                conflatedAttribute.category_names = [];
                conflatedAttribute.conflicting_categories = true;
            }
        }

        function conflateAttributes(groupProperty) {
            return (acc, attr) => {
                const groups = getGroups(attr, groupProperty);
                for (const group of groups) {
                    if (!acc[group.key]) {
                        acc[group.key] = initConflatedAttribute(attr, group);
                    }
                    updateConflatedAttribute(acc[group.key], attr);
                }
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

        function buildAggregatedAttributes(attributes, groupProperty) {
            let deduplicatedAttributes = Object.values(attributes.reduce(conflateAttributes(groupProperty), {})).map(conflatedAttribute => {
                if ($scope.ui.onlyDisplayCommon && conflatedAttribute.parent_elements.length < $scope.ui.clickedNodes.length) {
                    conflatedAttribute.isDisplayed = false;
                }
                return conflatedAttribute;
            });
            return Object.values(deduplicatedAttributes.reduce(groupAttributesIntoSections(), {}));
        }

        function splitAttributesOnProperty(splitProperty) {
            const attributes = $scope.attributeList;
            return {
                attributesWithProperty: attributes.filter((attribute) => attribute?.[splitProperty]),
                attributesWithoutProperty: attributes.filter((attribute) => !attribute?.[splitProperty])
            };
        }

        function buildGroupedAttributesResult(attributes, groupProperty) {
            const groups = buildAggregatedAttributes(attributes, groupProperty);
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

        $scope.buildGroupedAttributes = function(grouping) {
            const splitAttributes = splitAttributesOnProperty('template_name');
            return {
                attributesWithProperty: buildGroupedAttributesResult(
                    splitAttributes.attributesWithProperty,
                    grouping.groupProperty
                ),
                attributesWithoutProperty: buildGroupedAttributesResult(
                    splitAttributes.attributesWithoutProperty,
                    grouping.fallbackGroupProperty
                )
            };
        }

        function getGrouping() {
            let groupProperty = 'template_name';
            if ($scope.groupMode === GroupMode.CATEGORY) {
                groupProperty = 'category_names';
            }
            return {
                groupProperty: groupProperty,
                fallbackGroupProperty: 'parent_element',
            }
        }

        $scope.getAttributeTableTitle = function(fallback=false) {
            if (fallback) {
                return "Elements";
            }
            if ($scope.groupMode === GroupMode.CATEGORY) {
                return "Categories";
            }
            return "Templates";
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

        $scope.refreshAttributeSection = function() {
            const grouping = getGrouping();
            const groupedAttributes = $scope.buildGroupedAttributes(grouping)
            $scope.groupedAttributes = groupedAttributes.attributesWithProperty;
            $scope.groupedAttributesFallbackGrouping = groupedAttributes.attributesWithoutProperty;
            console.log("Attribute List", $scope.attributeList)
            console.log("Grouped attributes", $scope.groupedAttributes)
            console.log("Grouped fallback attributes", $scope.groupedAttributesFallbackGrouping)
        }

        $scope.addAttributeToSelection = function(attribute) {
            const index = $scope.config.outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);
            if (index !== -1) {
                console.warn("Cannot add attribute to selection because already present", attribute);
                return;
            }
            attribute.checked = true;
            $scope.config.outputSelectedAttributes.push(attribute);
            $scope.selectedElementPaths = buildSelectedElementPaths();
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
            $scope.selectedElementPaths = buildSelectedElementPaths();
            $scope.refreshAttributeSection();
            console.log("Removed attribute from selection", attribute);
        }

        $scope.updateAttributeInSelection = function(attribute) {
            const index = $scope.config.outputSelectedAttributes.findIndex(attr => attr.path === attribute.path);
            if (index === -1) {
                console.warn("Cannot update attribute in selection because not present", attribute);
                return;
            }
            $scope.config.outputSelectedAttributes[index] = attribute;
            $scope.selectedElementPaths = buildSelectedElementPaths();
        }

        async function addAttributeToLoadedAttributes(attribute) {
            return $scope.cache.addOrUpdateAttribute(attribute);
        }

        $scope.changeGroupingMode = function(mode) {
            if (mode === 'TEMPLATE') {
                $scope.groupMode = GroupMode.TEMPLATE;
            } else {
                $scope.groupMode = GroupMode.CATEGORY;
            }
            $scope.refreshAttributeSection();
        }

    }]);


app.component('treeNode', {
    bindings: {
        node: '=',
        getChildrenFromDb: '<',
        toggleDisplayAttributes: '<',
        clickedNodes: '<',
        config: '<',
        toggleNodeVisualization: '&',
        selectedElementPaths: '<'
    },

    controllerAs: 'ctrl',

    controller: function() {
        const ctrl = this;

        ctrl.showBreadcrumb = function(node) {
            if (ctrl.showPaperclip(node)) {
                return false;
            }
            return node?.paths?.some(path => {
                return ctrl.selectedElementPaths.some(selectedPath => selectedPath.startsWith(path))
            });
        };

        ctrl.showPaperclip = function(node) {
            return node?.paths?.some(path => ctrl.selectedElementPaths.includes(path));
        };

        ctrl.hasRenderableChildren = function(node) {
            if (!node || !Array.isArray(node.children) || !node.children.length) {
                return false;
            }
            return true;
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
            return ctrl.clickedNodes.includes(node.url);
        };

        ctrl.isSearchResult = function(node) {
            return !!node.searchHighlighted;
        };
    },
    templateUrl: "/plugins/pi-system/resource/tree-node.html"
});

app.directive('attributeTableBlock', function() {
    return {
        restrict: 'A',
        scope: {
            title: '<',
            activeTab: '<',
            displayElementDropdown: '<',
            displayPath: '<',
            excludedColumns: '<',
            groupMode: '<',
            elementsByTemplate: '<',
            groupedAttributes: '=',
            config: '=',
            aggregateDataTypeFields: '<',
            onToggleSelectAllGroupedAttributes: '&',
            onToggleGroupedAttributes: '&',
            onIsAtLeastPartiallySelected: '&',
            onInitElementsDropdown: '&',
            onIsTemplateAssociatedElementSelected: '&',
            onApplyClickElementsDropdown: '&',
            onCheckAttribute: '&',
            onUpdateDataType: '&',
            onUpdateAggregate: '&'
        },
        bindToController: true,
        controller: function() {},
        controllerAs: 'ctrl',
        templateUrl: "/plugins/pi-system/resource/attribute-table-block.html"
    };
});

// TODO: see if cleaner architecture
app.directive('attributeTableRow', function() {
    return {
        restrict: 'A',
        scope: {
            groupMode: '<',
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
            const ctrl = this;

            ctrl.showPartialCheckInfo = function() {
                return ctrl.mergedAttribute.checked === CheckboxStatus.PARTIAL_CHECK;
            }

            ctrl.generatePartialStateInfo = function() {
                const listParentElements = ctrl.mergedAttribute.attributes.reduce((acc, attr) =>
                    {
                        if (attr.checked) {
                            acc.push(attr.parent_element);
                        }
                        return acc;
                    }
                , []);
                const stringParentElements = listParentElements.join(', ');
                return 'Already selected for elements: ' + stringParentElements;
            }
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
app.component('dropdownElements', {
    bindings: {
        elements: '<',
        groupName: '<',
        initElementsDropdown: '&',
        isTemplateAssociatedElementSelected: '&',
        applyClickElementsDropdown: '&',
        activeTab: '<',
    },
    controllerAs: 'ctrl',
    controller: function() {
        const ctrl = this;
        ctrl.templatedModeUnselectedElements = [];

        ctrl.$onInit = function() {

            ctrl.onClick = function() {
                if (ctrl.elements?.length > 0) {
                    return;
                }

                ctrl.initElementsDropdown({ templateName: ctrl.groupName });
            }

            ctrl.onClickElement = function(element, $event) {
                $event.stopPropagation();

                let wasUnselected;
                if (ctrl.activeTab === 'template') {
                    wasUnselected = ctrl.templatedModeUnselectedElements.includes(element.url);
                    if (wasUnselected) {
                        ctrl.templatedModeUnselectedElements = ctrl.templatedModeUnselectedElements.filter(url => url !== element.url);
                    } else {
                        ctrl.templatedModeUnselectedElements.push(element.url)
                        console.log("ctrl.templatedModeUnselectedElements", ctrl.templatedModeUnselectedElements)
                        console.log("ctrl.elements", ctrl.elements)
                        if (ctrl.templatedModeUnselectedElements.length === ctrl.elements.length) {
                            console.log("empty dropdown")
                        }
                    }
                } else {
                    wasUnselected = ctrl.isTemplateAssociatedElementSelected({ element: element });
                }
                ctrl.applyClickElementsDropdown({
                    templateName: ctrl.groupName,
                    element: element,
                    wasUnselected: wasUnselected
                })
            }

            ctrl.isElementSelected = function(element) {
                if (ctrl.activeTab === 'element') {
                    return ctrl.isTemplateAssociatedElementSelected({element: element});
                } else {
                    return !ctrl.templatedModeUnselectedElements.includes(element.url);
                }
            }

            ctrl.getSelectedElementsCount = function() {
                return ctrl.elements.filter(element => ctrl.isElementSelected(element)).length;
            }

            ctrl.visualized = function(element) {
                return ctrl.isElementSelected(element);
            }

            ctrl.notVisualized = function(element) {
                return !ctrl.isElementSelected(element);
            }
        }
    },
    templateUrl: "/plugins/pi-system/resource/dropdown-elements.html"
});
