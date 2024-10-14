import numpy as np
from matplotlib import pylab as pylab0

from mcdp_dp import get_dp_bounds, M_Fun_AddMany_DP, M_Fun_MultiplyMany_DP, DPI_Any
from mcdp_posets import get_math_bundle
from mcdp_posets_algebra import ApproximationAlgorithms
from mcdp_report import get_best_plotter
from plot_utils import ieee_fonts_zoom3, ieee_spines_zoom3
from reprep import Report


def plot_nominal_invmult(plt):
    nomimal_x = np.linspace(0.1, 10, 100)
    nomimal_y = 1.0 / nomimal_x
    plt.plot(nomimal_x, nomimal_y, "k-")
    axes = plt.gca()
    axes.xaxis.set_ticklabels([])
    axes.yaxis.set_ticklabels([])


def plot_nominal_invplus(plt):
    nomimal_x = np.linspace(0, 1.0, 100)
    nomimal_y = 1.0 - nomimal_x
    plt.plot(nomimal_x, nomimal_y, "k-")
    axes = plt.gca()
    axes.xaxis.set_ticklabels([])
    axes.yaxis.set_ticklabels([])


def go1(r: Report, ns: list[int], dp: DPI_Any, plot_nominal, axis):
    f = r.figure(cols=len(ns))

    for n in ns:
        dpL, dpU = get_dp_bounds(dp, n, n)

        f0 = 1

        UR = dp.get_UR()
        space = UR % UR

        urL = dpL.solve_friendly(f=f0)
        urU = dpU.solve_friendly(f=f0)
        value = urL, urU

        plotter = get_best_plotter(space)
        figsize = (4, 4)
        with f.plot("plot_n%d" % n, figsize=figsize) as pylab:
            ieee_spines_zoom3(pylab)
            plotter.plot(pylab, axis, space, value)
            plot_nominal(pylab)
            pylab.axis(axis)


def go() -> None:
    ieee_fonts_zoom3(pylab0)

    r = Report()
    algos = [ApproximationAlgorithms.UNIFORM, ApproximationAlgorithms.VAN_DER_CORPUT]
    for algo in algos:
        # InvMult2.ALGO = algo
        # InvPlus2.ALGO = algo
        print("Using algorithm %s " % algo)
        with r.subsection(algo) as r2:
            # first
            # F = parse_poset("dimensionless")
            mb = get_math_bundle()
            F = opspace = mb.get_non_neg_reals()
            R = F
            dp = M_Fun_MultiplyMany_DP(F=F, opspace=opspace, Rs=(R, R), algo=algo)
            ns = [3, 4, 5, 6, 10, 15]

            axis = (0.0, 6.0, 0.0, 6.0)

            with r2.subsection("invmult2") as rr:
                go1(rr, ns, dp, plot_nominal_invmult, axis)

            # second
            axis = (0.0, 1.2, 0.0, 1.2)
            dp = M_Fun_AddMany_DP(F=F, Rs=(R, R), opspace=opspace, algo=algo)
            with r2.subsection("invplus2") as rr:
                go1(rr, ns, dp, plot_nominal_invplus, axis)

    fn = "out-plot_approximations/report.html"
    print("writing to %s" % fn)
    r.to_html(fn)


if __name__ == "__main__":
    go()
