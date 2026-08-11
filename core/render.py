"""Web 版公式/绘图渲染辅助。

桌面版（PySide6）中该模块负责把 LaTeX 渲染进 QGraphicsView 等；
Web 版中公式渲染由前端 MathJax 完成，本模块仅保留 matplotlib 绘图所需的
主题配色函数（applyPlotTheme），供 functions/paint2D.py、functions/paint3D.py
复用，使绘图配色与桌面版完全一致（浅色/深色主题）。
"""
import matplotlib
matplotlib.use('Agg')  # 服务端无显示器，使用非交互式后端
import os
os.environ['MPLBACKEND'] = 'Agg'


def applyPlotTheme(fig, ax, theme='light'):
    """将 matplotlib Figure/Axes 适配为浅色 / 深色主题配色。

    参数:
        fig: matplotlib.figure.Figure
        ax: matplotlib Axes（2D 或 3D）
        theme: 'light' 或 'dark'
    返回:
        (bg, fg, grid_color, axis_color)，供调用方继续设置网格、坐标轴线等。
    """
    dark = theme == 'dark'
    if dark:
        bg, fg, grid_c, axis_c = '#202124', '#e8eaed', '#5f6368', '#9aa0a6'
    else:
        bg, fg, grid_c, axis_c = 'white', 'black', '#cccccc', 'black'

    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg)
    try:
        for spine in ax.spines.values():
            spine.set_color(axis_c)
    except Exception:
        # 3D 轴没有 spines，改为设置三个坐标轴面板的颜色
        for aname in ('xaxis', 'yaxis', 'zaxis'):
            axi = getattr(ax, aname, None)
            if axi is not None:
                try:
                    axi.pane.set_facecolor(bg)
                    axi.pane.set_edgecolor(axis_c)
                except Exception:
                    pass
    return bg, fg, grid_c, axis_c
