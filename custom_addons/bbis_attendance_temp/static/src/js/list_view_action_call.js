odoo.define("bbis.attendance.temp.action_button", function (require) {
  "use strict";

  var core = require("web.core");
  var ListController = require("web.ListController");
  var rpc = require("web.rpc");
  var session = require("web.session");
  var _t = core._t;
  var Dialog = require("web.Dialog");

  ListController.include({
    renderButtons: function () {
      this._super.apply(this, arguments);

      var user = session.uid;
      var $bbis_att_buttons = this.$buttons;

      if (this.modelName == 'bbis.attendance.temp'){

      rpc
        .query({
          model: "bbis.attendance.temp",
          method: "get_attendance_count",
          args: [[user], { id: user }],
        })
        .then(function (count) {
          if (parseInt(count) > 1) {
            $bbis_att_buttons
              .find(".oe_action_upload_attendance")
              .css("display", "inline-block");
            $bbis_att_buttons
              .find(".oe_action_truncate_attendance")
              .css("display", "inline-block");
//            $bbis_att_buttons
//              .find(".oe_action_compute_attendance")
//              .css("display", "inline-block");
          } else {
            $bbis_att_buttons
              .find(".oe_action_upload_attendance")
              .css("display", "none");
            $bbis_att_buttons
              .find(".oe_action_truncate_attendance")
              .css("display", "none");
          }
        });

      }

      if (this.$buttons && this.modelName == 'bbis.attendance.temp') {

//        this.$buttons
//          .find(".oe_action_compute_attendance")
//          .click(this.proxy("action_compute_bbis_attendance"));
        this.$buttons
          .find(".oe_action_upload_attendance")
          .click(this.proxy("action_upload_bbis_attendance"));
        this.$buttons
          .find(".oe_action_truncate_attendance")
          .click(this.proxy("truncate_bbis_attendance"));
        /*this.$buttons
          .find(".o_button_import")
          .click(this.proxy("import_bbis_attendance"));*/
      }
      else if (this.$buttons && this.modelName == 'hr.holidays.balance.detail') {
        this.$buttons
          .find(".oe_action_upload_leave_balance")
          .click(this.proxy("action_upload_leave_balance"));
      }


    },

    action_upload_leave_balance: function() {
      var self = this;
      var user = session.uid;
      var $bbis_att_buttons = this.$buttons;
        rpc
        .query({
          model: "hr.holidays.balance.detail",
          method: "upload_leave_balances",
          args: [[user], { id: user }],
        })
        .then(function (result) {
          if (result) {
            self._display_dialog(result);
          }
        });

    },
    /*import_bbis_attendance: function () {
      var $bbis_att_buttons = this.$buttons;
      $bbis_att_buttons.find(".oe_action_compute_attendance").css("display", "inline-block");
    },*/

    action_compute_bbis_attendance: function () {
      var self = this;
      var user = session.uid;
      var $bbis_att_buttons = this.$buttons;

      rpc
        .query({
          model: "bbis.attendance.temp",
          method: "compute_time_in_out",
          args: [[user], { id: user }],
        })
        .then(function (result) {
          self._display_dialog(result);
          self.trigger_up("reload");

          if (result.status) {
            $bbis_att_buttons
              .find(".oe_action_upload_attendance")
              .css("display", "inline-block");
            $bbis_att_buttons
              .find(".oe_action_truncate_attendance")
              .css("display", "inline-block");
//            $bbis_att_buttons
//              .find(".oe_action_compute_attendance")
//              .css("display", "none");
          }
        });
    },

    action_upload_bbis_attendance: function () {
      var self = this;
      var user = session.uid;

      rpc
        .query({
          model: "bbis.attendance.temp",
          method: "upload_attendances",
          args: [[user], { id: user }],
        })
        .then(function (result) {
          if (result) {
            self._display_dialog(result);
          }
        });
    },

    truncate_bbis_attendance: function () {
      var self = this;
      var user = session.uid;
      var $bbis_att_buttons = this.$buttons;

      //Confirmation box on click of 'Click me' button.
      Dialog.confirm(self, _t("Are you sure you want to reset attendance?"), {
        confirm_callback: function () {
          rpc
            .query({
              model: "bbis.attendance.temp",
              method: "truncate_attendances",
              args: [[user], { id: user }],
            })
            .then(function (result) {
              // self._display_dialog(result);
              self.trigger_up("reload");
              $bbis_att_buttons
                .find(".oe_action_upload_attendance")
                .css("display", "none");
              $bbis_att_buttons
                .find(".oe_action_truncate_attendance")
                .css("display", "none");
//              $bbis_att_buttons
//                .find(".oe_action_compute_attendance")
//                .css("display", "inline-block");
            });
        },
        cancel_callback: function () {},
        title: _t("Confirmation"),
      });
    },

    _display_dialog: function (result) {
      return new Dialog(this, {
        size: "medium",
        title: result.title,
        $content: $("<div>").html(result.message),
      }).open();
    },
  });
});
