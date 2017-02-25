"use strict";

var vm = new Vue({
  el: '#app',
  data: {
    route: '/admin',
    user: $user,
    auth: {
      jobs: [],
      cur_job: null,
      cur_job_bak: null,
      cur_type: 5,
      ori_type: 5,
    },
    admins: {
      to_mod: "",
      list: [],
    },
    employees_failed: 0,
    employee: {
      helper_job: "",
      list: [],
    },
    upload: {
      baseUrl: "/api/upload/",
      type: "l1",
      fileList: [],
    },
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
    set_job: function(value) {
      var cur = this.auth.cur_job;
      if (this.auth.cur_job_bak === cur) { return; }
      $.ajax({
        url: "/api/job/select",
        type: "post",
        data: {
          job: cur
        },
        success: function(data) {
          if (data.error.code !== 1) {
            vm.auth.cur_job = vm.auth.cur_job_bak;
            return vm.alert = data.error;
          }
          vm.auth.cur_job_bak = cur;
          var type = vm.get_type(data.job);
          vm.auth.cur_type = type;
          vm.on_job_change();
        }
      });
    },
    on_job_change: function() {
      var type = vm.auth.cur_type;
      if (type === 1) {
        vm.upload.type = "l1";
      } else if (type === 2) {
        vm.upload.type = "l2";
      } else if (type === 3) {
        vm.upload.type = "l3";
      }
    },
    set_admin: function(act) {
      if (!this.admins.to_mod) {
        return this.alert = { message: "请输入学号或者选择管理员", code: 403 };
      }
      $.ajax({
        url: "/api/job/admin/set",
        type: "post",
        data: {
          card: this.admins.to_mod,
          act: act,
        },
        success: function(data) {
          if (data.error.code !== 1) {
            return vm.alert = data.error;
          }
          vm.alert = { message: "成功", code: 1 };
          if (data.is_admin) {
            vm.admins.to_mod = "";
            vm.admins.list.unshift(data);
            return;
          }
          var i = 0, list = vm.admins.list, len = list.length;
          for (; i < len; i++) {
            if (list[i].card === data.card) {
              list.splice(i, 1);
              break;
            }
          }
        }
      });
    },
    refresh_employees: function() {
      $.get("/api/list/main", function(data) {
        if (data.error.code !== 1) {
          if (vm.employees_failed) {
            return vm.alert = data.error;
          }
          var e = data.error;
          e.trace && console.log(e.trace);
          vm.employees_failed = e.code === 403 || e.code === 3 ? '权限不足' : e.message;
        }
        delete data.error;
        vm.employee = data;
      });
    },
    set_helper: function(act) {
      if (act === 1) {
        if (!this.employee.helper_job) {
          return this.alert = { message: "请选择负责人", code: 403 };
        }
      }
      $.post("/api/job/helper/set", {
        job_id: act === 1 && this.employee.helper_job || 0,
      }, function(data) {
        if (data.error.code !== 1) {
          return vm.alert = data.error;
        }
        vm.alert = { message: "成功", code: 1 };
        if (act !== 1) {
          vm.employee.helper_job = "";
        }
      });
    },
    get_type: function(job_id) {
      if (!job_id) { return 0; }
      for (var i = 0, arr = vm.auth.jobs || []; i < arr.length; i++) {
        if (arr[i].id === job_id) {
          return arr[i].type;
        }
      }
    },
    doParse: function(file) {
      console.log(file);
      if (!confirm("您将要批量更新数据，是否继续？")) {
        return;
      }
      $.ajax({
        type: "post",
        url: '/api/excel/parse',
        data: {
          id: file.id,
        },
        success: function(data) {
          if (data.error.code !== 1) {
            return vm.alert = data.error;
          }
          vm.alert = { message: "导入数据成功", code: 1 };
          console.log(data);
          if (vm.auth.ori_type === 2) {
            vm.refresh_employees();
          }
        }
      });
    }
  }
});

(function() {
  if (!$user.id) { return; }
  $.get("/api/job/list", function(data) {
    if (data.error.code != 1) {
      data.error.code = -1;
      vm.alert = data.error;
      return;
    }
    vm.auth.ori_type = data.ori_type;
    vm.auth.jobs = data.list;
    vm.auth.cur_job_bak = data.job;
    vm.auth.cur_job = data.job;
    var type = vm.get_type(data.job);
    vm.auth.cur_type = type || 5;
    vm.on_job_change();
    vm.refresh_employees();
  }, "json");
  $user.super && $.get("/api/job/admin/list", function(data) {
    if (data.error.code !== 1) {
      return vm.alert = data.error;
    }
    vm.admins.list = data.list;
  }, "json");
  return;

$.get("/api/list/file_history?" + $.param({
  creator_id: $user.id
}), function(data) {
  if (data.error.code != 1) {
    data.error.code = -1;
    vm.alert = data.error;
    return;
  }
  vm.upload.fileList = data.list;
}, "json");
})();
