
<a href="molbox/box.py#L13"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>class</kbd> `Box`
A box representing the bounds of the system. 

Parameters 
---------- 
* **`lengths`** : list-like, shape=(3,), dtype=float
Lengths of the edges of the box.

* **`angles`** : list-like, shape=(3,), dtype=float, default=None  
Angles (in degrees) that define the tilt of the edges of the box. If  None is given, angles are assumed to be [90.0, 90.0, 90.0]. 
These are  also known as alpha, beta, gamma in the crystallography community. 

* **`precision`** : int, optional, default=None 
Control the precision of the floating point representation of box  attributes. If none provided, the default is 6 decimals. 

Attributes 
---------- 
* **`vectors`** : np.ndarray, shape=(3,3), dtype=float
Vectors that define the parallelepiped (Box). 

* **`lengths`** : tuple, shape=(3,), dtype=float  
Lengths of the box in x,y,z angles : tuple, shape=(3,), dtype=float  

* **`angles`** : tuple, shape=(3,), dtype=float
Angles defining the tilt of the box.
 
* **`Lx`** : float
Length of the Box in the x dimension 

* **`Ly`** : float
Length of the Box in the y dimension 

* **`Lz`** : float  
Length of the Box in the z dimension

* **`xy`** : float
Tilt factor needed to displace an orthogonal box's xy face to its  parallelepiped structure.

* **`xz`** : float  
Tilt factor needed to displace an orthogonal box's xz face to its  parallelepiped structure. 

* **`yz`** : float 
Tilt factor needed to displace an orthogonal box's yz face to its  parallelepiped structure.

* **`precision`** : int  Precision of the floating point numbers when accessing values. 

Notes 
----- 
Box vectors are expected to be provided in row-major format. 

<a href="molbox/box.py#L59"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>method</kbd> `__init__`

```python
__init__(lengths, angles=None, precision=None)
```






---

### <kbd>property</kbd> Lx

Length in the x direction. 

---

### <kbd>property</kbd> Ly

Length in the y direction. 

---

### <kbd>property</kbd> Lz

Length in the z direction. 

---

### <kbd>property</kbd> angles

Angles defining the tilt of the box (alpha, beta, gamma). 

---

### <kbd>property</kbd> box_parameters

Lengths and tilt factors of the box. 

---

### <kbd>property</kbd> bravais_parameters

Return the Box representation as Bravais lattice parameters. 

Based on the box vectors, return the parameters to describe the box in terms of the Bravais lattice parameters: 

 a,b,c = the edges of the Box  alpha, beta, gamma = angles(tilt) of the parallelepiped, in degrees 

Returns 
------- 
parameters : tuple of floats,  (a, b, c, alpha, beta, gamma) 

---

### <kbd>property</kbd> lengths

Lengths of the box. 

---

### <kbd>property</kbd> precision

Amount of decimals to represent floating point values. 

---

### <kbd>property</kbd> tilt_factors

Return the 3 tilt_factors (xy, xz, yz) of the box. 

---

### <kbd>property</kbd> vectors

Box representation as a 3x3 matrix. 

---

### <kbd>property</kbd> xy

Tilt factor xy of the box. 

---

### <kbd>property</kbd> xz

Tilt factor xz of the box. 

---

### <kbd>property</kbd> yz

Tilt factor yz of the box. 



---

<a href="molbox/box.py#L79"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_lengths_angles`

```python
from_lengths_angles(lengths, angles, precision=None)
```

Generate a box from lengths and angles. 

---

<a href="molbox/box.py#L131"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_lengths_tilt_factors`

```python
from_lengths_tilt_factors(lengths, tilt_factors=None, precision=None)
```

Generate a box from box lengths and tilt factors. 

---

<a href="molbox/box.py#L150"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_lo_hi_tilt_factors`

```python
from_lo_hi_tilt_factors(lo, hi, tilt_factors, precision=None)
```

Generate a box from a lo, hi convention and tilt factors. 

---

<a href="molbox/box.py#L106"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_mins_maxs_angles`

```python
from_mins_maxs_angles(mins, maxs, angles, precision=None)
```

Generate a box from min/max distance calculations and angles. 

---

<a href="molbox/box.py#L84"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_uvec_lengths`

```python
from_uvec_lengths(uvec, lengths, precision=None)
```

Generate a box from unit vectors and lengths. 

---

<a href="molbox/box.py#L114"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>classmethod</kbd> `from_vectors`

```python
from_vectors(vectors, precision=None)
```

Generate a box from box vectors.
