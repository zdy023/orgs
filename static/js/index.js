"use strict";

var vm = new Vue({
  el: '#app',
  data: {
    route: '/',
    user: $user,
    alert_visible: false,
    dialog: {
      visible: false,
      title: "",
      callback: null,
    },
    metadata: {
      alertTypes: {
        "200": "success",
        "1": "info",
        "403": "warning",
        "400": "error",
        "-1": "error"
      },
    },
    alert: null,
    curTab: 0,
    tabs: [],
  },
  filters: {
    date: function(datei) {
      var a = new Date(datei), m = a.getMonth() + 1;
      return a.getFullYear() + "-" + (100+m+"").substr(1) + "-" + (100+a.getDate()+"").substr(1);
    }
  },
  watch: {
    alert: function(i) {
      this.alert_visible = i ? true : false;
      if (i && i.trace) {
        console.log("%c%s", "color: darkred;", i.trace.join("\n"));
        i.trace = null;
      }
    }
  },
  methods: {
    showDialog: function(callback, title) {
      var diag = this.dialog;
      diag.title = title;
      diag.callback = callback;
      diag.visible = true;
    },
    closeDialog: function(pass) {
      var diag = this.dialog, cb = diag.callback;
      diag.callback = null;
      diag.visible = false;
      if (!pass) {
        return;
      }
      cb.call(this, {confirmed: true});
    },
    switchPanel: function(key) {
      if (!key) { return; }
      if (key.indexOf("://") > 0 || key.lastIndexOf("/", 0) === 0) {
        if (key.lastIndexOf("/admin/", 0) === 0 && key.length > 7 && key.indexOf("?") < 0) {
          key += "?" + $.param({next: location.href.substring(location.pathname + location.search)});
        }
        location.href = key;
        return;
      }
      this.route = key;
      location.hash = '#' + key;
    },
    gotoUser: function(user_or_job) {
      window.location.href = "/" + user_or_job.card;
    },
    gotoJob: function(job) {
      console.log('gotojob', job);
      var job_id = job.id;
      for (var i = 0, arr = this.tabs; i < arr.length; i++) {
        if (arr[i].job.id == job_id) {
          return vm.curTab = job_id;
        }
      }
      var param = {
        id: job_id,
      };
      $.get("/api/list/job?" + $.param(param), function(data) {
        if (data.error.code !== 1) {
          var e = data.error;
          e.trace && console.log(e.trace);
          vm.alert = { message: e.code === 403 || e.code === 3 ? '权限不足' : e.message, code: e.code };
        }
        vm.alert = null;
        delete data.error;
        vm.tabs.push(data);
        vm.curTab = data.job.id;
      });
    },
    removeTab: function(tab) {
      var tabs = this.tabs, i;
      for (i = tabs.length; 0 <= --i; ) {
        if (tabs[i].job.id === tab.name) {
          tabs.splice(i, 1);
          return;
        }
      }
    }
  }
});

(function() {
  if (!$user.id) { 
    vm.alert = { message: "权限不足", code: -1 };
    return;
  }
  $.get("/api/list/main", function(data) {
    if (data.error.code !== 1) {
      var e = data.error;
      e.trace && console.log(e.trace);
      vm.alert = { message: e.code === 403 || e.code === 3 ? '权限不足' : e.message, code: -1 };
    }
    vm.alert = null;
    delete data.error;
    vm.tabs.push(data);
    vm.curTab = data.job.id;
  });
  return;
})();
