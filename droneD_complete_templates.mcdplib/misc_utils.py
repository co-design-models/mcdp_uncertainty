from dataclasses import dataclass
from typing import Mapping

from mcdp_dp import PrimitiveDPFRIB, Tracer
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
    dpL: PrimitiveDPFRIB[
        FT,
        RT,
        IT,
        BT,
    ]
    dpU: PrimitiveDPFRIB[
        FT,
        RT,
        IT,
        BT,
    ]
