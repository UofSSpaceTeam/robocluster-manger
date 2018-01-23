'''Example of a files that configures the processes and runs them'''
from ProcessManager import ProcessManager, RunOnce

PATH = './examples/demo'

process_list = [
    RunOnce("random-stream", f'python {}.format/random_stream.py'),
    RunOnce("printer", f'python {.format/printer.py'),
    # RunOnce("serialtest", f'python {PATH}.format/serial_test.py'),
]


with ProcessManager() as manager:
    # Initialize all the processes
    for proc in process_list:
        manager.addProcess(proc)

    # Start all processes
    manager.start()

    try:
        # Run asyncio event loop
        manager.run()
    except KeyboardInterrupt:
        pass # exit cleanly
