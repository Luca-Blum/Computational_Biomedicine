# RA, 2020-10-10

from unittest import TestCase
from pathlib import Path

from humdum.main import AllTheKingsHorses
from humdum.utils import relpath, unlist1

from humdum.io import AlignedSegment
from humdum.io import from_sam

from itertools import count

data_root = Path(__file__).parent / "data_for_tests"
source_path = data_root / "data_small"


class TestATKH(TestCase):
    def test_on_data_small(self):
        (read_file1, read_file2) = sorted(source_path.glob("*.fq"))
        genome_file = unlist1(source_path.glob("genome*.fa"))

        sam = AllTheKingsHorses.from_files(fa=genome_file, fq1=read_file1, fq2=read_file2)

        mine: AlignedSegment
        theirs: AlignedSegment
        for ((mine, theirs), n) in zip(zip(sam.alignments, from_sam(unlist1(source_path.glob("*.sam")))), count()):
            # See io/sam.py for the explanations
            self.assertEqual(mine.flag.is_minus_strand, bool(theirs.flag.value & 16))
            self.assertEqual(mine.flag.is_secondary_alignment, bool(theirs.flag.value & 256))

            cigar_match = (mine.cigar == theirs.cigar)
            pos_match = (mine.pos == theirs.pos)
            tlen_match = (mine.tlen == theirs.tlen)

            if cigar_match and pos_match:
                print(F"Read {mine.qname} looks good.")
            else:
                print(F"Read {mine.qname} does not match.")
                print(F"Mine:  ", mine.cigar, "at", mine.pos)
                print(F"Theirs:", theirs.cigar, "at", theirs.pos)
                print(F"Read:  ", mine.seq)
                # print(F"Neighborhood:  ", aligned_segments.ref_genome[(mine.pos - 10):(mine.pos + 10 + len(mine.seq))])

            if not tlen_match:
                print(F"tlen mismatch: {mine.tlen} (mine) vs {theirs.tlen} (theirs)")


