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
    def setup(self):
        # Configure example data for some profiles on some oscillators
        # e.g.: profile 3 on oscillator 11 will be 3 MHz, 0.3 amplitude full scale,
        # -0.3 turn (coherent) phase
        for osc in [0, 4, 11]:
            for profile in [1, 2, 3]:
                self.miqro0.set_profile(
                    osc,
                    profile,
                    frequency=1 * MHz * (osc - 8),
                    amplitude=0.1 * profile,
                    phase=-0.1 * profile,
                )
        # Configure some window data and interpolation parameters
        iq = [(1, 0), (1, 0), (0, 1), (0, 1)]
        # Pulse shape will be:
        # * n = len(iq) = 4 samples full scale
        # * Note the window has a pi/2 phase shift for the second half.
        # * r = 128 cubic (Parzen window) interpolation:
        #   Each window memory sample will last r tau = 512 ns and those samples
        #   will see cubic interpolation like this:
        #   Repeat each input sample r = 128 times, convolve the sequence of
        #   n * r samples with a rectangular window of length r = 128.
        #   Do that order = 3 times.
        # * The output of the shaper is thus a rise to full scale,
        #   and then a pi/2 phase shift, then a tail to zero again, all "smooth"
        #   in the sense of cubic interpolation: a continuous second derivative
        #   of I and Q (piecewise constant third derivative).
        # * Total pulse duration (shape support) is ((n + order) * r - order) * tau = 3.572 µs.
        self.miqro0.set_window(start=0, iq=iq, period=128 * 4 * ns, order=3)

    @kernel
    def pulse(self):
        # Choose example profiles and phase offsets
        # profiles[oscillator index] = profile index
        profiles = [0] * 16
        profiles[0] = 1
        profiles[4] = 2
        profiles[11] = 3
        # Choose window start address
        window = 0x000
        # Trigger the pulse
        # This will load frequencies and amplitudes for the oscillators,
        # compute the initial oscillator phases, add the offsets,
        # load the window samples, interpolate them and multiply the window with
        # the sum of the oscillator outputs, all in gateware with matched latency accross
        # all data paths. The DAC will interpolate further (by 4),
        # shift everything by frequency f1 and then the IQ mixer will shift
        # further by f2.
        # The encoded pulse words can just as well be computed offline with `encode()` and then emitted with `pule_mu()` for even higher rates.
        self.miqro0.pulse(window, profiles)

    @kernel
    def run(self):
        # self.phaser0.init()
        # self.miqro0.reset()
        self.setup()
        self.pulse()


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
        fig, ax = plt.subplots(2)
        t = np.arange(rf.shape[0]) * s.tau
        ax[0].plot(t, rf.real, t, rf.imag)
        ax[1].psd(rf, window=None, NFFT=rf.shape[0], Fs=1 / s.tau)
        ax[1].set_xlim(-0.1 / s.tau, 0.1 / s.tau)

# %%
