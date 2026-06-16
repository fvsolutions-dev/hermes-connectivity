"""Hermes nodes for UART / serial-port transports."""

from .serial_stream import SerialPortInfo, SerialStream, get_serial_ports

NODES = [SerialStream]

__all__ = ["SerialStream", "SerialPortInfo", "get_serial_ports", "NODES"]
