molbox
==============================
[//]: # (Badges)
[![GitHub Actions Build Status](https://github.com/REPLACE_WITH_OWNER_ACCOUNT/molbox/workflows/CI/badge.svg)](https://github.com/mosdef-hub/molbox/actions?query=workflow%3ACI)
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
```

### API
Full documentation can be accessed [here](API.md).

### Copyright

Copyright (c) 2021, Vanderbilt University


#### Acknowledgements
 
Project based on the 
[Computational Molecular Science Python Cookiecutter](https://github.com/molssi/cookiecutter-cms) version 1.5.
