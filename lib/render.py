"""Facade: the block registry and page shell now live in lib/core, hero, charts, weather, forecast and page. Everything is re-exported here."""
import sys, types
from lib.core import *
from lib.hero import *
from lib.charts import *
from lib.weather import *
from lib.forecast import *
from lib.page import *
import lib.core as _core, lib.hero as _hero, lib.charts as _charts, lib.weather as _weather, lib.forecast as _forecast, lib.page as _page
from lib.page import b2, b3, _guard_blocks

_PARTS = (_core, _hero, _charts, _weather, _forecast, _page)


class _Facade(types.ModuleType):
    # build.py and tests set render.PREVIEW / render.INDEX_CFG: pass the new value on to the module whose code reads it.
    def __setattr__(self, k, v):
        for m in _PARTS:
            if k in vars(m):
                setattr(m, k, v)
        types.ModuleType.__setattr__(self, k, v)


sys.modules[__name__].__class__ = _Facade
_guard_blocks()
