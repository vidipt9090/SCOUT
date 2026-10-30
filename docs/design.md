# SCOUT design

Supply network (modelled): M5 gives real sales for 10 stores. Those sales roll up to four locations in `configs/network.yaml`. Retail DC serves the 4 California stores, the two peer DCs serve Texas and Wisconsin, and Plant is the upstream source for all 10. M5 does not say how stores are supplied, so this network is an assumption, and Plant making food, hobby and household goods is a simplification. The two personas are positions in one chain: each run takes one position's point of view.

To be written in K3. One assumption is recorded early: M5 has no stock levels, so inventory is synthetic (D8).

The last M5 sales day (2016-05-22) is treated as simulated today. News is current text from GNews snapshots and planted scenario items, so news dates and sales dates do not align by design.
