var app = angular.module("esp32App", []);
app.controller("esp32Ctrl", function($scope, $http, $interval, $timeout) {

  $scope.update = function() {
    $http.get('/mem', {timeout: 3000})
    .then( function(response) {
      $scope.r = response.data;
      var tz = new Date().getTimezoneOffset();
      var dt = $scope.r.utc.split(/[: T-]/).map(parseFloat);
      $scope.r.dt = new Date(Date.UTC(dt[0], dt[1]-1, dt[2], dt[3] || 0, dt[4] || 0, dt[5] || 0, 0) - tz * 60000).toISOString().substring(0,19).replace('T', ' ');
      $scope.r.key = [];
      $scope.r.unit = [];
      for(i=0; i<6; i++) {
        u = $scope.r.units[i];
        if (u.includes('[') && u.endsWith(']')) {
          $scope.r.key[i] = u.substring(0, u.indexOf('['));
          $scope.r.unit[i] = u.substring(u.indexOf('[')+1, u.length-1);
          if ($scope.r.unit[i] == 'C')
            $scope.r.unit[i] = "\xB0C";
        }
        else {
          $scope.r.key[i] = u;
          $scope.r.unit[i] = '';
        }
      }
    })
    .catch( function() {
    });
  }

  $interval( function() {
    $scope.update();
  }, 60000);

  $scope.update();

});
