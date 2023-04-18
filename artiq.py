# ARTIQ mock environment

import logging
import typing

logger = logging.getLogger(__name__)

TInt32 = int
TFloat32 = float
TList = typing.List

Hz = 1.0
kHz = 1e3 * Hz
MHz = 1e6 * Hz
s = 1.0
ms = 1e-3 * s
us = 1e-6 * s
ns = 1e-9 * s

rtio_period = 4 * ns


class Timeline:
    def __init__(self):
        self.cursor = 0
        self.events = []


__timeline = Timeline()


def rtio_output(addr, data):
    logger.debug(f"RTIO @{__timeline.cursor:#010x}: {addr:#04x} < {data:#010x}")
    __timeline.events.append((__timeline.cursor, addr, data))


def rtio_get_all():
    global __timeline
    events = __timeline.events[:]
    del __timeline.events[:]
    __timeline.cursor = 0
    return events


def now_mu():
    return __timeline.cursor


def at_mu(t):
    global __timeline
    __timeline.cursor = t


def delay_mu(t):
    global __timeline
    __timeline.cursor += t


def delay(t):
    delay_mu(seconds_to_mu(t))


def seconds_to_mu(t):
    return int(round(t / rtio_period))


class EnvExperiment:
    pass


def kernel(f):
    return f


def rpc(f):
    return f


def portable(f):
    return f
