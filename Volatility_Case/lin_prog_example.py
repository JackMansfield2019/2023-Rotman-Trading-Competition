# Import required libraries
import numpy as np
from scipy.optimize import linprog

# OBJECTS
class Arb_Opp:
	def __init__(self, value : float, delta : float , fee : int, opt_gross_cost : float, opt_net_cost : float, ETF_gross_cost : float, ETF_net_cost : float,
	min_quantity : int, max_quantity : int ):
		self.value : float = value
		self.delta : float = delta
		self.fee : float = fee 
		self.opt_gross_cost : int = opt_gross_cost
		self.opt_net_cost : int = opt_net_cost 
		self.ETF_gross_cost : int = ETF_gross_cost
		self.ETF_net_cost : int = ETF_net_cost 
		self.min_quantity : int = min_quantity
		self.max_quantity : int = max_quantity

arb_opp = Arb_Opp(
    value =  0.05,
    delta = 0,
    fee = 4.00,
    opt_gross_cost = 1,
    opt_net_cost = -1,
    ETF_gross_cost = 100,
    ETF_net_cost = 100,
    min_quantity = 80,
    max_quantity = 100,
)

# Set the inequality constraints matrix
# Note: the inequality constraints must be in the form of <=
A = np.array([[-1,0,0,0,0], [1,0,0,0,0], [0,arb_opp.opt_gross_cost,0,0,0], [0,0,arb_opp.opt_net_cost,0,0], [0,0,0,arb_opp.ETF_gross_cost,0], [0,0,0,0,arb_opp.ETF_net_cost]])

# Set the inequality constraints vector
b = np.array([arb_opp.min_quantity, 100, 2500, 1000, 50000, 50000])

# Set the coefficients of the linear objective function vector
# Note: when maximizing, change the signs of the c vector coefficient
c = np.array([1,0,0,0,0])

# Solve linear programming problem
res = linprog(c, A_ub=A, b_ub=b)

# Print results
print('Optimal value:', round(res.fun*-1, ndigits=2),
      '\nx values:', res.x,
      '\nNumber of iterations performed:', res.nit,
      '\nStatus:', res.message)