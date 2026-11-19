"""Draw documented boundaries and partitions; these figures are not test results."""
from pathlib import Path

def create_media(data, output):
    """Export PNG and SVG snapshots, keeping labels separate from workbook tables."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    import textwrap
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style='whitegrid', font='DejaVu Sans', font_scale=0.95)
    media = []

    def save(fig, name, sheet):
        """Save both raster workbook media and scalable standalone graphics."""
        for suffix in ('png', 'svg'):
            fig.savefig(output / (name + '.' + suffix), dpi=160, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        media.append({'name': name, 'sheet': sheet, 'png': str(output / (name + '.png'))})
    limits = data['bva']
    lo, hi, step, nominal = [limits[key] for key in ('min', 'max', 'step', 'nominal')]
    values = [lo - step, lo, lo + step, nominal, hi - step, hi, hi + step]
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.axvspan(lo, hi, color='#e2f1e9', zorder=0)
    sns.scatterplot(x=values, y=list(range(7)), hue=[lo <= value <= hi for value in values], palette={True: '#176d52', False: '#bd3b40'}, s=120, ax=ax, legend=False)
    ax.set(yticks=range(7), yticklabels=data['bva_chart']['labels'], xticks=sorted(set(values)), xlabel=data['bva_chart']['xlabel'], ylabel='', title=data['bva_chart']['title'])
    ax.axvline(lo, color='#176d52', ls='--')
    ax.axvline(hi, color='#176d52', ls='--')
    save(fig, 'bva_quantity', 'BVA')
    groups = sorted({row[1] for row in data.get('extra_bva', [])})
    for index, group in enumerate(groups, 1):
        rows = [row for row in data['extra_bva'] if row[1] == group]
        fig, ax = plt.subplots(figsize=(12, 5.6))
        ax.scatter([row[2] for row in rows], range(len(rows)), color='#28778a', s=100)
        ax.set(yticks=range(len(rows)), yticklabels=[row[0] + ' / ' + row[4] for row in rows],
               xlabel='Gi\u00e1 tr\u1ecb / s\u1ed1 k\u00fd t\u1ef1', ylabel='', title=group + ' - Robust BVA')
        ax.set_xticks(sorted({row[2] for row in rows}))
        save(fig, 'bva_extension_' + str(index), 'BVA')
    modules = sorted({row[1] for row in data['ep']})
    for index, module in enumerate(modules, 1):
        rows = [row for row in data['ep'] if row[1] == module]
        valid = [row[5] == data['valid_partition'] for row in rows]
        matrix = np.array([[int(value), int(not value)] for value in valid])
        fig, ax = plt.subplots(figsize=(9, max(3, len(rows) * 0.66 + 1.5)))
        sns.heatmap(matrix, annot=np.where(matrix, 'X', ''), fmt='', cmap=sns.light_palette('#28778a', as_cmap=True), cbar=False, linewidths=0.6, xticklabels=data['partition_columns'], yticklabels=[textwrap.fill(row[0] + ' - ' + row[2] + ': ' + row[3] + ' (' + row[4] + ')', 58) for row in rows], ax=ax)
        ax.set_title(module + ' - EP')
        ax.tick_params(axis='y', rotation=0)
        save(fig, 'ep_' + str(index), 'EP')
    for index, table in enumerate(data['decisions'], 1):
        rows = table['conditions'] + table['actions']
        values = [[1 if value in ('T', 'X') else 0 if value == 'F' else 0.5 for value in row[1:]] for row in rows]
        fig, ax = plt.subplots(figsize=(9, max(3.5, len(rows) * 0.7 + 1.5)))
        sns.heatmap(values, annot=[[str(v) for v in row[1:]] for row in rows], fmt='', cmap=sns.light_palette('#3f9dac', as_cmap=True), cbar=False, linewidths=0.6, xticklabels=table['rules'], yticklabels=[textwrap.fill(row[0], 43) for row in rows], ax=ax)
        ax.set_title(table['title'])
        ax.tick_params(axis='y', rotation=0)
        save(fig, 'decision_' + str(index), 'Decision')
    return media
