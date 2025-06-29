#!/usr/bin/env python3
from dataclasses import dataclass

import numpy as np

from mcdp_dp import get_dp_bounds, Tracer
from mcdp_ipython_utils import set_axis_colors
from mcdp_lang import convert_string_query
from mcdp_library import get_librarian, MCDPLibrary
from mcdp_ndp import CompositeNamedDP
from mcdp_posets import P_Math, UpperSet
from misc_utils import SolveStatsResults
from plot_utils import ieee_fonts_zoom3, ieee_spines_zoom3
from quickapp import QuickApp, QuickAppContext
from reprep import Report
from zuper_commons.fs import make_sure_dir_exists
from zuper_commons.logs import ZLogger
from zuper_commons.text import LibraryName
from zuper_commons.types import add_context, ZValueError
from zuper_params import DecentParams
from zuper_utils_asyncio import SyncTaskInterface

logger = ZLogger(__name__)


#
# def create_power_approx(interval_mw, context):
#     s = """
#     mcdp {
#     provides power [W]
#     requires power [W]
#
#     required power  >= approxu(provided power, %s mW)
#     }
#     """ % interval_mw
#
#     ndp = parse_ndp(s, context)
#
#     return ndp


def get_ndp_code(interval_mw: float):
    s = (
        # language=mcdp
        """\
from repo "github.com/co-design-models/uav_energetics" import library droneD_complete_v2
from repo "github.com/co-design-models/uav_energetics" import library batteries_nodisc
 
ignore_resources(total_cost) specialize [
  Battery: `batteries_nodisc.batteries,
  Actuation: `droneD_complete_v2.Actuation,
  PowerApprox: mcdp {
    provides power [W]
    requires power [W]

    required power  >= approxu(provided power, %s mW)
   }
] `ActuationEnergeticsTemplate
"""
        % interval_mw
    )
    return s


# def create_ndp(context, interval_mw):
#     template = parse_template('`ActuationEnergeticsTemplate', context)
#     Battery = parse_ndp('`batteries_nodisc.batteries', context)
#     Actuation = parse_ndp('`droneD_complete_v2.Actuation', context)
#     PowerApprox = create_power_approx(interval_mw=interval_mw, context=context)
#     params = dict(Battery=Battery,
#                   PowerApprox=PowerApprox,
#                   Actuation=Actuation)
#     ndp = template.specialize(params, context)
#
#     ndp = ignore_some(ndp, ignore_fnames=[], ignore_rnames=['total_cost'])
#     return ndp


@dataclass
class DroneUnc2Result:
    intervals: list[float]
    results: list[SolveStatsResults]


def drone_unc2_go() -> DroneUnc2Result:
    librarian = get_librarian(main_dir="../..")
    library = librarian.load_library(LibraryName("droneD_complete_templates"))
    assert isinstance(library, MCDPLibrary), library
    library.use_cache_dir("_cached/drone_unc2")

    intervals = [0.001, 0.01, 0.1, 1.0, 5.0, 10.0, 50, 100.0, 250, 500, 1000]
    results = []
    for i, interval_mw in enumerate(intervals):
        s = get_ndp_code(interval_mw=interval_mw)
        si, ndp = library.interpret_ndp(s).split()

        basename = ("drone_unc2_%02d_%s_mw" % (i, interval_mw)).replace(".", "_")
        fn = basename + ".mcdp"
        make_sure_dir_exists(fn)

        with open(fn, "w") as f:
            f.write(s)
        print("Generated %s" % fn)

        result = solve_stats(ndp, 1)
        results.append(result)

    return DroneUnc2Result(intervals=intervals, results=results)


def solve_stats(ndp: CompositeNamedDP, n: int) -> SolveStatsResults:
    query = {
        "endurance": "1.5 hour",
        "velocity": "1 m/s",
        "extra_power": " 1 W",
        "extra_payload": "100 g",
        "num_missions": "100 []",
    }
    f = convert_string_query(ndp=ndp, query=query)

    dp0 = ndp.get_dp()
    dpL, dpU = get_dp_bounds(dp0, nl=n, nu=n)

    F = dp0.F
    F.belongs(f)

    traceL = Tracer(logger=logger)
    resL = dpL.solve_f_trace(f=f, tracer=traceL)
    traceU = Tracer(logger=logger)
    resU = dpU.solve_f_trace(f=f, tracer=traceU)
    # R = dp0.R
    UR = dp0.get_UR()
    print("resultsL: %s" % UR.format(resL))
    print("resultsU: %s" % UR.format(resU))
    #
    # res["traceL"] = traceL
    # res["traceU"] = traceU
    # res["resL"] = resL
    # res["resU"] = resU
    # res["nsteps"] = 100

    return SolveStatsResults(
        traceL=traceL, traceU=traceU, resL=resL, resU=resU, n=n, query=query, ndp=ndp, dpL=dpL, dpU=dpU
    )


def get_only_one[X](P: P_Math[X], w: UpperSet[X]) -> X | None:
    if not w.minimals:
        return None
    el = list(w.minimals)[0]

    _, v0, _, _ = P.to_interval2(el)
    return float(v0)  # FIXME: 1 can be infinite


def drone_unc2_report(data: DroneUnc2Result) -> Report:
    from matplotlib import pylab

    ieee_fonts_zoom3(pylab)
    r = Report()

    logger.info("reading iterations")
    num_iterations_L = [get_num_iterations(res_i.traceL) for res_i in data.results]
    num_iterations_U = [get_num_iterations(res_i.traceU) for res_i in data.results]

    with add_context(data=data):
        res_L = np.array([get_only_one(res_i.dpL.R, res_i.resL) for res_i in data.results], dtype=float)
        res_U = np.array([get_only_one(res_i.dpU.R, res_i.resU) for res_i in data.results], dtype=float)

    accuracy = np.array(res_U) - np.array(res_L)

    logger.debug(res_U=res_U, res_L=res_L, accuracy=accuracy)
    num_iterations = np.array(num_iterations_L) + np.array(num_iterations_U)

    print(res_L)
    print(res_U)
    print(num_iterations_L)
    print(num_iterations_U)

    intervals = np.array(data.intervals, dtype=float)

    print("Plotting")
    f = r.figure("fig1", cols=2)

    LOWER = "bo-"
    UPPER = "mo-"

    markers = dict(markeredgecolor="none", markerfacecolor="black", markersize=6, marker="o")
    LOWER2 = dict(color="orange", linewidth=4, linestyle="-", clip_on=False)
    UPPER2 = dict(color="purple", linewidth=4, linestyle="-", clip_on=False)
    LOWER2.update(markers)
    UPPER2.update(markers)
    color_resources = "#700000"
    # color_functions = '#007000'
    color_tolerance = "#000000"

    attrs = dict(clip_on=False)

    fig = dict(figsize=(4.5, 4))
    fig_tall = dict(figsize=(3.5, 7))

    label_tolerance = "tolerance α [mW]"
    #     label_tolerance = 'tolerance $\\alpha$ [mW]'

    with f.plot("fig_num_iterations", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.plot(intervals, num_iterations_L, **LOWER2)
        pylab.plot(intervals, num_iterations_U, **UPPER2)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("iterations")

    with f.plot("fig_num_iterations_log", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        logger.info(f"tolerance: {intervals}")
        pylab.loglog(intervals, num_iterations_L, **LOWER2)
        pylab.loglog(intervals, num_iterations_U, **UPPER2)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("iterations")

    with f.plot("mass", **fig_tall) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.plot(intervals, res_L, LOWER, **attrs)
        pylab.plot(intervals, res_U, UPPER, **attrs)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    with f.plot("mass3", **fig_tall) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.plot(intervals, res_L, **LOWER2)
        pylab.plot(intervals, res_U, **UPPER2)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    with f.plot("mass3log", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.semilogx(intervals, res_L, **LOWER2)
        pylab.semilogx(intervals, res_U, **UPPER2)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    with f.plot("mass_log", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.loglog(intervals, res_L, LOWER, **attrs)
        pylab.loglog(intervals, res_U, UPPER, **attrs)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    with f.plot("mass2_log", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.loglog(intervals, res_L, LOWER, **attrs)
        pylab.loglog(intervals, res_U, UPPER, **attrs)
        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    with f.plot("accuracy", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.plot(accuracy, num_iterations, "o", **attrs)
        pylab.ylabel("iterations")
        pylab.xlabel("solution uncertainty [g]")

    with f.plot("accuracy_log", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        pylab.loglog(accuracy, num_iterations, "o", **attrs)
        pylab.ylabel("iterations")
        pylab.xlabel("solution uncertainty [g]")

    with f.plot("mass2", **fig) as pylab:
        ieee_spines_zoom3(pylab)

        mean = res_L * 0.5 + res_U * 0.5
        err = (res_U - res_L) / 2

        e = pylab.errorbar(intervals, mean, yerr=err, color="black", linewidth=2, linestyle="None", **attrs)
        #         plotline: Line2D instance #         x, y plot markers and/or line
        #         caplines: list of error bar cap#         Line2D instances
        #         barlinecols: list of         LineCollection instances for the horizontal and vertical
        #         error ranges.
        e[0].set_clip_on(False)
        for b in e[1]:
            b.set_clip_on(False)
        for b in e[2]:
            b.set_clip_on(False)
            b.set_linewidth(2)

        pylab.xlabel(label_tolerance)
        pylab.ylabel("total mass [g]")
        set_axis_colors(pylab, color_tolerance, color_resources)

    return r


def get_num_iterations(trace: Tracer) -> int:
    loops = list(trace.find_loops())
    if len(loops) != 1:
        msg = "I expected to find only one loop."
        raise ZValueError(msg, loops=loops)

    loop = loops[0]

    # list of KleeneIteration
    iterations = loop.get_value1("iterations")
    return len(iterations)  # type: ignore


class DroneUnc2(QuickApp):
    def define_options(self, params: DecentParams) -> None:
        pass

    async def define_jobs_context(self, sti: SyncTaskInterface, context: QuickAppContext) -> None:
        result = context.comp(drone_unc2_go)
        r = context.comp(drone_unc2_report, result)
        context.add_report(r, "report")


if __name__ == "__main__":
    main = DroneUnc2.get_sys_main()
    main()
