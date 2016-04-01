'use strict';

angular.module('angularFlaskServices', ['ngResource'])
	.factory('Post', function($resource) {
		return $resource('/api/post/:postId', {}, {
			query: {
				method: 'GET',
				params: { postId: '' },
				isArray: true
			}
		});
	})
;

angular.module('angularFlaskServices', ['ngResource'])
	.factory('GlobalProjectFolderService', function($http) {
	    var getProjects = function() {
	        return $http({method:"GET", url:"/project_folders"}).then(function(response){
	            return response.data.project_folders;
	        });
	    };
	    var selected_project_folder;

		return {
		    project_folders: function() {
		    	return getProjects();
		    },
		    selected_project_folder: selected_project_folder,
		    select: function(data) {
		    	selected_project_folder = data;
		    }
		};
	})
;

// angular.module('angularFlaskServices', [])
// 	.factory('GlobalProjectFolderService', function() {

// 		project_folders = []
// 		// $http({
// 		//   method: 'GET',
// 		//   url: '/project_folders'
// 		// }).then(function successCallback(response) {
// 		// 	project_folders = response.data.project_folders;

// 		// 	return global_project_folder;
// 		//   }, function errorCallback(response) {
// 		// 		console.log(response);
// 		//   });

// 		var global_project_folder = {
// 			selected_folder: null
// 			folders = project_folders;
// 		};

// 		return global_project_folder;
// 	})
// ;