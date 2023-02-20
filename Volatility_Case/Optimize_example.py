import numpy as np
from scipy.optimize import minimize

def objective(x, *args):
    # Set total delta to current delta to start
    total_delta = args[0]
    # Set current value to 0
    value = 0.0

    for i, arb_op in enumerate(args[1:]):
        total_delta += arb_op["delta"] * x[i]
        value += (arb_op["value"] * x[i]) - arb_op["fee"]
    
    return (total_delta/value)

def constraint1(x,*args):
    return x[args[0]]

def constraint2(x, *args):
    return x[args[0]]

def constraint3(x, *args):
    value = 0

    for i, arb_op in enumerate(args[1:]):
        value += (arb_op["value"] * x[i]) - arb_op["fee"]

    return value

def constraint4(x, *args):
    # Set total delta to current delta to start
    total_delta = args[0]

    for i, arb_op in enumerate(args[1:]):
        total_delta += arb_op["delta"] * x[i]
    
    return total_delta

def constraint5(x,*args):
    return -1*constraint4(x,*args)

def constraint6(x,*args):
    total_gross_cost = 0.0

    for i, arb_op in enumerate(args[1:]):
        total_gross_cost += arb_op["gross_cost"] * x[i]
    
    return total_gross_cost
     
def constraint7(x,*args):
    total_net_cost = 0.0
    
    for i, arb_op in enumerate(args[1:]):
        total_net_cost += arb_op["net_cost"] * x[i]
    
    return total_net_cost

# initial guesses
n = len(arb_ops)
x0 = np.zeros(n)
x0[0] = 1.0
x0[1] = 5.0
x0[2] = 5.0
x0[3] = 1.0

# show initial objective
print('Initial SSE Objective: ' + str(objective(x0)))

# optimize
b = (1.0,5.0)
bnds = (b, b, b, b)
con1 = {'type': 'ineq', 'fun': constraint1} 
con2 = {'type': 'eq', 'fun': constraint2}
cons = ([con1,con2])
solution = minimize(objective,x0,method='SLSQP',\
                    bounds=bnds,constraints=cons)
x = solution.x

# show final objective
print('Final SSE Objective: ' + str(objective(x)))

# print solution
print('Solution')
print('x1 = ' + str(x[0]))
print('x2 = ' + str(x[1]))
print('x3 = ' + str(x[2]))
print('x4 = ' + str(x[3]))