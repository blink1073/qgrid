import pandas as pd
import numpy as np
import os
import uuid
import json
from numbers import Integral

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


class _DefaultSettings(object):

    def __init__(self):
        self._grid_options = {
            'enableCellNavigation': True,
            'fullWidthRows': True,
            'syncColumnCellResize': True,
            'forceFitColumns': True,
            'rowHeight': 28,
            'enableColumnReorder': False,
            'enableTextSelectionOnCells': True,
        }
        self._remote_js = False
        self._precision = None  # Defer to pandas.get_option

    def set_grid_option(self, optname, optvalue):
        """
        Set an option value to be passed to javascript SlickGrid instances

        Parameters
        ----------
        optname : str
            The name of the option to override
        optvalue : object
            The new value
        """
        self._grid_options[optname] = optvalue

    def set_defaults(self, remote_js=None, precision=None, grid_options=None):
        """
        Set a default value to be passed to Python SlickGrid instances.

        See documentation for `show_grid` for more info on configurable values.
        """
        if remote_js is not None:
            self._remote_js = remote_js
        if precision is not None:
            self._precision = precision
        if grid_options is not None:
            self._grid_options = grid_options

    @property
    def grid_options(self):
        return self._grid_options

    @property
    def remote_js(self):
        return self._remote_js

    @property
    def precision(self):
        return self._precision or pd.get_option('display.precision') - 1

defaults = _DefaultSettings()
set_defaults = defaults.set_defaults
set_grid_option = defaults.set_grid_option


def show_grid(data_frame, remote_js=None, precision=None, grid_options=None):
    """
    Main entry point for rendering DataFrames as SlickGrids.

    Parameters
    ----------
    remote_js : bool
        Whether to load slickgrid.js from a local filesystem or from a
        remote CDN.  Loading from the local filesystem means that SlickGrid
        will function even when not connected to the internet, but grid
        cells created with local filesystem loading will not render
        correctly on external sharing services like NBViewer.
    precision : integer
        The number of digits of precision to display for floating-point
        values.  If unset, we use the value of
        `pandas.get_option('display.precision')`.
    grid_options : dict
        Options to use when creating javascript SlickGrid instances.  See
        the SlickGrid documentation for information on the available
        options.  Default options are as follows:

        {
            'enableCellNavigation': True,
            'fullWidthRows': True,
            'syncColumnCellResize': True,
            'forceFitColumns': True,
            'rowHeight': 28,
            'enableColumnReorder': False,
            'enableTextSelectionOnCells': True,
        }

    See Also
    --------
    qgrid.set_defaults : Permanently set global defaults for `show_grid`.
    qgrid.set_grid_option : Permanently set individual Javascript options.
    """

    if remote_js is None:
        remote_js = defaults.remote_js
    if precision is None:
        precision = defaults.precision
        if not isinstance(precision, Integral):
            raise TypeError("precision must be int, not %s" % type(precision))
    if grid_options is None:
        grid_options = defaults.grid_options
        if not isinstance(grid_options, dict):
            raise TypeError(
                "grid_options must be dict, not %s" % type(grid_options)
            )

    return SlickGrid(
        data_frame,
        remote_js=remote_js,
        precision=precision,
        grid_options=grid_options,
    )


class SlickGrid(object):

    def __init__(self, data_frame, remote_js, precision, grid_options):
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

        self.precision = precision
        self.grid_options = grid_options

    def _ipython_display_(self):
        try:
            column_types_json = json.dumps(self.column_types)
            data_frame_json = self.df_copy.to_json(
                orient='records',
                date_format='iso',
                double_precision=self.precision,
            )
            options_json = json.dumps(self.grid_options)

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
                options_json=options_json,
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
    js_msg = Unicode('', sync=True)
    py_msg = Unicode('', sync=True)

    df = Instance(pd.DataFrame)
    editable = Bool(True, sync=True)
    remote_js = Bool(False)

    def _df_changed(self):
        """Build the Data Table for the DataFrame."""
        if self._loop_guard:
            return
        df = self.df.copy()

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
        print('remote_js_changed', self.remote_js)
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
        self._send_msg(msg)

    def remove_row(self, value):
        """Remove the current row from the table"""
        self._send_msg({'type': 'remove_row'})

    def _send_msg(self, msg):
        """Send a message to the QGridView"""
        msg['uid'] = uuid.uuid4().hex
        self.py_msg = json.dumps(msg)

    def _visible_changed(self):
        display_javascript('alert("visible_changed"')

    def _js_msg_changed(self):
        """Handle incoming messages from the QGridView"""
        data = json.loads(self.js_msg)

        if data['type'] == 'remove_row':
            self._loop_guard = True
            if data['row'] == 0:
                self.df = self.df[1:]
            self.df = pd.concat((self.df[:data['row']],
                                 self.df[data['row'] + 1:]))
            self._loop_guard = False

        elif data['type'] == 'cell_change':
            try:
                self.df.set_value(self.df.index[data['row']], data['column'],
                                  data['value'])
            except ValueError:
                pass
