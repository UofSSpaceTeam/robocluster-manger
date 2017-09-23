"""THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST)."""

import shlex
from subprocess import Popen
from time import sleep
import json  # For reading configuration files

class RoboProcess:
    """Manages and keeps track of a process."""

    def __init__(self, cmd):
        """Initialize a process containing command cmd."""
        self.cmd = cmd
        self.popen = None

    def start(self):
        """
        Start the process.

        Ignored if process is already running.
        """
        if not self.popen:
            args = shlex.split(self.cmd)
            self.popen = Popen(args)

    def stop(self):
        """
        Stop the process.

        Ignored if the process is not running.
        """
        if self.popen:
            self.popen.terminate()
            try:
                self.popen.wait(timeout=1)
            except TimeoutError:
                self.popen.kill()
                self.popen.wait()
            self.popen = None

    def status(self):
        """Return the status of a process."""
        raise NotImplementedError()

    def verify(self):
        """Verify if a process is running properly."""
        raise NotImplementedError()

    def fix(self):
        """Fix a process if its not running properly."""
        raise NotImplementedError()

class ProcessManager:
    """
    Manages processes that run in the robocluster framework.

    Processes are programs that can run independently from each other, in any
    language supported by the robocluster library.

    The ProcessManager is in charge of starting and stopping processes, and
    monitoring their status and handle the event of a crash or a process not
    responding.
    """

    def __init__(self, config_file):
        """Initialize a process manager."""
        self.processes = {}  # store processes by name
        if config_file:
            self.loadConfig(config_file)


    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped."""
        self.stop()
        return False

    def isEmpty(self):
        """Return if processes is empty."""
        return len(self.processes) == 0

    def loadConfig(self, file_name):
        if not isinstance(file_name, str):
            raise TypeError("Path to config file must be a string")
        with open(file_name) as file:
            config = json.load(file)
            local_processes = config['localhost']
            for name in local_processes:
                try:
                    self.createProcess(name, local_processes[name]['cmd'])
                except KeyError:
                    print('''Please use the following format:
"localhost" : {
    "process1": {"cmd" : "python program1.py"}
}
                            ''')

    def createProcess(self, name, command):
        """
        Create a process.

        Arguments:
        name    - name to identify process, must be unique to process manager.
        command - shell command for process to execute.
        """
        if name in self.processes:
            raise ValueError('Process with the same name exists: {name}')

        if not isinstance(command, str):
            raise ValueError('command must be a string')

        self.processes[name] = RoboProcess(command)


    def start(self, *names):
        """
        Start processes.

        If no arguments are provided, starts all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Starting:', process)
                self.processes[process].start()
            except KeyError:
                pass

    def stop(self, *names):
        """
        Stop processes.

        If no arguments are provided, stops all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Stopping:', process)
                self.processes[process].stop()
            except KeyError:
                pass


def main():
    """Run a process manager in the foreground."""

    with ProcessManager("config.json") as manager:
        manager.start()

        try:
            while True:
                # TODO: Verify processes.
                sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    exit(main())
