import unittest
from itertools import islice
from six.moves import zip
import pickle
import mock
from mock import MagicMock
from six import StringIO
import hashlib

from pysstv import sstv
from pysstv.sstv import SSTV
from pysstv.tests.common import get_asset_filename


class TestSSTV(unittest.TestCase):

    def setUp(self):
        self.s = SSTV(False, 48000, 16)
        self.s.VIS_CODE = 0x00
        self.s.SYNC = 7

    def test_horizontal_sync(self):
        horizontal_sync = self.s.horizontal_sync()
        expected = (1200, self.s.SYNC)
        actual = next(iter(horizontal_sync))
        self.assertEqual(expected, actual)

    def test_gen_freq_bits(self):
        gen_freq_bits = self.s.gen_freq_bits()
        expected = [(1900, 300),
                    (1200, 10),
                    (1900, 300),
                    (1200, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1300, 30),
                    (1200, 30)]
        actual = list(islice(gen_freq_bits, 0, 1000))
        self.assertEqual(expected, actual)

    # FIXME: Instead of using a test fixture, 'expected' should be synthesized?
    def test_gen_values(self):
        gen_values = self.s.gen_values()
        with open(get_asset_filename("SSTV_gen_values.p"), 'rb') as f:
            expected = pickle.load(f)
        for e, g in zip(expected, gen_values):
            self.assertAlmostEqual(e, g, delta=0.000000001)

    def test_gen_samples(self):
        gen_values = self.s.gen_samples()
        # gen_samples uses random to avoid quantization noise
        # by using additive noise, so there's always a chance
        # of running the code two consecutive times on the same machine
        # and having different results.
        # https://en.wikipedia.org/wiki/Quantization_%28signal_processing%29
        sstv.random = MagicMock(return_value=0.4)  # xkcd:221
        with open(get_asset_filename("SSTV_gen_samples.p"), 'rb') as f:
            expected = pickle.load(f)
        actual = list(islice(gen_values, 0, 1000))
        for e, a in zip(expected, actual):
            self.assertAlmostEqual(e, a, delta=1)

    def test_write_wav(self):
        self.maxDiff = None
        sio = StringIO()
        sio.close = MagicMock()  # ignore close() so we can .getvalue()
        mock_open = MagicMock(return_value=sio)
        with mock.patch('__builtin__.open', mock_open):
            self.s.write_wav('unittest.wav')
        expected = 'dd7eed880ab3360fb79ce09c469deee2'
        data = sio.getvalue()
        actual = hashlib.md5(data).hexdigest()
        self.assertEqual(expected, actual)

    def test_init(self):
        self.assertEqual(self.s.image, False)
        self.assertEqual(self.s.samples_per_sec, 48000)
        self.assertEqual(self.s.bits, 16)
