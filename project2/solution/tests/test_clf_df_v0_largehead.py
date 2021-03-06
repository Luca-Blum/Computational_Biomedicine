# RA, 2020-11-14

import io
import pandas as pd

from unittest import TestCase
from pathlib import Path

BASE = (Path(__file__).parent) / "data_for_tests"

MY_SPACE = BASE / F"my_space/{Path(__file__).stem}"
MY_SPACE.mkdir(exist_ok=True)

PATHS = {
    'ctrl': BASE / "large_head/control_v2.vcf",
    'case': BASE / "large_head/case_processed_v2.vcf",
}


class TestDf(TestCase):
    def test_makes_df(self):
        from idiva.clf.df import v0_df
        from idiva.io import ReadVCF
        from idiva.utils import seek_then_rewind

        for k in PATHS:
            with PATHS[k].open(mode='r') as fd:
                assert isinstance(fd, io.TextIOBase)
                with seek_then_rewind(fd):
                    datalines = list(ReadVCF(fd))
                with seek_then_rewind(fd):
                    df = v0_df(ReadVCF(fd))
                self.assertEqual(len(datalines), len(df))

    def test_combine(self):
        from idiva.io import ReadVCF
        from idiva.io.vcf import SEP
        from idiva.clf.df import v0_df, join, dtype_v0

        dfs = {}

        for k in PATHS:
            with PATHS[k].open(mode='r') as fd:
                assert isinstance(fd, io.TextIOBase)
                dfs[k] = v0_df(ReadVCF(fd))

        candidate = join(case=dfs['case'], ctrl=dfs['ctrl'])

        def read_csv(file) -> pd.DataFrame:
            return pd.read_csv(file, sep=SEP).astype(
                {
                    'CHROM': str,
                    'POS': int,
                    'ID': str,
                    'ALT0_case': float, 'ALT1_case': float, 'ALT2_case': float,
                    'ALT0_ctrl': float, 'ALT1_ctrl': float, 'ALT2_ctrl': float,
                }
            )

        ref_file = MY_SPACE / "reference.txt"

        # Hack to create the reference
        # candidate.to_csv(ref_file, sep=SEP, index=True)

        reference = read_csv(ref_file)

        # Write and read `candidate` to make comparable to `reference`
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w') as tf:
            candidate.to_csv(tf, sep=SEP, index=True)
            tf.flush()
            candidate = read_csv(tf.name)

        self.assertTrue(reference.equals(candidate))

    def test_join_does_something(self):
        from idiva.io import ReadVCF
        from idiva.clf.df import v0_df, join

        dfs = {}

        for k in PATHS:
            with PATHS[k].open(mode='r') as fd:
                assert isinstance(fd, io.TextIOBase)
                dfs[k] = v0_df(ReadVCF(fd))

        df = join(case=dfs['case'], ctrl=dfs['ctrl'])

        # print(df)
