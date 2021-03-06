
import time
from unittest import TestCase
from pathlib import Path

from humdum.io import open_maybe_gz
from humdum.utils import unlist1
from humdum.index import FmIndex as GenomeIndex


data_root = Path(__file__).parent / "data_for_tests/data"
genome_file = unlist1(data_root.glob("*.fa.gz"))


class TestFm(TestCase):
    def test_open_and_read(self):
        with open_maybe_gz(genome_file) as fd:
            fd.readline()
            fd.readline()
            fd.readline()

    def test_init_write(self):

        genome = ""

        with open_maybe_gz(genome_file) as fd:

            # skip first line
            line = fd.readline()
            line = fd.readline().rstrip()
            while True:

                genome += line
                line = fd.readline().rstrip()
                if not line:
                    break
        print("length", len(genome))

        print("init")
        index = GenomeIndex(genome)

        print("write")
        index.write(data_root / "genome.chr22.fa.gz.sa32_index")

    def test_time_to_read(self):

        t = time.perf_counter_ns()
        GenomeIndex.read(data_root / "genome.chr22.fa.gz.sa32_index")
        t = (time.perf_counter_ns() - t) * 1e-9

        # About 30s
        self.assertTrue(0 <= t < 300)

    def test_read_query(self):

        print("read")
        index = GenomeIndex.read(data_root / "genome.chr22.fa.gz.sa32_index")

        # The following strings are copied from the original genome

        ns = 10**(-9)

        print(len("AAAAGAATGCA"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("AAAAGAATGCA")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns * (end - start))

        print(len("CGACACCACCAAGGCCACCCACCTGCCT"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("CGACACCACCAAGGCCACCCACCTGCCT")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("GGCATTTACAACTAAAACATTGAATTCAGATTCATTTTCAGGTAATGATATAATCATGTG"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("GGCATTTACAACTAAAACATTGAATTCAGATTCATTTTCAGGTAATGATATAATCATGTG")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("AAAAGAATGCATTTCTGTATTTTTTGAAACCTTTTCTTTTGAAAACATAGTAATACATTT"
                  "CTACTCTAAAATAGAACTTAGCCTAAATACTTTCAAAACCTTTAGAATTTGGAAAAGAAA"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("AAAAGAATGCATTTCTGTATTTTTTGAAACCTTTTCTTTTGAAAACATAGTAATACATTT"
                                           "CTACTCTAAAATAGAACTTAGCCTAAATACTTTCAAAACCTTTAGAATTTGGAAAAGAAA")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("AAAAGAATGCA"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("AAAAGAATGCA")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("CGACACCACCAAGGCCACCCACCTGCCT"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("CGACACCACCAAGGCCACCCACCTGCCT")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("GGCATTTACAACTAAAACATTGAATTCAGATTCATTTTCAGGTAATGATATAATCATGTG"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("GGCATTTACAACTAAAACATTGAATTCAGATTCATTTTCAGGTAATGATATAATCATGTG")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))

        print(len("AAAAGAATGCATTTCTGTATTTTTTGAAACCTTTTCTTTTGAAAACATAGTAATACATTT"
                  "CTACTCTAAAATAGAACTTAGCCTAAATACTTTCAAAACCTTTAGAATTTGGAAAAGAAA"))
        start = time.perf_counter_ns()
        self.assertGreater(len(index.query("AAAAGAATGCATTTCTGTATTTTTTGAAACCTTTTCTTTTGAAAACATAGTAATACATTT"
                                           "CTACTCTAAAATAGAACTTAGCCTAAATACTTTCAAAACCTTTAGAATTTGGAAAAGAAA")), 0)
        end = time.perf_counter_ns()
        print("time: ", ns*(end - start))
