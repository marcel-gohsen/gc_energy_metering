import subprocess

from environments.environment import Environment
from error_handling.error_handler import ErrorHandler


class LocalEnvironment(Environment):

    def execute(self, benchmark):
        while benchmark.has_next_executable():
            command = benchmark.next_executable()

            print("Execute: " + command)
            process = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()

            status = process.returncode
            try:
                if status != 0:
                    raise RuntimeError
            except RuntimeError as exc:
                ErrorHandler.handle("Env",
                                    "Execution returned with error: \"" + err.decode("utf-8").replace("\n", "") + "\"",
                                    exc, terminate=False)
