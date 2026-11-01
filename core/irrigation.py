import numpy as np
from .crops import CROPS

EFFECTIVE_RAIN = 0.8   # share of rainfall the crop can use (assumption)


def water_balance(fc_daily, ens, crop, days=5):
    """Crop water need (ET0 x Kc) against forecast rain over the next days. Open-Meteo gives ET0 per day."""
    et0 = [float(x or 0) for x in fc_daily["et0_fao_evapotranspiration"][:days]]
    need = sum(et0) * CROPS[crop]["kc"]
    rain = np.array(ens["rain_mm"], dtype=float)[:, :days].sum(axis=1) * EFFECTIVE_RAIN
    median_rain = float(np.median(rain))
    dry_rain = float(np.percentile(rain, 10))
    return {"need_mm": round(need, 1), "useful_rain_mm": round(median_rain, 1),
            "gap_mm": round(max(0.0, need - median_rain), 1),
            "gap_dry_mm": round(max(0.0, need - dry_rain), 1), "days": days}
