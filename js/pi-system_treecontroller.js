const app = angular.module('piSystemTreeApp.module', []);

function sortAttributeGroups(attributesGroups, reverse = false) {
    if (!attributesGroups.length) {
        return;
    }

    attributesGroups.sort((firstGroup, secondGroup) => {
        const order = firstGroup.group_name.localeCompare(secondGroup.group_name);
        return reverse ? -order : order;
    });
}

app.directive('loadingOverlay', function() {
    return {
        restrict: 'E',
        scope: {
            header: '<',
            text: '<',
            warning: '<',
            warningText: '<',
        },
        templateUrl: '/plugins/pi-system/resource/loading-overlay.html'
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
            { value: 'RecordedAtTimes', label: 'Recorded at times' },
            { value: 'InterpolatedAtTimes', label: 'Interpolated at times' },
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
        calculation_basis: {
            label: 'Calculation Basis',
            type: 'select',
            defaultValue: '',
            isVisible: function(attribute) {
                return attribute.data_type === 'SummaryData';
            },
            options: [
                { value: '', label: 'None' },
                { value: 'TimeWeighted', label: 'Time-weighted' },
                { value: 'EventWeighted', label: 'Event-weighted' },
                { value: 'TimeWeightedContinuous', label: 'Time-weighted continuous' },
                { value: 'TimeWeightedDiscrete', label: 'Time-weighted discrete' },
            ]
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
        this.dbVersion = 2
        this.attributesStoreName = "attributes"
        this.elementTreeStoreName = "elementTree"
        this.templateTreeStoreName = "templateTree"
        this.elementsByTemplateStoreName = "elementsByTemplate"
        this.elementCategoriesStoreName = "elementCategories"
        this.attributeCategoriesStoreName = "attributeCategories"
        this.stores = [
            this.attributesStoreName,
            this.elementTreeStoreName,
            this.templateTreeStoreName,
            this.elementsByTemplateStoreName,
            this.elementCategoriesStoreName,
            this.attributeCategoriesStoreName
        ]

        this.elementTreeRecordId = "elementTree"
        this.templateTreeRecordId = "templateTree"
        this.elementsByTemplateRecordId = "elementsByTemplate"
        this.elementCategoriesRecordId = "elementCategories"
        this.attributeCategoriesRecordId = "attributeCategories"
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

    async getElementCategories() {
        return this.getObject(this.elementCategoriesStoreName, this.elementCategoriesRecordId).then((data) => data?.nodes);
    }

    async getAttributeCategories() {
        return this.getObject(this.attributeCategoriesStoreName, this.attributeCategoriesRecordId).then((data) => data?.nodes);
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

    async addOrUpdateElementCategories(elementCategories) {
        return this.addOrUpdate({
                id: this.elementCategoriesRecordId,
                nodes: elementCategories
        }, this.elementCategoriesStoreName);
    }

    async addOrUpdateAttributeCategories(attributeCategories) {
        return this.addOrUpdate({
                id: this.attributeCategoriesRecordId,
                nodes: attributeCategories
        }, this.attributeCategoriesStoreName);
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
    '$timeout',
    '$window',
    'CreateModalFromTemplate',
    function($scope, $stateParams, $q, $timeout, $window, CreateModalFromTemplate) {

        $scope.paramDesc = {
            'parameterSetId': 'basic-auth',
            'mandatory': true
        };

        $scope.attributeList = []; // The list of attributes that are currently displayed in the main panel
        $scope.config.outputSelectedAttributes = $scope.config.outputSelectedAttributes || []; // The list of attributes selected by the user
        $scope.elementsByTemplate = {};
        if (typeof $scope.config.displayLongestPath === "undefined") {
            $scope.config.displayLongestPath = true;
        }

        // $scope.config.selectedTemplateNames =  []; // la liste des templates sélectionnés utilisées pour filtrer le search. Stale

        $scope.ui = {
            clickedNodes: [],
            searchMatchedElementPaths: [], // la liste pour highlighter les elements de la recherche
            attributeFiltering: {
                attributeSearch: "",
                attributeCategoryFilterList: [],
                attributeValueTypeFilter: ""
            },
            templateSearch: "",
            templateSearchResults: [],
            displayPath: false,
            onlyDisplayCommon: false,
            uiFrozen: false,
            loadingOverlay: {
                displayed: false,
                text: "",
                header: "",
                warning: "",
                warningText: ""
            }
        };

        $scope.callInProgress = false;
        let activeLoadingStates = 0;
        let loadingOverlayTimeout = null;
        let loginModalOpen = false;

        function warnBeforeLeavingDuringLoading(event) {
            if (!$scope.ui.uiFrozen) {
                return;
            }
            event.preventDefault();
            event.returnValue = '';
        }

        $window.addEventListener('beforeunload', warnBeforeLeavingDuringLoading);
        $scope.$on('$destroy', function() {
            $window.removeEventListener('beforeunload', warnBeforeLeavingDuringLoading);
        });
        $scope.$on('$stateChangeStart', function(event) {
            if (!$scope.callInProgress) {
                return;
            }

            if (!$window.confirm('Setup is still in progress. Select Cancel to stay on this page.')) {
                event.preventDefault();
            }
        });

        $scope.attributeCategoryFilterOptions = [];

        $scope.showTreeData = false;
        $scope.errorBannerVisible = false;
        $scope.errorBannerMessage = '';

        $scope.aggregateDataTypeFields = aggregateDataTypeFields;
        $scope.elementSearchNoMatch = false;

        $scope.selectedElementPaths = buildSelectedElementPaths()

        $scope.inSearchMode = false;
        $scope.search = {
            searchMode: 'element',
            searchString: '',
            elementCategoryFilterList: [],
            elementTemplateFilter: '',
            attributeCategoryFilterList: [],
            attributeValueTypeFilter: '',
            searchResults: [],
            attributeResults: [],
            attributeSearchCurrentPage: 0,
            attributeLastPage: null,
            nextAttributeResultsPage: null,
            groupedAttributeResults: null,
            groupedAttributeResultsFallbackGrouping: null
        };

        $scope.valueTypes = Object.freeze(["Boolean", "Byte", "DateTime", "Double", "Guid", "Int16", "Int32", "Int64", "Single", "String"])

        function flattenTemplateTree(templateTree) {
            return (templateTree || []).flatMap((template) => [
                template,
                ...flattenTemplateTree(template.children)
            ]);
        }

        function rebuildTemplateList() {
            $scope.templateList = flattenTemplateTree($scope.templateTree);
        }

        $scope.toggleSearchMode = function(clickedSearchButton) {
            if (clickedSearchButton === $scope.inSearchMode) {
                return;
            }
            clearSearchHighlights($scope.elementTree); // Clearing search hightlights on leaving search mode
            $scope.inSearchMode = !$scope.inSearchMode;
        }

        function buildSelectedElementPaths() {
            return $scope.config.outputSelectedAttributes.flatMap(attribute => attribute.paths).map(getElementPathFromAttributePath);
        }

        $scope.showDatasetPreviewModal = function() {
            const modalScope = $scope.$new();
            modalScope.ui = {
                previewAttributeSearch: ""
            };

            function rebuildGroupedSelectedAttributes() {
                if (!$scope.config.outputSelectedAttributes) {
                    return;
                }
                const groupedAttributes = $scope.buildGroupedAttributes(
                    getGrouping(),
                    $scope.config.outputSelectedAttributes,
                    {
                        attributeSearch: modalScope.ui.previewAttributeSearch,
                        attributeCategoryFilterList: [],
                        attributeValueTypeFilter: ''
                    },
                    false
                );
                modalScope.groupedSelectedAttributes = groupedAttributes.attributesWithProperty;
                modalScope.groupedSelectedAttributesFallBackGrouping = groupedAttributes.attributesWithoutProperty;
                applyGroupSort(modalScope.groupedSelectedAttributes, 'previewDatasetMain');
                applyGroupSort(modalScope.groupedSelectedAttributesFallBackGrouping, 'previewDatasetFallback');
                applyGroupAttributesSort(modalScope.groupedSelectedAttributes, 'previewDatasetMain');
                applyGroupAttributesSort(modalScope.groupedSelectedAttributesFallBackGrouping, 'previewDatasetFallback');
            }


            rebuildGroupedSelectedAttributes();

            modalScope.$watchCollection(
                function() {
                    return $scope.config.outputSelectedAttributes;
                },
                rebuildGroupedSelectedAttributes
            );

            modalScope.$watch(
                function() {
                    return modalScope.ui.previewAttributeSearch;
                },
                rebuildGroupedSelectedAttributes
            );

            CreateModalFromTemplate('/plugins/pi-system/resource/pi-system_preview-dataset-modal.html', modalScope);
        };

        $scope.openLoginModal = function() {
            if (loginModalOpen) {
                return;
            }

            loginModalOpen = true;
            CreateModalFromTemplate('/plugins/pi-system/resource/pi-system_auth-banner.html', $scope, null, function(modalScope) {

                modalScope.$on('$destroy', function() {
                    loginModalOpen = false;
                });

                modalScope.login = function() {
                    if (!$scope.authConfigured()) {
                        return;
                    }

                    modalScope.dismiss();
                    initData().then(() => {
                        $scope.showTreeData = true;
                    }).catch(() => {
                        $scope.showTreeData = false;
                        $scope.errorBannerMessage = 'There was a problem fetching data';
                        $scope.errorBannerVisible = true;
                    }).finally(() => {
                        $scope.$applyAsync();
                    });
                };

                modalScope.refreshCachedTree = function() {
                    if (!$scope.authConfigured() || !$scope.showTreeData) {
                        return;
                    }

                    modalScope.dismiss();
                    $scope.refreshCachedTree();
                };
            });
        };

        $scope.isAtLeastPartiallySelected = function(node) {
            return node.checked === CheckboxStatus.CHECKED || node.checked === CheckboxStatus.PARTIAL_CHECK;
        };

        $scope.onAdvancedToggle = function() {
            // TODO: cleanup the max count things
            if (!$scope.config.show_advanced_parameters) {
                $scope.config.is_ssl_check_disabled = false;
            }
        };

        $scope.init = function() {
            $scope.config.show_advanced_parameters = $scope.config.show_advanced_parameters || false;
            $scope.activeTab = $scope.activeTab || 'element';
            $scope.templateTree = $scope.templateTree || [];
            rebuildTemplateList();
            $scope.attributeCategories = $scope.attributeCategories || [];
            $scope.elementCategories = $scope.elementCategories || [];
            $scope.groupMode = $scope.groupMode || GroupMode.TEMPLATE;
            $scope.tableState = {
                tableSortStatus: [],
                groupSortStatus: {}
            };
            $scope.closedFolds = {
                groupClosedFolds: {},
                mergedAttributeClosedFolds: {}
            };
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
                    $scope.showTreeData = true;
                }).catch(() => {
                    $scope.errorBannerMessage = 'There was a problem fetching data';
                    $scope.errorBannerVisible = true;
                    $scope.openLoginModal();
                }).then(() => {
                    $scope.$applyAsync()
                })
            } else {
                $scope.openLoginModal();
            }
            $scope.onAdvancedToggle();
        };

        $scope.getServers = function() {
            startLoadingState(false);
            $scope.callPythonDo({ parameterName: "server_name" }).then(function(data) {
                console.log("server_name", data);
                $scope.server_name = data.choices;
            }).finally(stopLoadingState);
        };
        $scope.getDatabases = function() {
            startLoadingState(false);
            $scope.callPythonDo({ parameterName: "database_name" }).then(function(data) {
                console.log("database_name", data);
                $scope.database_name = data.choices;
                $scope.config.database_title = getDatabaseTitle($scope.config.database_name);
            }).finally(stopLoadingState);
        };

        function getDatabaseTitle(databaseName) {
            const matchingDatabase = ($scope.database_name || []).find(function(database) {
                return database.value === databaseName;
            });

            return matchingDatabase?.label || null;
        }

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
                    if (!object) {
                        throw new Error(`Could not load ${scopeKey} from DB`);
                    }
                    $scope[scopeKey] = object;
                    if (fromDb) {
                        cacheSetter(object);
                    }
                });
        }

        function loadAttributeCategories() {
            return loadObject(
                () => $scope.cache.getAttributeCategories(),
                () => $scope.getAttributeCategoriesFromDB(),
                (categories) => $scope.cache.addOrUpdateAttributeCategories(categories),
                'attributeCategories',
            ).then(buildAttributeCategoryFilterOptions).catch((error) => {
                console.error("Could not load attribute categories", error);
            });
        }

        function loadElementCategories() {
            return loadObject(
                () => $scope.cache.getElementCategories(),
                () => $scope.getElementCategoriesFromDB(),
                (categories) => $scope.cache.addOrUpdateElementCategories(categories),
                'elementCategories',
            ).catch((error) => {
                console.error("Could not load element categories", error);
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
            ).then(rebuildTemplateList);
        }

        function loadElementsByTemplate() {
            return $scope.cache.getElementsByTemplate().then(elementsByTemplate => {
                $scope.elementsByTemplate =  elementsByTemplate || {}
            });
        }

        // Fetching data - only once auth has been verified
       function initData() {
           startLoadingState(true,
               "Getting everything ready",
               "The first load can take several minutes. It's a one-time process to optimize performance. Keep this tab open and come back later if you'd like.",
               "Please don't close, refresh, or leave this page while loading",
               "Leaving before the process is complete may interrupt the setup and cause errors"
           )
            return initCache().catch((error) => {
                // TODO: figure out what we want in that case
                throw new Error(`There was an error initializing cache: ${error}`);
            }).then(() => {
                return $q.all([
                    loadElementTree(),
                    loadTemplateTree(),
                    loadElementsByTemplate(),
                    loadElementCategories(),
                    loadAttributeCategories()
                ])
            }).catch((error) => {
                throw new Error(`There was an error initializing data: ${error}`);
            }).then(() => {
                $scope.$applyAsync();
            }).finally(stopLoadingState);
        }

        $scope.hasPreset = function() {
            return $scope.config.credentials?.mode && $scope.config.credentials.mode !== 'NONE' && $scope.config.credentials.name
        }

        $scope.cleanTree = function() { // utile quand on change de serveur ou de db dans la config
            $scope.resetSearch();
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
            $scope.config.database_title = null;
            $scope.templateTree = [];
            rebuildTemplateList();
            $scope.attributeCategories = [];
            $scope.elementCategories = [];
            $scope.config.loadedDatabaseName = null;
            $scope.attributeList = [];
            $scope.config.outputSelectedAttributes = [];
            $scope.selectedElementPaths = []
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        $scope.onServerChanged = function() {
            $scope.config.database_name = null;
            $scope.config.database_title = null;
            $scope.templateTree = [];
            rebuildTemplateList();
            $scope.attributeCategories = [];
            $scope.elementCategories = [];
            $scope.config.loadedDatabaseName = null;
            $scope.showTreeData = false;
            $scope.cleanTree();
            $scope.getDatabases();
        };

        $scope.onDatabaseChanged = function() {
            $scope.config.database_title = getDatabaseTitle($scope.config.database_name);
            $scope.templateTree = [];
            rebuildTemplateList();
            $scope.attributeCategories = [];
            $scope.elementCategories = [];
            $scope.config.loadedDatabaseName = null;
            $scope.showTreeData = false;
            $scope.cleanTree();
        };

        $scope.refreshCachedTree = function() {
            if (!$scope.authConfigured() || !$scope.showTreeData) {
                return;
            }
            $scope.resetSearch();
            startLoadingState(true, "Refreshing cache",
                "Refreshing the cache requires a full fetch from the database and can take several minutes. Keep this tab open and come back later if you'd like.",
                "Please don't close, refresh, or leave this page while loading",
                "Leaving before the process is complete may interrupt the database load and cause errors"
        )
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
                    $scope.getAttributeCategoriesFromDB(),
                    $scope.getElementCategoriesFromDB()
                ]);
            }).then(([elementTree, templateTree, attributeCategories, elementCategories]) => {
                $scope.elementTree = elementTree;
                $scope.templateTree = templateTree;
                rebuildTemplateList();
                $scope.attributeCategories = attributeCategories;
                buildAttributeCategoryFilterOptions();
                $scope.elementCategories = elementCategories;
                cacheElementTree();
                cacheTemplateTree();
                $scope.cache.addOrUpdateElementCategories(elementCategories);
                $scope.cache.addOrUpdateAttributeCategories(attributeCategories);
                $scope.$applyAsync();
            }).finally(stopLoadingState);
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
            startLoadingState(false);
            return $scope.callPythonDo({ method: "build_af_tree"}).then(function(data) {
                console.log("af_tree", data);
                return data.tree;
            }).finally(stopLoadingState);
        };

        $scope.getFromCacheOrFetchBaselineObjects = function() {
            $scope.cleanTree();
            return $q.all([
                $scope.getElementTreeFromDB(),
                $scope.getTemplatesFromDB(),
            ]).then(function([elementTree, templateTree]) {
                $scope.elementTree = elementTree;
                $scope.templateTree = templateTree;
                rebuildTemplateList();
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
            startLoadingState(
                true,
                "Fetching element attributes",
                "Fetching attributes for this element from the server can take a little bit of time",
                "Please don't close, refresh, or leave this page while loading",
                "Leaving before the process is complete may interrupt download and cause errors"
            );
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
                })
                .finally(stopLoadingState);
        }


        $scope.getTemplatesFromDB = function() {
            startLoadingState(false);
            return $scope.callPythonDo({ method: "get_templates_from_db" }).then(function(data) {
                console.log("get_templates_from_db", data)
                return data.choices.filter(template => template.title !== "-- Any --")
            }).finally(stopLoadingState);
        }

        $scope.onAttributeSearchKeydown = function($event) {
            if ($event.key !== "Enter") {
                return;
            }

            $event.preventDefault();
            $event.stopPropagation();
            $scope.searchAttributesInDb();
        };

        $scope.searchAttributesInDb = function(nextPage) {
            if (!$scope.search.searchString || !$scope.search.searchString.trim()) {
                return;
            }

            const isFirstLoad = !nextPage;

            if (isFirstLoad) {
                $scope.search.attributeResults = [];
                $scope.search.nextAttributeResultsPage = null;
                $scope.search.attributeSearchCurrentPage = 0;
                $scope.search.attributeLastPage = null;
            }
            startLoadingState(
                true,
                "Searching for attributes",
                "Searching for your query. Loading the attributes can take a little bit of time"
            );
            return $scope.callPythonDo({
                method: "get_attributes_per_page",
                attribute_name: $scope.search.searchString,
                element_category: $scope.search.attributeCategoryFilterList,
                attribute_value_type: $scope.search.attributeValueTypeFilter,
                next_page: nextPage,
            }).then(function(data) {
                console.log("Attribute search results", data.attributes);
                const attributes = (data.attributes || []).map(attribute => {
                    const elementPath = getElementPathFromAttributePath(attribute.path);
                    return enrichAttribute({
                        ...attribute,
                        expanded: false,
                        parent_element: getElementNameFromPath(elementPath),
                        parent_element_path: elementPath
                    }, {});
                });
                $scope.search.attributeResults.push(attributes);
                if (!isFirstLoad) {
                    $scope.search.attributeSearchCurrentPage += 1;
                }
                $scope.search.nextAttributeResultsPage = data.next_page || null;
                if (!isFirstLoad && !data.next_page) {
                    $scope.search.attributeLastPage =
                        // a checker
                        $scope.search.attributeSearchCurrentPage + 1;
                }
                refreshSearchAttributeResults();
                console.log("get_attributes_per_page", data);
            }).finally(stopLoadingState);
        };

        $scope.showPreviousAttributeSearchPage = function() {
            if ($scope.search.attributeSearchCurrentPage === 0) {
                return;
            }
            $scope.search.attributeSearchCurrentPage -= 1;
            refreshSearchAttributeResults();
        };

        $scope.showNextAttributeSearchPage = function() {
            const nextPageIndex = $scope.search.attributeSearchCurrentPage + 1;
            if ($scope.search.attributeResults[nextPageIndex]) {
                $scope.search.attributeSearchCurrentPage = nextPageIndex;
                refreshSearchAttributeResults();
                return;
            }
            if ($scope.search.nextAttributeResultsPage) {
                $scope.searchAttributesInDb($scope.search.nextAttributeResultsPage);
            }
        };

        $scope.getDisplayedAttributeResultsRange = function() {
            const currentPage = $scope.search.attributeSearchCurrentPage;
            const previousResultsCount = $scope.search.attributeResults
                .slice(0, currentPage)
                .reduce((count, page) => count + page.length, 0);
            const currentResultsCount = $scope.search.attributeResults[currentPage].length;

            return {
                start: previousResultsCount + 1,
                end: previousResultsCount + currentResultsCount
            };
        };

        $scope.getAttributeCategoriesFromDB = function() {
            startLoadingState(false);
            return $scope.callPythonDo({ method: "get_attribute_categories_from_db" }).then(function(data) {
                console.log("get_attribute_categories_from_db", data);
                return data.choices;
            }).finally(stopLoadingState);
        }

        $scope.getElementCategoriesFromDB = function() {
            startLoadingState(false);
            return $scope.callPythonDo({ method: "get_element_categories_from_db" }).then(function(data) {
                console.log("get_element_categories_from_db", data);
                return data.choices;
            }).finally(stopLoadingState);
        }

        function resetRightPanelForCurrentTabContext() {
            $scope.ui.clickedNodes = [];
            $scope.attributeList = [];
            $scope.ui.searchMatchedElementPaths = [];
            $scope.ui.attributeFiltering.attributeSearch = "";
            $scope.ui.templateSearch = "";
            $scope.elementSearchNoMatch = false;
            if ($scope.activeTab === "template") {
                $scope.config.element_name = "";
            }
            $scope.refreshAttributeSection();
        }

        $scope.resetSearch = function() {
            $scope.search.searchString = ''
            $scope.search.elementCategoryFilterList = []
            $scope.search.elementTemplateFilter = ''
            $scope.search.attributeCategoryFilterList = []
            $scope.search.attributeValueTypeFilter = ''
            $scope.search.searchResults = []
            $scope.search.attributeResults = []
            $scope.search.attributeSearchCurrentPage = 0
            $scope.search.attributeLastPage = null
            $scope.search.nextAttributeResultsPage = null
            $scope.search.groupedAttributeResults = null
            $scope.search.groupedAttributeResultsFallbackGrouping = null
            clearSearchHighlights($scope.elementTree);
        }

        $scope.setTab = function(tab) {
            clearSearchHighlights($scope.elementTree); // Clearing highlights on change mode
            const previousTab = $scope.activeTab;
            if (tab !== previousTab) {
                resetRightPanelForCurrentTabContext();
                $scope.resetSearch();
            }
            $scope.activeTab = tab;
            $timeout(function() {
                $scope.search.searchMode = tab;
            });
        };

        $scope.doSearch = function(element_name) {
            $scope.ui.searchInProgress = true;
            $scope.ui.searchMatchedElementPaths = [];
            startLoadingState(false);
            return $scope.callPythonDo({ method: "do_search", element_name: element_name, elementTree: $scope.elementTree }).then(
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
            ).finally(stopLoadingState);
        };

        function clearSearchHighlights(nodes) {
            if (!nodes) {
                return;
            }
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
            startLoadingState(true, "Fetching attributes", "Fetching attributes from the server can take a little bit of time");
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
            ).finally(stopLoadingState);
        }

        $scope.isTemplateAssociatedElementSelected = function(element) {
            return $scope.ui.clickedNodes.includes(element.url);
        }

        $scope.getElementsForTemplate = function (templateName) {
            startLoadingState(false);
            return $scope.callPythonDo({ method: "get_elements_for_template", template_name: templateName}).then(
                function(data) {
                    console.log("get_elements_for_template", data);
                    $scope.elementsByTemplate[templateName] = data.elements;
                    cacheElementsByTemplate();
                }
            ).finally(stopLoadingState);
        }

        $scope.templateModeExcludedAttributes = {};

        $scope.initElementsDropdown = async function(templateName) {
            const existingElements = $scope.elementsByTemplate[templateName];
            if (Array.isArray(existingElements)) {
                return existingElements.map(element => element.url);
            }
            await $scope.getElementsForTemplate(templateName);
            return $scope.elementsByTemplate[templateName].map(element => element.url);
        }

        // FIXME: the parent_element_path is not properly present !!! probably because loaded from cache
        // should be properly populated f we want the condition l835 to populate
        // TODO: check if fixme is up to date
        $scope.applyClickElementsDropdown = function(templateName, element, wasUnselected) {
            $scope.$applyAsync(() => {
                // TODO: redo everything by templateID
                if ($scope.activeTab === 'element') {
                    $scope.toggleNodeVisualization(element);
                } else if ($scope.activeTab === 'template') {
                    if (!wasUnselected) {
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
            clearSearchHighlights($scope.elementTree);
            console.log("clicked on ", node)

            const indexClickedNode = $scope.ui.clickedNodes.indexOf(node.url);
            const nodeAlreadySelected = indexClickedNode > -1;
            // If the node is already clicked, remove it from clicked nodes - else add it
            if (nodeAlreadySelected) {
                $scope.ui.clickedNodes.splice(indexClickedNode, 1);
            } else {
                $scope.ui.clickedNodes.push(node.url);
            }

            // In element node, the visualized nodes are reflected on the elements dropdown
            console.log("clickedNodes: " + JSON.stringify($scope.ui.clickedNodes));

            return $scope.toggleDisplayAttributes(node, !nodeAlreadySelected).then(() => {
                $scope.refreshAttributeSection();
                // Necessary because no digest cycle triggered for awaited cache reads
                $scope.$applyAsync();
            });
        };

        function nodeMatchesSearch(searchText, name, categoryNames, templateName) {
            const selectedCategories = $scope.search.elementCategoryFilterList;
            const selectedTemplate = $scope.search.elementTemplateFilter;
            const hasCategoryFilters =
                $scope.search.searchMode === 'element' && selectedCategories.length > 0;
            const hasTemplateFilter =
                $scope.search.searchMode === 'element' && !!selectedTemplate;
            if (!searchText && !hasCategoryFilters && !hasTemplateFilter) {
                return false;
            }
            const matchesName = !searchText || name.toLowerCase().includes(searchText.toLowerCase());
            const matchesCategories = !hasCategoryFilters || selectedCategories.every((category) => categoryNames.includes(category));
            const matchesTemplate = !hasTemplateFilter || templateName === selectedTemplate;
            return matchesName && matchesCategories && matchesTemplate;
        }

        $scope.prettifyElementPath = function(elementPath, paths, isAttributePath=false, cutEndElement=false) {
            if (paths && paths.length > 1 && $scope.config.displayLongestPath) {
                elementPath = paths.reduce((longestPath, path) =>
                    path.length > longestPath.length ? path : longestPath
                );
            }
            if (isAttributePath) {
                elementPath = getElementPathFromAttributePath(elementPath);
            }
            const pathParts = elementPath.split('\\').filter(Boolean);
            const databaseIndex = pathParts.indexOf($scope.config.database_title);

            if (databaseIndex === -1) {
                return pathParts.join(" > ");
            }

            if (cutEndElement) {
                return pathParts.slice(databaseIndex + 1, -1).join(" > ");
            }
            return pathParts.slice(databaseIndex + 1).join(" > ");
        }


        function addMatchingObjectsToSearchResults(nodeList, resultArray, parentList) {
            nodeList.forEach((node) => {
                if (nodeMatchesSearch($scope.search.searchString, node.title, node.category_names, node.template_name)) {
                    // Handling weak links
                    if (resultArray[node.id]) {
                        resultArray[node.id].parentList.push(parentList);
                        resultArray[node.id].nodes.push(node);
                    } else {
                        resultArray[node.id] = {
                            nodes: [node],
                            parentList: [parentList]
                        };
                    }
                }
                if (node.children.length > 0) {
                    addMatchingObjectsToSearchResults(
                        node.children,
                        resultArray,
                        parentList.concat(node)
                    );
                }
            })
        }

        $scope.applySearch = function() {
            if ($scope.search.searchMode === 'attribute') {
                return;
            }
            clearSearchHighlights($scope.elementTree);
            // console.log("$scope.templateTree", $scope.templateTree)
            const searchTree = $scope.search.searchMode === 'element' ? $scope.elementTree : $scope.templateTree;
            $scope.search.searchResults = {};
            addMatchingObjectsToSearchResults(searchTree, $scope.search.searchResults, []);
        }

        $scope.hasSearchResults = function() {
            return Object.keys($scope.search.searchResults || {}).length > 0;
        };

        $scope.hasSearchCriteria = function(searchType) {
            const hasSearchString = Boolean($scope.search.searchString.trim());
            if (searchType === 'element') {
                return hasSearchString ||
                    $scope.search.elementCategoryFilterList.length > 0 ||
                    Boolean($scope.search.elementTemplateFilter);
            }
            return hasSearchString;
        };

        $scope.areAllSearchResultsSelected = function() {
            const results = Object.values($scope.search.searchResults || {});
            return results.length > 0 && results.every((result) =>
                $scope.ui.clickedNodes.includes(result.nodes[0].url)
            );
        };

        $scope.getSearchResultCount = function() {
            return Object.keys($scope.search.searchResults || {}).length;
        };

        $scope.selectAllResults = async function() {
            for (const result of Object.values($scope.search.searchResults)) {
                const node = result.nodes[0];
                if (!$scope.ui.clickedNodes.includes(node.url)) {
                    await $scope.toggleNodeVisualization(node);
                }
            }
        }

        function openSearchResultInTree(parentNodeLists) {
            // Multiple parent node lists because of weak links
            parentNodeLists.forEach((parentNodeList) => {
                parentNodeList.forEach((node) => {
                    node.expanded = true;
                })
            })
        }

        function highlightSearchResult(nodes) {
            nodes.forEach((node) => node.searchHighlighted = true);
        }

        $scope.targetSearchResult = function(result) {
            clearSearchHighlights($scope.elementTree);
            openSearchResultInTree(result.parentList);
            highlightSearchResult(result.nodes);

            $timeout(function() {
                const targetUrl = result.nodes[0].url;
                const targetRow = Array.prototype.find.call(
                    document.querySelectorAll('.tree-node__row'),
                    function(row) {
                        return row.dataset.nodeUrl === targetUrl;
                    }
                );

                if (targetRow) {
                    targetRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
        }

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

        $scope.checkSingleAttribute = function(attribute) {
            if (attribute.checked) {
                $scope.addAttributeToSelection(attribute);
            } else {
                $scope.removeAttributeFromSelection(attribute);
            }
            $scope.refreshAttributeSection();
        };

        $scope.updateSingleAttributeDataType = function(attribute) {
            resetAggregate(attribute);
            if (attribute.checked) {
                $scope.updateAttributeInSelection(attribute);
            }
            $scope.refreshAttributeSection();
        };

        $scope.updateSingleAttributeAggregate = function(attribute) {
            if (attribute.checked) {
                $scope.updateAttributeInSelection(attribute);
            }
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

        function attributeMatchesFiltering(searchFilters, attribute, group_name) {
            const matchesCategoryFilters = attributesMatchesCategoryFilters(
                attribute.category_names,
                searchFilters.attributeCategoryFilterList
            );
            const matchesValueTypeFilter =
                !searchFilters?.attributeValueTypeFilter ||
                attribute?.value_type === searchFilters.attributeValueTypeFilter;
            const matchesTextSearch = attributeMatchesSearch(
                searchFilters.attributeSearch, attribute.title, group_name, attribute.description
            );
            return matchesValueTypeFilter && matchesCategoryFilters && matchesTextSearch;
        }

        function attributeMatchesSearch(searchText, attribute_name, group_name, attribute_description="") {
            if (!searchText) {
                return true;
            }
            const lowercasedSearch = searchText.toLowerCase();
            const groupNameMatches = group_name.toLowerCase().includes(lowercasedSearch);
            const attributeNameMatches = attribute_name.toLowerCase().includes(lowercasedSearch);
            let attributeDescriptionMatches = false;
            if (attribute_description) {
                attributeDescriptionMatches = attribute_description.toLowerCase().includes(lowercasedSearch);
            }
            return (groupNameMatches || attributeNameMatches || attributeDescriptionMatches)
        }

        function attributesMatchesCategoryFilters(attributeCategories, attributeCategoryFilterList) {
            if (!attributeCategoryFilterList || attributeCategoryFilterList.length === 0) {
                return true;
            }
            if (!attributeCategories || attributeCategories.length === 0) {
                return false;
            }
            return attributeCategoryFilterList.every((category) => {
                return attributeCategories.includes(category);
            });
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
        function getGroups(attr, groupingKey, titleKey) {
            const groupingPropertyValue = attr[groupingKey];
            const groupTitles = attr[titleKey];
            if (groupingKey === "category_names"){
                // category_names is an array
                return groupingPropertyValue.map(( value, index ) => {
                    const differentiatingKey = attr.template_name ? attr.template_name : attr.parent_element_path;
                    return {
                        key: value + "::" + differentiatingKey + "::" + attr.title,
                        sectionKey: value,
                        value: value,
                        getConflatedAttributeKey: (attribute) => differentiatingKey + "::" + attr.title
                    };
                });
            }
            return [ {
                //
                key: groupingPropertyValue + "::" + attr.title,
                sectionKey: groupingPropertyValue,
                value: groupTitles,
                path: groupingPropertyValue,
                getConflatedAttributeKey: (attribute) => attribute.title
            } ];
        }

        function initConflatedAttribute(attr, group, searchFilters) {
            const conflatedAttribute = {
                key: group.getConflatedAttributeKey(attr),
                title: attr.title,
                description: attr.description,
                group: group.value,
                group_key: group.key,
                section_key: group.sectionKey,
                group_path: group.path,
                template_name: attr.template_name,
                parent_elements: [],
                checked: null, // Used to determine UI checkbox state
                allChecked: attr.checked,
                attributes: [],
                checkStates: [],
                paths: [],
                data_type: attr.data_type,
                data_types: [],
                isDisplayed: attributeMatchesFiltering(searchFilters, attr, group.value),
                category_names: attr.category_names,
                conflicting_categories: false,
                value_type: attr.value_type,
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

        function conflateAttributes(groupingKey, titleKey, searchFilters) {
            return (acc, attr) => {
                const groups = getGroups(attr, groupingKey, titleKey);
                for (const group of groups) {
                    if (!acc[group.key]) {
                        acc[group.key] = initConflatedAttribute(attr, group, searchFilters);
                    }
                    updateConflatedAttribute(acc[group.key], attr);
                }
                return acc
            }
        }

        function groupAttributesIntoSections() {
            return (acc, attr) => {
                const key = attr.section_key;
                if (!acc[key]) {
                    acc[key] = {
                        group_name: attr.group,
                        group_key: key,
                        group_path: attr.group_path,
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

        function buildAggregatedAttributes(attributes, groupingKey, titleKey, searchFilters, onlyDisplayCommonAttributes) {
            let deduplicatedAttributes = Object.values(attributes.reduce(conflateAttributes(groupingKey, titleKey, searchFilters), {})).map(conflatedAttribute => {
                if (onlyDisplayCommonAttributes && conflatedAttribute.parent_elements.length < $scope.ui.clickedNodes.length) {
                    conflatedAttribute.isDisplayed = false;
                }
                return conflatedAttribute;
            });
            return Object.values(deduplicatedAttributes.reduce(groupAttributesIntoSections(), {}));
        }

        function splitAttributesOnProperty(attributes, splitProperty) {
            function hasGroupingValue(attribute) {
                const value = attribute?.[splitProperty];
                if (Array.isArray(value)) {
                    return value.length > 0;
                }
                return !!value;
            }
            return {
                attributesWithProperty: attributes.filter(hasGroupingValue),
                attributesWithoutProperty: attributes.filter((attribute) => !hasGroupingValue(attribute))
            };
        }

        function buildGroupedAttributesResult(attributes, groupingKey, titleKey, searchFilters, onlyDisplayCommonAttributes) {
            const groups = buildAggregatedAttributes(attributes, groupingKey, titleKey, searchFilters, onlyDisplayCommonAttributes);
            const displayedGroups = groups.filter(group => !group.isDisplayed);
            // TODO: probably turn this into a reduce
            return {
                allChecked: displayedGroups.length > 0 && displayedGroups.every(group => group.allChecked),
                checked: getCheckboxStatus(groups.reduce((acc, group) => acc.concat(group.checkStates), [])),
                // a table can be empty because all it's attributes have been filtered out OR there are no elements to show
                empty: groups.every(group => group.isDisplayed),
                groups: groups
            }
        }

        $scope.buildGroupedAttributes = function(
            grouping,
            attributes,
            searchFilters,
            onlyDisplayCommonAttributes,
        ) {
            console.log("buildGroupedAttributes", attributes)
            const splitAttributes = splitAttributesOnProperty(attributes, grouping.group.groupingKey);
            return {
                attributesWithProperty: buildGroupedAttributesResult(
                    splitAttributes.attributesWithProperty,
                    grouping.group.groupingKey,
                    grouping.group.titleKey,
                    searchFilters,
                    onlyDisplayCommonAttributes
                ),
                attributesWithoutProperty: buildGroupedAttributesResult(
                    splitAttributes.attributesWithoutProperty,
                    grouping.fallbackGroup.groupingKey,
                    grouping.fallbackGroup.titleKey,
                    searchFilters,
                    onlyDisplayCommonAttributes
                )
            };
        }

        function getGrouping() {
            return {
                group: {
                    groupingKey: $scope.groupMode === GroupMode.CATEGORY ? 'category_names' : 'template_name',
                    titleKey: $scope.groupMode === GroupMode.CATEGORY ? 'category_names' : 'template_name'
                },
                fallbackGroup: {
                    groupingKey: 'parent_element_path', // Elements can have duplicated names
                    titleKey: 'parent_element'
                },
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

        function refreshSearchAttributeResults() {
            if (!$scope.search.attributeResults) {
                return;
            }
            const currentPageAttributes =
                $scope.search.attributeResults[$scope.search.attributeSearchCurrentPage];
            updateCheckStatus(currentPageAttributes);
            const groupedAttributes = $scope.buildGroupedAttributes(
                getGrouping(),
                currentPageAttributes,
                {
                    attributeSearch: '',
                    attributeCategoryFilterList: [],
                    attributeValueTypeFilter: ''
                },
                false
            );
            $scope.search.groupedAttributeResults = groupedAttributes.attributesWithProperty;
            $scope.search.groupedAttributeResultsFallbackGrouping = groupedAttributes.attributesWithoutProperty;
            applyGroupSort($scope.search.groupedAttributeResults, 'attributeSearchResultsMain');
            applyGroupSort($scope.search.groupedAttributeResultsFallbackGrouping, 'attributeSearchResultsFallback');
            applyGroupAttributesSort($scope.search.groupedAttributeResults, 'attributeSearchResultsMain');
            applyGroupAttributesSort($scope.search.groupedAttributeResultsFallbackGrouping, 'attributeSearchResultsFallback');
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

        function buildAttributeCategoryFilterOptions() {
            $scope.attributeCategoryFilterOptions = $scope.attributeCategories?.filter((category) => category.title !== "-- Any --").map((category) => {
                const categoryName = category.title;
                const occurrencesCount = $scope.attributeList?.filter((attribute) => {
                    return Array.isArray(attribute.category_names) && attribute.category_names.includes(categoryName) ;
                }).length;

                return {
                    value: categoryName,
                    // label: categoryName + ' (' + occurrencesCount + ')'
                    label: categoryName
                };
            });
        }

        function updateCheckStatus(attributeList) {
            if (!attributeList || !$scope.config.outputSelectedAttributes) {
                return;
            }
            // checking which attributes are still in the output selection
            const selectedAttributePaths = new Set(
                $scope.config.outputSelectedAttributes.map(attribute => attribute.path)
            );
            attributeList.forEach(attribute => {
                attribute.checked = selectedAttributePaths.has(attribute.path);
            });
        }

        function applyGroupSort(groupedAttributes, identifier) {
            const sortStatus = $scope.tableState.tableSortStatus[identifier];
            if (sortStatus != null) {
                sortAttributeGroups(groupedAttributes.groups, sortStatus === 'reverse');
            }
        }

        function applyGroupAttributesSort(groupedAttributes, tableIdentifier) {
            groupedAttributes.groups.forEach(group => {
                const sortStatus = $scope.tableState.groupSortStatus[tableIdentifier]?.[group.group_key];
                if (sortStatus != null) {
                    group.attributes.sort((firstAttribute, secondAttribute) => {
                        const order = firstAttribute.title.localeCompare(secondAttribute.title);
                        return sortStatus === 'reverse' ? -order : order;
                    });
                }
            });
        }

        $scope.refreshAttributeSection = function() {
            console.log("Refresh attribute selction")
            updateCheckStatus($scope.attributeList)

            buildAttributeCategoryFilterOptions();
            const grouping = getGrouping();
            const groupedAttributes = $scope.buildGroupedAttributes(
                grouping,
                $scope.attributeList,
                $scope.ui.attributeFiltering,
                $scope.ui.onlyDisplayCommon
            )
            $scope.groupedAttributes = groupedAttributes.attributesWithProperty;
            $scope.groupedAttributesFallbackGrouping = groupedAttributes.attributesWithoutProperty;
            applyGroupSort($scope.groupedAttributes, 'attributesViewMain');
            applyGroupSort($scope.groupedAttributesFallbackGrouping, 'attributesViewFallback');
            applyGroupAttributesSort($scope.groupedAttributes, 'attributesViewMain');
            applyGroupAttributesSort($scope.groupedAttributesFallbackGrouping, 'attributesViewFallback');
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

        function startLoadingState(freezeUI, headerLoadingOverlay, textLoadingOverlay, warningLoadingOverlay, warningTextLoadingOverlay, timeoutModalSeconds) {
            activeLoadingStates += 1;
            $scope.callInProgress = true;
            if (!freezeUI) {
                return;
            }
            $scope.ui.uiFrozen = true;
            $scope.ui.loadingOverlay.displayed = false;
            $scope.ui.loadingOverlay.text = textLoadingOverlay;
            $scope.ui.loadingOverlay.header = headerLoadingOverlay;
            $scope.ui.loadingOverlay.warning = warningLoadingOverlay;
            $scope.ui.loadingOverlay.warningText = warningTextLoadingOverlay;
            if (loadingOverlayTimeout) {
                clearTimeout(loadingOverlayTimeout);
                loadingOverlayTimeout = null;
            }
            if (timeoutModalSeconds) {
                loadingOverlayTimeout = setTimeout(() => {
                    $scope.ui.loadingOverlay.displayed = true;
                    loadingOverlayTimeout = null;
                }, timeoutModalSeconds * 1000);
            } else {
                $scope.ui.loadingOverlay.displayed = true;
            }
        }

        function stopLoadingState() {
            activeLoadingStates -= 1;
            if (activeLoadingStates > 0) {
                return;
            }
            $scope.callInProgress = false;
            if (loadingOverlayTimeout) {
                clearTimeout(loadingOverlayTimeout);
                loadingOverlayTimeout = null;
            }
            $scope.ui.uiFrozen = false;
            $scope.ui.loadingOverlay.displayed = false;
            $scope.ui.loadingOverlay.text = "";
            $scope.ui.loadingOverlay.header = "";
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
        selectedElementPaths: '<',
        hideChildren: '<?'
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

        ctrl.canExpand = function(node) {
            return !ctrl.hideChildren && !!node?.has_children;
        };

        ctrl.showElementFolder = function(node) {
            return ctrl.canExpand(node) && node.type === 'element';
        };

        ctrl.toggleExpand = function(node, $event) {
            if ($event) {
                $event.stopPropagation();
            }
            if (!ctrl.canExpand(node)) {
                return;
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
                displayDetailAttributes: '<?',
                activeTab: '<',
                displayGroupPath: '<?',
                displayElementDropdown: '<',
                excludedColumns: '<',
                identifier: '@',
                groupMode: '<',
                tableState: '<',
                closedFolds: '<',
                elementsByTemplate: '<',
                groupedAttributes: '=',
                config: '=',
                aggregateDataTypeFields: '<',
                prettifyElementPath: '<',
                onToggleSelectAllGroupedAttributes: '&',
                onToggleGroupedAttributes: '&',
                onIsAtLeastPartiallySelected: '&',
                onInitElementsDropdown: '&',
                onIsTemplateAssociatedElementSelected: '&',
                onApplyClickElementsDropdown: '&',
                onCheckAttribute: '&',
                onCheckSingleAttribute: '&',
                onUpdateDataType: '&',
                onUpdateSingleDataType: '&',
                onUpdateAggregate: '&',
                onUpdateSingleAggregate: '&'
        },
        bindToController: true,
        controller: function() {
            const ctrl = this;

            ctrl.sortGroupAttributes = function(attributesGroup, tableIdentifier, groupId, reverse = false) {
                ctrl.tableState.groupSortStatus[tableIdentifier] ||= {};
                ctrl.tableState.groupSortStatus[tableIdentifier][groupId] = reverse ? 'reverse' : 'sort';
                if (!attributesGroup.length) {
                    return;
                }
                console.log("tableState", ctrl.tableState);
                attributesGroup.sort((firstAttribute, secondAttribute) => {
                    const order = firstAttribute.title.localeCompare(secondAttribute.title);
                    return reverse ? -order : order;
                });
            };

            ctrl.sortGroups = function(attributesGroups, identifier, reverse = false) {
                ctrl.tableState.tableSortStatus[identifier] = reverse ? 'reverse' : 'sort';
                console.log("tableState", ctrl.tableState);
                sortAttributeGroups(attributesGroups, reverse);
            };

            ctrl.closeGroup = function(group) {
                if (!ctrl.closedFolds.groupClosedFolds[ctrl.identifier]) {
                    ctrl.closedFolds.groupClosedFolds[ctrl.identifier] = new Set();
                }
                ctrl.closedFolds.groupClosedFolds[ctrl.identifier].add(group.group_key);
            };

            ctrl.openGroup = function(group) {
                ctrl.closedFolds.groupClosedFolds[ctrl.identifier]?.delete(group.group_key);
            };

            ctrl.isGroupFoldOpen = function(group) {
                return !ctrl.closedFolds.groupClosedFolds[ctrl.identifier]?.has(group.group_key);
            };

            ctrl.isMergedAttributeOpened = function(mergedAttributeKey) {
                return !ctrl.closedFolds.mergedAttributeClosedFolds[ctrl.identifier]?.has(mergedAttributeKey);
            };

            ctrl.getMergedAttributeFoldKey = function(mergedAttribute) {
                return mergedAttribute.group_key + "::" + mergedAttribute.title;
            };

            ctrl.getVisibleAttributeColumnCount = function(includeCheckbox) {
                let count = includeCheckbox ? 5 : 4;

                if (ctrl.groupMode !== 'CATEGORY') {
                    count += 1;
                }
                if (ctrl.groupMode !== 'TEMPLATE') {
                    count += 1;
                }

                return count;
            };
        },
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
            isSingleAttribute: '<?',
            displayDetailAttributes: '<?',
            closedFolds: '<',
            tableIdentifier: '<',
            isLast: '<',
            prettifyElementPath: '<',
            aggregateDataTypeFields: '<',
            isMergedAttributeOpened: '<',
            getMergedAttributeFoldKey: '<',
            onCheckAttribute: '&',
            onUpdateDataType: '&',
            onUpdateAggregate: '&',
        },
        bindToController: true,
        controllerAs: 'ctrl',
        controller: function() {
            const ctrl = this;

            ctrl.showPartialCheckInfo = function() {
                return !ctrl.isSingleAttribute && ctrl.mergedAttribute.checked === CheckboxStatus.PARTIAL_CHECK;
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
            };

            ctrl.closeMergedAttribute = function(mergedAttributeKey) {
                ctrl.closedFolds.mergedAttributeClosedFolds[ctrl.tableIdentifier] ||= new Set();
                ctrl.closedFolds.mergedAttributeClosedFolds[ctrl.tableIdentifier].add(mergedAttributeKey);
            };

            ctrl.openMergedAttribute = function(mergedAttributeKey) {
                ctrl.closedFolds.mergedAttributeClosedFolds[ctrl.tableIdentifier]?.delete(mergedAttributeKey);
            };

            ctrl.isGroupFoldOpen = function(group) {
                return !ctrl.closedFolds.groupClosedFolds[ctrl.tableIdentifier]?.has(group.group_key);
            };

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
        prettifyElementPath: '<',
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
