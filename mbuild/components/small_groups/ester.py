import numpy as np

from mbuild.compound import Compound
from mbuild.port import Port
from mbuild.coordinate_transform import translate, translate_to, rotate_around_z


class Ester(Compound):
    """A ester group -C(=O)O-. """
    def __init__(self):
        super(Ester, self).__init__(self)

        self.append_from_file('ester.pdb', relative_to_module=self.__module__)
        translate(self, -self.C[0])

        self.add(Port(anchor=self.O[1]), 'up')
        rotate_around_z(self.up, np.pi / 2)
        translate_to(self.up, self.O[1] + np.array([0.07, 0, 0]))

        self.add(Port(anchor=self.C[0]), 'down')
        rotate_around_z(self.down, np.pi / 2)
        translate(self.down, np.array([-0.07, 0, 0]))

if __name__ == '__main__':
    m = Ester()
    m.visualize(show_ports=True)

