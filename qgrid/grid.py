import pandas as pd
import numpy as np
import os
import uuid
import json

from IPython.display import display_html, display_javascript
from IPython.html import widgets
from IPython.display import display, Javascript
from IPython.utils.traitlets import Unicode, Instance, Bool


def template_contents(filename):
    template_filepath = os.path.join(
        os.path.dirname(__file__),
        'templates',
        filename,
    )
    with open(template_filepath) as f:
        return f.read()


SLICK_GRID_CSS = template_contents('slickgrid.css.template')
SLICK_GRID_JS = template_contents('slickgrid.js.template')
REMOTE_URL = ("https://cdn.rawgit.com/quantopian/qgrid/"
              "ddf33c0efb813cd574f3838f6cf1fd584b733621/qgrid/qgridjs/")


class SlickGrid(object):

    def __init__(self, data_frame, remote_js=False):
        self.data_frame = data_frame
        self.remote_js = remote_js
        self.div_id = str(uuid.uuid4())

        self.df_copy = data_frame.copy()

        if type(self.df_copy.index) == pd.core.index.MultiIndex:
            self.df_copy.reset_index(inplace=True)
        else:
            self.df_copy.insert(0, self.df_copy.index.name, self.df_copy.index)

        tc = dict(np.typecodes)
        for key in np.typecodes.keys():
            if "All" in key:
                del tc[key]

        self.column_types = []
        for col_name, dtype in self.df_copy.dtypes.iteritems():
            column_type = {'field': col_name}
            for type_name, type_codes in tc.items():
                if dtype.kind in type_codes:
                    column_type['type'] = type_name
                    break
            self.column_types.append(column_type)

        self.precision = pd.get_option('display.precision') - 1

    def _ipython_display_(self):
        try:
            column_types_json = json.dumps(self.column_types)
            data_frame_json = self.df_copy.to_json(
                orient='records',
                date_format='iso',
                double_precision=self.precision,
            )

            if self.remote_js:
                cdn_base_url = REMOTE_URL
            else:
                cdn_base_url = "/nbextensions/qgridjs"

            raw_html = SLICK_GRID_CSS.format(
                div_id=self.div_id,
                cdn_base_url=cdn_base_url,
            )
            raw_js = SLICK_GRID_JS.format(
                cdn_base_url=cdn_base_url,
                div_id=self.div_id,
                data_frame_json=data_frame_json,
                column_types_json=column_types_json,
            )

            display_html(raw_html, raw=True)
            display_javascript(raw_js, raw=True)
        except Exception as err:
            display_html('ERROR: {}'.format(str(err)), raw=True)


class QGridWidget(widgets.DOMWidget):
    _view_name = Unicode('QGridView', sync=True)
    _df_json = Unicode('', sync=True)
    _column_types_json = Unicode('', sync=True)
    _loop_guard = Bool(False)
    _index_name = Unicode('')
    _cdn_base_url = Unicode("/nbextensions/qgridjs", sync=True)

    df = Instance(pd.DataFrame)
    editable = Bool(True, sync=True)
    remote_js = Bool(False)

    def _df_changed(self):
        """Build the Data Table for the DataFrame."""
        if self._loop_guard:
            return
        df = self.df.copy()

        # register a callback for custom messages
        self.on_msg(self._handle_qgrid_msg)

        if not df.index.name:
            df.index.name = 'Index'

        if type(df.index) == pd.core.index.MultiIndex:
            df.reset_index(inplace=True)
        else:
            df.insert(0, df.index.name, df.index)

        self._index_name = df.index.name

        tc = dict(np.typecodes)
        for key in np.typecodes.keys():
            if "All" in key:
                del tc[key]

        column_types = []
        for col_name, dtype in df.dtypes.iteritems():
            column_type = {'field': col_name}
            for type_name, type_codes in tc.items():
                if dtype.kind in type_codes:
                    column_type['type'] = type_name
                    break
            column_types.append(column_type)
        self._column_types_json = json.dumps(column_types)

        precision = pd.get_option('display.precision') - 1

        self._df_json = df.to_json(
                orient='records',
                date_format='iso',
                double_precision=precision,
            )

    def _remote_js_changed(self):
        if self.remote_js:
            self._cdn_base_url = REMOTE_URL
        else:
            self._cdn_base_url = "/nbextensions/qgridjs"

    def add_row(self, value=None):
        """Append a row at the end of the dataframe."""
        df = self.df
        if not df.index.is_integer():
            msg = 'alert("Cannot add a row a table with a non-integer index")'
            display(Javascript(msg))
            return
        last = df.loc[df.index[-1], :]
        last.name += 1
        self._loop_guard = True
        self.df = self.df.append(last)
        self._loop_guard = False
        precision = pd.get_option('display.precision') - 1
        row_data = last.to_json(date_format='iso',
                                double_precision=precision)
        msg = json.loads(row_data)
        msg[self._index_name] = str(last.name)
        msg['id'] = str(last.name)
        msg['type'] = 'add_row'
        self.send(msg)

    def remove_row(self, value):
        """Remove the current row from the table"""
        self.send({'type': 'remove_row'})

    def _handle_qgrid_msg(self, widget, msg):
        """Handle incoming messages from the QGridView"""
        if 'type' not in msg:
            return
        if msg['type'] == 'remove_row':
            self._loop_guard = True
            if msg['row'] == 0:
                self.df = self.df[1:]
            self.df = pd.concat((self.df[:msg['row']],
                                 self.df[msg['row'] + 1:]))
            self._loop_guard = False

        elif msg['type'] == 'cell_change':
            try:
                self.df.set_value(self.df.index[msg['row']], msg['column'],
                                  msg['value'])
            except ValueError:
                pass
