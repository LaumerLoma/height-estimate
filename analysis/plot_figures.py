"""README figures (light and dark SVG) from the solver.

    uv run --with numpy --with scipy --with matplotlib python analysis/plot_figures.py
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import solve_height as sh  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), '..', 'docs')
THEMES = {
    'light': dict(text='#0b0b0b', muted='#52514e', grid='#e4e3df', series='#2a78d6', soft='#cde2fb'),
    'dark': dict(text='#ffffff', muted='#c3c2b7', grid='#383835', series='#3987e5', soft='#184f95'),
}


def style(ax, t):
    ax.set_facecolor('none')
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(t['grid'])
    ax.tick_params(colors=t['muted'], length=0, labelsize=10)
    ax.grid(axis='x', color=t['grid'], linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name, theme):
    fig.savefig(os.path.join(OUT, f'{name}-{theme}.svg'), transparent=True, bbox_inches='tight')
    plt.close(fig)


def steps(r, theme):
    t = THEMES[theme]
    labels = ['Shadow formula,\nimage taken at face value', '+ camera relief\ndisplacement',
              '+ glider motion\nduring the scan', 'Final (Monte Carlo)']
    values = [r['naive'], r['static'], r['moving'], r['median']]
    y = np.arange(len(values))[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 3.1))
    style(ax, t)
    ax.plot(values[:3], y[:3], color=t['grid'], linewidth=2, zorder=1)  # the three model steps
    ax.hlines(y[-1], r['p2.5'], r['p97.5'], color=t['soft'], linewidth=8, zorder=2)
    ax.hlines(y[-1], r['p16'], r['p84'], color=t['series'], linewidth=8, zorder=3, alpha=0.55)
    ax.scatter(values, y, s=70, color=t['series'], zorder=4, edgecolor='none')
    for v, yy in zip(values, y):
        ax.annotate(f'{v:.1f} m', (v, yy), xytext=(0, 11), textcoords='offset points',
                    ha='center', color=t['text'], fontsize=10)
    ax.annotate('68 %  /  95 %', (r['p97.5'], y[-1]), xytext=(8, -3.5), textcoords='offset points',
                color=t['muted'], fontsize=9)
    ax.set_yticks(y, labels, color=t['text'], fontsize=10)
    ax.set_xlim(135, 198)
    ax.set_ylim(-0.6, len(values) - 0.3)
    ax.set_xlabel('Height above ground (m)', color=t['muted'], fontsize=10)
    ax.set_title('How the estimate builds up', color=t['text'], fontsize=12, loc='left', pad=12)
    save(fig, 'estimate-steps', theme)


def distribution(r, hs, theme):
    t = THEMES[theme]
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    style(ax, t)
    ax.grid(False)
    ax.spines['bottom'].set_color(t['muted'])
    ax.axvspan(r['p2.5'], r['p97.5'], color=t['soft'], alpha=0.45, linewidth=0, zorder=0)
    bins = np.arange(168, 192.01, 0.75)
    counts, edges = np.histogram(hs, bins)
    width = edges[1] - edges[0]
    ax.bar(edges[:-1] + width / 2, counts, width=width * 0.82, color=t['series'], linewidth=0, zorder=2)
    ax.axvline(r['median'], color=t['text'], linewidth=1.2, zorder=3)
    top = counts.max()
    ax.annotate(f"median {r['median']:.1f} m", (r['median'], top * 1.08), xytext=(6, 0),
                textcoords='offset points', ha='left', va='center', color=t['text'], fontsize=10)
    ax.annotate(f"95 %: {r['p2.5']:.0f}–{r['p97.5']:.0f} m", (r['p97.5'], top * 0.55),
                xytext=(6, 0), textcoords='offset points', color=t['muted'], fontsize=9)
    ax.set_yticks([])
    ax.set_xlim(bins[0], bins[-1])
    ax.set_ylim(0, top * 1.18)
    ax.set_xlabel('Height above ground (m)', color=t['muted'], fontsize=10)
    ax.set_title(f'Monte Carlo over all input uncertainties ({len(hs):,} draws)',
                 color=t['text'], fontsize=12, loc='left', pad=10)
    save(fig, 'estimate-distribution', theme)


def budget(b, total, theme):
    t = THEMES[theme]
    names = {'image': 'Shadow position in the image', 'motion': 'Glider airspeed and heading',
             'camera': 'Camera altitude and track', 'terrain': 'Terrain model',
             'time': 'Exposure time / Sun angle'}
    items = sorted(b.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(7.5, 2.6))
    style(ax, t)
    y = np.arange(len(items))
    ax.barh(y, [v for _, v in items], height=0.62, color=t['series'], linewidth=0)
    for yy, (_, v) in zip(y, items):
        ax.annotate(f'±{v:.1f} m', (v, yy), xytext=(5, 0), textcoords='offset points',
                    va='center', color=t['text'], fontsize=10)
    ax.set_yticks(y, [names[k] for k, _ in items], color=t['text'], fontsize=10)
    ax.set_xlim(0, 3.3)
    ax.set_xlabel('Spread in height from each source alone, 1σ (m)', color=t['muted'], fontsize=10)
    ax.set_title(f'Error budget (all together: ±{total:.1f} m)', color=t['text'], fontsize=12,
                 loc='left', pad=10)
    save(fig, 'error-budget', theme)


def main():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'path'})
    alpha0, az0 = sh.sun([sh.T_MIN])[0]
    central = dict(alpha=alpha0, az=az0, glider=sh.GLIDER_IMG, shadow=sh.SHADOW_IMG,
                   zc=sh.ZC, x0=sh.X0, gamma=0.0, speed=0.0, heading=sh.HEADING, v_air=sh.V_AIR,
                   dz_shadow=0.0, dz_glider=0.0, dz_ortho=0.0)
    tgrid = np.linspace(sh.T_MIN - 5 * sh.T_SD, sh.T_MIN + 5 * sh.T_SD, 41)
    sg = sh.sun(tgrid)
    hs = sh.monte_carlo(20000, central, sg, tgrid, sh.GROUPS)
    b = {g: float(sh.monte_carlo(5000, central, sg, tgrid, [g]).std()) for g in sh.GROUPS}
    p = np.percentile(hs, [2.5, 16, 50, 84, 97.5])
    r = {'naive': float(sh.naive(alpha0)), 'static': sh.solve(central)['h'],
         'moving': sh.solve({**central, 'speed': 30.0})['h'],
         'p2.5': p[0], 'p16': p[1], 'median': p[2], 'p84': p[3], 'p97.5': p[4]}
    print({k: round(float(v), 1) for k, v in r.items()}, {k: round(v, 2) for k, v in b.items()})
    for theme in THEMES:
        steps(r, theme)
        distribution(r, hs, theme)
        budget(b, hs.std(), theme)


if __name__ == '__main__':
    main()
