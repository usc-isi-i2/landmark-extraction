'use strict';

/** Header Controller stuff**/
// app.controller('HeaderController', ['$scope', '$rootScope','$location', '$window', '$http', 'GlobalProjectFolderService', HeaderController]);

// function HeaderController($scope, $rootScope, $location, $window, $http, GlobalProjectFolderService) {
app.controller('HeaderController', ['$scope', '$route', '$rootScope','$location', '$window', '$http', '$attrs', HeaderController]);

function HeaderController($scope, $route, $rootScope, $location, $window, $http, $attrs) {

	$rootScope.selected_project_folder = "-- Select Project --";
	$rootScope.project_filter = "";
	$rootScope.onChangeFunction = null;

	$http({method:"GET", url:"/project_folders"}).then(function(response){
        $rootScope.project_folders = response.data.project_folders;
		$rootScope.filtered_project_folders = $rootScope.project_folders;
		$scope.changeProjectFilter();
        // $rootScope.filtered_project_folders.push("+ Add New Project");
        // $rootScope.filtered_project_folders.unshift("-- Select Project --");
    });

	$scope.changeSelectedProject = function() {
		if($rootScope.filtered_project_folders != "-- Select Project --") {
			var index = $rootScope.filtered_project_folders.indexOf("-- Select Project --");
			if (index > -1) {
    			$rootScope.filtered_project_folders.splice(index, 1);
			}
		}

		if($rootScope.filtered_project_folders == "+ Add New Project") {
			$location.path('/markup');
		}

		else if($rootScope.filtered_project_folders == "-- Select Project --") {
			$location.path('/');
		}

		if($rootScope.onChangeFunction) {
			$rootScope.onChangeFunction();
		}
	}

	$scope.changeProjectFilter = function() {
		$rootScope.filtered_project_folders = ["-- Select Project --"];
		$rootScope.selected_project_folder = "-- Select Project --";

		for (var i in $rootScope.project_folders) {
			if($rootScope.filtered_project_folders.length > 35) {
				break;
			}
			if($rootScope.project_folders[i].indexOf($rootScope.project_filter) > -1) {
				$rootScope.filtered_project_folders.push($rootScope.project_folders[i]);
			}
		}
		$rootScope.filtered_project_folders.push("+ Add New Project");
	}
}


/* Controllers */

function IndexController($scope, $location, $rootScope) {
	$rootScope.onChangeFunction = function() {
		$location.path('/markup');
	};
	if($rootScope.filtered_project_folders) {
		var index = $rootScope.filtered_project_folders.indexOf("-- Select Project --");
		if (index == -1) {
			$rootScope.filtered_project_folders.unshift("-- Select Project --");
		}
	}

	$rootScope.selected_project_folder = "-- Select Project --";
}

function AboutController($scope) {
	
}

function PostListController($scope, Post) {
	var postsQuery = Post.get({}, function(posts) {
		$scope.posts = posts.objects;
	});
}

function PostDetailController($scope, $routeParams, Post) {
	var postQuery = Post.get({ postId: $routeParams.postId }, function(post) {
		$scope.post = post;
	});
}

function MarkupController($scope, $http, $window, $rootScope) {
	$scope.cancelMarkup = function() {
		//we want to force a reload because of the modal
		$window.location.href = '/';
	}

	$scope.startFormSubmit = function() {
		$('.loading').show();
		
		project_folder = $('#modal-project-name').val();
		if(!project_folder) {
			$('#modal-project-name-error').html('<div class="alert alert-danger">Enter an existing or new Project Folder!</div>');
			$('.loading').hide();
		}
		else {
			var index = $rootScope.filtered_project_folders.indexOf("-- Select Project --");
			if (index > -1) {
				$rootScope.filtered_project_folders.splice(index, 1);
			}

			var index = $rootScope.filtered_project_folders.indexOf(project_folder);
			if (index == -1) {
				$rootScope.filtered_project_folders.unshift(project_folder);
			}
			$rootScope.selected_project_folder = project_folder;
			load(project_folder);
		}		
	}

	$scope.deletedRule = function(rule_name) {
		var postdata = {
			project_folder: $rootScope.selected_project_folder,
			rule_name: rule_name
		};
		$http({
			  method: 'POST',
			  data: postdata,
			  url: '/delete_rule'
		}).then(function successCallback(response) {
		    $('#markup-data').html(JSON.stringify(response.data.markup, null, 2).split('>').join('&gt;').split('<').join('&lt;'));
		    $('#rules-data').html(JSON.stringify(response.data.rules, null, 2).split('>').join('&gt;').split('<').join('&lt;'));
		  }, function errorCallback(response) {
			console.log(response);
		  });
	}

	$scope.renamedRule = function(old_rule_name, new_rule_name) {
		var postdata = {
			project_folder: $rootScope.selected_project_folder,
			old_rule_name: old_rule_name,
			new_rule_name: new_rule_name
		};
		$http({
			  method: 'POST',
			  data: postdata,
			  url: '/rename_rule'
		}).then(function successCallback(response) {
		    $('#markup-data').html(JSON.stringify(response.data.markup, null, 2).split('>').join('&gt;').split('<').join('&lt;'));
		    $('#rules-data').html(JSON.stringify(response.data.rules, null, 2).split('>').join('&gt;').split('<').join('&lt;'));
		  }, function errorCallback(response) {
			console.log(response);
		  });
	}

	$rootScope.onChangeFunction = function() {
		if($rootScope.selected_project_folder == "+ Add New Project") {
			$window.location.href = '/markup';
		}
		else {
			$window.project_folder = $rootScope.selected_project_folder;
 			load($rootScope.selected_project_folder);
		}
	};

	if($rootScope.selected_project_folder != "+ Add New Project" && $rootScope.selected_project_folder != "-- Select Project --") {
		$window.project_folder = $rootScope.selected_project_folder;
		load($rootScope.selected_project_folder);
	}
	else {
	    $('#modal-content-start-select').modal('show');
	}
}

function ProjectsController($scope, $http, $rootScope) {
	$scope.project_folders = [];

	$scope.deleteProject = function(project_folder) {
		if (confirm('Are you sure you want to delete ' + project_folder + '?')) {
			var postdata = {
				project_folder: project_folder
			};

			$http({
			  method: 'POST',
			  data: postdata,
			  url: '/project_folder/delete'
			}).then(function successCallback(response) {
				$http({
					  method: 'GET',
					  url: '/project_folders'
					}).then(function successCallback(response) {
						$scope.project_folders = response.data.project_folders;

						$http({method:"GET", url:"/project_folders"}).then(function(response){
					        $rootScope.project_folders = response.data.project_folders;


							$rootScope.filtered_project_folders = ["-- Select Project --"];
							$rootScope.selected_project_folder = "-- Select Project --";

							for (var i in $rootScope.project_folders) {
								if($rootScope.project_folders[i].indexOf($rootScope.project_filter) > -1) {
									$rootScope.filtered_project_folders.push($rootScope.project_folders[i]);
								}
							}
							$rootScope.filtered_project_folders.push("+ Add New Project");

					        // $rootScope.project_folders.push("+ Add New Project");
					        // $rootScope.project_folders.unshift("-- Select Project --");
					    });
					  }, function errorCallback(response) {
							console.log(response);
					  });
			  }, function errorCallback(response) {
				console.log(response);
			  });
		}
	};

	$http({
		  method: 'GET',
		  url: '/project_folders'
		}).then(function successCallback(response) {
			$scope.project_folders = response.data.project_folders;
		  }, function errorCallback(response) {
				console.log(response);
		  });
}

function LearningController($scope, $http, $rootScope) {
	$scope.markup_file = '';
	$scope.results = '';
	
	$scope.runLearning = function() {
//		var postdata = {
//			urls: [$scope.url],
//			rules_file :$scope.rules_file
//		};
//		
//		$http({
//			  method: 'POST',
//			  data: postdata,
//			  url: '/extract'
//			}).then(function successCallback(response) {
//				$scope.results = JSON.stringify(response.data, undefined, 4);
//			  }, function errorCallback(response) {
//					console.log(response);
//			  });
	};
	
	$http({
		  method: 'GET',
		  url: '/markup_files'
		}).then(function successCallback(response) {
			$scope.markup_files = response.data.rules_files
		  }, function errorCallback(response) {
				console.log(response);
		  });
}

function ExtractionController($scope, $http, $window, $rootScope) {
	$scope.url = '';
	$scope.rules_file = '';
	$scope.results = '';
	$scope.results_object = {};
	$scope.results_filenames = [];
	$scope.results_keys = [];
	$scope.results_by_key = {};

	$scope.modal_page_url_error = '';
	$scope.modal_page_url = '';
	
	$scope.runExtraction = function() {
		$scope.errorMessage
		$('.loading').show();

		$scope.results = '';
		$scope.results_object = {};
		$scope.results_filenames = [];
		$scope.results_keys = [];
		$scope.results_by_key = {};

		var postdata = {
			project_folder: $rootScope.selected_project_folder
		};
		
		$window.project_folder = $rootScope.selected_project_folder;

		// var postdata = {
		// 	project_folder: $scope.rules_file
		// };
		
		// $window.project_folder = $scope.rules_file;

		$http({
			  method: 'POST',
			  data: postdata,
			  url: '/test_extraction'
			}).then(function successCallback(response) {
				$scope.results = JSON.stringify(response.data, undefined, 4);
				$scope.results_object = response.data;
				$scope.results_filenames = Object.keys($scope.results_object);

				var index = $scope.results_filenames.indexOf('__URLS__');
				if (index > -1) {
				    $scope.results_filenames.splice(index, 1);
				}
				index = $scope.results_filenames.indexOf('__SCHEMA__');
				if (index > -1) {
				    $scope.results_filenames.splice(index, 1);
				}

				for (var i = 0; i < $scope.results_filenames.length; i++) {
					var keys = Object.keys($scope.results_object[$scope.results_filenames[i]]);
					for (var j = 0; j < keys.length; j++) {
						var key = keys[j];
						if ($scope.results_keys.indexOf(key) == -1) {
							$scope.results_keys.push(key);
						}
					}
				}

				loadMarkup($scope.results_object);
			  }, function errorCallback(response) {
					$scope.errorMessage = "There was an error with your extraction!";
					$('.loading').hide();
			  });
	};

	$scope.runSingleExtraction = function() {
		$('.loading').show();
		$scope.modal_page_url_error = '';

		var postdata = {
			url: $scope.modal_page_url,
			// project_folder: $scope.rules_file
			project_folder: $rootScope.selected_project_folder
		};

		$http({
			  method: 'POST',
			  data: postdata,
			  url: '/test_extraction'
			}).then(function successCallback(response) {
				page_name = Object.keys(response.data)[0];
				$scope.results_object = JSON.parse($scope.results);

				$scope.results_object['__URLS__'][page_name] = $scope.modal_page_url;
				$scope.results_object[page_name] = response.data[page_name];

				$scope.results = JSON.stringify($scope.results_object, undefined, 4);

				$scope.results_filenames.push(page_name);

				loadSinglePage($scope.modal_page_url, response.data);

			  }, function errorCallback(response) {
					$scope.modal_page_url_error = 'Problem with URL!';
					$('.loading').hide();
			  });

	};

	$scope.addPage = function() {
		$scope.modal_page_url_error = '';
		$scope.modal_page_url = '';

		$('#modal-add-page').modal('show');
	};

	$rootScope.onChangeFunction = $scope.runExtraction;

	if($scope.selected_project_folder != '-- Select Project --' && $scope.selected_project_folder != '-- Add Project --') {
		$rootScope.onChangeFunction();
	}
	
	// $http({
	// 	  method: 'GET',
	// 	  url: '/project_folders'
	// 	}).then(function successCallback(response) {
	// 		$scope.rules_files = response.data.project_folders
	// 	  }, function errorCallback(response) {
	// 			console.log(response);
	// 	  });
}


function VisibleTestController($scope, $http, $window, $rootScope) {

	$scope.visible_tokens_pages = []
	$http({
		  method: 'GET',
		  url: '/visible_tokens_pages'
		}).then(function successCallback(response) {
			$scope.visible_tokens_pages = response.data['files'];
		  }, function errorCallback(response) {
		  });

	$scope.runTest = function() {
		$scope.results = null;
		$scope.resultsraw = null;
		$('.loading').show();
		var postdata = {
			test_string: $scope.inputvalue
		};

		$http({
			  method: 'POST',
			  data: postdata,
			  url: '/visible_tokens'
			}).then(function successCallback(response) {
				$scope.resultsraw = JSON.stringify(response.data, null, 2);
				$scope.results = response.data;
				$('.loading').hide();
			  }, function errorCallback(response) {
			  	alert("Error...???");
			  	$('.loading').hide();
			  });
	}
}