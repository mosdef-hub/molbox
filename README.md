molbox
==============================
[//]: # (Badges)
[![CI](https://github.com/mosdef-hub/molbox/actions/workflows/CI.yaml/badge.svg)](https://github.com/mosdef-hub/molbox/actions/workflows/CI.yaml)
[![codecov](https://codecov.io/gh/REPLACE_WITH_OWNER_ACCOUNT/molbox/branch/master/graph/badge.svg)](https://codecov.io/gh/mosdef-hub/molbox/branch/master)


A generic Box implementation for molecular simulation objects.

This project is a fork of [`mbuild`](https://github.com/mosdef-hub/mbuild) providing a generic `Box` object to be used with molecular simulation objects.

## Usage
This package provides a single `Box` class:
```python
from molbox import Box
# Create a box using lengths and angles
box = Box(lengths=[2, 3, 4], angles=[90, 90, 120], precision=5)
print("Box Attributes:")
print(f"Lengths(x, y, z): ({box.Lx}, {box.Ly}, {box.Lz})")
print(f"Tilt Factors(xy, yz, xz): ({box.xy}, {box.yz}, {box.xz}")
print(f"Vectors: {box.vectors}")
# Create a box from box vectors
from_vec_box = Box.from_vectors([[2, 0, 0], [-1.5, 2.59808, 0], [0, 0, 4]])
```

### API
Full documentation can be accessed [here](API.md).

## Copyright

Copyright (c) 2021, Vanderbilt University


## Acknowledgements
 
Project based on the 
[Computational Molecular Science Python Cookiecutter](https://github.com/molssi/cookiecutter-cms) version 1.5.
