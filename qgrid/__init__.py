from .grid import SlickGrid, QGridWidget


def show_grid(data_frame, remote_js=False):
    return SlickGrid(data_frame, remote_js)


def edit_grid(data_frame):
    from IPython.html.widgets import Button, HBox
    from IPython.display import display

    # create a visualization for the dataframe
    grid = QGridWidget(df=data_frame)

    add_row = Button(description="Add Row")
    add_row.on_click(grid.add_row)

    rem_row = Button(description="Remove Row")
    rem_row.on_click(grid.remove_row)

    display(HBox((add_row, rem_row)), grid)
    return grid


def nbinstall(user=True, overwrite=False):
    """
    """
    # Lazy imports so we don't pollute the namespace.
    import os
    from IPython.html.nbextensions import install_nbextension
    from IPython import version_info

    qgridjs_path = os.path.join(
        os.path.dirname(__file__),
        'qgridjs',
    )

    install_nbextension(
        qgridjs_path,
        overwrite=overwrite,
        symlink=False,
        verbose=0,
        **({'user': user} if version_info>=(3, 0, 0, '') else {})
    )
