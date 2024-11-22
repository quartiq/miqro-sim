# %%
import logging

import numpy as np

from artiq import *
import miqro

logger = logging.getLogger(__name__)


class Example(EnvExperiment):
    def build(self):
        self.phaser0 = miqro.Phaser()
        self.miqro0 = self.phaser0.channel0.miqro

    @kernel
    def run(self):
        self.miqro0.set_profile(oscillator=0, profile=1, frequency=0, amplitude=1)
        #base = np.array([1.31, 0.41 + 1.095j])
        base = np.array([1.3078, 0.3848 + 1.1222j])
        #base = np.array([1.08333152, 0.83999943, 0.62181901]) + 1j*np.array([ 0, -6.16051289e-01, -7.64764113e-01])
        #base = np.r_[base, base[-2]]
        base = np.r_[np.tile(np.r_[base, base.conj()], 10), base[0]]
        iq = list(zip(base.real, base.imag))
        self.miqro0.set_window(start=0, iq=iq, period=100 * 4 * ns, order=3)
        self.miqro0.pulse(window=0x000, profiles=[1])


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import sim

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    t = Example()
    t.build()
    t.run()

    s = sim.MiqroSim(rtio_get_all())
    for ts, rf in s.get_rf():
        fig, ax = plt.subplots(2, sharex=True)
        t = np.arange(rf.shape[0]) * s.tau
        ax[0].plot(t, rf.real, t, rf.imag)
        ax[0].set_ylabel("i (blue), q (orange)")
        ax[1].plot(t, np.angle(rf) / np.pi)
        ax[1].plot(t, np.absolute(rf))
        ax[1].plot(
            t, np.angle(rf) / np.pi + 1/4 * np.sin(t * np.pi / 2 / (100 * 4 * ns))
        )
        ax[1].set_ylabel("phase/pi (blue), amplitude")
        ax[1].set_xlabel("time (s)")

        # ax[1].psd(rf, window=None, NFFT=rf.shape[0], Fs=1 / s.tau)
        # ax[1].set_xlim(-0.1 / s.tau, 0.1 / s.tau)
        fig, ax = plt.subplots()
        ax.plot(rf.real, rf.imag)
        x = np.exp(0.8j * np.sin(np.arange(100) / 100 * 2 * np.pi))
        ax.plot(x.real, x.imag)
        ax.set_aspect("equal")

# %%
