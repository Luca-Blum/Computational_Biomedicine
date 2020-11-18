# RA, 2020-11-14

import pandas

from unittest import TestCase
from pathlib import Path
from tcga.utils import download
from idiva.io import open_maybe_gz

download_cache = (Path(__file__).parent.parent.parent / "input/download_cache")
assert download_cache.is_dir()
download = download.to(abs_path=download_cache)

URLS = {
    'ctrl': "https://public.bmi.inf.ethz.ch/eth_intern/teaching/cbm_2020/cbm_2020_project2/control_v2.vcf.gz",
    'case': "https://public.bmi.inf.ethz.ch/eth_intern/teaching/cbm_2020/cbm_2020_project2/case_processed_v2.vcf.gz",
}

# ref_len = {'ctrl': 2329288, 'case': 2360972} # v1
ref_len = {'ctrl': 2329288, 'case': 2360972}


class TestDf(TestCase):
    def test_makes_df_case(self):
        from idiva.clf.df import v0_df
        from idiva.io import ReadVCF
        with download(URLS['case']).now.open(mode='rb') as fd:
            with open_maybe_gz(fd) as fd:
                df = v0_df(ReadVCF(fd))
                self.assertTrue(len(df) > 0)
                self.assertEqual(len(df), ref_len['case'])

    def test_makes_df_ctrl(self):
        from idiva.clf.df import v0_df
        from idiva.io import ReadVCF
        with download(URLS['ctrl']).now.open(mode='rb') as fd:
            with open_maybe_gz(fd) as fd:
                df = v0_df(ReadVCF(fd))
                self.assertTrue(len(df) > 0)
                self.assertEqual(len(df), ref_len['ctrl'])

    def test_combines(self):
        from idiva.io import ReadVCF
        from idiva.clf.df import v0_df, join
        dfs = {}

        for k in URLS:
            with download(URLS[k]).now.open(mode='rb') as fd:
                with open_maybe_gz(fd) as fd:
                    dfs[k] = v0_df(ReadVCF(fd))

        df = join(case=dfs['case'], ctrl=dfs['ctrl'])
