import plotly
import networkx

from math import sqrt, cos, sin


EDGE_SPACE = 2

HEAD_ANGLE = 0.5

NX_LAYOUTS = {
    'bipartite': networkx.bipartite_layout,
    'circular': networkx.circular_layout,
    'kamada_kawai': networkx.kamada_kawai_layout,
    'random': networkx.random_layout,
    'shell': networkx.shell_layout,
    'spring': networkx.spring_layout,
    'spectral': networkx.spectral_layout,
}


_frames = []


graph_width = 800
graph_height = 450

node_size = 20
node_color = (255, 255, 255)
node_labpos = 'middle center'

edge_width = 1
edge_color = (0, 0, 0)
edge_labfrac = 0.5
edge_labflip = False
edge_labdist = 10


def _scale(dx, dy, width, height, size):
    s2 = size**2

    x2 = (dx * width)**2
    y2 = (dy * height)**2

    return sqrt(s2 / (x2 + y2))


def _rotate(dx, dy, width, height, angle):
    dx *= width
    dy *= height

    rx = dx * cos(angle) - dy * sin(angle)
    ry = dx * sin(angle) + dy * cos(angle)

    return rx / width, ry / height


def _convert(color):
    r = color[0]
    g = color[1]
    b = color[2]

    if len(color) == 4:
        a = color[3]

        return 'rgba({}, {}, {}, {})'.format(r, g, b, a)

    return 'rgb({}, {}, {})'.format(r, g, b)


def _normalize_positions(g):
    xs = []
    ys = []
    for n in g.nodes:
        pos = g.nodes[n]['pos']
        xs.append(pos[0])
        ys.append(pos[1])

    xmin = min(xs)
    xmax = max(xs) - xmin
    ymin = min(ys)
    ymax = max(ys) - ymin

    for n in g.nodes:
        pos = g.nodes[n]['pos']
        x = (pos[0] - xmin) / (xmax - xmin)
        y = (pos[1] - ymin) / (ymax - ymin)
        g.nodes[n]['pos'] = (x, y)


def _build_node_trace(size, color, labpos):
    if labpos == 'hover':
        hoverinfo = 'text'
        mode = 'markers'
    else:
        hoverinfo = 'none'
        mode = 'markers+text'

    fontcolor = (0, 0, 0)
    if labpos == 'middle center':
        if 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2] < 128:
            fontcolor = (255, 255, 255)

    return {
        'x': [],
        'y': [],
        'text': [],
        'textposition': 'middle center' if labpos == 'hover' else labpos,
        'hoverinfo': hoverinfo,
        'mode': mode,
        'marker': {
            'size': size,
            'color': _convert(color),
            'line': {
                'width': edge_width,
                'color': _convert(edge_color),
            },
        },
        'textfont': {
            'color': _convert(fontcolor),
        },
    }


def _build_edge_trace(width, color):
    return {
        'x': [],
        'y': [],
        'hoverinfo': 'none',
        'mode': 'lines',
        'line': {
            'width': width,
            'color': _convert(color),
        },
    }


def _build_edge_label_trace():
    fontcolor = (0, 0, 0)

    return {
        'x': [],
        'y': [],
        'text': [],
        'textposition': 'middle center',
        'hoverinfo': 'none',
        'mode': 'text',
        'textfont': {
            'color': _convert(fontcolor),
        },
    }


def _build_layout(width, height):
    return {
        'showlegend': False,
        'width': width,
        'height': height,
        'margin': {
            'b': 0,
            'l': 0,
            'r': 0,
            't': 0,
        },
        'xaxis': {
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
        },
        'yaxis': {
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
        },
    }


def _add_node(g, n, node_trace):
    x, y = g.nodes[n]['pos']
    text = g.nodes[n]['label'] if 'label' in g.nodes[n] else ''

    node_trace['x'].append(x)
    node_trace['y'].append(y)
    node_trace['text'].append(text)


def _add_edge(g, width, height, n, m, local_size, local_width, edge_trace, edge_label_trace, labfrac, labflip, labdist):
    x0, y0 = g.nodes[n]['pos']
    x1, y1 = g.nodes[m]['pos']

    # parameters estimated from screenshots
    width = 0.9 * width - 24
    height = 0.9 * height - 24

    ratio = width / height

    dx = (y0 - y1) / ratio
    dy = (x1 - x0) * ratio

    space = (local_width + EDGE_SPACE) / 2

    if isinstance(g, networkx.DiGraph) and g.has_edge(m, n):
        s = _scale(dx, dy, width, height, space)
        x0 += s * dx
        y0 += s * dy
        x1 += s * dx
        y1 += s * dy

    edge_trace['x'].extend([x0, x1, None])
    edge_trace['y'].extend([y0, y1, None])

    s = _scale(dx, dy, width, height, labdist)
    if labflip:
        dx = -dx
        dy = -dy
    edge_label_trace['x'].append(x0 + labfrac * (x1 - x0) + s * dx)
    edge_label_trace['y'].append(y0 + labfrac * (y1 - y0) + s * dy)
    edge_label_trace['text'].append(g.edges[n, m]['label'] if 'label' in g.edges[n, m] else '')

    if isinstance(g, networkx.DiGraph):
        dx = x0 - x1
        dy = y0 - y1

        # adjustment estimated from screenshots
        radius = (local_size + local_width) / 1.8

        if g.has_edge(m, n):
            radius -= space

        s = _scale(dx, dy, width, height, radius)
        x0 = x1 + s * dx
        y0 = y1 + s * dy

        rx, ry = _rotate(dx, dy, width, height, -HEAD_ANGLE)
        s = _scale(rx, ry, width, height, radius)
        x1 = x0 + s * rx
        y1 = y0 + s * ry
        edge_trace['x'].extend([x0, x1, None])
        edge_trace['y'].extend([y0, y1, None])

        if not g.has_edge(m, n):
            rx, ry = _rotate(dx, dy, width, height, HEAD_ANGLE)
            s = _scale(rx, ry, width, height, radius)
            x1 = x0 + s * rx
            y1 = y0 + s * ry
            edge_trace['x'].extend([x0, x1, None])
            edge_trace['y'].extend([y0, y1, None])


def label(g):
    for n in g.nodes:
        g.nodes[n]['label'] = str(n)


def load(path, layout=None, *args, **kwargs):
    g = networkx.read_gml(path, label='id')

    has_positions = True
    for n in g.nodes:
        if 'x' in g.nodes[n] and 'y' in g.nodes[n]:
            g.nodes[n]['pos'] = (g.nodes[n]['x'], g.nodes[n]['y'])
            del g.nodes[n]['x']
            del g.nodes[n]['y']
        else:
            has_positions = False
            break

    if not has_positions:
        for n, pos in NX_LAYOUTS[layout](g, *args, **kwargs).items():
            g.nodes[n]['pos'] = pos

    _normalize_positions(g)

    return g


def show(g, toolbar=False):
    local_width = g.graph['width'] if 'width' in g.graph else graph_width
    local_height = g.graph['height'] if 'height' in g.graph else graph_height

    node_traces = {}
    for n in g.nodes:
        size = g.nodes[n]['size'] if 'size' in g.nodes[n] else node_size
        color = g.nodes[n]['color'] if 'color' in g.nodes[n] else node_color
        labpos = g.nodes[n]['labpos'] if 'labpos' in g.nodes[n] else node_labpos
        key = (size, color, labpos)
        if key not in node_traces:
            node_traces[key] = _build_node_trace(size, color, labpos)
        _add_node(g, n, node_traces[key])

    edge_traces = {}
    edge_label_trace = _build_edge_label_trace()
    for n, m in g.edges:
        size = g.nodes[m]['size'] if 'size' in g.nodes[m] else node_size
        width = g.edges[n, m]['width'] if 'width' in g.edges[n, m] else edge_width
        color = g.edges[n, m]['color'] if 'color' in g.edges[n, m] else edge_color
        labfrac = g.edges[n, m]['labfrac'] if 'labfrac' in g.edges[n, m] else edge_labfrac
        labflip = g.edges[n, m]['labflip'] if 'labflip' in g.edges[n, m] else edge_labflip
        labdist = g.edges[n, m]['labdist'] if 'labdist' in g.edges[n, m] else edge_labdist
        key = (width, color, labfrac, labflip, labdist)
        if key not in edge_traces:
            edge_traces[key] = _build_edge_trace(width, color)
        _add_edge(g, local_width, local_height, n, m, size, width, edge_traces[key], edge_label_trace, labfrac, labflip, labdist)

    data = list(edge_traces.values())
    data.append(edge_label_trace)
    data.extend(node_traces.values())

    figure = {
        'data': data,
        'layout': _build_layout(local_width, local_height),
    }

    plotly.offline.iplot(figure, config={'displayModeBar': toolbar}, show_link=False)


def setup():
    _frames.clear()


def snap(g):
    local_width = g.graph['width'] if 'width' in g.graph else graph_width
    local_height = g.graph['height'] if 'height' in g.graph else graph_height

    node_traces = []
    for n in g.nodes:
        size = g.nodes[n]['size'] if 'size' in g.nodes[n] else node_size
        color = g.nodes[n]['color'] if 'color' in g.nodes[n] else node_color
        labpos = g.nodes[n]['labpos'] if 'labpos' in g.nodes[n] else node_labpos
        node_trace = _build_node_trace(size, color, labpos)
        node_traces.append(node_trace)
        _add_node(g, n, node_trace)

    edge_traces = []
    edge_label_trace = _build_edge_label_trace()
    for n, m in g.edges:
        size = g.nodes[m]['size'] if 'size' in g.nodes[m] else node_size
        width = g.edges[n, m]['width'] if 'width' in g.edges[n, m] else edge_width
        color = g.edges[n, m]['color'] if 'color' in g.edges[n, m] else edge_color
        labfrac = g.edges[n, m]['labfrac'] if 'labfrac' in g.edges[n, m] else edge_labfrac
        labflip = g.edges[n, m]['labflip'] if 'labflip' in g.edges[n, m] else edge_labflip
        labdist = g.edges[n, m]['labdist'] if 'labdist' in g.edges[n, m] else edge_labdist
        edge_trace = _build_edge_trace(width, color)
        edge_traces.append(edge_trace)
        _add_edge(g, local_width, local_height, n, m, size, width, edge_trace, edge_label_trace, labfrac, labflip, labdist)

    data = edge_traces
    data.append(edge_label_trace)
    data.extend(node_traces)

    _frames.append({
        'number_of_nodes': g.number_of_nodes(),
        'number_of_edges': g.number_of_edges(),
        'width': local_width,
        'height': local_height,
        'data': data,
    })


def play():
    number_of_nodes = _frames[0]['number_of_nodes']
    number_of_edges = _frames[0]['number_of_edges']
    width = _frames[0]['width']
    height = _frames[0]['height']

    steps = []

    for index, frame in enumerate(_frames):
        if frame.pop('number_of_nodes') != number_of_nodes:
            raise ValueError('number of nodes varies from frame to frame')
        if frame.pop('number_of_edges') != number_of_edges:
            raise ValueError('number of edges varies from frame to frame')
        if frame.pop('width') != width:
            raise ValueError('width varies from frame to frame')
        if frame.pop('height') != height:
            raise ValueError('height varies from frame to frame')

        frame['name'] = index

        steps.append({
            'args': [[index], {'frame': {'redraw': False}, 'mode': 'immediate'}],
            'label': '',
            'method': 'animate',
        })

    # parameters estimated from screenshots
    width = 1.05 * width + 72
    height = 1.00 * height + 76

    layout = _build_layout(width, height)

    layout.update({
        'updatemenus': [
            {
                'buttons': [
                    {
                        'args': [None, {'frame': {'redraw': False}, 'fromcurrent': True}],
                        'label': 'Play',
                        'method': 'animate',
                    },
                    {
                        'args': [[None], {'frame': {'redraw': False}, 'mode': 'immediate'}],
                        'label': 'Pause',
                        'method': 'animate',
                    },
                ],
                'showactive': True,
                'type': 'buttons',
            },
        ],
        'sliders': [
            {
                'currentvalue': {'visible': False},
                'steps': steps,
            },
        ],
    })

    figure = {
        'data': _frames[0]['data'],
        'layout': layout,
        'frames': _frames,
    }

    plotly.offline.iplot(figure, config={'staticPlot': True}, show_link=False)


plotly.offline.init_notebook_mode(connected=True)
