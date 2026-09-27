"""GraphCast adapter (B4)."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from canonical import accumulation as acc
from canonical.forecast import CanonicalForecast
from ingestion.base import Adapter
from ingestion.registry import register


class GraphCastAdapter(Adapter):
    name = "graphcast"
    label = "Google DeepMind GraphCast"
    kind = "ai"
    variables = ("precip", "t2m", "u10", "v10")

    def load(self, init_time: pd.Timestamp, variable: str,
             lead_days: list[int] | None = None) -> Optional[CanonicalForecast]:
        lead_days = lead_days or list(acc.LEAD_DAYS)
        month = init_time.strftime("%Y-%m")
        ds = self._read_nc(variable, month)
        if ds is None:
            return None
        if init_time not in ds.init.values:
            return None
        sel = ds[variable].sel(init=init_time)
        available = set(sel.lead_day.values.tolist())
        keep = [d for d in lead_days if d in available]
        if not keep:
            return None
        vals = sel.sel(lead_day=keep).values.astype(np.float32)
        return self._build_forecast(init_time, variable, keep, vals)


register(GraphCastAdapter())
