from unittest import TestCase
from aligner03.align import Smith_Waterman
from typing import Iterable
import pysam

Read = pysam.libcalignedsegment.AlignedSegment

from aligner03.io import from_sam as read_sam


def test_read_sam(file):
    with open(file, mode='rb') as fd_sam:
        for read in read_sam(fd_sam):
            read: Read

            # https://en.wikipedia.org/wiki/SAM_(file_format)
            # Col   Field	Type	Brief description
            #   1   QNAME	String  Query template NAME
            #   2   FLAG	Int	    bitwise FLAG
            #   3   RNAME	String  References sequence NAME
            #   4   POS     Int     1- based leftmost mapping POSition
            #   5   MAPQ	Int     MAPping Quality
            #   6   CIGAR	String	CIGAR String
            #   7   RNEXT	String	Ref. name of the mate/next read
            #   8   PNEXT	Int     Position of the mate/next read
            #   9   TLEN	Int     observed Template LENgth
            #  10	SEQ     String  segment SEQuence
            #  11	QUAL	String  ASCII of Phred-scaled base QUALity+33

            print("QNAME ", read.query_name)
            print("FLAG  ", read.flag)
            print("RNAME ", read.reference_id)
            print("POS   ", read.reference_start)
            print("MAPQ  ", read.mapping_quality)
            print("CIGAR ", read.cigartuples)
            print("RNEXT ", read.next_reference_id)
            print("PNEXT ", read.next_reference_start)
            print("TLEN  ", read.template_length)
            print("SEQ   ", read.query_sequence)
            print("QUAL  ", read.query_qualities)

            # print(read.get_aligned_pairs())
            print(read.get_blocks())


class TestAlign(TestCase):
    def test_smith_waterman_aligner(self, verbose=0):
        """
        Test if sw_aligner finds the right scoring matrix and the right matching blocks
        """
        mutation_costs = {
            # Deletion
            'D': -2,
            # Insertion
            'I': -2,
            # Mutation
            'X': -1,
            # Match
            '=': 3,
        }
        aligner = Smith_Waterman(mutation_costs=mutation_costs)
        for alignment in aligner(ref='ATGGCCTC', query='ACGGCTC'):
            matching_blocks = alignment.get_matching_blocks()
            # print(matching_blocks)
        # true values from http://rna.informatik.uni-freiburg.de/Teaching/index.jsp?toolName=Smith-Waterman#
        true_scoring_matrix = [[0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 1, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 1, 0],
                               [0, 0, 0, 1, 1, 0, 0, 0],
                               [0, 0, 0, 1, 2, 0, 0, 0],
                               [0, 0, 1, 0, 0, 3, 0, 1],
                               [0, 0, 1, 0, 0, 1, 0, 1],
                               [0, 0, 0, 0, 0, 0, 2, 0],
                               [0, 0, 1, 0, 0, 1, 0, 3]]
        # true matching blocks calculated on paper
        true_matching_blocks = [(1, 1), (3, 4), (6, 8)]

        if verbose:
            x, y, z = alignment.visualize(ref='ATGGCCTC', query='ACGGCTC')
            print(x)
            print(y)
            print(z)
            print('matching blocks = ', matching_blocks)

        assert (aligner.create_scoring_matrix(ref='ATGGCCTC', query='ACGGCTC') == true_scoring_matrix).all
        assert matching_blocks == true_matching_blocks

    def test_sw_on_data(self):
        from pathlib import Path
        from Bio import SeqIO

        fa = Path(__file__).parent.parent.parent / "input/data_small/genome.chr22.5K.fa"

        template = str(SeqIO.read(fa, format='fasta').seq)

        in_file = list((Path(__file__).parent.parent.parent / "input/data_small/").glob("*.sam")).pop()
        with open(in_file, mode='rb') as fd_sam:
            for read in read_sam(fd_sam):
                read: Read
                ref = template
                query = read.query_sequence
                aligner = Smith_Waterman()
                nbr_iterations = 1
                # somehow breaks after one iteration
                for i, alignment in enumerate(aligner(query=query, ref=ref)):
                    if i < nbr_iterations:
                        print(alignment.cigar_string, ' vs ', read.cigarstring)
                        print(read.query_qualities, ' vs ', alignment.score)
                        x, y, z = alignment.visualize(ref, query)
                        print(x)
                        print(y)
                        print(z)
                        print(alignment.get_matching_blocks(), ' vs ', read.cigar)
                        for alignment in aligner(ref=template, query=reversed):
                            self.assertEqual(alignment.cigar_string,
                                             read.cigarstring), f'{alignment.cigar_string} is not equal to cigar from sam file {read.cigarstring}'
                    else:
                        break


if __name__ == '__main__':
    pass
# test_smith_waterman_aligner(1)
# test_sw_on_data()
