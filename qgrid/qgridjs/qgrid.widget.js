require(["widgets/js/widget", "widgets/js/manager"], function(widget, manager){

    /**
     * Date input handler.
     *
     * Adapted from https://github.com/mleibman/SlickGrid/blob/master/slick.editors.js
     * MIT License, Copyright (c) 2010 Michael Leibman
     */
    function DateEditor(args) {
        var $input;
        var defaultValue;
        var scope = this;
        var calendarOpen = false;
        this.init = function () {
          $input = $("<INPUT type=text class='editor-text' />");
          $input.appendTo(args.container);
          $input.focus().select();
          $input.datepicker({
            showOn: "button",
            buttonImageOnly: true,
            beforeShow: function () {
              calendarOpen = true
            },
            onClose: function () {
              calendarOpen = false
            }
          });

          $input.width($input.width() - 18);
        };

        this.destroy = function () {
          $.datepicker.dpDiv.stop(true, true);
          $input.datepicker("hide");
          $input.datepicker("destroy");
          $input.remove();
        };

        this.show = function () {
          if (calendarOpen) {
            $.datepicker.dpDiv.stop(true, true).show();
          }
        };

        this.hide = function () {
          if (calendarOpen) {
            $.datepicker.dpDiv.stop(true, true).hide();
          }
        };

        this.position = function (position) {
          if (!calendarOpen) {
            return;
          }
          $.datepicker.dpDiv
              .css("top", position.top + 30)
              .css("left", position.left);
        };

        this.focus = function () {
          $input.focus();
        };

        this.loadValue = function (item) {
          defaultValue = item[args.column.field];
          $input.val(defaultValue);
          $input[0].defaultValue = defaultValue;
          $input.select();
        };

        this.serializeValue = function () {
          return $input.val();
        };

        this.applyValue = function (item, state) {
          item[args.column.field] = state;
        };

        this.isValueChanged = function () {
          return (!($input.val() == "" && defaultValue == null)) && ($input.val() != defaultValue);
        };

        this.validate = function () {
          return {
            valid: true,
            msg: null
          };
        };

        this.init();
    }

    /**
     * Text input handler.
     *
     * From https://github.com/mleibman/SlickGrid/blob/master/slick.editors.js
     * MIT License, Copyright (c) 2010 Michael Leibman
     */
    function TextEditor(args) {
        var $input;
        var defaultValue;
        var scope = this;

        this.init = function () {
          $input = $("<INPUT type=text class='editor-text' />")
              .appendTo(args.container)
              .bind("keydown.nav", function (e) {
                if (e.keyCode === $.ui.keyCode.LEFT || e.keyCode === $.ui.keyCode.RIGHT) {
                  e.stopImmediatePropagation();
                }
              })
              .focus()
              .select();
        };

        this.destroy = function () {
          $input.remove();
        };

        this.focus = function () {
          $input.focus();
        };

        this.getValue = function () {
          return $input.val();
        };

        this.setValue = function (val) {
          $input.val(val);
        };

        this.loadValue = function (item) {
          defaultValue = item[args.column.field] || "";
          $input.val(defaultValue);
          $input[0].defaultValue = defaultValue;
          $input.select();
        };

        this.serializeValue = function () {
          return $input.val();
        };

        this.applyValue = function (item, state) {
          item[args.column.field] = state;
        };

        this.isValueChanged = function () {
          return (!($input.val() == "" && defaultValue == null)) && ($input.val() != defaultValue);
        };

        this.validate = function () {
          if (args.column.validator) {
            var validationResults = args.column.validator($input.val());
            if (!validationResults.valid) {
              return validationResults;
            }
          }

          return {
            valid: true,
            msg: null
          };
        };

        this.init();
    }
    
    /**
     * Validator for numeric cells.
     */
    function validateNumber(value) {
      if (isNaN(value)) {
        return {
          valid: false,
          msg: "Please enter a valid integer"
        };
      }
      return {
        valid: true,
        msg: null
      };
    }

    var grid;

    var QGridView = widget.DOMWidgetView.extend({

        render: function() {
            var that = this;
            var cdn_base_url = this.model.get('_cdn_base_url');
            
            // Load the custom css
            if ($("#dg-css").length == 0){
                $("head").append([
                    "<link href='" + cdn_base_url + "/lib/slick.grid.css' rel='stylesheet'>",
                    "<link href='" + cdn_base_url + "/lib/slick-default-theme.css' rel='stylesheet'>",
                    "<link href='https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.10.4/css/jquery-ui.min.css' rel='stylesheet'>",
                    "<link id='dg-css' href='" + cdn_base_url + "/qgrid.css' rel='stylesheet'>"
                ]);
            }
            
            // set the custom script load paths
            var path_dictionary = {
                jquery_drag: cdn_base_url + "/lib/jquery.event.drag-2.2",
                slick_core: cdn_base_url + "/lib/slick.core.2.2",
                slick_data_view: cdn_base_url + "/lib/slick.dataview.2.2",
                slick_check_box_column: cdn_base_url + "/lib/slick.checkboxselectcolumn",
                slick_row_selection_model: cdn_base_url + "/lib/slick.rowselectionmodel",
                slick_grid: cdn_base_url + "/lib/slick.grid.2.2",
                data_grid: cdn_base_url + "/qgrid",
                date_filter: cdn_base_url + "/qgrid.datefilter",
                text_filter: cdn_base_url + "/qgrid.textfilter",
                slider_filter: cdn_base_url + "/qgrid.sliderfilter",
                filter_base:  cdn_base_url + "/qgrid.filterbase",
                handlebars: "https://cdnjs.cloudflare.com/ajax/libs/handlebars.js/2.0.0/handlebars.min"
            };

            var existing_config = require.s.contexts._.config;
            if (!existing_config.paths['underscore']){
                path_dictionary['underscore'] = "https://cdnjs.cloudflare.com/ajax/libs/underscore.js/1.7.0/underscore-min";
            }

            if (!existing_config.paths['moment']){
                path_dictionary['moment'] = "https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.8.3/moment.min";
            }

            if (!existing_config.paths['jqueryui']){
                path_dictionary['jqueryui'] = "https://ajax.googleapis.com/ajax/libs/jqueryui/1.11.1/jquery-ui.min";
            }

            require.config({
                paths: path_dictionary
            });
            
            if (typeof jQuery === 'function') {
                define('jquery', function() { return jQuery; });
            }
    
            /**
             * Load the required scripts and create the grid.
             */
            require([
                'jquery',
                'jquery_drag',
                'slick_core',
                'slick_data_view',
                'slick_check_box_column',
                'slick_row_selection_model',
            ],
            function() {
                require(['slick_grid'], function() {
                    require(["data_grid"], 
                        function(dgrid) {
                            that.setupQGrid(dgrid);
                    });
                });
            });
        },

        /**
         * Set up our QGrid and event handlers.
         */
        setupQGrid: function(dgrid) {
            var that = this;
            // set up the divs and styles
            this.$el.addClass('q-grid-container');
            var table = this.$el.append('div');
            table.addClass('q-grid');
            var width = this.el.parentElement.clientWidth.toString();
            this.el.setAttribute("style", "max-width:" + width + "px;");

            // create the table
            var df = JSON.parse(this.model.get('_df_json'));
            var column_types = JSON.parse(this.model.get('_column_types_json'));
            
            grid = new dgrid.QGrid(table[0], df, column_types);
            grid.initialize_slick_grid();

            // set up editing
            var editable = this.model.get('editable');
            if (!editable) {
                return;
            }

            var sgrid = grid.slick_grid;
            sgrid.setOptions({'editable': true, 
                              'autoEdit': false});
            var columns = sgrid.getColumns();
            for (var i = 1; i < columns.length; i++) {
                if (columns[i].type === 'date') {
                   columns[i].editor = DateEditor;
                } else {
                   columns[i].editor = TextEditor;
                }
                if (columns[i].type === 'number') {
                   columns[i].validator = validateNumber;
                } 
            }
            sgrid.setColumns(columns);

            // set up callbacks
            sgrid.onCellChange.subscribe(function(e, args) {
                var column = columns[args.cell].name;
                var msg = {'row': args.row, 'column': column,
                           'value': args.item[column], 'type': 'cell_change'};
                that.send(msg);
            });

            // subscribe to incoming messages from the QGridWidget
            this.model.on('msg:custom', this.handleMsg, this);
        },
        
        /**
         * Handle messages from the QGridWidget.
         */
        handleMsg: function(msg) {
            var sgrid = grid.slick_grid;
            if (msg.type === 'remove_row') {
                var row = sgrid.getActiveCell().row;
                var data = sgrid.getData().getItem(row);                         
                grid.data_view.deleteItem(data.id);
                msg = {'type': 'remove_row', 'row': row, 'id': data.id};
                this.send(msg);

            } else if (msg.type === 'add_row') {
                var dd = sgrid.getData();
                dd.addItem(msg);
                dd.refresh();
                this.send(msg);
            }
        }
    });

    manager.WidgetManager.register_widget_view('QGridView', QGridView);
});
