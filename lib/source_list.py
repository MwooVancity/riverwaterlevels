"""Which collect.py sources are expected everywhere vs only where a feature physically exists.
The source-health gate uses UNIVERSAL for its coverage check; the failure-rate check applies to
every source. Keep UNIVERSAL tight: a universal source's absence is essentially always a fault
(dead endpoint, bad key, schema change), not a per-river gap. A sensor/record/monitor-dependent
source is CONDITIONAL — its absence on a given reach is normal and never fails the gate."""

# exists at essentially every CONUS gauge point regardless of sensors or record length
UNIVERSAL = {"meta", "nws", "rain", "wpc", "cpc", "cpc610", "usdm", "acis", "uv"}

# only where the feature exists: a sensor, a forecast point, a tidal reach, a nearby monitor, a long record
CONDITIONAL = {"related", "nwps", "nwm", "peaks", "wtemp", "snotel", "attains", "fieldmeas",
               "floodfreq", "tides", "cameras", "airnow", "ridb", "near_wtemp", "streamcat",
               "nid", "fema_zone", "rise", "stocking", "access", "rating", "atlas14",
               "year", "multiyear", "record", "land"}

ALL_SOURCES = UNIVERSAL | CONDITIONAL
