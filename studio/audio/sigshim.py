# numpy-only stand-ins for the few scipy.signal calls the sound scripts use (scipy.signal's compiled module is blocked
# by Windows Application Control on this PC). Filters are applied in the frequency domain: Butterworth magnitude
# responses (zero-phase) and exact biquad / IIR responses B(z)/A(z) evaluated on the FFT grid with zero padding so the
# tails do not wrap. Good enough for sound design and loudness metering.
import numpy as np


def butter(order, Wn, btype="low", fs=2.0, output="sos"):
    return ("butter", btype, Wn, order, fs)


def _mag(desc, n, square=False):
    _, kind, Wn, order, fs = desc
    f = np.fft.rfftfreq(n, 1.0 / fs)
    f = np.maximum(f, 1e-9)
    if kind in ("low", "lowpass"):
        h = 1 / np.sqrt(1 + (f / Wn) ** (2 * order))
    elif kind in ("high", "highpass"):
        h = 1 / np.sqrt(1 + (Wn / f) ** (2 * order))
    else:
        lo, hi = Wn
        f0, B = np.sqrt(lo * hi), hi - lo
        h = 1 / np.sqrt(1 + (((f * f - f0 * f0) / (f * B)) ** 2) ** order)
    return h * h if square else h


def _apply(desc, x, axis=-1, square=False):
    x = np.asarray(x, float)
    x = np.moveaxis(x, axis, -1)
    n = x.shape[-1]
    N = n + min(n, 4096)
    y = np.fft.irfft(np.fft.rfft(x, N, axis=-1) * _mag(desc, N, square), N, axis=-1)[..., :n]
    return np.moveaxis(y, -1, axis)


def sosfilt(sos, x, axis=-1):
    return _apply(sos, x, axis)


def sosfiltfilt(sos, x, axis=-1):
    return _apply(sos, x, axis, square=True)


def lfilter(b, a, x, axis=-1):
    x = np.asarray(x, float)
    x = np.moveaxis(x, axis, -1)
    n = x.shape[-1]
    N = n + min(max(n, 256), 48000)
    z = np.exp(-2j * np.pi * np.arange(N // 2 + 1) / N)
    B = np.polyval(np.asarray(b, float)[::-1], z)
    A = np.polyval(np.asarray(a, float)[::-1], z)
    y = np.fft.irfft(np.fft.rfft(x, N, axis=-1) * (B / A), N, axis=-1)[..., :n]
    return np.moveaxis(y, -1, axis)


def fftconvolve(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a) + len(b) - 1
    N = 1 << int(np.ceil(np.log2(n)))
    return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:n]


def resample_poly(x, up, down=1, axis=-1):
    x = np.asarray(x, float)
    x = np.moveaxis(x, axis, -1)
    n = x.shape[-1]
    X = np.fft.rfft(x, axis=-1)
    M = n * up
    Y = np.zeros(x.shape[:-1] + (M // 2 + 1,), complex)
    Y[..., : X.shape[-1]] = X
    y = np.fft.irfft(Y, M, axis=-1) * up
    return np.moveaxis(y, -1, axis)


def _win(n):
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)


def stft(x, fs=1.0, window="hann", nperseg=256, noverlap=None, boundary="zeros", padded=True):
    hop = nperseg - noverlap
    xp = np.pad(np.asarray(x, float), (nperseg // 2, nperseg // 2))
    extra = (-(len(xp) - nperseg)) % hop
    xp = np.pad(xp, (0, extra))
    nf = 1 + (len(xp) - nperseg) // hop
    idx = np.arange(nperseg)[None, :] + hop * np.arange(nf)[:, None]
    Z = np.fft.rfft(xp[idx] * _win(nperseg)[None, :], axis=-1).T
    return np.fft.rfftfreq(nperseg, 1.0 / fs), np.arange(nf) * hop / fs, Z


def istft(Z, fs=1.0, window="hann", nperseg=256, noverlap=None, boundary=True):
    hop = nperseg - noverlap
    fr = np.fft.irfft(Z.T, nperseg, axis=-1) * _win(nperseg)[None, :]
    nf = fr.shape[0]
    L = nperseg + hop * (nf - 1)
    y = np.zeros(L); wsum = np.zeros(L)
    w2 = _win(nperseg) ** 2
    for i in range(nf):
        y[i * hop: i * hop + nperseg] += fr[i]
        wsum[i * hop: i * hop + nperseg] += w2
    y /= np.maximum(wsum, 1e-8)
    if boundary:
        y = y[nperseg // 2:]
    return np.arange(len(y)) / fs, y
