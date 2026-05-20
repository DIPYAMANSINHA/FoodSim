# Hyper-local Food Delivery Simulation

An agent-based simulation of hyper-local food delivery operations, developed as part of doctoral research at IIT Kharagpur. The simulation models on-demand meal delivery by gig workers and has been used to estimate negative externalities (emissions, parking demand), assess the economic sustainability of gig work, evaluate alternative delivery models (cloud kitchens), and explore policy interventions such as bicycle adoption.

## Publications

This code accompanies the following publications and the underlying doctoral thesis:

**Journal articles**

- Sinha, D., & Pandit, D. (2021). A simulation-based study to determine the negative externalities of hyper-local food delivery. *Transportation Research Part D: Transport and Environment*, 100, 103071.
- Sinha, D., & Pandit, D. (2023). Assessing the economic sustainability of gig work: A case of hyper-local food delivery workers in Kolkata, India. *Research in Transportation Economics*, 100, 101335.

**Conference papers**

- Sinha, D., & Pandit, D. (2024). Understanding the negative externalities of a cloud kitchen-based hyper-local food delivery model. In *Annual Conference on Infrastructure and Built Environment: Towards Sustainable and Resilient Societies* (pp. 271–287). Singapore: Springer Nature Singapore.
- Sinha, D., & Pandit, D. (2025). The role of gig worker earnings and workload in the adoption of bicycles in last-mile freight: A case of hyper-local food delivery in India. *Transportation Research Procedia*, 92, 218.

**Doctoral thesis**

- Sinha, D. (2022). *A Simulation-Based Study of Hyper-Local Food Delivery and Its Impact on Urban Environment and Employment* (Doctoral dissertation, IIT Kharagpur).

## Overview

The simulation runs in two stages:

- **Step 1** (`step1.py`) — bootstraps the delivery fleet. Starts with zero agents and progressively creates them to meet a given order volume. Outputs shift-wise fleet sizes required across the day.
- **Step 2** (`step2.py`) — takes the fleet sizes from Step 1 as input and simulates 30 days of operation. Produces emissions per delivery, parking demand, and the income distribution of delivery workers under a given pay structure.

The simulation supports several configurations explored across the publications:

- **Restaurant-based vs cloud-kitchen-based** delivery models (set via the `cloudkitchen` parameter).
- **Motorbike vs bicycle** delivery agents (set via the `shiftvol` parameter and a distance threshold).
- **Variable pay structures** (set via the `wagerate` parameter) to explore policy scenarios.
- **Order batching** of up to three orders per trip (set via `max_batching_limit`).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

(To be filled in after the code is cleaned up.)

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use this code in academic work, please cite the relevant paper(s) listed above.