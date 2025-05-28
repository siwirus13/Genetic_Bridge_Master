# 🃏 Bridge Solver AI — Genetic Algorithm vs CPLEX

## 📌 Overview

This project applies Artificial Intelligence and Optimization techniques to **solve predetermined deals in the card game Duplicate Bridge**, inspired by the Bridge Master challenges on BBO (Bridge Base Online).

We use two methods to find the optimal line of play for the declarer:
- **Genetic Algorithm (GA)** — a nature-inspired optimization heuristic
- **Integer Linear Programming (ILP)** solved using **IBM CPLEX**

The goal is to compare the two methods in terms of:
- Tricks won (solution quality)
- Solving time
- Flexibility and scalability

---

## ♠️♦️ Project Objectives

- Simulate and solve **3–4 static bridge deals** with perfect information
- Implement a **Genetic Algorithm in Python** to evolve possible play sequences
- Model the problem as an **ILP** and solve it using **CPLEX**
- Provide a fair **comparison** between both methods

---

## 🗂️ Repository Structure

```bash
bridge_solver/
├── deals/             # Bridge deals in PBN or JSON format
│   ├── deal1.pbn
│   ├── deal2.pbn
│   └── ...
├── ga_solver.py       # Genetic Algorithm implementation
├── ilp_solver.py      # ILP model and CPLEX integration
├── bridge_engine.py   # Card legality, trick resolution logic
├── evaluate.py        # Runs experiments and generates plots
├── plots/             # Comparison visualizations
└── README.md          # You're here!

