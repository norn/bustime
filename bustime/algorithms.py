import networkx as nx


def all_shortest_paths(graphx: nx.DiGraph, source: str, target: str, weight: str):
    pred, dist = nx.dijkstra_predecessor_and_distance(graphx, source, weight=weight)

    if target not in pred:
        raise nx.NetworkXNoPath('Target {} cannot be reached '
                                'from Source {}'.format(target, source))
    stack = [[target, 0]]
    top = 0
    while top >= 0:
        node, i = stack[top]
        if node == source:
            yield [p for p, n in reversed(stack[:top + 1])]
        if len(pred[node]) > i:
            top += 1
            if top == len(stack):
                if type(pred[node][i]) == str and top > 2 and \
                        type(pred[stack[top - 2][0]][i]) == str and \
                        type(pred[stack[top - 3][0]][i]) == str:
                    stack[top - 1][1] += 1
                    top -= 1
                else:
                    stack.append([pred[node][i], 0])
            else:
                stack[top] = [pred[node][i], 0]
        else:
            stack[top - 1][1] += 1
            top -= 1
