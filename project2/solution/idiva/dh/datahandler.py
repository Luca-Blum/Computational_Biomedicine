# LB 23-11-2020

import typing
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from idiva.io import ReadVCF
from idiva.utils import seek_then_rewind


class DataHandler:
    URL = {
        'vcf_37': "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh37/clinvar.vcf.gz",
        'vcf_38': "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz"
    }

    """
    A -> C = 0
    A -> G = 1
    A -> T = 2

    C -> A = 3
    C -> G = 4
    C -> T = 5

    G -> A = 6
    G -> C = 7
    G -> T = 8

    T -> A = 9
    T -> C = 10
    T -> G = 11
    """

    mapping = {'A': {'C': 1, 'G': 2, 'T': 2},
               'C': {'A': 3, 'G': 4, 'T': 5},
               'G': {'A': 6, 'C': 7, 'T': 8},
               'T': {'A': 9, 'C': 10, 'G': 11}}

    INIT_COLS = ["CHROM", "POS", "ID", "REF", "ALT"]
    CLINVAR_COLS = INIT_COLS
    CLINVAR_COLS_IDX = [0, 1, 2, 3, 4]

    def get_clf_datalines(self, df_clinvar: pd.DataFrame):
        """
        HK, 2020-11-21
        """
        for idx, row in tqdm(df_clinvar.iterrows(), total=len(df_clinvar), postfix='iterating df_clinvar'):
            if (str(row.ref) in ['A', 'C', 'G', 'T']) and (str(row.alt) in ['A', 'C', 'G', 'T']):

                line = {
                    'ID': row.id,
                    'CHROM': self.translate_chrom(row.chrom),
                    'POS': row['pos'],
                    'REF': row.ref,
                    'ALT': row.alt,
                    'VAR': self.mapping[row.ref][row.alt],
                    'label': 1 if row['CLNSIG'] == 'Pathogenic' else 0,

                }

                yield line

    def df_clinvar_to_clf_data(self, df_clinvar: pd.DataFrame) -> pd.DataFrame:
        """
        HK, 2020-11-21
        """
        dataframe = pd.DataFrame(data=self.get_clf_datalines(df_clinvar))
        dataframe = dataframe.drop_duplicates()
        print(dataframe)

        dataframe = dataframe.sort_values(by=['CHROM', 'POS'])

        dataframe = self.add_cadd_score(dataframe)
        dataframe = self.add_sift_score(dataframe)
        print(dataframe)
        dataframe = dataframe.drop(columns=['REF', 'ALT'])

        return dataframe

    def get_clinvar_clf_data(self, clinvar_file: str = 'vcf_37') -> pd.DataFrame:
        """
        Loads clinvar_clf_data suitable for a classifier.
        Looks for in "_cache" or creates if not found two files:
            - the "exploded" clinvar file as a dataframe compatible csv (exploded meaning that all information from
            the INFO column is extracted to its own column)

            - the dataframe compatible csv file containing all extracted and encoded features
            to train a classifier from the clinvar dataframe

        HK, 2020-11-22
        RA, 2020-11-22
        """

        from idiva.io import cache_df

        def maker_clinvar() -> pd.DataFrame:
            from idiva.db import clinvar_open
            from idiva.io import ReadVCF
            from idiva.db.clinvar import clinvar_to_df

            with clinvar_open(which=clinvar_file) as fd:
                return clinvar_to_df(ReadVCF(fd))

        df_clinvar = cache_df(name=("clinvar_" + clinvar_file), key=[clinvar_file], df_maker=maker_clinvar)
        df_clinvar_reduced = df_clinvar[df_clinvar['CLNSIG'].isin({'Pathogenic', 'Benign'})]

        return cache_df(name="clinvar_clf_data", key=[clinvar_file, "v01"],
                        df_maker=lambda: self.df_clinvar_to_clf_data(df_clinvar_reduced))

    def create_training_set(self, clinvar_file: str = 'vcf_37') -> typing.Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Returns training features and corresponding labels given a clinvar vcf file
        """

        # create training set containg
        # CHROM, POS, VAR, Polyphen2 score & success, sift score & success, cadd score & success
        clinvar_clf_data = self.get_clinvar_clf_data(clinvar_file)

        x_train = clinvar_clf_data.loc[:, clinvar_clf_data.columns != 'label']
        y_train = clinvar_clf_data.loc[:, clinvar_clf_data.columns == 'label']
        y_train.set_index(x_train.index)

        return x_train, y_train

    def create_test_set(self, vcf_file: str, vcf_file2: str = None) -> pd.DataFrame:

        frame = self.translate_vcf(vcf_file)

        if vcf_file2 is not None:
            baseframe2 = self.translate_vcf(vcf_file2)

            # merge both frames into one
            frame = pd.concat([frame, baseframe2])
            frame.drop_duplicates()

        return frame

    def translate_vcf(self, vcf_file: str) -> pd.DataFrame:
        """
        Returns a dataframe that contains the following features from a vcf file
        CHROM, POS, ID, VAR
        """

        cache = (Path(__file__).parent.parent.parent.parent / "input/download_cache").resolve()
        assert cache.is_dir()

        with open(str(cache) + "/" + vcf_file) as vcf:
            reader = ReadVCF(vcf)

            with seek_then_rewind(reader.fd, seek=reader.dataline_start_pos) as fd:

                dataframe = pd.read_csv(fd, sep='\t', usecols=range(len(DataHandler.INIT_COLS)), header=None,
                                        names=DataHandler.INIT_COLS,
                                        dtype={'CHROM': np.int, 'POS': np.int, 'ID': np.str, 'REF': np.str,
                                               'ALT': np.str})

                # Check if ALT contains only one value or several values seperated by ','
                assert (len([uni for uni in dataframe['ALT'].unique().tolist() if ',' in uni]) == 0)

                # store only SNP variants
                dataframe = dataframe[dataframe['REF'].apply(lambda x: {x}.issubset({'A', 'C', 'G', 'T'}))]
                dataframe = dataframe[dataframe['ALT'].apply(lambda x: {x}.issubset({'A', 'C', 'G', 'T'}))]

                # Check if only SNP
                for ref in dataframe['REF']:
                    assert (len(ref) == 1)

                for alt in dataframe['ALT']:
                    assert (len(alt) == 1)

                assert (set(dataframe['REF'].unique().tolist()).issubset({'A', 'C', 'G', 'T'}))
                assert (set(dataframe['ALT'].unique().tolist()).issubset({'A', 'C', 'G', 'T'}))

        dataframe['CHROM'] = pd.to_numeric(dataframe[['CHROM']].apply(self.translate_chrom, axis=1))

        dataframe = self.encode_ref_alt(dataframe)

        dataframe.drop_duplicates()

        # TODO:        same CHROM POS and rsID but not same REF & ALT
        #              same CHROM rsID REF ALT but not same POS
        #              => rsIDs are not completely unique !
        #              Ignore rsID (Kjong Nov 23)
        """
        
        print(len(dataframe['ID'].unique().tolist()))
        print(len(dataframe['ID'].tolist()))

                 CHROM       POS           ID REF ALT  VAR
        56638       17   1649616  rs544719440   A   G    2
        576511      17  19159733  rs540831825   A   G    2
        717227      17  27196477  rs202111951   T   C   10
        919995      17  34642425  rs568794696   C   A    3
        2105598     17  77663493  rs148485780   C   T    5
                 CHROM       POS           ID REF ALT  VAR
        56637       17   1649616  rs544719440   A   C    1
        576510      17  19159733  rs540831825   A   C    1
        717226      17  27196477  rs202111951   T   A    9
        919587      17  34540858  rs568794696   C   A    3
        2105592     17  77663435  rs148485780   C   T    5        

        print(dataframe[dataframe.duplicated('ID', keep='first')])
        print(dataframe[dataframe.duplicated('ID', keep='last')])
 
        assert(len(dataframe['ID'].unique().tolist()) == len(dataframe['ID'].tolist()))
       
        """

        return dataframe

    def encode_ref_alt(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Returns: Dataframe which contains CHROM, POS, ID and VAR
        where VAR interprets the SNP variant given REF and ALT
        """

        def map(refalt) -> int:
            ref = refalt[0]
            alt = refalt[1]

            return DataHandler.mapping[ref][alt]

        dataframe['VAR'] = dataframe[['REF', 'ALT']].apply(map, axis=1)

        return dataframe

    def add_sift_score(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Returns: status of sift score query and the corresponding sift score for a given rsID
        """
        # TODO: get sift score

        dataframe['SS'] = np.zeros(shape=(dataframe.shape[0], 1))
        dataframe['SP'] = np.zeros(shape=(dataframe.shape[0], 1))

        return dataframe

    def add_cadd_score(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Returns: CADD score and the phred score for a given dataframe containing CHROM, POS, REF, ALT
        """

        def fetch(chrom: int, poss: list, refs: list, alts: list, pbar: tqdm):

            from subprocess import Popen, PIPE

            next = {'A': {'start': 'C', 'C': 'G', 'G': 'T', 'T': 'start'},
                    'C': {'start': 'A', 'A': 'G', 'G': 'T', 'T': 'start'},
                    'G': {'start': 'A', 'A': 'C', 'C': 'T', 'T': 'start'},
                    'T': {'start': 'A', 'A': 'C', 'C': 'G', 'G': 'start'}}

            scores = np.zeros(shape=(len(poss), 1))
            phreds = np.zeros(shape=(len(poss), 1))

            current_pos = 0

            old_ref = ''
            new_ref = ''

            current_alt = ''


            status = 0
            count = 0

            # in case of an "error" ([E::hts_open_format] Failed to open ...) retry (max 100 times)
            while status == 0 and count < 100:

                process = Popen(
                    ['tabix',
                     'https://krishna.gs.washington.edu/download/CADD/v1.6/GRCh37/whole_genome_SNVs_inclAnno.tsv.gz',
                     'IndexFile', str(chrom) + ':' + str(poss[0]) + '-' + str(poss[-1])], stdout=PIPE)

                for idx, line in enumerate(process.stdout):

                    # Success, we got an output
                    status = 1

                    # interpret line as list
                    string_list = line.decode("utf-8").strip().split("\t")

                    # set new reference
                    new_ref = string_list[2]

                    # if we get the same information for the same alternative variant then skip it
                    if string_list[3] == current_alt:
                        continue
                    # set alternative to next nucleotide
                    else:
                        if old_ref != new_ref or next[new_ref][current_alt] == 'start':
                            current_alt = 'start'

                        current_alt = next[string_list[2]][current_alt]

                    # if the current line contains information about a asked position then store it
                    if int(string_list[1]) == poss[current_pos]:
                        """
                        # for debugging:
                        print("score", string_list[-2], "phred", string_list[-1], "pos", string_list[1], "ref", new_ref,
                              "alt",
                              current_alt)
                        """

                        scores[current_pos] = string_list[-2]
                        phreds[current_pos] = string_list[-1]

                        current_pos += 1

                        # break if we iterated over all positions
                        if current_pos == len(poss):
                            break

                    old_ref = new_ref

                process.terminate()
                count += 1

            pbar.update(1)

            return [scores, phreds]

        import concurrent.futures
        import multiprocessing

        chroms = dataframe['CHROM'].tolist()
        chroms = [self.translate_chrom_back(chrom) for chrom in chroms]

        poss = dataframe['POS'].tolist()
        alts = dataframe['REF'].tolist()
        refs = dataframe['ALT'].tolist()

        # start index of first bucket
        start_pos = 0
        buckets = [start_pos]

        current_chrom = chroms[0]

        # bucket spans a range of max cut_off nucleotide bases
        cut_off = 50000


        for idx, pos in enumerate(poss[1:], 1):
            if pos - poss[start_pos] > cut_off or current_chrom != chroms[idx]:
                start_pos = idx
                current_chrom = chroms[idx]
                buckets.append(idx)

        buckets.append(len(poss))

        futures = []

        with tqdm(total=len(buckets)-1, postfix='creating CADD scores') as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() - 1) as executor:

                for idx in range(len(buckets) - 1):

                    args = [chroms[idx],
                            poss[buckets[idx]:buckets[idx + 1]],
                            refs[buckets[idx]:buckets[idx + 1]],
                            alts[buckets[idx]:buckets[idx + 1]],
                            pbar]

                    futures.append(executor.submit(lambda p: fetch(*p), args))

        scores = futures[0].result()[0].ravel()
        phreds = futures[0].result()[1].ravel()

        for idx, future in enumerate(futures[1:], 1):

            scores = np.concatenate([scores, future.result()[0].ravel()])
            phreds = np.concatenate([phreds, future.result()[1].ravel()])

        print(scores)
        print(phreds)

        print(len(scores))
        print(len(phreds))

        print(scores.tolist().count(0))
        print(phreds.tolist().count(0))

        dataframe['CS'] = scores
        dataframe['CP'] = phreds

        return dataframe

    def translate_chrom(self, chrom: typing.Union[str, int]) -> int:
        """
        translate non integer chromosomes (X,Y & MT) to integers (23, 24 & 25)
        """
        if chrom == 'X':
            return 23
        elif chrom == 'Y':
            return 24
        elif chrom == 'MT':
            return 25
        else:
            return int(chrom)

    def translate_chrom_back(self, chrom: int) -> typing.Union[str, int]:
        if chrom == 23:
            return 'X'
        elif chrom == 24:
            return 'Y'
        elif chrom == 25:
            return 'MT'
        else:
            return chrom


if __name__ == '__main__':

    dh = DataHandler()

    x, y = dh.create_training_set()

    print(x)
    print(y)