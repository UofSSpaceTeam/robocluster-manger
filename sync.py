"""
Sync module for robocluster process manager.

Implements a context managers for the process manager server and for services.
"""

__author__ = 'Jarrod Pas <j.pas@usask.ca>'

import asyncio
import json
import socket
import sys
from argparse import ArgumentParser
from ipaddress import ip_network
from time import time


class BaseSocketLoop:
    """Base context for event loops using sockets."""

    def __init__(self):
        """Initialize the event loop."""
        self.loop = asyncio.new_event_loop()

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager."""
        self.close()
        return False

    def run(self):
        """Run the event loop forever."""
        self.loop.run_forever()

    def stop(self):
        """Stop the event loop."""
        self.loop.stop()

    def close(self):
        """Close the event loop in a clean manner."""
        self.stop()
        for task in asyncio.Task.all_tasks(loop=self.loop):
            task.cancel()
        self.loop.run_forever()  # wait for all tasks to be cancelled
        self.loop.close()

    @staticmethod
    def socket(*args, **kwargs):
        """Create a socket."""
        sock = socket.socket(*args, **kwargs)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

    def accept(self, sock):
        """Accept a connection."""
        return self.loop.sock_accept(sock)

    def connect(self, sock, addressess):
        """Connect to a remote socket at addressess."""
        return self.loop.sock_connect(sock, addressess)

    async def recv(self, sock):
        """Receive data from the socket."""
        packet = await self.loop.sock_recv(sock, 4096)
        return self.decode(packet)

    def recvfrom(self, sock, future=None):
        """Receive data from the socket."""
        fileno = sock.fileno()
        if future is None:
            future = self.loop.create_future()
        else:
            self.loop.remove_reader(fileno)

        try:
            packet, address = sock.recvfrom(4096)
        except (BlockingIOError, InterruptedError):
            self.loop.add_reader(fileno,
                                 self.recvfrom, sock, future)
        else:
            data = self.decode(packet)
            future.set_result((data, address))

        return future

    def send(self, sock, data):
        """Send data to the socket."""
        packet = json.dumps(data).encode('utf-8')
        return self.loop.sock_sendall(sock, packet)

    def sendto(self, sock, data, address, future=None):
        """Send data to the socket."""
        fileno = sock.fileno()
        if future is None:
            future = self.loop.create_future()
        else:
            self.loop.remove_writer(fileno)

        if not data:
            return

        try:
            packet = self.encode(data)
            nbytes = sock.sendto(packet, address)
        except (BlockingIOError, InterruptedError):
            self.loop.add_writer(fileno,
                                 self.sendto, sock, data, address, future)
        else:
            future.set_result(nbytes)

        return future

    @staticmethod
    def decode(packet):
        """Decode a packet."""
        return packet

    @staticmethod
    def encode(packet):
        """Encode a packet."""
        return packet


class JSONSocketLoop(BaseSocketLoop):
    """Socket loop with JSON as transport."""

    @staticmethod
    def decode(packet):
        """Decode a packet from JSON."""
        try:
            return json.loads(packet)
        except json.JSONDecodeError:
            # "Doesn't look like anything to me." - Dolores
            return None

    @staticmethod
    def encode(packet):
        """Encode a packet to JSON."""
        return json.dumps(packet).encode('utf-8')


class Server(JSONSocketLoop):
    """Server to keep track of services."""

    def __init__(self, subnet, port):
        """Initialize server."""
        super().__init__()

        self.broadcast = ip_network(subnet).broadcast_address.compressed
        self.port = port

    def run(self):
        """Run event loop forever."""
        self.loop.create_task(self.discover())
        self.loop.create_task(self.server())
        super().run()

    async def discover(self):
        """Loop for discovering services."""
        with self.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((self.broadcast, self.port))
            while True:
                data, address = await self.recvfrom(sock)
                if data:
                    print(f'discover: {address} > {data}')

    async def server(self):
        """Loop for serving requests for where services reside."""
        with self.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', self.port))
            sock.listen()
            while True:
                conn, address = await self.accept(sock)
                self.loop.create_task(self.handler(conn, address))

    async def handler(self, conn, address):
        """Handle request for services."""
        with conn:
            data = await self.recv(conn)
            if data:
                print(f'handle: {address} > {data}')


class Service(JSONSocketLoop):
    """Service for the server to track."""

    def __init__(self, subnet, port):
        """Initialize service."""
        super().__init__()

        self.broadcast = ip_network(subnet).broadcast_address.compressed
        self.port = port

    def run(self):
        """Run the event loop forever."""
        self.loop.create_task(self.advertise())
        super().run()

    async def advertise(self):
        """Advertise service to server."""
        sock = self.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            address = self.broadcast, self.port
            data = {'time': time()}
            await self.sendto(sock, data, address)
            await asyncio.sleep(1)


def server(args):
    """Run a server."""
    with Server(args.subnet, args.port) as server_:
        try:
            server_.run()
        except KeyboardInterrupt:
            pass


def service(args):
    """Run a service."""
    with Service(args.subnet, args.port) as service_:
        try:
            service_.run()
        except KeyboardInterrupt:
            pass


def main(args):
    """Parse arguments and run main routine."""
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    server_parser = subparsers.add_parser('server')
    server_parser.add_argument('subnet')
    server_parser.add_argument('port', type=int)
    server_parser.set_defaults(func=server)

    service_parser = subparsers.add_parser('service')
    service_parser.add_argument('subnet')
    service_parser.add_argument('port', type=int)
    service_parser.set_defaults(func=service)

    args = parser.parse_args(args)
    return args.func(args)


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
