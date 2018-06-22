#!/usr/bin/env python3
import matplotlib.pyplot as plt
import argparse
import glob
import re
import numpy as np
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create graphs in the current directory")
    parser.add_argument("outfile")
    args = parser.parse_args()
    fnames = glob.glob("lookupresults.*")
    assert len(fnames) != 0, "Couldn't find file of the name lookupresults.* in current directory"
    conditions = set()
    for f in fnames:
        m = re.search(r".*?\.(.*)", f)
        conditions.add(m.group(1))

    for condition in conditions:
        guesses = []
        with open("lookupresults.{}".format(condition)) as f:
            for line in f:
                try:
                    guesses.append(int(line.split("\t")[5]))
                except:
                    continue
            guesses.sort()
            counts = np.arange(1, len(guesses)+1)
            counts = (counts/len(counts))*100
            plt.step(guesses, counts, label=condition)
    plt.xscale('log')
    axes = plt.gca()
    axes.set_xlim([1, 10e25])
    plt.legend()
    plt.grid(True)
    plt.xlabel("Guesses")
    plt.ylabel("Percent guessed")
    plt.savefig(args.outfile)
