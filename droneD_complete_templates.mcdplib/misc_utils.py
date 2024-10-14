from dataclasses import dataclass
from typing import Mapping

from mcdp_dp import DPI_FRIB, Tracer
from mcdp_ndp import CompositeNamedDP
from mcdp_posets import UpperSet


@dataclass
class SolveStatsResults[FT, RT, IT, BT]:
    traceL: Tracer
    traceU: Tracer
    resL: UpperSet[RT]
    resU: UpperSet[RT]
    n: int
    query: Mapping[str, str]
    ndp: CompositeNamedDP[FT, RT, IT, BT]
    dpL: DPI_FRIB[
        FT,
        RT,
        IT,
        BT,
    ]
    dpU: DPI_FRIB[
        FT,
        RT,
        IT,
        BT,
    ]
