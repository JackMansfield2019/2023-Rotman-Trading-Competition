import numpy as np
from scipy.optimize import linprog

# Define the problem constants
delta = 2
current_delta = 5
min_quantity = 10
max_trade_size = 50
delta_limit = 100

# Set up the objective function
c = [1, 0]

# Set up the inequality constraints
A_ub = [[0, -1],
        [delta, -1],
        [-delta, -1]]
b_ub = [0, 0, 0]

# Set up the equality constraints
A_eq = [[1, 1/(current_delta + delta_limit)]]
b_eq = [0]

# Set up the bounds for x
bounds = [(min_quantity, max_trade_size), (0, delta_limit)]

# Solve the linear programming problem
res = linprog(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)

# Print the results
print(res)