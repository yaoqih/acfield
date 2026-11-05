# ACField reference hardware

The current compact first-article candidate is the [95 × 80 mm acrylic design](acrylic_95/README.md), including DXF cutting files and 72 mm black-square robot tags. The previous [V11](print_v11/README.md) 130 mm printed design remains available as a separate reference. Neither has completed physical acceptance; check fit, strength, rolling resistance and control behavior before replication.

See the [hardware guide](https://yaoqih.github.io/acfield/hardware/overview) and [bring-up procedure](https://yaoqih.github.io/acfield/hardware/bringup).

For the compact candidate, start with the [dimension and dynamics notes](acrylic_95/dimensions.md), [one/four-robot BOM](acrylic_95/bom.csv), [updated audit layout](acrylic_95/audit_layout.png) and [exploded assembly](acrylic_95/exploded.png). The reproducible `acrylic_95/review.py` reads the committed DXFs; `acrylic_95/tag_images/generate.py` rebuilds and verifies twelve 80 mm labels. Legacy CSVs in this directory describe earlier versions and are not the compact purchase list.
