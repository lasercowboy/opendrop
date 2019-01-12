from math import sin, cos, pi


# minimise calls to sin() and cos()
# defines the Young--Laplace system of differential equations to be solved
# x_vec can be an array of vectors, in which case, ylderiv will calculate the derivative for each
# row in a for loop and return an np.ndarray of of the derivatives
def ylderiv(x_vec, t, bond_number):
    x, y, phi, x_Bond, y_Bond, phi_Bond = x_vec

    x_s = cos(phi)
    y_s = sin(phi)
    phi_s = 2 - bond_number * y - y_s/x
    x_Bond_s = - y_s * phi_Bond
    y_Bond_s = x_s * phi_Bond
    phi_Bond_s = y_s * x_Bond / (x**2) - x_s * phi_Bond / x - y - bond_number * y_Bond

    return [x_s, y_s, phi_s, x_Bond_s, y_Bond_s, phi_Bond_s]


# defines the Young--Laplace system of differential equations to be solved
def dataderiv(x_vec, t, bond_number):
    x, y, phi, vol, sur = x_vec

    x_s = cos(phi)
    y_s = sin(phi)
    phi_s = 2 - bond_number * y - sin(phi)/x
    vol_s = pi * x**2 * y_s
    sur_s = 2 * pi * x

    return [x_s, y_s, phi_s, vol_s, sur_s]