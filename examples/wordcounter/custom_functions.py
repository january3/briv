def filter_by_total_number(files, min_n = 2):
    """ Filter a dictionary by the number of occurrences of its values.

    If a value is an integer, it is converted to lowercase and the number of total occurrences is counted.
    If the number of occurrences is greater than 2, the value is kept.
    If the value is not an integer, it is kept as is.
    """

    counts = { }

    # count total occurences
    for o in files:
        for k, v in o.items():
            if not isinstance(v, int):
                continue
            k = k.lower()
            counts[k] = counts.get(k, 0) + v

    # filter by min_n
    selected = [ k for k, v in counts.items() if v >= min_n ]

    filtered = [ { k: v for k, v in o.items() if k in selected or not isinstance(v, int) } for o in files ]

    return filtered

def remove_short_words(o, min_len = 3):
    """ Remove words that are shorter than min_len. """

    filtered = { k: v for k, v in o.items() if len(k) >= min_len or not isinstance(v, int)}

    return filtered

def filter_by_number(o, min_n = 2):
    """ Filter a dictionary by the number of occurrences of its values.

    If a value is an integer, it is converted to lowercase and the number of occurrences is counted.
    If the number of occurrences is greater than 2, the value is kept.
    If the value is not an integer, it is kept as is.
    """

    ret = { }

    for k, v in o.items():
        if not isinstance(v, int):
            ret[k] = v
            continue
        k = k.lower()
        ret[k] = ret.get(k, 0) + v

    ret = { k: v for k, v in ret.items() if not isinstance(v, int) or v > min_n }

    return ret
