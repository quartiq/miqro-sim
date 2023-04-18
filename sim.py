import logging
import numpy as np

from artiq import *
import miqro

logger = logging.getLogger(__name__)


class MiqroSim:
    """MIQRO simulator."""

    def __init__(self, events):
        self.events = events
        self.tau = 4 * ns
        # state
        self.profile = np.zeros((16, 32), "i4,u2,u2")
        self.window = np.zeros((1 << 10, 2), "i2")
        self.cfg = np.zeros(16, "u1")

    def get_rf(self):
        ev = np.array(self.events, "i8,u4,u4").ravel()
        ev.sort(order=["f0"])
        addr = 0
        for t, a, d in ev:
            if a == miqro.PHASER_ADDR_MIQRO_MEM_ADDR | 0x80:
                addr = d
            elif a == miqro.PHASER_ADDR_MIQRO_MEM_DATA | 0x80:
                self._handle_mem(addr, d)
                addr += 1
            elif 0 <= a - 0x100 < 3:
                self._handle_cfg(a - 0x100, d)
            else:
                raise ValueError("addr", a)
            if a - 0x100 == 0:
                yield self._handle_trigger(t, d)

    def _handle_mem(self, addr, data):
        channel = addr >> 15
        if channel != 0:
            raise NotImplementedError
        if addr & miqro.PHASER_MIQRO_SEL_PROFILE:
            mem = self.profile
        else:
            mem = self.window
        mem = mem.view("u4").ravel()
        mem[addr & 0x3FFF] = data

    def _handle_cfg(self, a, d):
        split = [0, 4, 10, 16]
        for osc in range(*split[a : a + 2]):
            idx = (osc - split[a]) * 5
            if a == 0:
                idx += 10
            profile = (d >> idx) & 0x1F
            self.cfg[osc] = profile

    def _handle_trigger(self, t, d):
        logger.info(f"trigger t={t}, {t*rtio_period:g} s")
        window = self._get_window(d & 0x3FF)
        ts = int(t * (rtio_period / self.tau))
        sig = self._get_sum(ts, window.shape[0]) * window / (1 << 31)
        return ts, sig

    def _get_sum(self, ts, n):
        sum = np.zeros(n, "c8")
        for osc in range(16):
            f, a, p = self.profile[osc, self.cfg[osc]]
            if a == 0:
                continue
            logging.info(
                f"osc {osc}: profile {self.cfg[osc]} ({f / (1 << 32) / self.tau / MHz:g} MHz, {a / (1 << 16):g} @{p / (1 << 16):g} turn)"
            )
            p1 = (f * (ts - 1) + (p << 16)).astype(np.int32)
            p1 = (
                np.cumsum(np.lib.stride_tricks.as_strided(np.array(f), (n,), (0,))) + p1
            )
            sum += a * np.exp(2j * np.pi / (1 << 32) * p1)
        return sum

    def _get_window(self, start):
        header = self.window[start].view("u4").ravel()[0]
        length = header & 0x3FF
        rate = ((header >> 10) & 0x3FF) + 1
        shift = (header >> 22) & 0x3F
        order = (header >> 28) & 0x3
        head = (header >> 30) & 1
        tail = (header >> 31) & 1

        if not (head and tail):
            raise NotImplementedError

        duration = (length + order) * rate - order
        logger.info(
            f"window start={start:#x} len={length:#x} order={order} rate={rate}: {duration * self.tau / us:g} µs duration"
        )
        window = self.window[start + 1 : start + length + 1]
        window = np.repeat(window[:, 0] + 1j * window[:, 1], rate)
        rect = np.ones(rate)
        for _ in range(order):
            window = np.convolve(window, rect)
        assert window.shape[0] == duration
        return window / (1 << shift)
