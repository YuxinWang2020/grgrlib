#!/bin/python
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm, SymLogNorm
from .core import fast0


def grplot(X, yscale=None, labels=None, title='', styles=None, colors=None, legend=None, bulk_plot=False, ax=None, fig=None, figsize=None, nlocbins=None, sigma=0.05, alpha=None, stat=np.nanmedian, **plotargs):

    if not isinstance(X, tuple):
        # make it a tuple
        X = X,

    # use first object in X to get some infos
    X0 = np.array(X[0])

    if yscale is None:
        if isinstance(X[0], pd.DataFrame):
            yscale = X[0].index
        elif X0.ndim > 1:
            yscale = np.arange(X[0].shape[-2])
        else:
            yscale = np.arange(len(X0))
    elif isinstance(yscale, tuple):
        yscale = np.arange(yscale[0], yscale[0] +
                           X0.shape[-2]*yscale[1], yscale[1])

    if labels is None:
        if isinstance(X[0], pd.DataFrame):
            labels = np.array(X[0].keys())
        elif X0.shape[-1] > 1 and X0.ndim > 1:
            labels = np.arange(X0.shape[-1]) + 1
        else:
            labels = np.array([None])
    else:
        labels = np.ascontiguousarray(labels)

    if styles is None:
        styles = '-'

    if not isinstance(styles, tuple):
        styles = np.repeat(styles, len(X))

    if nlocbins is None:
        nlocbins = 'auto'

    # yet we can not be sure about the number of dimensions
    if X0.ndim == 1:
        selector = False
    else:
        selector = np.zeros(X[0].shape[-1], dtype=bool)

    X_list = []
    for x_raw in X:

        x = np.array(x_raw)

        # X.shape[0] is the number of time series
        # X.shape[1] is the len of the x axis (e.g. time)
        # X.shape[2] is the no of different objects (e.g. states)
        if x.ndim == 1:
            # be sure that X has 3 dimensions
            x = x.reshape(1, len(x), 1)
        if x.ndim == 2:
            x = x.reshape(1, *x.shape)

        line = None
        interval = None
        bulk = None

        if x.shape[0] == 1:
            line = x[0]
        if x.shape[0] == 2:
            interval = x
        if x.shape[0] == 3:
            line = x[1]
            interval = x[[0, 2]]
        if x.shape[0] > 3:
            if not bulk_plot:
                interval = np.nanpercentile(
                    x, [sigma*100/2, (1 - sigma/2)*100], axis=0)
                line = stat(x, axis=0)
            else:
                bulk = x

        # check if there are states that are always zero
        if line is not None:
            selector += ~fast0(line, 0)
        if interval is not None:
            selector += ~fast0(interval[0], 0)
            selector += ~fast0(interval[1], 0)
        if bulk is not None:
            selector[:] = 1

        X_list.append((line, interval, bulk))

    colors = colors or [None]*len(X_list)
    if isinstance(colors, str):
        colors = (colors,)
    no_states = sum(selector)

    # first create axes as an iterateble if it does not exist
    if ax is None:
        ax = []
        figs = []
        rest = no_states % 4
        plt_no = no_states // 4 + bool(rest)

        # assume we want to have two rows and cols per plot
        no_rows = 2
        no_cols = 2
        for i in range(plt_no):

            no_rows -= 4*(i+1) - no_states > 1
            no_cols -= 4*(i+1) - no_states > 2

            if figsize is None:
                figsize_loc = (no_cols*4, no_rows*3)
            else:
                figsize_loc = figsize

            fig, ax_of4 = plt.subplots(no_rows, no_cols, figsize=figsize_loc)
            ax_flat = np.array(ax_of4).flatten()

            # assume we also want two cols per plot
            for j in range(no_rows*no_cols):

                if 4*i+j >= no_states:
                    ax_flat[j].set_visible(False)
                ax.append(ax_flat[j])

            if title:
                if plt_no > 1:
                    plt.suptitle('%s %s' % (title, i+1))
                else:
                    plt.suptitle('%s' % (title))
            figs.append(fig)
    else:
        try:
            len(ax)
        except TypeError:
            ax = (ax,)
        [axis.set_prop_cycle(None) for axis in ax]
        figs = fig or None

    if not isinstance(yscale, pd.DatetimeIndex):
        locator = MaxNLocator(nbins=nlocbins, steps=[1, 2, 4, 8, 10])

    handles = []
    for obj_no, obj in enumerate(X_list):

        if legend is not None:
            legend_tag = np.ascontiguousarray(legend)[obj_no]
        else:
            legend_tag = None

        subhandles = []
        line, interval, bulk = obj
        # ax is a list of all the subplots
        for i in range(no_states):

            if line is not None:
                lalpha = alpha if (
                    interval is None and len(X_list) == 1) else 1
                lline = ax[i].plot(yscale, line[:, selector][:, i], styles[obj_no],
                                   color=colors[obj_no], lw=2, label=legend_tag, alpha=lalpha, **plotargs)
                subhandles.append(lline)

            if interval is not None:

                label = legend_tag if line is None else None
                color = lline[-1].get_color() if line is not None else colors[obj_no]

                if color:
                    ax[i].fill_between(yscale, *interval[:, :, selector][:, :, i], lw=0, color=color, alpha=alpha or 0.3, label=label, **plotargs)
                else:
                    ax[i].fill_between(yscale, *interval[:, :, selector][:, :, i], lw=0, alpha=alpha or 0.3, label=label, **plotargs)

            elif bulk is not None:
                color = colors[obj_no] or 'maroon'

                ax[i].plot(yscale, bulk[..., i].swapaxes(
                    0, 1), c=color, alpha=alpha or 0.05)
            ax[i].tick_params(axis='both', which='both',
                              top=False, right=False)
            if not isinstance(yscale, pd.DatetimeIndex):
                ax[i].xaxis.set_major_locator(locator)

        handles.append(subhandles)

    if figs is not None:
        [fig.autofmt_xdate() for fig in figs]

    for i in range(no_states):
        ax[i].set_title(labels[selector][i])

    # the notebook `inline` backend does not like `tight_layout`. But better don't use it...
    # shell = get_ipython().__class__.__name__
    # if not shell == 'ZMQInteractiveShell' and figs is not None:
        # [fig.tight_layout() for fig in figs]

    if figs is not None:
        [fig.tight_layout() for fig in figs]

    return figs, ax, handles


def bifplot(y, X=None, plot_dots=None, ax=None, color='k', ylabel=None, xlabel=None):
    """A bifurcation diagram

    (add further documentation)
    """

    if X is None:
        X = y
        y = np.arange(y.shape[0])

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = None

    if plot_dots is None:
        if X.shape[0] > 50:
            plot_dots = False
        else:
            plot_dots = True

    if not plot_dots:
        ax.plot(y, X, '.', color=color, markersize=0.01)
    else:
        ax.plot(y, X, 'o', color=color)

    ax.set_xlim(np.min(y), np.max(y))
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

    if fig is not None:
        fig.tight_layout()

    return fig, ax


def grheat(X, gridbounds, xlabel=None, ylabel=None, zlabel=None):
    """Simple interface to a heatmap (uses matplotlib's `imshow`).

    Parameters
    ----------
    X : numpy.array
        a matrix-like object 
    gridbounds : float or tuple
        the bounds of the grid. If a float, -/+ this value is taken as the bounds
    xlabel : str (optional)
    ylabel : str (optional)
    zlabel : str (optional)
    """

    fig, ax = plt.subplots()

    if isinstance(gridbounds, tuple):
        if isinstance(gridbounds[0], tuple):
            extent = [*gridbounds[0], *gridbounds[1], ]
        else:
            extent = [-gridbounds[0], gridbounds[0], -
                      gridbounds[1], gridbounds[1], ]
    else:
        extent = [-gridbounds, gridbounds, -gridbounds, gridbounds, ]

    plt.imshow(X, cmap="hot", extent=extent, vmin=np.nanmin(
        X), vmax=np.nanmax(X), norm=SymLogNorm(1, linscale=1))

    clb = plt.colorbar()

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(False)
    clb.set_label(zlabel)

    plt.tight_layout()


def figurator(nrows=2, ncols=2, nfigs=1, format_date=True, **args):
    """Create list of figures and axes with (potentially) more than one graph

    Parameters
    ----------
    nrows : int, optional
        Number of rows per figure, defaults to 2
    ncols : int, optional
        Number of cols per figure, defaults to 2
    nfigs : int, optional
        Number of figures, defaults to 1
    args : keyword arguments, optional
        keyword arguments that will be forwarded to `matplotlib.pyplot.subplots`

    Returns
    -------
    fig, ax : list, list
        A tuple of two lists: the first list are all figure handlers, the second is a list of all the axis
    """

    fax = [plt.subplots(nrows, ncols, **args) for _ in range(nfigs)]
    axs = np.array([f[1] for f in fax]).flatten()
    figs = [f[0] for f in fax]

    if format_date:
        [fig.autofmt_xdate() for fig in figs]

    return figs, axs


def axformater(ax, mode='rotate'):
    """Rotate ax as in `autofmt_xdate`
    """

    if mode == 'rotate':
        return plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    elif mode == 'off':
        return ax.set_axis_off()
    else:
        raise NotImplementedError('No such modus: %s' % mode)


def save_png2pdf(fig, path, **args):
    """Save as a .png and use unix `convert` to convert to PDF.
    """

    import os

    fig.savefig(path + 'png', **args)
    os.system('convert %s.png %s.pdf' %(path,path))

    return 

pplot = grplot
