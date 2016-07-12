'use strict';

var app = angular.module('AngularFlask', ['ngRoute', 'angularFlaskServices']);

app.config(['$routeProvider', '$locationProvider',
		function($routeProvider, $locationProvider) {
		$routeProvider
		.when('/', {
			templateUrl: 'static/partials/landing.html',
			controller: IndexController
		})
		.when('/about', {
			templateUrl: 'static/partials/about.html',
			controller: AboutController
		})
		.when('/post', {
			templateUrl: 'static/partials/post-list.html',
			controller: PostListController
		})
		.when('/post/:postId', {
			templateUrl: '/static/partials/post-detail.html',
			controller: PostDetailController
		})
		/* Create a "/blog" route that takes the user to the same place as "/post" */
		.when('/blog', {
			templateUrl: 'static/partials/post-list.html',
			controller: PostListController
		})
		.when('/markup', {
			templateUrl: 'static/partials/markup.html',
			controller: MarkupController
		})
		.when('/projects', {
			templateUrl: 'static/partials/projects.html',
			controller: ProjectsController
		})
		.when('/extraction', {
			templateUrl: 'static/partials/extraction.html',
			controller: ExtractionController
		})
		.when('/learning', {
			templateUrl: 'static/partials/learning.html',
			controller: LearningController
		})
		.when('/visible_test', {
			templateUrl: 'static/partials/visible_test.html',
			controller: VisibleTestController
		})
		.otherwise({
			redirectTo: '/'
		})
		;

		$locationProvider.html5Mode({
		  enabled: true,
		  requireBase: false
		});
	}])
;