# HK, pre- 2020-10-09
# RA, 2020-10-09

from unittest import TestCase

import numpy as np

from humdum.align import Alignment
from humdum.align import SmithWaterman

from humdum.io import from_sam, from_fasta, AlignedSegment as Read
from humdum.utils import first, unlist1

from pathlib import Path


class TestAlign(TestCase):
    def test_indexing(self):
        aligner = SmithWaterman()

        alignment = first(aligner(ref="AB", query="A"))
        self.assertIsInstance(alignment, Alignment)

        alignment = first(aligner(ref="ABCDEFG", query="CDE"))
        self.assertEqual(alignment.loc_in_query, 0)
        self.assertEqual(alignment.loc_in_ref, 2)

    def test_semilocal(self):
        aligner = SmithWaterman()
        alignment = first(aligner(ref="ABCDEFG", query="ZBCDE", alignment_type='semi-local'))
        self.assertEqual(alignment.loc_in_query, 0)

    def test_aligner_on_integers(self):
        aligner = SmithWaterman()
        ref = "ABCDEFG"
        query = "CDE"
        A1 = list(aligner(ref=ref, query=query))
        to_int = (lambda s: np.array([ord(c) for c in s]))
        A2 = list(aligner(ref=to_int(ref), query=to_int(query)))
        self.assertCountEqual([a.cigar for a in A1], [a.cigar for a in A2])

    def test_smith_waterman_aligner(self, verbose=0):
        """
        Test if sw_aligner finds the right scoring matrix and the right matching blocks.
        """

        mutation_costs = {
            # Deletion
            'D': -2,
            # Insertion
            'I': -2,
            # Mutation
            'X': -1,
            # Match
            '=': 1,
        }
        aligner = SmithWaterman(mutation_costs=mutation_costs)
        matching_segments = []
        for alignment in aligner(ref='ATGGCCTC', query='ACGGCTC'):
            matching_segments.append(alignment.matching_subsegments())
        matching_segments = matching_segments[0]
        # true values from http://rna.informatik.uni-freiburg.de/Teaching/index.jsp?toolName=Smith-Waterman#
        true_scoring_matrix = [[0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 1, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 1, 0],
                               [0, 0, 0, 1, 1, 0, 0, 0],
                               [0, 0, 0, 1, 2, 0, 0, 0],
                               [0, 0, 1, 0, 0, 3, 1, 1],
                               [0, 0, 1, 0, 0, 1, 2, 2],
                               [0, 0, 0, 0, 0, 0, 2, 1],
                               [0, 0, 1, 0, 0, 1, 0, 3]]
        # true matching blocks calculated on paper
        true_matching_segments = [(3, 5)]

        if verbose:
            x, y, z = alignment.visualize(ref='ATGGCCTC', query='ACGGCTC')
            print(x)
            print(y)
            print(z)
            print('matching blocks = ', matching_segments)

        self.assertTrue(
            (
                    aligner._compute_scoring_matrix(ref='ATGGCCTC', query='ACGGCTC')
                    ==
                    np.array(true_scoring_matrix)
            ).all()
        )
        self.assertEqual(matching_segments, true_matching_segments)

    def test_sw_on_data_small(self, verbose=0):


        fa = Path(__file__).parent / "data_for_tests/data_small/genome.chr22.5K.fa"

        reference = str(unlist1(list(from_fasta(fa))).seq)

        in_file = list((Path(__file__).parent / "data_for_tests/data_small/").glob("*.sam")).pop()
        max_reads = 2
        for (read, __) in zip(from_sam(in_file), range(max_reads)):
            read: Read
            ref = reference
            query = read.seq
            aligner = SmithWaterman()
            for alignment in aligner(ref=ref, query=query):
                if verbose:
                    print(alignment.cigar, ' vs ', read.cigar)
                    print(read.mapq, ' vs ', alignment.score)
                    x, y, z = alignment.visualize(ref=ref, query=query)
                    print(x)
                    print(y)
                    print(z)
                    print(alignment.matching_subsegments(), ' vs ', read.cigar)
                self.assertEqual(
                    alignment.cigar, read.cigar,
                    f'{alignment.cigar} is not equal to cigar from sam file {read.cigar}'
                )

    def test_linker_adapter_Ingolia2009(self):
        oNTI200 = "CAAGCAGAAGACGGCATA"
        oNTI201 = "AATGATACGGCGACCACCGACAGGTTCAGAGTTCTACAGTCCGACG"
        oNTI202 = "                 CGACAGGTTCAGAGTTCTACAGTCCGACGATC"
        aligner = SmithWaterman()
        (list(aligner(ref=oNTI202, query=(oNTI201))))
