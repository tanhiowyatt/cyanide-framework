
class Command:
    """Base class for shell commands."""
    
    def __init__(self, emulator):
        self.emulator = emulator
        self.fs = emulator.fs
        self.username = emulator.username

    async def execute(self, args: list[str], input_data: str = "") -> tuple[str, str, int]:
        """Execute the command asynchronously.
        
        Args:
            args: Command arguments (excluding command name).
            input_data: Input from stdin (e.g. from pipe).
            
        Returns:
            tuple: (stdout, stderr, return_code)
        """
        raise NotImplementedError
