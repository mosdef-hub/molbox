from __future__ import print_function

from collections import OrderedDict
from copy import deepcopy
import os
import sys

import numpy as np
import mdtraj as md
from mdtraj.core.element import Element
from mdtraj.core.element import get_by_symbol
from orderedset import OrderedSet

from mbuild.formats.hoomdxml import HOOMDTopologyFile
from mbuild.formats.lammps import LAMMPSTopologyFile
from mbuild.formats.mol2 import write_mol2

from mbuild.box import Box
from mbuild.part_mixin import PartMixin
from mbuild.topology import Topology


__all__ = ['load', 'Compound', 'Port', 'Atom', 'Bond']


def load(filename, relative_to_module=None, frame=-1, compound=None,
         coords_only=False, **kwargs):
    """ """

    # For mbuild *.py files with a class that wraps a structure file in its own
    # folder. E.g., you build a system from ~/foo.py and it imports from
    # ~/bar/baz.py where baz.py loads ~/bar/baz.pdb.
    if relative_to_module:
        current_dir = os.path.dirname(os.path.realpath(sys.modules[relative_to_module].__file__))
        filename = os.path.join(current_dir, filename)

    # This can return a md.Trajectory or an mb.Compound.
    loaded = md.load(filename, **kwargs)

    if not compound:
        if isinstance(loaded, Compound):
            return loaded
        else:
            compound = Compound()

    if isinstance(loaded, md.Trajectory):
        compound.from_trajectory(loaded, frame=frame, coords_only=coords_only)
    elif isinstance(loaded, Compound):  # Only updating coordinates.
        for atom, loaded_atom in zip(compound.atoms, loaded.atoms):
            atom.pos = loaded_atom.pos
    return compound


class Compound(PartMixin):
    """A building block in the mBuild hierarchy.

    Compound is the superclass of all composite building blocks in the mBuild
    hierarchy. That is, all composite building blocks must inherit from
    compound, either directly or indirectly. The design of Compound follows the
    Composite design pattern (Gamma, Erich; Richard Helm; Ralph Johnson; John
    M. Vlissides (1995). Design Patterns: Elements of Reusable Object-Oriented
    Software. Addison-Wesley. p. 395. ISBN 0-201-63361-2.), with Compound being
    the composite, and Atom playing the role of the primitive (leaf) part.

    Compound maintains a list of parts (contained Compounds, Atoms, Bonds,
    etc., that inherit from PartMixin), and provides a means to tag the parts
    with labels, so that the parts can be easily looked up later. Labels may
    also point to objects outside the Compound's containment hierarchy.
    Compound has built-in support for copying and deepcopying Compound
    hierarchies, enumerating atoms or bonds in the hierarchy, proximity based
    searches, visualization, I/O operations, and a number of other convenience
    methods.

    Parameters
    ----------
    kind : str, optional, default=self.__class__.__name__
        The type of Compound.
    periodicity : np.ndarray, shape=(3,), dtype=float, optional
        The periodic lengths of the Compound in the x, y and z directions.
        Defaults to zeros which is treated as non-periodic.

    Attributes
    ----------
    kind : str, optional, default=self.__class__.__name__
        The type of Compound.
    periodicity : np.ndarray, shape=(3,), dtype=float, optional
        The periodic lengths of the Compound in the x, y and z directions.
        Defaults to zeros which is treated as non-periodic.
    parts : OrderedSet
        Contains all child parts. Parts can be Atom, Bond or Compound - anything
        that inherits from PartMixin.
    labels : OrderedDict
        Labels to Compound/Atom mappings. These do not necessarily need not be
        in parts.
    parent : mb.Compound
        The parent Compound that contains this part. Can be None if this
        compound is the root of the containment hierarchy.
    referrers : set
        Other compounds that reference this part with labels.

    """
    def __init__(self, kind=None, periodicity=None):
        super(Compound, self).__init__()

        if kind:
            self.kind = kind
        else:
            self.kind = self.__class__.__name__

        # A periodocity of zero in any direction is treated as non-periodic.
        if not periodicity:
            periodicity = np.array([0.0, 0.0, 0.0])
        self.periodicity = periodicity

        self.parts = OrderedSet()
        self.labels = OrderedDict()

    @property
    def atoms(self):
        """A list of all Atoms in the Compound and sub-Compounds.  """
        return self.atom_list_by_kind(excludeG=True)

    def yield_atoms(self):
        """ """
        return self._yield_parts(Atom)

    @property
    def n_atoms(self):
        """Return the number of Atoms in the Compound. """
        return len(self.atoms)

    def atom_list_by_kind(self, kind='*', excludeG=False):
        """Return a list of Atoms filtered by their kind.

        Parameters
        ----------
        kind : str
            Return only atoms of this type. '*' indicates all.
        excludeG : bool
            Exclude Port particles of kind 'G' - reserved for Ports.

        Returns
        -------
        atom_list : list
            List of Atoms matching the inputs.
        """
        atom_list = []
        for atom in self.yield_atoms():
            if not (excludeG and atom.kind == "G"):
                if kind == '*':
                    atom_list.append(atom)
                elif atom.kind == kind:
                    atom_list.append(atom)
        return atom_list

    @property
    def bonds(self):
        """A list of all Bonds in the Compound and sub-Compounds. """
        return self.bond_list_by_kind()

    def yield_bonds(self):
        """ """
        return self._yield_parts(Bond)

    @property
    def n_bonds(self):
        """Return the number of Bonds in the Compound. """
        return len(self.bonds)

    def bond_list_by_kind(self, kind='*'):
        """Return a list of Bonds filtered by their kind. """
        bond_list = []
        for bond in self.yield_bonds():
            if kind == '*':
                bond_list.append(bond)
            elif bond.kind == kind:
                bond_list.append(bond)
        return bond_list

    def _yield_parts(self, part_type):
        """Yield parts of a specified type in the Compound recursively. """
        for part in self.parts:
            # Parts local to the current Compound.
            if isinstance(part, part_type):
                yield part
            # Parts further down the hierarchy.
            if isinstance(part, Compound):
                for subpart in part._yield_parts(part_type):
                    yield subpart

    def add(self, new_part, label=None, containment=True, replace=False,
            inherit_periodicity=True):
        """Add a part to the Compound.

        Note:
            This does not necessarily add the part to self.parts but may
            instead be used to add a reference to the part to self.labels. See
            'containment' argument.

        Parameters
        ----------
        new_part : mb.Atom, mb.Bond or mb.Compound
            The object to be added to this Compound.
        label : str, optional
            A descriptive string for the part.
        containment : bool, optional, default=True
            Add the part to self.parts.
        replace : bool, optional, default=True
            Replace the label if it already exists.

        """
        assert isinstance(new_part, (PartMixin, list, tuple, set))
        if containment:
            # Support batch add via lists, tuples and sets.
            if isinstance(new_part, (list, tuple, set)):
                for elem in new_part:
                    assert (elem.parent is None)
                    self.add(elem)
                    elem.parent = self
                return

            assert new_part.parent is None, "Part {} already has a parent: {}".format(
                new_part, new_part.parent)
            self.parts.add(new_part)
            new_part.parent = self

        # Add new_part to labels. Does not currently support batch add.
        assert isinstance(new_part, PartMixin)

        if not containment and label is None:
            label = '_{0}[$]'.format(new_part.__class__.__name__)

        if label is not None:
            if label.endswith("[$]"):
                label = label[:-3]
                if label not in self.labels:
                    self.labels[label] = []
                label_pattern = label + "[{}]"

                count = len(self.labels[label])
                self.labels[label].append(new_part)
                label = label_pattern.format(count)

            if not replace and label in self.labels:
                raise Exception(
                    "Label {0} already exists in {1}".format(label, self))
            else:
                self.labels[label] = new_part
        new_part.referrers.add(self)

        if (inherit_periodicity and isinstance(new_part, Compound) and
                new_part.periodicity.any()):
            self.periodicity = new_part.periodicity

    def remove(self, objs_to_remove):
        """Remove parts (Atom, Bond or Compound) from the Compound. """
        if not isinstance(objs_to_remove, (list, tuple, set)):
            objs_to_remove = [objs_to_remove]
        objs_to_remove = set(objs_to_remove)

        if len(objs_to_remove) == 0:
            return

        intersection = objs_to_remove.intersection(self.parts)
        self.parts.difference_update(intersection)
        objs_to_remove.difference_update(intersection)

        for removed_part in intersection:
            self._remove_bonds(removed_part)
            self._remove_references(removed_part)

        # Remove the part recursively from sub-components.
        for part in self.parts:
            if isinstance(part, Compound) and len(objs_to_remove) > 0:
                part.remove(objs_to_remove)

    @staticmethod
    def _remove_bonds(removed_part):
        """If removing an atom, make sure to remove the bonds it's part of. """
        if isinstance(removed_part, Atom):
            for bond in removed_part.bonds:
                bond.other_atom(removed_part).bonds.remove(bond)
                if bond.parent is not None:
                    bond.parent.remove(bond)

    @staticmethod
    def _remove_references(removed_part):
        """Remove labels pointing to this part and vice versa. """
        removed_part.parent = None

        # Remove labels in the hierarchy pointing to this part.
        referrers_to_remove = set()
        for referrer in removed_part.referrers:
            if removed_part not in referrer.ancestors():
                for label, referred_part in referrer.labels.items():
                    if referred_part is removed_part:
                        del referrer.labels[label]
                        referrers_to_remove.add(referrer)
        removed_part.referrers.difference_update(referrers_to_remove)

        # Remove labels in this part pointing into the hierarchy.
        labels_to_delete = []
        if isinstance(removed_part, Compound):
            for label, part in removed_part.labels.items():
                if removed_part not in part.ancestors():
                    part.referrers.remove(removed_part)
                    labels_to_delete.append(label)
        for label in labels_to_delete:
            del removed_part.labels[label]

    def referenced_ports(self):
        """Return all Ports referenced by this Compound. """
        return [port for port in self.labels.values() if isinstance(port, Port)]

    # Interface to Trajectory for reading/writing.
    # --------------------------------------------
    def from_trajectory(self, traj, frame=-1, coords_only=False):
        """Extract atoms and bonds from a md.Trajectory.

        Will create sub-compounds for every chain if there is more than one
        and sub-sub-compounds for every residue.

        Parameters
        ----------
        traj : md.Trajectory
            The trajectory to load.
        frame : int
            The frame to take coordinates from.

        """
        atom_mapping = dict()
        for chain in traj.topology.chains:
            if traj.topology.n_chains > 1:
                chain_compound = Compound()
                self.add(chain_compound, "chain[$]")
            else:
                chain_compound = self
            for res in chain.residues:
                for atom in res.atoms:
                    new_atom = Atom(str(atom.name), traj.xyz[frame, atom.index])
                    chain_compound.add(new_atom, label="{0}[$]".format(atom.name))
                    atom_mapping[atom] = new_atom

        if not coords_only:
            for a1, a2 in traj.topology.bonds:
                atom1 = atom_mapping[a1]
                atom2 = atom_mapping[a2]
                self.add(Bond(atom1, atom2))

            if np.any(traj.unitcell_lengths) and np.any(traj.unitcell_lengths[0]):
                self.periodicity = traj.unitcell_lengths[0]
            else:
                self.periodicity = np.array([0., 0., 0.])

    def to_trajectory(self, show_ports=False, chain_types=None,
                      residue_types=None, forcefield=None):
        """Convert to an md.Trajectory and flatten the compound.

        This also produces an object subclassed from MDTraj's Topology which
        can be used in place of an actual MDTraj.Topology.

        Parameters
        ----------
        show_ports : bool

        Returns
        -------
        trajectory : md.Trajectory

        See also
        --------
        _to_topology
        mbuild.topology

        """
        exclude = not show_ports
        atom_list = self.atom_list_by_kind('*', excludeG=exclude)

        top = self._to_topology(atom_list, chain_types=chain_types,
                                residue_types=residue_types, forcefield=forcefield)

        # Coordinates.
        xyz = np.ndarray(shape=(1, top.n_atoms, 3), dtype='float')
        for idx, atom in enumerate(atom_list):
            xyz[0, idx] = atom.pos

        # Unitcell information.
        box = self.boundingbox()
        unitcell_lengths = np.empty(3)
        for dim, val in enumerate(self.periodicity):
            if val:
                unitcell_lengths[dim] = val
            else:
                unitcell_lengths[dim] = box.lengths[dim]

        return md.Trajectory(xyz, top, unitcell_lengths=unitcell_lengths,
                             unitcell_angles=np.array([90, 90, 90]))

    def _to_topology(self, atom_list, chain_types=None, residue_types=None,
                     forcefield=None):
        """Create a Topology from a Compound.

        Parameters
        ----------
        atom_list :
        chain_types :
        residue_types :

        Returns
        -------
        top : mbuild.Topology

        """

        if isinstance(chain_types, list):
            chain_types = tuple(chain_types)
        if isinstance(residue_types, list):
            residue_types = tuple(residue_types)
        top = Topology()
        atom_mapping = {}

        default_chain = top.add_chain()
        default_residue = top.add_residue("RES", default_chain)

        last_residue_compound = None
        last_chain_compound = None
        last_residue = None
        last_chain = None

        for atom in atom_list:
            # Chains
            for parent in atom.ancestors():
                if chain_types and isinstance(parent, chain_types):
                    if parent != last_chain_compound:
                        last_chain_compound = parent
                        last_chain = top.add_chain()
                        last_chain_default_residue = top.add_residue("RES", last_chain)
                        last_chain.compound = last_chain_compound
                    break
            else:
                last_chain = default_chain
                last_chain.compound = last_chain_compound

            # Residues
            for parent in atom.ancestors():
                if residue_types and isinstance(parent, residue_types):
                    if parent != last_residue_compound:
                        last_residue_compound = parent
                        last_residue = top.add_residue(parent.__class__.__name__, last_chain)
                        last_residue.compound = last_residue_compound
                    break
            else:
                if last_chain != default_chain:
                    last_residue = last_chain_default_residue
                else:
                    last_residue = default_residue
                last_residue.compound = last_residue_compound

            # Add the actual atoms
            try:
                ele = get_by_symbol(atom.kind)
            except KeyError:
                ele = Element(1000, atom.kind, atom.kind, 1.0)
            at = top.add_atom(atom.kind, ele, last_residue)
            at.charge = atom.charge

            try:
                at.atomtype = atom.atomtype
            except AttributeError:
                at.atomtype = atom.kind
            atom_mapping[atom] = at

        for bond in self.bonds:
            a1 = bond.atom1
            a2 = bond.atom2
            top.add_bond(atom_mapping[a1], atom_mapping[a2])

        if forcefield:
            from mbuild.tools.parameterize.forcefield import apply_forcefield
            apply_forcefield(top, forcefield)

        return top

    def update_coordinates(self, filename):
        """ """
        load(filename, compound=self, coords_only=True)

    def save(self, filename, show_ports=False, forcefield=None, **kwargs):
        """Save the Compound to a file.

        Parameters
        ----------
        filename : str
            Filesystem path in which to save the trajectory. The extension or
            prefix will be parsed and will control the format.

        Other Parameters
        ----------------
        force_overwrite : bool

        """
        # grab the extension of the filename
        extension = os.path.splitext(filename)[-1]

        savers = {'.hoomdxml': self.save_hoomdxml,
                  #'.gro': self.save_gromacs,
                  #'.top': self.save_gromacs,
                  '.mol2': self.save_mol2,
                  '.lammps': self.save_lammpsdata,
                  '.lmp': self.save_lammpsdata,
                  }

        try:
            saver = savers[extension]
        except KeyError:  # TODO: better reporting
            saver = None

        if not saver and forcefield:
            ff_formats = ', '.join(list(savers.keys()).remove('.mol2'))
            raise ValueError('The only supported formats with forcefield'
                             'information are: {0}'.format(ff_formats))

        if saver:  # mBuild supported saver.
            traj = self.to_trajectory(forcefield=forcefield)
            return saver(filename, traj, show_ports=show_ports)
        else:  # MDTraj supported saver.
            traj = self.to_trajectory(show_ports=show_ports)
            return traj.save(filename, **kwargs)

    def save_hoomdxml(self, filename, traj, force_overwrite=True, **kwargs):
        """ """
        with HOOMDTopologyFile(filename, 'w', force_overwrite=force_overwrite) as f:
            f.write(traj)

    def save_mol2(self, filename, traj, **kwargs):
        write_mol2(filename, traj)

    # def save_gromacs(self):

    def save_lammpsdata(self, filename, traj, force_overwrite=True, show_ports=False,
                        **kwargs):
        """ """
        with HOOMDTopologyFile(filename, 'w', force_overwrite=force_overwrite) as f:
            f.write(traj)

    # Convenience functions
    # ---------------------
    def visualize(self, show_ports=False):
        """Visualize the Compound using VMD.

        Assumes you have VMD installed and can call it from the command line via
        'vmd'.

        TODO: Look into pizza.py's vmd.py. See issue #32.
        """
        filename = 'visualize_{}.mol2'.format(self.__class__.__name__)
        self.save(filename, show_ports=show_ports)
        import os

        try:
            os.system('vmd {}'.format(filename))
        except OSError:
            print("Visualization with VMD failed. Make sure it is installed"
                  "correctly and launchable from the command line via 'vmd'.")

    @property
    def center(self):
        """The cartesian center of the Compound based on its Atoms. """
        try:
            return sum(atom.pos for atom in self.atoms) / self.n_atoms
        except ZeroDivisionError:  # Compound only contains 'G' atoms.
            atoms = self.atom_list_by_kind('G')
            return sum(atom.pos for atom in atoms) / len(atoms)

    def boundingbox(self, excludeG=True):
        """Compute the bounding box of the compound. """
        minx = np.inf
        miny = np.inf
        minz = np.inf
        maxx = -np.inf
        maxy = -np.inf
        maxz = -np.inf

        for atom in self.yield_atoms():
            if excludeG and atom.kind == 'G':
                continue
            if atom.pos[0] < minx:
                minx = atom.pos[0]
            if atom.pos[0] > maxx:
                maxx = atom.pos[0]
            if atom.pos[1] < miny:
                miny = atom.pos[1]
            if atom.pos[1] > maxy:
                maxy = atom.pos[1]
            if atom.pos[2] < minz:
                minz = atom.pos[2]
            if atom.pos[2] > maxz:
                maxz = atom.pos[2]

        min_coords = np.array([minx, miny, minz])
        max_coords = np.array([maxx, maxy, maxz])

        return Box(mins=min_coords, maxs=max_coords)

    def min_periodic_distance(self, xyz0, xyz1):
        """Vectorized distance calculation considering minimum image. """
        d = np.abs(xyz0 - xyz1)
        d = np.where(d > 0.5 * self.periodicity, self.periodicity - d, d)
        return np.sqrt((d ** 2).sum(axis=-1))

    def add_bonds(self, type_a, type_b, dmin, dmax, kind=None):
        """Add Bonds between all Atom pairs of types a/b within [dmin, dmax].

        TODO: testing for periodic boundaries.
        """
        for a1 in self.atom_list_by_kind(type_a):
            nearest = self.atoms_in_range(a1.pos, dmax)
            for a2 in nearest:
                if (a2.kind == type_b) and (dmin <= self.min_periodic_distance(a2.pos, a1.pos) <= dmax):
                    self.add(Bond(a1, a2, kind=kind))

    # Magic
    # -----
    def __getattr__(self, attr):
        assert "labels" != attr, ("Compound __init__ never called. Make "
                                  "sure to call super().__init__() in the "
                                  "__init__ method of your class.")
        if attr in self.labels:
            return self.labels[attr]
        else:
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__.__name__, attr))

    def __deepcopy__(self, memo):
        cls = self.__class__
        newone = cls.__new__(cls)
        if len(memo) == 0:
            memo[0] = self
        memo[id(self)] = newone

        # First copy those attributes that don't need deepcopying.
        newone.kind = deepcopy(self.kind, memo)
        newone.periodicity = deepcopy(self.periodicity, memo)

        # Create empty containers.
        newone.parts = OrderedSet()
        newone.labels = OrderedDict()
        newone.referrers = set()

        # Copy the parent of everyone, except topmost Compound being deepcopied.
        if memo[0] == self:
            newone.parent = None
        else:
            newone.parent = deepcopy(self.parent, memo)

        # Copy parts, except bonds with atoms outside the hierarchy.
        for part in self.parts:
            if isinstance(part, Bond):
                if memo[0] in part.atom1.ancestors() and memo[0] in part.atom2.ancestors():
                    newone.parts.add(deepcopy(part, memo))
            else:
                newone.parts.add(deepcopy(part, memo))

        # Copy labels, except bonds with atoms outside the hierarchy
        for k, v in self.labels.items():
            if isinstance(v, Bond):
                if memo[0] in v.atom1.ancestors() and memo[0] in v.atom2.ancestors():
                    newone.labels[k] = deepcopy(v, memo)
                    newone.labels[k].referrers.add(newone)
            else:
                newone.labels[k] = deepcopy(v, memo)
                if not isinstance(newone.labels[k], list):
                    newone.labels[k].referrers.add(newone)

        # Copy referrers that do not point out of the hierarchy.
        for r in self.referrers:
            if memo[0] in r.ancestors():
                newone.referrers.add(deepcopy(r, memo))

        return newone


class Port(Compound):
    """A set of four ghost Atoms used to connect parts.

    Parameters
    ----------
    anchor : mb.Atom, optional, default=None
        An atom associated with the port. Used to form bonds.

    Attributes
    ----------
    anchor : mb.Atom, optional, default=None
        An atom associated with the port. Used to form bonds.
    up : mb.Compound
        Collection of 4 ghost particles used to perform equivalence transforms.
        Faces the opposite direction as self.down.
    down : mb.Compound
        Collection of 4 ghost particles used to perform equivalence transforms.
        Faces the opposite direction as self.up.

    """
    def __init__(self, anchor=None):
        super(Port, self).__init__(kind='Port')
        self.anchor = anchor

        up = Compound()
        up.add(Atom(kind='G', pos=np.array([0, 0, 0])), 'middle')
        up.add(Atom(kind='G', pos=np.array([0, 0.02, 0])), 'top')
        up.add(Atom(kind='G', pos=np.array([-0.02, -0.01, 0])), 'left')
        up.add(Atom(kind='G', pos=np.array([0.0, -0.02, 0.01])), 'right')

        down = deepcopy(up)

        from mbuild.coordinate_transform import rotate_around_z
        rotate_around_z(down, np.pi)

        self.add(up, 'up')
        self.add(down, 'down')

    def __deepcopy__(self, memo):
        newone = super(Port, self).__deepcopy__(memo)
        newone.anchor = deepcopy(self.anchor, memo)
        return newone


class Atom(PartMixin):
    """Elementary container class - typically a leaf in the hierarchy.

    Notes
    -----
    Atoms are also used as "ghost" particles in Ports.
    Atoms can be added and substracted using +/- operators. The result is
    the addition or subtraction of the Atoms' cartesian coordinates.

    Attributes
    ----------
    kind : str
        The kind of atom, usually the chemical element.
    pos : np.ndarray, shape=(3,), dtype=float
        Cartesian coordinates of the atom.
    charge : float
        Partial charge on the atom.
    parent : mb.Compound
        Compound to which the Atom belongs.
    referrers : set of mb.Compounds
        All Compounds that refer to this instance of Atom.
    bonds : set of mb.Bonds
        Every Bond that the Atom is a part of.

    """
    __slots__ = ['kind', 'pos', 'charge', 'parent', 'referrers', 'bonds', 'uid',
                 '_extras']

    def __init__(self, kind, pos=None, charge=0.0):
        super(Atom, self).__init__()

        if pos is None:
            pos = np.array([0, 0, 0], dtype=float)

        self.kind = kind
        self.pos = np.asarray(pos, dtype=float)
        self.charge = charge
        self.bonds = set()
        self._extras = None

    def bonded_atoms(self, memo=None):
        """Return a list of Atoms bonded to self. """
        if memo is None:
            memo = dict()
        for bond in self.bonds:
            bonded_atom = bond.other_atom(self)
            if id(bonded_atom) not in memo:
                memo[id(bonded_atom)] = bonded_atom
                bonded_atom.bonded_atoms(memo)
        return memo.values()

    @property
    def neighbors(self):
        """Return a list of all neighboring Atoms. """
        return [bond.other_atom(self) for bond in self.bonds]

    @property
    def n_bonds(self):
        return len(self.bonds)

    @property
    def extras(self):
        """Return the Atom's optional, extra attributes. """
        if self._extras is None:
            self._extras = dict()
        return self._extras

    def __getattr__(self, item):
        if self._extras and item in self._extras:
            return self._extras[item]
        else:
            raise AttributeError

    def __add__(self, other):
        if isinstance(other, Atom):
            other = other.pos
        return self.pos + other

    def __radd__(self, other):
        if isinstance(other, Atom):
            other = other.pos
        return self.pos + other

    def __sub__(self, other):
        if isinstance(other, Atom):
            other = other.pos
        return self.pos - other

    def __rsub__(self, other):
        if isinstance(other, Atom):
            other = other.pos
        return self.pos - other

    def __neg__(self):
        return -self.pos

    def __repr__(self):
        return "Atom{0}({1}, {2})".format(id(self), self.kind, self.pos)

    def __deepcopy__(self, memo):
        cls = self.__class__
        newone = cls.__new__(cls)

        # Remember the topmost component being deepcopied.
        if len(memo) == 0:
            memo[0] = self
        memo[id(self)] = newone

        # Copy fields that don't need recursion.
        newone.referrers = set()
        newone.bonds = set()

        # Do the rest recursively.
        newone.kind = deepcopy(self.kind, memo)
        newone.pos = deepcopy(self.pos, memo)
        newone.charge = deepcopy(self.charge, memo)
        newone._extras = deepcopy(self._extras, memo)

        # Copy parents, except the topmost compound being deepcopied.
        if memo[0] == self or isinstance(memo[0], Bond):
            newone.parent = None
        else:
            newone.parent = deepcopy(self.parent, memo)

        return newone


class Bond(PartMixin):
    """Connection between two Atoms.

    Attributes
    ----------
    atom1 : mb.Atom
        First Atom in the bond.
    atom2 : mb.Atom
        Second Atom in the bond.
    parent : mb.Compound
        Compound to which the Bond belongs.
    """
    __slots__ = ['_atom1', '_atom2', 'kind', 'parent', 'referrers']

    def __init__(self, atom1, atom2, kind=None):
        super(Bond, self).__init__()
        assert(not atom1 == atom2)

        # If a Port is used to initialize a Bond, the Atom that the Port is
        # anchored to will be used to create the Bond.
        if isinstance(atom1, Port):
            atom1 = atom1.anchor
        if isinstance(atom2, Port):
            atom2 = atom2.anchor
        self._atom1 = atom1
        self._atom2 = atom2

        if kind is not None:
            self.kind = kind
        else:
            self.kind = '{0}-{1}'.format(atom1.kind, atom2.kind)

        # Ensure Atoms in Bond know about the Bond.
        atom1.bonds.add(self)
        atom2.bonds.add(self)

    @property
    def atom1(self):
        return self._atom1

    @property
    def atom2(self):
        return self._atom2

    def other_atom(self, atom):
        """Returns the other Atom in the Bond. """
        if self._atom1 is atom:
            return self._atom2
        elif self._atom2 is atom:
            return self._atom1

    def distance(self, periodicity=np.array([0.0, 0.0, 0.0])):
        """Calculate the bond distance considering minimum image. """
        d = np.abs(self.atom1 - self.atom2)
        d = np.where(d > 0.5 * periodicity, periodicity - d, d)
        return np.sqrt((d ** 2).sum(axis=-1))

    def __hash__(self):
        return id(self.atom1) ^ id(self.atom2)

    def __eq__(self, bond):
        return isinstance(bond, Bond) and (self.atom1 == bond.atom1 and self.atom2 == bond.atom2
             or self.atom2 == bond.atom1 and self.atom1 == bond.atom1)

    def __repr__(self):
        return "Bond{0}({1}, {2})".format(id(self), self.atom1, self.atom2)

    def __deepcopy__(self, memo):
        cls = self.__class__
        newone = cls.__new__(cls)

        # Remember the topmost component being deepcopied.
        if len(memo) == 0:
            print('bond is root of deepcopy')
            memo[0] = self
        memo[id(self)] = newone

        # Copy fields that don't need recursion.
        newone.kind = self.kind
        newone.referrers = set()

        # Do the rest recursively.
        newone._atom1 = deepcopy(self.atom1, memo)
        newone._atom2 = deepcopy(self.atom2, memo)
        newone._atom1.bonds.add(newone)
        newone._atom2.bonds.add(newone)

        # Copy parents, except the topmost compound being deepcopied.
        if memo[0] == self:
            newone.parent = None
        else:
            newone.parent = deepcopy(self.parent, memo)

        return newone
