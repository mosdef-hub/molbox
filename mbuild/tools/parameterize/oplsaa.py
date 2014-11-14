from collections import defaultdict
from copy import copy
import os
from warnings import warn
from pkg_resources import resource_filename
import sys
from itertools import combinations_with_replacement

from mbuild.compound import Compound
from mbuild.orderedset import OrderedSet

# Map opls ids to the functions that check for them.
rule_number_to_rule = dict()
rule_map = dict()

# Globally maintained neighbor information (see `neighbor_types()`).
neighbor_types_map = {}

class OplsDecorator(object):
    pass

class Element(OplsDecorator):
    def __init__(self, element_type):
        self.element_type = element_type

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if atom.kind == self.element_type:
                return f(atom)
        return wrapped

class NeighborCount(OplsDecorator):
    def __init__(self, count):
        self.count = count

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if len(atom.neighbors) == self.count:
                return f(atom)
        return wrapped

class NeighborsExactly(OplsDecorator):
    def __init__(self, neighbor_type, count):
        self.neighbor_type = neighbor_type
        self.count = count

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if self.neighbor_type in neighbor_types(atom) and neighbor_types(atom)[self.neighbor_type] == self.count:
                return f(atom)
        return wrapped

class NeighborsAtLeast(OplsDecorator):
    def __init__(self, neighbor_type, count):
        self.neighbor_type = neighbor_type
        self.count = count

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if self.neighbor_type in neighbor_types(atom) and neighbor_types(atom)[self.neighbor_type] >= self.count:
                return f(atom)
        return wrapped

class NeighborsAtMost(OplsDecorator):
    def __init__(self, neighbor_type, count):
        self.neighbor_type = neighbor_type
        self.count = count

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if self.neighbor_type in neighbor_types(atom) and neighbor_types(atom)[self.neighbor_type] <= self.count:
                return f(atom)
        return wrapped

class Whitelist(OplsDecorator):
    def __init__(self, rule_numbers):
        if isinstance(rule_numbers, (list, tuple, set)):
            self.rule_numbers = list(map(str, rule_numbers))
            self.rule_numbers.sort()
        else:
            self.rule_numbers = [str(rule_numbers)]

    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if f(atom):
                whitelist(atom, self.rule_numbers)
                return True

        return wrapped

class Blacklist(OplsDecorator):
    def __init__(self, rule_numbers):
        if isinstance(rule_numbers, (list, tuple, set)):
            self.rule_numbers = list(map(str,rule_numbers))
            self.rule_numbers.sort()
        else:
            self.rule_numbers = [str(rule_numbers)]


    def __call__(self, f):
        # this must be called 'wrapped'
        def wrapped(atom):
            if f(atom):
                blacklist(atom, self.rule_numbers)
                return True

        return wrapped



def get_decorator_objects_by_type(decorated_function, decorator_type):
    rval = []

    # find an object of decorator_type in the function's closure (there should be only one)
    for cell in decorated_function.func_closure:
        closure_entry = cell.cell_contents
        if isinstance(closure_entry, decorator_type):
            rval.append(closure_entry)
            break

    # find a function called wrapper in the function's closure, and recurse on that
    for cell in decorated_function.func_closure:
        closure_entry = cell.cell_contents
        if hasattr(closure_entry, '__name__') and closure_entry.__name__ is "wrapped":
            wrapped_decorator_objects = get_decorator_objects_by_type(closure_entry, decorator_type)
            rval += wrapped_decorator_objects
            break

    return rval



# def get_decorator_objects(decorated_function):
#     rval = []
#
#     # find an object of decorator_type in the function's closure (there should be only one)
#     for cell in decorated_function.func_closure:
#         closure_entry = cell.cell_contents
#         if isinstance(closure_entry, decorator_type):
#             rval.append(closure_entry)
#             break
#
#     # find a function called wrapper in the function's closure, and recurse on that
#     for cell in decorated_function.func_closure:
#         closure_entry = cell.cell_contents
#         if hasattr(closure_entry, '__name__') and closure_entry.__name__ is "wrapped":
#             wrapped_decorator_objects = get_decorator_objects_by_type(closure_entry, decorator_type)
#             rval += wrapped_decorator_objects
#             break
#
#     return rval


def check_neighbors_exactly(pattern, neighbor_type, count):
    cnt = 0
    for elem in pattern:
        if elem == neighbor_type:
            cnt+=1

    return cnt == count

def check_neighbors_at_least(pattern, neighbor_type, count):
    cnt = 0
    for elem in pattern:
        if elem == neighbor_type:
            cnt+=1

    return cnt >= count

def check_neighbors_at_least(pattern, neighbor_type, count):
    cnt = 0
    for elem in pattern:
        if elem == neighbor_type:
            cnt+=1

    return cnt <= count


def atomtypes_opls(compound, debug=False):
    """Determine OPLS-aa atomtypes for all atoms in `compound`.

    This is where everything is orchestrated and the outer iteration happens.


    TODO: look into factoring out functions for different rings (see 145)
    """
    # Build a map to all of the supported opls_* functions.
    for fn, fcn in sys.modules[__name__].__dict__.items():
        if fn.startswith('opls_'):
            rule_number_to_rule[fn.split("_")[1]] = fcn

    for rule_number, rule in rule_number_to_rule.items():
        decorators = get_decorator_objects_by_type(rule, OplsDecorator)

        element_type = None
        neighbor_count = None
        for dec in decorators:
            if isinstance(dec, Element):
                element_type = dec.element_type
            if isinstance(dec, NeighborCount):
                neighbor_count = dec.count

        if element_type and (neighbor_count is None):
            if element_type not in rule_map:
                rule_map[element_type] = dict()

            if '*' not in rule_map[element_type]:
                rule_map[element_type]['*'] = []

            rule_map[element_type]['*'].append(rule)

        elif element_type and (neighbor_count is not None):
            if element_type not in rule_map:
                rule_map[element_type] = dict()

            if neighbor_count not in rule_map[element_type]:
                rule_map[element_type][neighbor_count] = []

            rule_map[element_type][neighbor_count].append(rule_number)
        else:
            warn('rule {} has no element type'.format(rule_number))

    # print rule_map


    supported_atom_types = set()
    for rule_number, rule in rule_number_to_rule.items():
        decorators = get_decorator_objects_by_type(rule, OplsDecorator)

        element_type = None
        for dec in decorators:
            if isinstance(dec, Element):
                assert element_type is None, "Duplicate element type decorators on rule {}".format(rule_number)
                element_type = dec.element_type
                supported_atom_types.add(element_type)

    supported_atom_types = list(supported_atom_types)
    supported_atom_types.sort()

    print(supported_atom_types)


    rule_matches = dict()
    for rule_number, rule in rule_number_to_rule.items():
        decorators = get_decorator_objects_by_type(rule, OplsDecorator)

        element_type = None
        neighbor_count = None
        rule_string = []

        for dec in decorators:
            if isinstance(dec, Element):
                assert element_type is None, "Duplicate element type decorators on rule {}".format(rule_number)
                element_type = dec.element_type
            if isinstance(dec, NeighborCount):
                assert neighbor_count is None, "Duplicate neighbor count decorators on rule {}".format(rule_number)
                neighbor_count = dec.count

        all_patterns = set(combinations_with_replacement(supported_atom_types, neighbor_count))

        removed_patterns = set()
        for dec in decorators:
            if isinstance(dec, NeighborsExactly):
                for pattern in all_patterns:
                    if not pattern.count(dec.neighbor_type)==dec.count:
                        removed_patterns.add(pattern)
            if isinstance(dec, NeighborsAtLeast):
                for pattern in all_patterns:
                    if not pattern.count(dec.neighbor_type)>=dec.count:
                        removed_patterns.add(pattern)
            if isinstance(dec, NeighborsAtMost):
                for pattern in all_patterns:
                    if not pattern.count(dec.neighbor_type)<=dec.count:
                        removed_patterns.add(pattern)

        all_patterns.difference_update(removed_patterns)

        for pattern in all_patterns:
            if (element_type, pattern) not in rule_matches:
                rule_matches[(element_type, pattern)] = set([rule_number])
            else:
                rule_matches[(element_type, pattern)].add(rule_number)


    print rule_matches

    for k, rules in rule_matches.items():
        import networkx as nx
        if len(rules) > 1:
            element_type, pattern = k

            G = nx.DiGraph()

            for rule_number in rules:
                blacklisted_rules = set()
                decorators = get_decorator_objects_by_type(rule_number_to_rule[rule_number], OplsDecorator)

                for dec in decorators:
                    if isinstance(dec, Blacklist):
                        blacklisted_rules.update(dec.rule_numbers)

                for blacklisted_rule in blacklisted_rules:
                    # if blacklisted_rule not in rules:
                    #

                    G.add_edge(rule_number, blacklisted_rule)

            # check if connected
            if not nx.is_connected(G.to_undirected()):
                warn("for pattern {} rule graph {} is not connected: {}".format(pattern, rule_number, G.edges()))

            # check if DAG
            if not nx.is_directed_acyclic_graph(G):
                warn("for pattern {} rule graph {} is not a DAG: {}".format(pattern, rule_number, G.edges()))

            # check if there's a unique sink
            sinks = []
            for node in G.nodes():
                if len(nx.descendants(G, node)) == 0:
                    sinks.append(node)

            if len(sinks)>1:
                warn("for pattern {} rule graph {} has multiple sinks ({}): {} ".format(pattern, rule_number, sinks, G.edges()))



    # Add white- and blacklists to all atoms.
    for atom in compound.yield_atoms():
        prepare(atom)

    max_iter = 10
    for iter_cnt in range(max_iter):
        #print ("Iteration {}".format(iter_cnt))

        # For comparing the lengths of the white- and blacklists.
        old_len = 0
        new_len = 0
        for atom in compound.yield_atoms():
            old_len += len(atom.opls_whitelist)
            old_len += len(atom.opls_blacklist)

            if atom.kind == 'G':  # Ignore Ports.
                continue

            if atom.kind in rule_map:
                if '*' in rule_map[atom.kind]:
                    for rule in rule_map[atom.kind]['*']:
                        run_rule(atom, rule)

                if len(atom.neighbors) in rule_map[atom.kind]:
                    for rule in rule_map[atom.kind][len(atom.neighbors)]:
                        run_rule(atom, rule)
                else:
                    warn("No rule for {}-neighbor '{}' atom".format(len(atom.neighbors), atom.kind))
            else:
                warn("No rule for atom kind '{}'".format(atom.kind))

            new_len += len(atom.opls_whitelist)
            new_len += len(atom.opls_blacklist)

        # Nothing changed, we're done!
        if old_len == new_len:
            break
    else:
        warn("Reached maximum iterations. Something probably went wrong.")

    for i, atom in enumerate(compound.atoms):
        opls_type = atom.opls_whitelist - atom.opls_blacklist
        opls_type = [a for a in opls_type]

        if debug:
            atom.extras['opls_type'] = opls_type
        else:
            if len(opls_type) == 1:
                atom.extras['opls_type'] = opls_type[0]
            else:
                warn("CHECK YOUR TOPOLOGY. Found multiple or no OPLS types for atom {0} ({1}): {2}.".format(
                        i, atom.kind, opls_type))
                atom.extras['opls_type'] = "XXX"

def prepare(atom):
    """Add white- and blacklists to atom. """
    atom.extras['opls_whitelist'] = OrderedSet()
    atom.extras['opls_blacklist'] = OrderedSet()


def run_rule(atom, rule_id):
    """Execute the rule function for a specified OPLS-aa atomtype. """
    if not rule_id in atom.opls_blacklist and not rule_id in atom.opls_whitelist:
        try:
            rule_fn = rule_number_to_rule[str(rule_id)]
        except KeyError:
            raise KeyError('Rule for {} not implemented'.format(rule_id))
        rule_fn(atom)


def neighbor_types(atom):
    """Maintains number of neighbors of each element type for all atoms.

    The dict maintained is `neighbor_types_map` and is organized as follows:
        atom: defaultdict{element: number of neighbors of that element type}

    E.g. for an atom with 3 carbon and 1 hydrogen neighbors:
        Atom: {'C': 3, 'H': 1}
    """
    if atom in neighbor_types_map:
        return neighbor_types_map[atom]
    else:
        rval = defaultdict(int)
        for b in atom.bonds:
            kind = b.other_atom(atom).kind
            rval[kind] += 1
        neighbor_types_map[atom] = rval
    return rval


def check_atom(neighbor, input_rule_ids):
    """Ensure that atom is valid candidate.

    Checks that every rule in `rule_ids` is in the white- and not the blacklist.
    """
    rule_ids = set()
    if isinstance(input_rule_ids, (list, tuple, set)):
        for r in input_rule_ids:
            rule_ids.add(str(r))
    else:
        rule_ids.add(str(input_rule_ids))
    rule_ids.intersection_update(neighbor.opls_whitelist)
    rule_ids.difference_update(neighbor.opls_blacklist)
    return rule_ids


def whitelist(atom, rule):
    """Whitelist an OPLS-aa atomtype for an atom. """
    if isinstance(rule, (list, tuple, set)):
        for r in rule:
            atom.opls_whitelist.add(str(r))
    else:
        atom.opls_whitelist.add(str(rule))


def blacklist(atom, rule):
    """Blacklist an OPLS-aa atomtype for an atom. """
    if isinstance(rule, (list, tuple, set)):
        for r in rule:
            atom.opls_blacklist.add(str(r))
    else:
        atom.opls_blacklist.add(str(rule))


def get_opls_fn(name):
    """Get the full path to a file used to validate the OPLS-aa atomtyper.

    In the source distribution, these files are in ``opls_validation``.

    Args:
        name (str): Name of the file to load.
    """
    fn = resource_filename('mbuild',
                           os.path.join('..', 'opls_validation', name))
    if not os.path.exists(fn):
        raise ValueError('Sorry! {} does not exists. If you just '
                         'added it, you\'ll have to re install'.format(fn))
    return fn


def no_pattern(atom, valency):
    warn("No connectivity patterns matched {} with valency {} and neighbors "
         "{}.".format(atom, valency, neighbor_types(atom).items()))


def no_rule(atom, valency):
    warn("Found no rules for {}-valent {}.".format(valency, atom))


class Rings(object):
    """Find all rings of a specified length that the atom is a part of.

    Note: Finds each ring twice because the graph is traversed in both directions.
    """
    def __init__(self, atom, ring_length):
        """Initialize a ring bearer. """
        self.rings = list()
        self.current_path = list()
        self.ring_length = ring_length
        self.current_path.append(atom)
        self.step(atom)

    def step(self, atom):
        neighbors = atom.neighbors
        if len(neighbors) > 1:
            for n in neighbors:
                # Check to see if we found a ring.
                current_length = len(self.current_path)
                if current_length > 2 and n == self.current_path[0]:
                    self.rings.append(copy(self.current_path))
                # Prevent stepping backwards.
                elif n in self.current_path:
                    continue
                else:
                    if current_length < self.ring_length:
                        # Take another step.
                        self.current_path.append(n)
                        self.step(n)
                    else:
                        # Reached max length.
                        continue
            else:
                # Finished looping over all neighbors.
                del self.current_path[-1]
        else:
            # Found a dead end.
            del self.current_path[-1]

#-----------------------------------------------#
# Filters for each element to break up the code #
#-----------------------------------------------#


# def carbon(atom):
#     valency = len(atom.bonds)
#     assert valency < 5, 'Found carbon with valency {}.'.format(valency)
#
#     if valency == 4:
#         if neighbor_types(atom)['H'] == 4:
#             for rule_id in [138]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['H'] == 3 and neighbor_types(atom)['C'] == 1:
#             for rule_id in [135, 148]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['H'] == 2 and neighbor_types(atom)['C'] == 2:
#             for rule_id in [136, 149, 218]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['H'] == 1 and neighbor_types(atom)['C'] == 3:
#             for rule_id in [137]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['C'] == 4:
#             for rule_id in [139]:
#                 run_rule(atom, rule_id)
#         elif (neighbor_types(atom)['C'] == 1 and
#               neighbor_types(atom)['O'] == 1 and
#               neighbor_types(atom)['H'] == 2):
#             for rule_id in [218]:
#                 run_rule(atom, rule_id)
#         else:
#             no_pattern(atom, valency)
#     elif valency == 3:
#         if neighbor_types(atom)['H'] == 2 and neighbor_types(atom)['C'] == 1:
#             for rule_id in [143]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['H'] == 1 and neighbor_types(atom)['C'] == 2:
#             for rule_id in [142, 145]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['C'] == 3:
#             for rule_id in [141, 145, '145B', 221]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['C'] >= 2:
#             for rule_id in [145]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['C'] >= 1 and neighbor_types(atom)['O'] == 1:
#             for rule_id in [232]:
#                 run_rule(atom, rule_id)
#         else:
#             no_pattern(atom, valency)
#     else:
#         no_rule(atom, valency)
#
#
# def hydrogen(atom):
#     valency = len(atom.bonds)
#     assert valency < 2, 'Found hydrogen with valency {}'.format(valency)
#
#     if valency == 1:
#         if neighbor_types(atom)['C'] == 1:
#             for rule_id in [140, 144, 146, 279]:
#                 run_rule(atom, rule_id)
#         elif neighbor_types(atom)['O'] == 1:
#             for rule_id in [155]:
#                 run_rule(atom, rule_id)
#         else:
#             no_pattern(atom, valency)
#     else:
#         no_rule(atom, valency)
#
#
# def oxygen(atom):
#     valency = len(atom.bonds)
#     # TODO: check if OPLS has parameters for things like hydronium
#     assert valency < 3, 'Found oxygen with valency {}.'.format(valency)
#
#     if valency == 2:
#         if neighbor_types(atom)['H'] == 1 and neighbor_types(atom)['C'] == 1:
#             for rule_id in [154]:
#                 run_rule(atom, rule_id)
#         else:
#             no_pattern(atom, valency)
#     elif valency == 1:
#         if neighbor_types(atom)['C'] == 1:
#             for rule_id in [278]:
#                 run_rule(atom, rule_id)
#         else:
#             no_pattern(atom, valency)
#     else:
#         no_rule(atom, valency)
#


#---------------------------------------------------------#
# Filters for some specific patterns to break up the code #
#---------------------------------------------------------#


def benzene(atom):
    """Check if atom is part of a single benzene ring. """
    benzene = Rings(atom, 6).rings
    # 2 rings, because we count the traversal in both directions.
    if len(benzene) == 2:
        for c in benzene[0]:
            if not (c.kind == 'C' and len(c.neighbors) == 3):
                break
        else:
            return benzene[0]  # Only return one direction of the ring.
    return False

#----------------#
# House of rules #
#----------------#


# Alkanes
@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 1)
@NeighborsExactly('H', 3)
@Whitelist(135)
def opls_135(atom):
    # alkane CH3
    return True


@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 2)
@NeighborsExactly('H', 2)
@Whitelist(136)
def opls_136(atom):
    # alkane CH2
    return True

@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 3)
@NeighborsExactly('H', 1)
@Whitelist(137)
def opls_137(atom):
    # alkane CH
    return True


@Element('C')
@NeighborCount(4)
@NeighborsExactly('H', 4)
@Whitelist(138)
def opls_138(atom):
    # alkane CH4
    return True


@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 4)
@Whitelist(139)
def opls_139(atom):
    # alkane C
    return True


@Element('H')
@NeighborCount(1)
@NeighborsExactly('C', 1)
@Whitelist(140)
def opls_140(atom):
    # alkane H
    return True


# Alkenes

@Element('C')
@NeighborCount(3)
@NeighborsExactly('C', 3)
@Whitelist(141)
def opls_141(atom):
    # alkene C (R2-C=)
    return True


@Element('C')
@NeighborCount(3)
@NeighborsExactly('C', 2)
@NeighborsExactly('H', 1)
@Whitelist(142)
def opls_142(atom):
    # alkene C (RH-C=)
    return True


@Element('C')
@NeighborCount(3)
@NeighborsExactly('C', 1)
@NeighborsExactly('H', 2)
@Whitelist(143)
def opls_143(atom):
    # alkene C (H2-C=)
    return True

@Element('H')
@NeighborCount(1)
@NeighborsExactly('C', 1)
@Whitelist(144)
@Blacklist(140)
def opls_144(atom):
    # alkene H (H-C=)
    # Make sure that the carbon is an alkene carbon.
    rule_ids = [141, 142, 143]
    return check_atom(atom.neighbors[0], rule_ids)

@Element('C')
@NeighborCount(3)
@NeighborsAtLeast('C', 2)
@Whitelist(145)
@Blacklist([141, 142])
def opls_145(atom):
    # Benzene C - 12 site JACS,112,4768-90. Use #145B for biphenyl
    return benzene(atom)

@Element('C')
@NeighborCount(3)
@NeighborsExactly('C', 3)
@Whitelist('145B')
@Blacklist([141, 145])
def opls_145B(atom):
    # Biphenyl C1
    # Store for checking for neighbors outside the first ring.
    ring_one = benzene(atom)
    if ring_one:
        for neighbor in atom.neighbors:
            if neighbor not in ring_one:
                if benzene(neighbor):
                    return True

@Element('H')
@NeighborCount(1)
@Whitelist(146)
@Blacklist([140, 144])
def opls_146(atom):
    # Benzene H - 12 site.
    return check_atom(atom.neighbors[0], 145)

#def opls_147
    # Napthalene fusion C (C9)

@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 1)
@NeighborsExactly('H', 3)
@Whitelist(148)
@Blacklist(135)
def opls_148(atom):
    # C: CH3, toluene
    for neighbor in atom.neighbors:
        if neighbor.kind == 'C':
            if check_atom(neighbor, 145):
                return True

@Element('C')
@NeighborCount(4)
@NeighborsExactly('C', 2)
@NeighborsExactly('H', 2)
@Whitelist(149)
@Blacklist(136)
def opls_149(atom):
    # C: CH2, ethyl benzene
    for neighbor in atom.neighbors:
        if neighbor.kind == 'C':
            if check_atom(neighbor, 145):
                return True

@Element('O')
@NeighborCount(2)
@NeighborsExactly('H', 1)
@Whitelist(154)
def opls_154(atom):
    # all-atom O: mono alcohols
    return True

@Element('H')
@NeighborCount(1)
@NeighborsExactly('O', 1)
@Whitelist(155)
def opls_155(atom):
    # all-atom H(O): mono alcohols, OP(=O)2
    return check_atom(atom.neighbors[0], 154)


@Element('C')
@NeighborCount(4)
@NeighborsExactly('O', 1)
@NeighborsExactly('C', 1)
@NeighborsExactly('H', 2)
@Whitelist(218)
def opls_218(atom):
    # C in CH2OH - benzyl alcohols
    benzene_carbon = False
    alcohol_oxygen = False
    for neighbor in atom.neighbors:
        if neighbor.kind == 'C':
            benzene_carbon = check_atom(neighbor, 145)
        if neighbor.kind == 'O':
            alcohol_oxygen = check_atom(neighbor, 154)
    if benzene_carbon and alcohol_oxygen:
        return True

@Element('C')
@NeighborCount(3)
@NeighborsExactly('C', 3)
@Whitelist(221)
@Blacklist([141, 145, '145B'])
def opls_221(atom):
    # C(CH2OH)   - benzyl alcohols
    if check_atom(atom, 145):  # Already identified as part of benzene.
        for neighbor in atom.neighbors:
            if check_atom(neighbor, 218):
                return True

@Element('C')
@NeighborCount(3)
@NeighborsAtLeast('C', 1)
@NeighborsExactly('O', 1)
@Whitelist(232)
def opls_232(atom):
    # C: C=0 in benzaldehyde, acetophenone (CH)
    for neighbor in atom.neighbors:
        if neighbor.kind == 'C':
            benzene_carbon = check_atom(neighbor, 145)
        if neighbor.kind == 'O':
            aldehyde_oxygen = check_atom(neighbor, 278)
    if benzene_carbon and aldehyde_oxygen:
        return True

@Element('O')
@NeighborCount(1)
@NeighborsAtLeast('C', 1)
@Whitelist(278)
def opls_278(atom):
    # AA O: aldehyde
    return True


@Element('H')
@NeighborCount(1)
@NeighborsAtLeast('C', 1)
@Whitelist(279)
@Blacklist([140, 144, 146])
def opls_279(atom):
    # AA H-alpha in aldehyde & formamide
    return check_atom(atom.neighbors[0], [232, 277])

if __name__ == "__main__":
    import pdb

    from mbuild.examples.methane.methane import Methane

    m = Methane()
    # m = Compound.load(get_opls_fn('isopropane.pdb'))
    # m = Compound.load(get_opls_fn('cyclohexane.pdb'))
    # m = Compound.load(get_opls_fn('neopentane.pdb'))
    # m = Compound.load(get_opls_fn('benzene.pdb'))
    # m = Compound.load(get_opls_fn('1-propene.pdb'))
    # m = Compound.load(get_opls_fn('biphenyl.pdb'))

    # from mbuild.examples.alkane_monolayer.alkane_monolayer import AlkaneMonolayer
    # m = AlkaneMonolayer(chain_length=3)

    atomtypes_opls(m)

    for i, atom in enumerate(m.atoms):
        # if i > 1799:
            #print "Atom kind={}, opls_whitelist={},  opls_blacklist={}".format(
            #    atom.kind, atom.opls_whitelist, atom.opls_blacklist)
            print "Atom kind={}, opls_type={}".format(
                atom.kind, atom.opls_type)
