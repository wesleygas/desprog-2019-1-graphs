import plotly
import networkx

from math import isinf, sqrt, cos, sin


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
graph_bottom = 0
graph_left = 0
graph_right = 0
graph_top = 0

node_size = 20
node_color = (255, 255, 255)
node_labpos = 'middle center'

edge_width = 1
edge_color = (0, 0, 0)
edge_labfrac = 0.5
edge_labdist = 10
edge_labflip = False


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
        x = (pos[0] - xmin) / xmax
        y = (pos[1] - ymin) / ymax
        g.nodes[n]['pos'] = (x, y)


def _build_graph_key(g):
    local_width = g.graph['width'] if 'width' in g.graph else graph_width
    local_height = g.graph['height'] if 'height' in g.graph else graph_height
    local_bottom = g.graph['bottom'] if 'bottom' in g.graph else graph_bottom
    local_left = g.graph['left'] if 'left' in g.graph else graph_left
    local_right = g.graph['right'] if 'right' in g.graph else graph_right
    local_top = g.graph['top'] if 'top' in g.graph else graph_top

    return local_width, local_height, local_bottom, local_left, local_right, local_top


def _build_node_key(g, n):
    size = g.nodes[n]['size'] if 'size' in g.nodes[n] else node_size
    color = g.nodes[n]['color'] if 'color' in g.nodes[n] else node_color
    labpos = g.nodes[n]['labpos'] if 'labpos' in g.nodes[n] else node_labpos

    return size, color, labpos


def _build_edge_key(g, n, m):
    size = g.nodes[m]['size'] if 'size' in g.nodes[m] else node_size
    width = g.edges[n, m]['width'] if 'width' in g.edges[n, m] else edge_width
    color = g.edges[n, m]['color'] if 'color' in g.edges[n, m] else edge_color
    labfrac = g.edges[n, m]['labfrac'] if 'labfrac' in g.edges[n, m] else edge_labfrac
    labdist = g.edges[n, m]['labdist'] if 'labdist' in g.edges[n, m] else edge_labdist
    labflip = g.edges[n, m]['labflip'] if 'labflip' in g.edges[n, m] else edge_labflip

    return size, width, color, labfrac, labdist, labflip


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
                'width': 1,
                'color': 'rgb(0, 0, 0)',
            },
        },
        'textfont': {
            'color': _convert(fontcolor),
        },
    }


def _build_node_label_trace(width, height, bottom, left, right, top):
    return {
        'x': [0.5, -left / width, 1 + right / width, 0.5],
        'y': [-bottom / height, 0.5, 0.5, 1 + top / height],
        'hoverinfo': 'none',
        'mode': 'markers',
        'marker': {
            'color': 'rgba(0, 0, 0, 0.0)',
            'line': {
                'width': 0,
            },
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


def _add_edge(g, width, height, n, m, local_size, local_width, edge_trace, edge_label_trace, labfrac, labdist, labflip):
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

        radius = (local_size / 2)

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


def unset_nodes(g, key):
    for n in g.nodes:
        if key in g.nodes[n]:
            del g.nodes[n][key]

def set_nodes(g, key, value):
    for n in g.nodes:
        g.nodes[n][key] = value

def set_nodes_size(g, value=node_size):
    set_nodes(g, 'size', value)

def set_nodes_color(g, value=node_color):
    set_nodes(g, 'color', value)

def set_nodes_labpos(g, value=node_labpos):
    set_nodes(g, 'labpos', value)


def unset_edges(g, key):
    for n, m in g.edges:
        if key in g.edges[n, m]:
            g.edges[n, m][key]

def set_edges(g, key, value):
    for n, m in g.edges:
        g.nodes[n, m][key] = value

def set_edges_width(g, value=edge_width):
    set_edges(g, 'width', value)

def set_edges_color(g, value=edge_color):
    set_edges(g, 'color', value)

def set_edges_labfrac(g, value=edge_labfrac):
    set_edges(g, 'labfrac', value)

def set_edges_labdist(g, value=edge_labdist):
    set_edges(g, 'labdist', value)

def set_edges_labflip(g, value=edge_labflip):
    set_edges(g, 'labflip', value)


def label_nodes(g, key=None):
    for n in g.nodes:
        if key is None:
            if isinstance(n, str):
                g.nodes[n]['label'] = n
            else:
                g.nodes[n]['label'] = str(n)
        else:
            if key in g.nodes[n]:
                value = g.nodes[n][key]

                if isinf(value):
                    g.nodes[n]['label'] = '∞'
                elif isinstance(value, str):
                    g.nodes[n]['label'] = value
                else:
                    g.nodes[n]['label'] = str(value)
            else:
                if 'label' in g.nodes[n]:
                    del g.nodes[n]['label']


def label_edges(g, key):
    for n, m in g.edges:
        if key in g.edges[n, m]:
            value = g.edges[n, m][key]

            if isinf(value):
                g.nodes[n]['label'] = '∞'
            elif isinstance(value, str):
                g.edges[n, m]['label'] = value
            else:
                g.edges[n, m]['label'] = str(value)
        else:
            if 'label' in g.edges[n, m]:
                del g.edges[n, m]['label']


def move(g, key, *args, **kwargs):
    layout = NX_LAYOUTS[key]

    for n, pos in layout(g, *args, **kwargs).items():
        g.nodes[n]['pos'] = pos

    _normalize_positions(g)


def load(path, key='random', *args, **kwargs):
    g = networkx.read_gml(path, label='id')

    if isinstance(g, networkx.MultiGraph):
        raise TypeError('plotnetx does not support multigraphs')

    has_positions = True

    for n in g.nodes:
        if 'x' not in g.nodes[n] or 'y' not in g.nodes[n]:
            has_positions = False
            break

    if has_positions:
        for n in g.nodes:
            g.nodes[n]['pos'] = (g.nodes[n]['x'], g.nodes[n]['y'])
            del g.nodes[n]['x']
            del g.nodes[n]['y']

        _normalize_positions(g)
    else:
        move(g, key, *args, **kwargs)

    for n, m in g.edges:
        if 'labflip' in g.edges[n, m]:
            value = g.edges[n, m]['labflip']

            if value == 0 or value == 1:
                g.edges[n, m]['labflip'] = bool(value)
            else:
                raise ValueError("attribute 'labflip' of edge ({}, {}) must be 0 or 1".format(n, m))

    return g


def show(g, nodes_key=None, edges_key=None, toolbar=False):
    if nodes_key is not None:
        label_nodes(g, nodes_key)

    if edges_key is not None:
        label_edges(g, edges_key)

    local_width, local_height, local_bottom, local_left, local_right, local_top = _build_graph_key(g)

    local_width += local_left + local_right
    local_height += local_bottom + local_top

    node_traces = {}
    node_label_trace = _build_node_label_trace(local_width, local_height, local_bottom, local_left, local_right, local_top)
    for n in g.nodes:
        size, color, labpos = _build_node_key(g, n)
        key = (size, color, labpos)
        if key not in node_traces:
            node_traces[key] = _build_node_trace(size, color, labpos)
        _add_node(g, n, node_traces[key])

    edge_traces = {}
    edge_label_trace = _build_edge_label_trace()
    for n, m in g.edges:
        size, width, color, labfrac, labdist, labflip = _build_edge_key(g, n, m)
        key = (width, color, labfrac, labdist, labflip)
        if key not in edge_traces:
            edge_traces[key] = _build_edge_trace(width, color)
        _add_edge(g, local_width, local_height, n, m, size, width, edge_traces[key], edge_label_trace, labfrac, labdist, labflip)

    data = list(edge_traces.values())
    data.append(edge_label_trace)
    data.extend(node_traces.values())
    data.append(node_label_trace)

    layout = _build_layout(local_width, local_height)

    if isinstance(g, networkx.DiGraph):
        layout['xaxis']['fixedrange'] = True
        layout['yaxis']['fixedrange'] = True

    figure = {
        'data': data,
        'layout': layout,
    }

    plotly.offline.iplot(figure, config={'displayModeBar': toolbar}, show_link=False)


def start():
    _frames.clear()


def rec(g, nodes_key=None, edges_key=None):
    if nodes_key is not None:
        label_nodes(g, nodes_key)

    if edges_key is not None:
        label_edges(g, edges_key)

    local_width, local_height, local_bottom, local_left, local_right, local_top = _build_graph_key(g)

    local_width += local_left + local_right
    local_height += local_bottom + local_top

    node_traces = []
    node_label_trace = _build_node_label_trace(local_width, local_height, local_bottom, local_left, local_right, local_top)
    for n in g.nodes:
        size, color, labpos = _build_node_key(g, n)
        node_trace = _build_node_trace(size, color, labpos)
        node_traces.append(node_trace)
        _add_node(g, n, node_trace)

    edge_traces = []
    edge_label_trace = _build_edge_label_trace()
    for n, m in g.edges:
        size, width, color, labfrac, labdist, labflip = _build_edge_key(g, n, m)
        edge_trace = _build_edge_trace(width, color)
        edge_traces.append(edge_trace)
        _add_edge(g, local_width, local_height, n, m, size, width, edge_trace, edge_label_trace, labfrac, labdist, labflip)

    data = edge_traces
    data.append(edge_label_trace)
    data.extend(node_traces)
    data.append(node_label_trace)

    _frames.append({
        'number_of_nodes': g.number_of_nodes(),
        'number_of_edges': g.number_of_edges(),
        'width': local_width,
        'height': local_height,
        'data': data,
    })


def play():
    if not _frames:
        raise ValueError('no frames')

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
