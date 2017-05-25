
def get_ups_data():
    "Get UPS stats from apcupsd via apcaccess"

    if not path.exists('/sbin/apcaccess'):
        raise RuntimeError('/sbin/apcaccess not found')

    dump = commands.getstatusoutput('/sbin/apcaccess')

    if dump[0]:
        raise RuntimeError('Failed to run apcaccess command')

    lines = string.split(dump[1], "\n")

    info = {}
    for line in lines:
        m = re.search('(\w+)\s*:\s*(\d+)', line)
        if m:
            info[m.group(1)] = int(m.group(2))

    return info


def percent_bar(value,_max,_min=0):
    'Return a value, capped integer 0-100 to render a bar chart'
    val = (value-_min) / (_max-_min)
    val *= 100
    val = int(val)
    val = min(val,100)
    val = max(val,0)
    return val


