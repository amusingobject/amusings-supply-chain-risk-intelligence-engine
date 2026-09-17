# Scenario Grounding Queue

This is a collection/review queue. It does not modify scenario expectations, create evidence, or certify operational claims.

| Scenario | Split | Missing support | Collection requirement |
| --- | --- | --- | --- |
| Carrier ETA vs AIS conflicting evidence | holdout | `carrier_exception`, `carrier_service`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Conflicting port closure and restricted-operations notices | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Maersk cyberattack / carrier correlation | holdout | `carrier_exception`, `carrier_service`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Untrusted source prompt injection / port claim | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Shanghai lockdown / no Taiwan-origin dependency | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Yantian congestion / transshipment dependency | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Typhoon Gaemi / Keelung closure | dev | `carrier_service`, `port_operations`, `weather` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Typhoon Gaemi / Kaohsiung restrictions | dev | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Typhoon Gaemi / recovery lifecycle | dev | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Los Angeles–Long Beach congestion / inbound shipment | dev | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Los Angeles–Long Beach congestion / Seattle shipment | selection | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Panama Canal restrictions / eastbound route | selection | `carrier_service`, `infrastructure`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Panama Canal restrictions / Long Beach route | selection | `carrier_service`, `infrastructure`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| News-only geopolitical report / ambiguous location | holdout | `carrier_service`, `geopolitical`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Departure delay with deterministic stockout exposure | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| West Coast labor disruption / destination port | selection | `carrier_service`, `labor`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Port reopening vs stale closure report | holdout | `carrier_service`, `port_disruption`, `port_operations` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Caltrans closure / drayage leg | selection | `carrier_service`, `port_operations`, `road_disruption` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |
| Wildfire near inland facility / no closure evidence | holdout | `carrier_service`, `port_operations`, `wildfire` | Retain a dated primary source that explicitly supports the operational claim; weather-only or search-result evidence is insufficient. |

Open items: 19
