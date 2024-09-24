//odoo.define('website_support.new_help_page', function (require) {
//'use strict';
//
//    var core = require('web.core');
//    var base = require('web_editor.base');
//    var WebsiteNewMenu = require("website.newMenu");
//    var wUtils = require('website.utils');
//    var rpc = require('web.rpc');
//    var weContext = require('web_editor.context');
//
//    var _t = core._t;
//
//    WebsiteNewMenu.include({
//        actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
//            new_help_page: 'new_help_page',
//        }),
//
//        new_help_page: function() {
//
//             rpc.query({
//			    model: 'website.support.help.group',
//				method: 'name_search',
//				args: [],
//				context: weContext.get()
//		     }).then(function(help_group_ids){
//                 wUtils.prompt({
//                     id: "editor_new_help_page",
//                     window_title: _t("New Help Page"),
//                     select: _t("Help Group"),
//                     init: function (field) {
//                         var $group = this.$dialog.find("div.form-group");
//                         $group.removeClass("mb0");
//
//                         var $add = $(
//                         '<div class="form-group row mb0 ">'+
//                         '    <label for="help_page_name" class="col-md-3 col-form-label"></label>'+
//                         '    <div class="col-md-8">'+
//                         '        <input name="help_page_name" type="input" class="form-control" required="required"/>'+
//                         '    </div>'+
//                         '</div>');
//                         $add.find('label').append(_t("Name"));
//                         $group.after($add);
//                         return help_group_ids;
//                     }
//                 }).then(function (help_group_id, field, $dialog) {
//					 var help_page_name = ($dialog.find('input[name="help_page_name"]').val());
//                     document.location = '/helppage/new?group_id=' + help_group_id + '&help_page_name=' + help_page_name;
//                 });
//            });
//        },
//    });
//});
//
//
//odoo.define('website_support.new_help_group', function (require) {
//'use strict';
//
//    var core = require('web.core');
//    var base = require('web_editor.base');
//    var WebsiteNewMenu = require("website.newMenu");
//    var wUtils = require('website.utils');
//
//    var _t = core._t;
//
//    WebsiteNewMenu.include({
//        actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
//            new_help_group: 'new_help_group',
//        }),
//
//        new_help_group: function() {
//            wUtils.prompt({
//                id: "editor_new_help_group",
//                window_title: _t("New Help Group"),
//                input: _t("Help Group"),
//                init: function () {
//
//                }
//            }).then(function (val, field, $dialog) {
//                if (val) {
//                    var url = '/helpgroup/new/' + encodeURIComponent(val);
//                    document.location = url;
//                }
//            });
//        },
//
//    });
//});

odoo.define('website_support.new_help_page', function (require) {
    'use strict';

    const core = require('web.core');
    const webEditorBase = require('web_editor.base');
    const NewMenu = require("website.newMenu");
    const wUtils = require('website.utils');
    const rpc = require('web.rpc');
    const Context = require('web_editor.context');

    const _t = core._t;

    NewMenu.include({
        events: _.extend({}, NewMenu.prototype.events, {
            'click .js_new_help_page': 'newHelpPage',
        }),

        newHelpPage: function (ev) {
            ev.preventDefault();
            const self = this;

            rpc.query({
                model: 'website.support.help.group',
                method: 'name_search',
                args: [],
                context: Context.get()
            }).then(function (helpGroupIds) {
                wUtils.prompt({
                    id: "editor_new_help_page",
                    window_title: _t("New Help Page"),
                    select: _t("Help Group"),
                    init: function (field) {
                        const $group = this.$dialog.find("div.form-group");
                        $group.removeClass("mb0");

                        const $add = $('<div class="form-group row mb0">' +
                            '    <label for="help_page_name" class="col-md-3 col-form-label"></label>' +
                            '    <div class="col-md-8">' +
                            '        <input name="help_page_name" type="input" class="form-control" required="required"/>' +
                            '    </div>' +
                            '</div>');
                        $add.find('label').append(_t("Name"));
                        $group.after($add);
                        return helpGroupIds;
                    }
                }).then(function (helpGroupId, field, $dialog) {
                    const helpPageName = $dialog.find('input[name="help_page_name"]').val();
                    const url = '/helppage/new?group_id=' + helpGroupId + '&help_page_name=' + encodeURIComponent(helpPageName);
                    document.location.href = url;
                });
            });
        },
    });
});


odoo.define('website_support.new_help_group', function (require) {
    'use strict';

    const core = require('web.core');
    const webEditorBase = require('web_editor.base');
    const NewMenu = require("website.newMenu");
    const wUtils = require('website.utils');

    const _t = core._t;

    NewMenu.include({
        events: _.extend({}, NewMenu.prototype.events, {
            'click .js_new_help_group': 'newHelpGroup',
        }),

        newHelpGroup: function (ev) {
            ev.preventDefault();
            const self = this;

            wUtils.prompt({
                id: "editor_new_help_group",
                window_title: _t("New Help Group"),
                input: _t("Help Group"),
                init: function () {

                }
            }).then(function (val, field, $dialog) {
                if (val) {
                    const url = '/helpgroup/new/' + encodeURIComponent(val);
                    document.location.href = url;
                }
            });
        },
    });
});