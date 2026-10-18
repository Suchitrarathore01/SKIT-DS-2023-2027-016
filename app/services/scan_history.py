scan_history = []


def add_scan(result: dict):
    scan_history.append(result)


def get_scan_history():
    return scan_history