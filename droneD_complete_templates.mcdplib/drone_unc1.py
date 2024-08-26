#!/usr/bin/env python3

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast, Iterator

import numpy as np

from mcdp_ipython_utils import (
    plot_all_directions,
    set_axis_colors,
    solve_combinations,
    SolveQueriesResult,
    SolveQueryMultiple,
    to_numpy_array,
)
from mcdp_library import get_librarian, Librarian, MCDPLibrary
from mcdp_posets_algebra import frac_linspace
from plot_utils import ieee_fonts_zoom3, ieee_spines_zoom3
from quickapp import QuickApp
from reprep import Report
from zuper_commons.fs import make_sure_dir_exists
from zuper_commons.text import LibraryName


def get_ndp_code(battery: str) -> str:
    s = (
        """\
from shelf "github.com/co-design-models/uav_energetics" import library droneD_complete_v2
specialize [
  Battery: %s,
  Actuation: `droneD_complete_v2.Actuation,
  PowerApprox: mcdp {
    provides power [W]
    requires power [W]

    required power  >= approxu(provided power, 1 mW)
   }
] `ActuationEnergeticsTemplate
"""
        % battery
    )
    return s


@dataclass
class ProcessResult:
    dataL: SolveQueriesResult[Any]
    dataU: SolveQueriesResult[Any]


def drone_unc1_process(s: str) -> ProcessResult:
    librarian = get_librarian(main_dir='../..')
    # librarian.find_libraries("../..")
    library = librarian.load_library(cast(LibraryName, "droneD_complete_templates"))
    assert isinstance(library, MCDPLibrary), library
    library.use_cache_dir("_cached/drone_unc1")

    si, ndp = library.interpret_ndp(s).split()

    combinations0 = {
        "endurance": (frac_linspace(1, Decimal("1.5"), 10), "hour"),
        "extra_payload": (100, "g"),
        "num_missions": (1000, "[]"),
        "velocity": (1, "m/s"),
        "extra_power": (Decimal("0.5"), "W"),
    }
    combinations = SolveQueryMultiple(combinations0)

    result_like = dict(total_cost="USD", total_mass="kg")

    dataU = solve_combinations(ndp, combinations, result_like, upper=1, lower=None)
    dataL = solve_combinations(ndp, combinations, result_like, upper=None, lower=1)

    return ProcessResult(dataL=dataL, dataU=dataU)


def get_value(data: SolveQueriesResult[Any], field: str) -> Iterator[float]:
    for res in data.results:
        a = to_numpy_array({field: "kg"}, res)

        if len(a):
            a = min(a[field])
        else:
            a = None
        yield a


def drone_unc1_report(pr: ProcessResult) -> Report:
    r = Report()

    dataL = pr.dataL
    dataU = pr.dataU

    queries = dataL.queries
    endurance = [q.q["endurance"] for q in queries]

    from matplotlib import pylab

    ieee_fonts_zoom3(pylab)

    markers = dict(markeredgecolor="none", markerfacecolor="black", markersize=6, marker="o")
    LOWER2 = dict(color="orange", linewidth=4, linestyle="-", clip_on=False)
    UPPER2 = dict(color="purple", linewidth=4, linestyle="-", clip_on=False)
    LOWER2.update(markers)
    UPPER2.update(markers)
    color_resources = "#700000"
    color_functions = "#007000"

    fig = dict(figsize=(4.5, 4))

    with r.plot("total_mass", **fig) as pylab:
        ieee_spines_zoom3(pylab)
        total_massL = np.array(list(get_value(dataL, "total_mass")))
        total_massU = np.array(list(get_value(dataU, "total_mass")))
        print(endurance)
        print(total_massL, total_massU)
        pylab.plot(endurance, total_massL, **LOWER2)
        pylab.plot(endurance, total_massU, **UPPER2)
        set_axis_colors(pylab, color_functions, color_resources)
        pylab.xlabel("endurance [hours]")
        pylab.ylabel("total_mass [kg]")

    return r

    if False:
        what_to_plot_res = dict(total_cost="USD", total_mass="kg")
        what_to_plot_fun = dict(endurance="hour", extra_payload="g")

        print("Plotting lower")
        with r.subsection("lower") as rL:
            plot_all_directions(
                rL,
                queries=dataL.queries,
                results=dataL.results,
                what_to_plot_res=what_to_plot_res,
                what_to_plot_fun=what_to_plot_fun,
            )

        print("Plotting upper")
        with r.subsection("upper") as rU:
            plot_all_directions(
                rU,
                queries=dataU["queries"],
                results=dataU["results"],
                what_to_plot_res=what_to_plot_res,
                what_to_plot_fun=what_to_plot_fun,
            )

        return r


class DroneU(QuickApp):
    def define_options(self, params):
        pass

    async def define_jobs_context(self, sti, context):
        for l in ["batteries_uncertain1", "batteries_uncertain2", "batteries_uncertain3"]:
            battery = "`%s.batteries" % l
            s = get_ndp_code(battery)

            fn = f"drone_unc1_{l}.mcdp"
            make_sure_dir_exists(fn)

            with open(fn, "w") as f:
                f.write(s)
            print("Generated %s" % fn)

            result = context.comp(drone_unc1_process, s)
            r = context.comp(drone_unc1_report, result)
            context.add_report(r, "report", l=l)


if __name__ == "__main__":
    main = DroneU.get_sys_main()
    main()
