# MIPLIB2017-Infeas

[![Licence: see LICENSE](https://img.shields.io/badge/Licence-see%20LICENSE-lightgrey.svg)](LICENSE)

Linear programs with no optimal solution, derived from
[MIPLIB 2017](https://miplib.zib.de/) instances with their integrality dropped. One set has
no feasible point and the other is unbounded, forming a large-scale benchmark for detecting
infeasibility and unboundedness.

**Browse the collection:** https://mit-lu-lab.github.io/MIPLIB2017-Infeas

| | instances | variables | constraints | ZIP download |
| :--- | ---: | :--- | :--- | ---: |
| Primal-infeasible | 229 | 622 to 20,682,487 | 36 to 19,912,111 | 1.55 GiB |
| Dual-infeasible | 105 | 297 to 550,539 | 27 to 19,335,696 | 686.9 MiB |

Each instance is a gzipped MPS file holding continuous variables only. Beside it sits a `.meta.json` sidecar that records how the program was derived from its source instance.

## Primal-infeasible

A branch-and-bound search splits on a variable and explores one side of the split. These instances are the other side, taken at nodes where that side turns out to have no feasible point.

## Dual-infeasible

For 103 instances, bounds and constraints were dropped from a feasible, bounded root LP relaxation until its objective became unbounded; every unnecessary drop was then restored. The other two root relaxations were already unbounded and therefore required no drops.

## Download

Everything is on the [release](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/tag/v1.0): [`primal-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/download/v1.0/primal-infeasible.zip) and [`dual-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB2017-Infeas/releases/download/v1.0/dual-infeasible.zip) each hold a whole subset, laid out as `instances/infeasible/` and `instances/unbounded/`.

To script against it, the site publishes the same catalogue as JSON.
[`index.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/index.json) names both subsets and the release prefix;
[`primal-infeasible.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/primal-infeasible.json) and
[`dual-infeasible.json`](https://mit-lu-lab.github.io/MIPLIB2017-Infeas/dual-infeasible.json) list every instance with its
dimensions, its SHA-256 and its filename. Join the prefix and a filename for a
download URL. The `.csv` beside each one carries the same rows.

## This repository

The instances are release assets; what is tracked here is the site that presents
them and the metadata it renders.

```
website/    the generator, standard library only
metadata/   site-index.json, what the pages render, projected from the sidecars
            miplib_meta.json, MIPLIB 2017's own entry for each source instance
schema/     a JSON Schema for the .meta.json sidecars
fonts/      the eight faces the site serves, OFL subsets of IBM Plex
scripts/    tooling for the published set; only these read the instances
```

CI builds and checks the site for every proposed change, then deploys that same
verified artifact from `main`; nothing generated is committed. To build it yourself:

```bash
python -m website.build_site --out-dir _site
python -m http.server -d _site
```

## Citation

```bibtex
@misc{miplib2017_infeas,
  author       = {Haihao Lu and Bo Tang},
  title        = {MIPLIB2017-Infeas: Primal- and Dual-Infeasible Linear Programs from MIPLIB 2017},
  howpublished = {\url{https://mit-lu-lab.github.io/MIPLIB2017-Infeas}},
  year         = {2026}
}
```

Please also cite [Gleixner et al., “MIPLIB 2017: Data-Driven Compilation of the
6th Mixed-Integer Programming Library”](https://doi.org/10.1007/s12532-020-00194-3).

## Licence

The 262 MIPLIB 2017 instances adapted here do not all carry the same terms, and
[LICENSE](LICENSE) sets out each case against MIPLIB's own submission records:

| source instances | terms |
| ---: | :--- |
| 131 | CC BY-SA 4.0, the default of the MIPLIB 2017 submission form |
| 1 | BSD 3-Clause, for `adult-max5features`, whose notice is reproduced in full |
| 130 | no licence of record: MIPLIB's own instance pages record these as imported from an earlier edition, which predates its licensing requirement |

To the extent this project holds copyright or related rights in them, its own
work (the derivation, the sidecars, the indexes, and the site and the code that
builds it) is released under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), as are the
linear programs derived from the 131 instances that carry it. That licence is
**not** applied to the 130, because neither MIPLIB nor anyone else ever placed
them under it; they are redistributed on the footing ZIB distributes them on,
with their source named and their contributor credited.
