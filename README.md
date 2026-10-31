# MIPLIB 2017 Infeas

[![Licence: see LICENSE](https://img.shields.io/badge/Licence-see%20LICENSE-lightgrey.svg)](LICENSE)

Mixed-integer programs with no optimal solution, derived from
[MIPLIB 2017](https://miplib.zib.de/) instances and keeping their integrality. One set has
no feasible point and the other is unbounded, forming a large-scale benchmark for detecting
infeasibility and unboundedness.

**Browse the collection:** https://mit-lu-lab.github.io/MIPLIB2017-Infeas

| | instances | variables | constraints | ZIP download |
| :--- | ---: | :--- | :--- | ---: |
| Primal-infeasible | 229 | 622 to 20,682,487 | 36 to 19,912,111 | 1.54 GiB |
| Dual-infeasible | 105 | 297 to 550,539 | 27 to 19,335,696 | 723.2 MiB |

Each instance is a gzipped MPS file that keeps its source's integer variables. Beside it sits a `.meta.json` sidecar that records how the program was derived from its source instance.

## Primal-infeasible

A branch-and-bound search splits on a variable and explores one side of the split. These instances are the other side, taken at nodes where that side has no feasible point.

## Dual-infeasible

A greedy search drops bounds and constraints from a feasible, bounded root LP relaxation until its objective becomes unbounded, then restores every unnecessary drop. 103 instances come from that search; the other 2 root relaxations were unbounded as given.

## Software

These are the versions that produced the published files. A solver named without its version describes a run nobody can repeat: which nodes a tree holds depends on the solver that built it, and what a presolve run disposes of changes between releases.

| software | version | what it did |
| :--- | :--- | :--- |
| CPLEX | 22.1.2.1 | Built the branch-and-bound trees the primal-infeasible set is taken from, and ran the loop that drops bounds and constraints for the dual-infeasible one. |
| HiGHS | 1.14.0 | The first presolver a candidate had to survive, reached through the highspy bindings. It also wrote the v1.1 files, with the integrality of each source restored. |
| Gurobi | 12.0.3 | The second presolver a candidate had to survive. |
| Python | 3.11.9 | Ran the mining code driving all three: the callback that follows the search, the drop loop, and the selection. |

## Download

Everything is on the [latest release](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/latest): [`primal-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/latest/download/primal-infeasible.zip) and [`dual-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/latest/download/dual-infeasible.zip) each hold a whole subset, laid out as `instances/infeasible/` and `instances/unbounded/`.

To script against it, the site publishes the same catalogue as JSON. [`index.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/index.json) names both subsets and the release prefix; [`primal-infeasible.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/primal-infeasible.json) and [`dual-infeasible.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/dual-infeasible.json) list every instance with its dimensions, its SHA-256 and its filename. Join the prefix and a filename for a download URL. Each JSON document declares its `format_version`; the `.csv` beside each subset document carries the same rows.

## Citation

```bibtex
@misc{miplib2017_infeas,
  author       = {Haihao Lu and Bo Tang},
  title        = {MIPLIB 2017 Infeas: Primal- and Dual-Infeasible Mixed-Integer Programs from MIPLIB 2017},
  howpublished = {\url{https://mit-lu-lab.github.io/MIPLIB2017-Infeas}},
  year         = {2026}
}
```

Please also cite [Gleixner et al., “MIPLIB 2017: Data-Driven Compilation of the 6th Mixed-Integer Programming Library”](https://doi.org/10.1007/s12532-020-00194-3).

## Licence

The 262 MIPLIB 2017 instances adapted here do not all carry the same terms, and [LICENSE](LICENSE) sets out each case against MIPLIB's own submission records:

| source instances | terms |
| ---: | :--- |
| 131 | CC BY-SA 4.0, the default of the MIPLIB 2017 submission form |
| 1 | BSD 3-Clause, for `adult-max5features`, whose notice is reproduced in full |
| 130 | no licence of record: MIPLIB's own instance pages record these as imported from an earlier edition, which predates its licensing requirement |

To the extent this project holds copyright or related rights in them, its own work (the derivation, the sidecars, the indexes, and the site and the code that builds it) is released under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), as are the programs derived from the 131 instances that carry it. That licence is **not** applied to the 130, because neither MIPLIB nor anyone else ever placed them under it; they are redistributed on the footing ZIB distributes them on, with their source named and their contributor credited.
