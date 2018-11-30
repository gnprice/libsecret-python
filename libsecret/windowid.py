from subprocess import check_output, SubprocessError


def x_active_window_id() -> str:
    # '32x' and ' $0' are formatting options, to simplify our parsing.
    data = check_output(['xprop', '-root', '32x', ' $0', '_NET_ACTIVE_WINDOW'])
    return data.split(b' ', 1)[1].decode('utf-8')


def active_window_id() -> str:
    try:
        return x_active_window_id()
    except SubprocessError:
        raise RuntimeError(
            "Couldn't get active window ID to invoke prompt.  "
            "If your window system isn't X, add an implementation in libsecret.windowid.")
