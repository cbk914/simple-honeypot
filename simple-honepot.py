#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: cbk914
import asyncio
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HoneypotProtocol(asyncio.Protocol):
    def __init__(self, service_name):
        self.service_name = service_name
        self.state = "initial"

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        logger.info(f"Connection from {peername} on {self.service_name}")
        self.transport = transport
        if self.service_name == "ssh":
            self.transport.write(b"SSH-2.0-OpenSSH_7.6p1 Ubuntu-4ubuntu0.5\r\n")
        elif self.service_name == "ftp":
            self.transport.write(b"220 Welcome to FTP service.\r\n")
        elif self.service_name == "telnet":
            self.transport.write(b"Welcome to Telnet service.\r\n")

    def data_received(self, data):
        message = data.decode()
        logger.info(f"Received data on {self.service_name}: {message.strip()}")
        if self.service_name == "ftp":
            self.process_ftp_commands(message)
        elif self.service_name == "telnet":
            self.transport.write(b"Command not found.\r\n")

    def process_ftp_commands(self, message):
        if self.state == "initial" and message.startswith("USER"):
            self.transport.write(b"331 Please specify the password.\r\n")
            self.state = "user_received"
        elif self.state == "user_received" and message.startswith("PASS"):
            self.transport.write(b"230 Login successful.\r\n")
            self.state = "authenticated"
        else:
            self.transport.write(b"500 Invalid command.\r\n")

    def connection_lost(self, exc):
        logger.info(f"Connection closed on {self.service_name}")

async def create_honeypot_service(port, service_name):
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda: HoneypotProtocol(service_name), "0.0.0.0", port)
    logger.info(f"{service_name} honeypot running on port {port}")

    async with server:
        await server.serve_forever()

async def main(services):
    tasks = []
    for service, port in services.items():
        tasks.append(create_honeypot_service(port, service))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--services", nargs="+", help="List of services and ports (e.g., ssh:2222 ftp:2121 telnet:2323)")
    args = parser.parse_args()

    services = {}
    for s in args.services:
        service, port = s.split(":")
        services[service] = int(port)

    asyncio.run(main(services))
