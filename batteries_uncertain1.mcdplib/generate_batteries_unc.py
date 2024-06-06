#!/usr/bin/env python3

import string
from decimal import Decimal

from mcdp_posets import PosetWithMath
from zuper_commons.text import remove_escapes
from zuper_commons.types import add_context, check_isinstance, ZValueError

template = """\
mcdp {
    provides capacity [J]
    provides missions [dimensionless]

    requires mass     [g]
    requires cost     [USD]

    # Number of replacements
    requires maintenance [dimensionless]

    # Battery properties
    specific_energy_inv = Uncertain(1.0 []/ $specific_energy_U, 1.0 [] /  $specific_energy_L)
    specific_cost_inv = Uncertain(1.0 [] / $specific_cost_U, 1.0 [] / $specific_cost_L)
    cycles_inv = Uncertain(1.0 []/$cycles_U, 1.0[]/ $cycles_L)

    # Constraint between mass and capacity
    massc = provided capacity * specific_energy_inv

    # How many times should it be replaced?
    num_replacements = ceil(provided missions * cycles_inv)
    required maintenance >= num_replacements

    # Cost is proportional to number of replacements
    costc = (provided capacity * specific_cost_inv) * num_replacements

    required cost >= costc
    required mass >= massc
}

"""

types = {
    "NCA": dict(
        desc="Lithium nickel cobalt aluminum oxide",
        specific_energy="220 Wh/kg",
        specific_cost="",
        cycles="1500",
    ),
    "NMC": dict(
        desc="Lithium nickel manganese cobalt oxide",
        specific_energy="205 Wh/kg",
        specific_cost="",
        cycles="5000",
    ),
    "LCO": dict(
        desc="Lithium cobalt oxide", specific_energy="195 Wh/kg", specific_cost=" 2.84 Wh/$", cycles="750"
    ),
    "LiPo": dict(
        desc="Lithium polimer", specific_energy="150 Wh/kg", specific_cost=" 2.50 Wh/$", cycles="600"
    ),
    "LMO": dict(
        desc="Lithium manganese oxide ", specific_energy="150 Wh/kg", specific_cost=" 2.84 Wh/$", cycles="500"
    ),
    "NiMH": dict(
        desc="Nickel-metal hydride", specific_energy="100 Wh/kg", specific_cost=" 3.41 Wh/$", cycles="500"
    ),
    "LFP": dict(
        desc="Lithium iron phosphate", specific_energy=" 90 Wh/kg", specific_cost=" 1.50 Wh/$", cycles="1500"
    ),
    "NiH2": dict(
        desc="Nickel-hydrogen", specific_energy=" 45 Wh/kg", specific_cost="10.50 Wh/$", cycles="20000"
    ),
    "NiCad": dict(
        desc="Nickel-cadmium", specific_energy=" 30 Wh/kg", specific_cost=" 7.50 Wh/$", cycles="500"
    ),
    "SLA": dict(desc="Lead-acid", specific_energy=" 30 Wh/kg", specific_cost=" 7.00 Wh/$", cycles="500"),
}

from mcdp_lang import parse_constant


def enlarge(value_string: str, alpha: Decimal) -> tuple[str, str]:
    c = parse_constant(value_string)
    c_unit = check_isinstance(c.unit, PosetWithMath)
    c_unit = c_unit.get_ambient_poset()[-1]
    with add_context(c=c):
        _, value, _, _ = c_unit.to_interval2(c.value)

        # value = c_unit.to_interval(c.value)[0]

        l = c_unit.from_number_lower(value * (1 - alpha))
        u = c_unit.from_number_upper(value * (1 + alpha))

        ls = c.unit.format(l)
        us = c.unit.format(u)

        # if "[]" in value_string:
        #     ls = "%s []" % l
        #     us = "%s []" % u
        return remove_escapes(ls), remove_escapes(us)


def go(alpha: Decimal):
    summary = ""

    good = []
    discarded = []
    for name, v in types.items():
        if not v["specific_cost"]:
            # print("skipping %s because no specific cost" % name)
            discarded.append(name)
            continue

        v["cycles"] = "%s []" % v["cycles"]

        values = {}

        l, u = enlarge(v["specific_cost"], alpha)
        values["specific_cost_L"] = l
        values["specific_cost_U"] = u

        l, u = enlarge(v["specific_energy"], alpha)
        values["specific_energy_L"] = l
        values["specific_energy_U"] = u

        l, u = enlarge(v["cycles"], alpha)
        values["cycles_L"] = l
        values["cycles_U"] = u

        s2 = string.Template(template).substitute(values)

        print(s2)
        # ndp = parse_ndp(s2)
        model_name = f"Battery_{name}"
        fname = model_name + ".mcdp"
        with open(fname, "w") as f:
            f.write(s2)

        good.append(name)

        summary += "\n%10s %10s %10s %10s  %s" % (
            name,
            v["specific_energy"],
            v["specific_cost"],
            v["cycles"],
            v["desc"],
        )

    print(summary)
    with open("summary.txt", "w") as f:
        f.write(summary)
    ss = """
choose(
    %s
)
    """ % ",\n    ".join(
        "%8s: (load Battery_%s)" % (g, g) for g in good
    )
    with open("batteries.mcdp", "w") as f:
        f.write(ss)


import sys


def go0():
    alpha = Decimal(sys.argv[1])
    if not alpha > 0:
        raise ZValueError(arg=sys.argv[1])
    print("alpha: %s" % alpha)
    go(alpha)


if __name__ == "__main__":
    go0()
