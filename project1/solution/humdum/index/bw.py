
# How the Burrows Wheeler transform works by Ben Langmead
# https://www.youtube.com/watch?v=4n7NPk5lwbI
# https://www.youtube.com/watch?v=6BJbEWyO_N0
# https://www.youtube.com/watch?v=GWFb_C4IR14&t=1035s

# Manber and Myers:
# Sufix Arrays: A New Method for On-Line String Searches
# https://courses.cs.washington.edu/courses/cse590q/00au/papers/manber-myers_soda90.pdf

# Kärkkäinen and Sanders:
# Simple Linear Work Suffix Array Construction
# https://www.cs.helsinki.fi/u/tpkarkka/publications/icalp03.pdf

from typing import List, Tuple
from bitarray import frozenbitarray
import numpy as np
from humdum.utils import minidict


class BurrowsWheeler:
    """
    Generates a Suffix Array (SA), Burrows Wheeler Transformation (BWT),
    Occurrence Matrix (tally) and first column of Suffix Matrix (f).
    Upon creation of the object:
    - SA is created, compressed and stored
        len(reference_genome) / compression_sa * sizeof(int).
    - BWT is created and stored
        len(reference_genome) * sizeof(str)
    - tally is created,compressed and stored
        6*len(reference_genome) / compression_occ * sizeof(dict(char:List[int]))
    - f is created and stored (cumulative frequencies of characters)
        6 * sizeof(dict(char:int))
    - helper data structures
        ~ len(reference_genome)
    Works for strings over the alphabet {A, C, G, N, T}.
    The compression for the occurrence matrix (compression_occ >= 1, where =1 indicates no compression)
    and the compression for the suffix array (compression_sa >=1, where =1 indicates no compression)
    can be select upon creation of the object.
    Different algorithms are provided and can be selected upon creation of the object:
    - KaerkkaeinenSanders (recommended):
        Runtime: O(n)
        Space: O(n)
    - ManberMyers:
        Runtime: O(nlog(n) )
        Space: O(n)
    - Simple:
        Runtime: O(n^2 log(n) )
        Space: O(n^2)
    """

    def __init__(self, reference_genome: str, strategy: str = 'KaerkkaeinenSanders',
                 compression_occ: int = 32, compression_sa: int = 32):

        if strategy not in ['KaerkkaeinenSanders', 'ManberMyers', 'Simple']:
            raise ValueError('strategy needs to be KaerkkaeinenSanders, ManberMyers or Simple ')

        if len(reference_genome) < 1:
            raise ValueError('please provide a non empty string for the reference genome')

        if compression_occ < 1 or compression_sa < 1:
            raise ValueError("compression coefficients need to be >=1")

        if reference_genome[-1] != '$':
            reference_genome = reference_genome + '$'

        # level of compression for occurrence matrix and suffix array
        self.compression_occ = compression_occ
        self.compression_sa = compression_sa

        # helper dictionary to determine the next character (used in query method)
        self.next_chars = minidict({'$': 'A', 'A': 'C', 'C': 'G', 'G': 'N', 'N': 'T', 'T': None})

        # step size for the storage of the ranks of the bitvector used by the compressed suffix array
        self.bucket_step = int(np.log2(len(reference_genome)))

        # get a compressed suffix array, bitvector indicating the stored indices of the compressed suffix array
        # and the burrows wheeler transformation
        self.sa, self.bitvector, self.bucket, self.code = self.suffix_array(reference_genome, strategy, compression_sa)

        # compressed first column of burrows wheeler matrix (e.g. cumulative frequencies of characters)
        self.f = self._shifts_f(reference_genome)

        # occurrence matrix
        # '$' will occur only once, therefore only the index needs to be stored
        # Structure:  A | C | G | N | T
        self.tally, self.index_s = self._build_tally(self.code)

    def _shifts_f(self, reference_genome: str) -> dict:
        """
        Returns the shifts in the first column of the burrows wheeler matrix (compressed).
        Works only for strings over the alphabet {A,C,G,N,T}.
        """

        # `None` key is added later
        shifts = {k: 0 for k in self.next_chars.keys()}

        for i in range(len(reference_genome)):
            shifts[reference_genome[i]] = shifts[reference_genome[i]] + 1

        count_a = shifts['$']
        count_c = count_a + shifts['A']
        count_g = count_c + shifts['C']
        count_n = count_g + shifts['G']
        count_t = count_n + shifts['N']

        shifts['$'] = 0
        shifts['A'] = count_a
        shifts['C'] = count_c
        shifts['G'] = count_g
        shifts['N'] = count_n
        shifts['T'] = count_t
        shifts[None] = len(reference_genome)

        return shifts

    def _build_tally(self, bw_transform: str) -> Tuple[dict, int]:
        """
        Returns tally, i.e. the ranks/occurrence of characters.
        """

        index_s = int(bw_transform[0] == '$')
        a = [int(bw_transform[0] == 'A')]
        c = [int(bw_transform[0] == 'C')]
        g = [int(bw_transform[0] == 'G')]
        n = [int(bw_transform[0] == 'N')]
        t = [int(bw_transform[0] == 'T')]

        count_a = a[0]
        count_c = c[0]
        count_g = g[0]
        count_n = n[0]
        count_t = t[0]

        for (count, item) in enumerate(bw_transform[1:], start=1):
            index_s += (item == '$') * count
            count_a = count_a + (item == 'A')
            count_c = count_c + (item == 'C')
            count_g = count_g + (item == 'G')
            count_n = count_n + (item == 'N')
            count_t = count_t + (item == 'T')

            if not (count % self.compression_occ):
                a.append(count_a)
                c.append(count_c)
                g.append(count_g)
                n.append(count_n)
                t.append(count_t)

        return {'A': a, 'C': c, 'G': g, 'N': n, 'T': t}, index_s

    def suffix_array(self, reference_genome: str, strategy: str,
                     compression: int = 1) -> Tuple[List[int], frozenbitarray, List[int], str]:
        """
        Returns the compressed suffix array, a bitarray indicating the stored indices of the suffix array
        and the burrows wheeler transformation
        """

        suffix_array = []
        if strategy == 'Simple':
            suffix_array = self.suffix_array_simple(reference_genome)
        elif strategy == 'ManberMyers':
            suffix_array = self.suffix_array_manbermyers(reference_genome)
        else:
            suffix_array = self.suffix_array_kaerkkaeinensanders(reference_genome, len(reference_genome), 6)

        code = self.get_bwt(reference_genome, suffix_array)

        if self.compression_sa == 1:
            return suffix_array, None, None, code
        else:
            suffix_compressed = []
            bucket = [suffix_array[0] % compression == 0]
            bits = []
            rank = 0
            for index, num in enumerate(suffix_array):
                if num % compression == 0:
                    bits.append(1)
                    rank += 1
                    suffix_compressed.append(num)
                else:
                    bits.append(0)

                if index > 0 and index % self.bucket_step == 0:
                    bucket.append(rank)

            return (suffix_compressed, frozenbitarray(bits), bucket, code)

    def suffix_array_kaerkkaeinensanders(self, reference_genome, n: int, k: int) -> List[int]:
        """
        Returns the suffix array created by the algorithm of Käerkkäeinen & Sanders
        """

        def to_int(string: str) -> List[int]:
            str_to_int = {'$': 1, 'A': 2, 'C': 3, 'G': 4, 'N': 5, 'T': 6}
            return [str_to_int[char] for char in string]

        def leq2(a1: int, a2: int, b1: int, b2: int) -> bool:
            return a1 < b1 or a1 == b1 and a2 <= b2

        def leq3(a1: int, a2: int, a3: int, b1: int, b2: int, b3: int) -> bool:
            return a1 < b1 or a1 == b1 and leq2(a2, a3, b2, b3)

        def radix_pass(a: List[int], r: List[int], len_a: int, len_k: int) -> List[int]:
            c = [0] * (len_k + 1)
            b = [0] * len_a

            for i in range(len_a):
                c[r[a[i]]] += 1
            sum = 0
            for i in range(len_k + 1):
                t = c[i]
                c[i] = sum
                sum += t
            for i in range(len_a):
                b[c[r[a[i]]]] = a[i]
                c[r[a[i]]] += 1
            return b

        sa = [0] * n
        s = reference_genome
        if type(s[0]) is not int:
            s = to_int(reference_genome)
            s += [0, 0, 0]

        n0 = int((n + 2) / 3)
        n1 = int((n + 1) / 3)
        n2 = int(n / 3)
        n02 = n0 + n2

        s12 = [0] * (n02 + 3)
        s0 = [0] * n0

        j = 0
        for i in range(n + n0 - n1):
            if i % 3 != 0:
                s12[j] = i
                j += 1

        sa12 = radix_pass(s12, s[2:], n02, k) + [0, 0, 0]
        s12 = radix_pass(sa12, s[1:], n02, k) + [0, 0, 0]
        sa12 = radix_pass(s12, s, n02, k) + [0, 0, 0]

        name = 0
        c0 = -1
        c1 = -1
        c2 = -1
        for i in range(n02):
            if s[sa12[i]] != c0 or s[sa12[i] + 1] != c1 or s[sa12[i] + 2] != c2:
                name += 1
                c0 = s[sa12[i]]
                c1 = s[sa12[i] + 1]
                c2 = s[sa12[i] + 2]
            if sa12[i] % 3 == 1:
                s12[int(sa12[i] / 3)] = name
            else:
                s12[int(sa12[i] / 3) + n0] = name

        if name < n02:
            sa12 = self.suffix_array_kaerkkaeinensanders(s12, n02, name)
            for i in range(n02):
                s12[sa12[i]] = i + 1
        else:
            for i in range(n02):
                sa12[s12[i] - 1] = i

        j = 0
        for i in range(n02):
            if sa12[i] < n0:
                s0[j] = 3 * sa12[i]
                j += 1

        sa0 = radix_pass(s0, s, n0, k)

        p = 0
        t = n0 - n1
        k = 0

        while k < n:

            i = sa12[t] * 3 + 1 if sa12[t] < n0 else (sa12[t] - n0) * 3 + 2
            j = sa0[p]
            if leq2(s[i], s12[sa12[t] + n0], s[j], s12[int(j / 3)]) if sa12[t] < n0 \
                    else leq3(s[i], s[i + 1], s12[sa12[t] - n0 + 1], s[j], s[j + 1], s12[int(j / 3) + n0]):
                sa[k] = i
                t += 1
                if t == n02:
                    k += 1
                    while p < n0:
                        sa[k] = sa0[p]
                        p += 1
                        k += 1

            else:
                sa[k] = j
                p += 1
                if p == n0:
                    k += 1
                    while t < n02:
                        sa[k] = sa12[t] * 3 + 1 if sa12[t] < n0 else (sa12[t] - n0) * 3 + 2
                        k += 1
                        t += 1
            k += 1

        return sa

    def suffix_array_manbermyers(self, reference_genome: str) -> List[int]:
        """
        Returns the suffix array created by the algorithm of Manber & Myers
        """

        def sort_chars(reference_genome: str) -> List[int]:
            n = len(reference_genome)
            order = [0] * n
            count = {'$': 0, 'A': 0, 'C': 0, 'G': 0, 'N': 0, 'T': 0}

            for i in range(n):
                count[reference_genome[i]] = count[reference_genome[i]] + 1
            keys = list(count.keys())
            for (i, j) in enumerate(count):
                if j == '$':
                    continue
                count[j] = count[j] + count[keys[i - 1]]

            for i in range(n - 1, -1, -1):
                c = reference_genome[i]
                count[c] = count[c] - 1
                order[count[c]] = i

            return order

        def compute_classes(reference_genome: str, order: List[int]) -> List[int]:
            n = len(reference_genome)
            classes = [0] * n
            classes[order[0]] = 0

            for i in range(1, n):
                if reference_genome[order[i]] != reference_genome[order[i - 1]]:
                    classes[order[i]] = classes[order[i - 1]] + 1
                else:
                    classes[order[i]] = classes[order[i - 1]]
            return classes

        def sort_doubled(reference_genome: str, step: int, order: List[int], classes: List[int]) -> List[int]:
            n = len(reference_genome)
            count = [0] * n
            new_order = [0] * n

            for i in range(0, n):
                count[classes[i]] = count[classes[i]] + 1
            for j in range(1, n):
                count[j] = count[j] + count[j - 1]
            for i in range(n - 1, -1, -1):
                start = (order[i] - step + n) % n
                cl = classes[start]
                count[cl] = count[cl] - 1
                new_order[count[cl]] = start

            return new_order

        def updated_classes(order: List[int], classes: List[int], step: int) -> List[int]:
            n = len(order)
            new_classes = [0] * n
            new_classes[order[0]] = 0
            for i in range(1, n):
                cur = order[i]
                prev = order[i - 1]
                mid = cur + step
                mid_prev = (prev + step) % n

                if classes[cur] != classes[prev] or classes[mid] != classes[mid_prev]:
                    new_classes[cur] = new_classes[prev] + 1
                else:
                    new_classes[cur] = new_classes[prev]

            return new_classes

        order = sort_chars(reference_genome)
        classes = compute_classes(reference_genome, order)

        step = 1
        n = len(reference_genome)
        while step < n:
            order = sort_doubled(reference_genome, step, order, classes)
            classes = updated_classes(order, classes, step)
            step *= 2

        return order

    def suffix_array_simple(self, reference_genome):
        """
        Returns the suffix array
        """

        n = len(reference_genome)

        suffix_array = sorted([(reference_genome[i:], i) for i in range(n)])

        offsets = [i[1] for i in suffix_array]

        return offsets

    def get_bwt(self, reference_genome: str, suffix_array: List[int] = None) -> str:
        """
        Returns the burrows wheeler transformation given the corresponding suffix array
        """

        suffix_array = suffix_array or self.sa

        bw_transform = []

        for w in suffix_array:
            if w == 0:
                bw_transform.append('$')
            else:
                bw_transform.append(reference_genome[w - 1])

        return ''.join(bw_transform)

    def __len__(self):
        """
        Returns the length of the burrows wheeler transformation
        """

        return len(self.code) - 1

    def __str__(self):
        """
        Returns the original string
        """

        half_compression = self.compression_occ * 0.5
        n = len(self.code) - 1

        next_char = self.code[0]
        next_row = 0
        original = next_char

        rank = 0

        for i in range(n - 1):
            rank = self.rank(next_char, next_row)

            skip = self.f[next_char]
            next_row = rank + skip - 1

            next_char = self.code[next_row]
            original = next_char + original

        return original

    def __sizeof__(self):
        """
        Returns the size of the object in bytes (if the module 'objsize' can be used otherwise 0)
        """

        try:
            from objsize import get_deep_size
            print("sizes:")
            print("compression_occ:\t ", get_deep_size(self.compression_occ))
            print("compression_sa:\t\t ", get_deep_size(self.compression_sa))
            print("bucket_step:\t\t ", get_deep_size(self.bucket_step))
            print("next_chars\t\t\t ", get_deep_size(self.next_chars))
            print("SA:\t\t\t\t\t ", get_deep_size(self.sa))
            print("F:\t\t\t\t\t ", get_deep_size(self.f))
            print("Occ:\t\t\t\t ", get_deep_size(self.tally))
            print("bitvec:\t\t\t\t ", get_deep_size(self.bitvector))
            print("code:\t\t\t\t ", get_deep_size(self.code))
            print("bucket:\t\t\t\t ", get_deep_size(self.bucket))

            total = get_deep_size(self.compression_occ) + get_deep_size(self.compression_sa) + \
                get_deep_size(self.bucket_step) + get_deep_size(self.next_chars) + get_deep_size(self.sa) + \
                get_deep_size(self.f) + get_deep_size(self.tally) + get_deep_size(self.bitvector) + \
                get_deep_size(self.code) + get_deep_size(self.bucket)

            print("Total:\t\t\t\t ", total)

            return total
        except ImportError:
            return 0

    def rank_bit(self, index: int) -> int:
        """
        Returns the rank of the bit at the position 'index'
        """

        if self.compression_sa == 0:
            return index + 1

        rank = 0
        bucket_index = int(index / self.bucket_step)
        for i in range(bucket_index * self.bucket_step + 1, index + 1):
            rank += self.bitvector[i]

        return self.bucket[bucket_index] + rank

    def rank(self, char: str, index: int) -> int:
        """
        Returns the rank of the character at the position 'index'
        """

        half_compression = self.compression_occ * 0.5
        n = len(self.code) - 1

        next_char = char
        next_row = index

        rank = 0

        if char == '$':
            return int(index >= self.index_s)

        # Find rank of char
        if next_row % self.compression_occ == 0:
            return self.tally[next_char][int(next_row / self.compression_occ)]

        elif next_row % self.compression_occ < half_compression \
                or next_row > int(n / self.compression_occ) * self.compression_occ:
            count = 0
            for up in range(next_row, next_row - (next_row % self.compression_occ), -1):
                if self.code[up] == next_char:
                    count += 1

            return self.tally[next_char][int(next_row / self.compression_occ)] + count

        else:
            count = 0
            for down in range(next_row + 1,
                              next_row + (self.compression_occ - (next_row % self.compression_occ)) + 1):
                if self.code[down] == next_char:
                    count += 1

            return self.tally[next_char][int(next_row / self.compression_occ + 1)] - count

    def get_sa(self, index: int) -> int:
        """
        Returns the entry in the Suffix Array at the position 'index'
        """

        if self.compression_sa == 1:
            return self.sa[index]
        if self.bitvector[index] == 1:
            return self.sa[self.rank_bit(index) - 1]
        else:

            half_compression = self.compression_occ * 0.5
            n = len(self.code) - 1

            next_char = self.code[index]
            next_row = index

            rank = 0
            counter = 0
            while self.bitvector[next_row] != 1:
                rank = self.rank(next_char, next_row)

                skip = self.f[next_char]
                next_row = rank + skip - 1
                next_char = self.code[next_row]

                counter += 1

            return self.sa[self.rank_bit(next_row) - 1] + counter
