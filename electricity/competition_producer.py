count = 0
first_lower = 0
first_upper = 0
second_lower = 0
second_upper = 0
final = 0
total_elec = 0
while(True):
    if(count == 0):
        first_lower = input("Enter the first forecast lower: ")
        first_upper = input("Enter the first forecast upper: ")
        print("First estimated ELEC generation: ", (first_lower+first_upper)/2)
    if(count == 1):
        second_lower = input("Enter the second forecast lower: ")
        second_upper = input("Enter the second forecast upper: ")
        print("Second estimated ELEC generation: ", (second_lower+second_upper)/2)
    if(count == 2):
        final = input("Enter the final hours of sunlight: ")
        total_elec -= final*6
        print("This is how much elec the solar plant will generate", total_elec*-1)
    else:
        temp = input("Enter any additional ELEC needed: ")
        final += temp
        print("This is how many NG you need to buy: ", total_elec*8)
    count+=1
