def process_terminal_input(input_str: str, preserve_control: bool = False) -> str:
    """
    Handles common terminal control characters.
    If preserve_control is True, it returns control characters as-is (except for BS/DEL processing).
    """
    res: list[str] = []

    for char in input_str:
        if char in ("\x08", "\x7f"):
            if res:
                res.pop()
            continue

        if not preserve_control:
            if char in ("\x03", "\x15"):
                res = []
                continue
            if ord(char) < 32 and char not in ("\n", "\r", "\t", "\x1b"):
                continue

        res.append(char)

    return "".join(res)
