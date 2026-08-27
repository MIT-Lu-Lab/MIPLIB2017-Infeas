# MIPLIB-Infeas

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC_BY--SA_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

Linear programs with no optimal solution, derived from
[MIPLIB 2017](https://miplib.zib.de/) instances with their integrality dropped. One set has
no feasible point and the other is unbounded. A large-scale benchmark for detection.

**Browse the collection:** https://mit-lu-lab.github.io/MIPLIB-Infeas

| | instances | variables | constraints | size |
| :--- | ---: | :--- | :--- | ---: |
| Primal-infeasible | 229 | 622 to 20,682,487 | 36 to 19,912,111 | 1.54 GB |
| Dual-infeasible | 105 | 297 to 550,539 | 27 to 19,335,696 | 0.73 GB |

Each instance is a gzipped MPS file holding continuous variables only. Beside it sits a `.meta.json` sidecar that records how the program was derived from its source instance.

### Primal-infeasible

A branch-and-bound search splits on a variable and explores one side of the split. These instances are the other side, taken at nodes where that side turns out to have no feasible point.

### Dual-infeasible

These start from a root LP relaxation that is feasible and bounded. Bounds and constraints were dropped until the objective became unbounded, then any drop that proved unnecessary was restored.

## Download

Everything is on the [release](https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/releases/tag/v1.0): [`primal-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/releases/download/v1.0/primal-infeasible.zip) and [`dual-infeasible.zip`](https://github.com/MIT-Lu-Lab/MIPLIB-Infeas/releases/download/v1.0/dual-infeasible.zip) each hold a whole subset, laid out as `instances/infeasible/` and `instances/unbounded/`.

## This repository

The instances are release assets; what is tracked here is the site that presents
them and the metadata it renders.

```
website/    the generator, standard library only
metadata/   site-index.json, what the pages render, projected from the sidecars
            miplib_meta.json, MIPLIB 2017's own entry for each source instance
schema/     a JSON Schema for the .meta.json sidecars
fonts/      the eight IBM Plex faces the site serves, under the OFL
scripts/    tooling for the published set; only these read the instances
```

The site is built by CI and deployed to Pages on every push, so nothing generated
is committed. To build it yourself:

```bash
python -m website.build_site --out-dir _site
python -m http.server -d _site
```

## Citation

```bibtex
@misc{miplib_infeas,
  author       = {Haihao Lu and Bo Tang},
  title        = {MIPLIB-Infeas: Primal- and Dual-Infeasible Linear Programs from MIPLIB 2017},
  howpublished = {\url{https://mit-lu-lab.github.io/MIPLIB-Infeas}},
  year         = {2026}
}
```

Please cite MIPLIB 2017 as well.

## Licence

[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), the same licence the source instances carry. MIPLIB 2017 requires each contributed instance to be submitted under a licence granting redistribution, by default CC BY-SA 4.0. These instances are adapted material, so ShareAlike carries over.
