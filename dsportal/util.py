
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
