def process_terminal_input(input_str: str, preserve_control: bool = False) -> str:
    """
    Handles common terminal control characters.
    If preserve_control is True, it returns control characters as-is (except for BS/DEL processing).
    """
    res: list[str] = []
    # Simplified ANSI arrow handling for line-based emulation
    # If the user presses Up multiple times, we'll see sequences of \x1b[A

    # First, handle backspaces/deletes
    for char in input_str:
        if char in ("\x08", "\x7f"):
            if res:
                res.pop()
            continue

        if not preserve_control:
            # Ctrl+C or Ctrl+U: Clear the current buffer/line (Shell behavior)
            if char in ("\x03", "\x15"):
                res = []
                continue

            # Strip most control characters (0-31) except whitespace and ESC
            if ord(char) < 32 and char not in ("\n", "\r", "\t", "\x1b"):
                continue

        res.append(char)

    return "".join(res)
