import random


def generate_quadratic_algebra(difficulty):
    pass

def generate_algebra(difficulty):
    pass

def generate_long_division(difficulty):
    if difficulty == "easy":
        first_num_range = list(range(1, 100))
        second_num_range = first_num_range * list(range(10, 50))
    elif difficulty == "medium":
        first_num_range = list(range(1, 999))
        second_num_range = first_num_range * list(range(10, 100))
    elif difficulty == "hard":
        first_num_range = list(range(1, 999))
        second_num_range = first_num_range * list(range(10, 500))
    problem = str(first_num_range) + "/" + str(second_num_range)
    return problem, eval(problem)

def generate_long_multiplication(difficulty):
    if difficulty == "easy":
        first_num_range = list(range(1, 100))
        second_num_range = list(range(1, 100))
    elif difficulty == "medium":
        first_num_range = list(range(1, 999))
        second_num_range = list(range(1, 100))
    elif difficulty == "hard":
        first_num_range = list(range(1, 999))
        second_num_range = list(range(1, 999))
    problem = str(first_num_range) + "*" + str(second_num_range)
    return problem, eval(problem)
    
def generate_arithmetic(difficulty="easy"):
    if difficulty == "easy":
        num_count = random.randint(3, 4)
        norm_num_range = list(range(1, 11))
        mult_num_range = list(range(1, 4))
        ops_allowed = ["+", "-"]
        max_mult_in_a_row = 1
    elif difficulty == "medium":
        num_count = random.randint(4, 6)
        norm_num_range = list(range(1, 51))
        mult_num_range = list(range(1, 11))
        ops_allowed = ["+", "-", "*"]
        max_mult_in_a_row = 2
    else:
        num_count = random.randint(5, 7)
        norm_num_range = list(range(1, 101))
        mult_num_range = list(range(1, 21))
        ops_allowed = ["+", "-", "*", "/"]
        max_mult_in_a_row = 2

    while True:
        divison_in = False
        mult_in_a_row = 0
        ops = []

        for _ in range(num_count - 1):
            if divison_in:
                current_ops_allowed = ops_allowed.copy()
                if "/" in current_ops_allowed:
                    current_ops_allowed.remove("/")

                op = random.choice(current_ops_allowed)
                divison_in = False
                mult_in_a_row = 0 if op != "*" else 1
                ops.append(op)

            else:
                current_ops_allowed = ops_allowed.copy()

                if mult_in_a_row >= max_mult_in_a_row:
                    if "*" in current_ops_allowed:
                        current_ops_allowed.remove("*")

                op = random.choice(current_ops_allowed)

                if op == "*":
                    mult_in_a_row += 1
                else:
                    mult_in_a_row = 0

                if op == "/":
                    divison_in = True

                ops.append(op)

        expr_parts = []
        is_division = False
        is_mult = False
        divisor = 0

        for op in ops:
            if is_division:
                expr_parts.append(str(divisor))
                expr_parts.append(op)
                is_division = False
                continue

            if op == "/":
                is_division = True
                is_mult = False
                divisor = random.choice(mult_num_range)
                num = divisor * random.choice(mult_num_range)
                expr_parts.append(str(num))
                expr_parts.append(op)

            elif op == "*":
                is_mult = True
                num = random.choice(mult_num_range)
                expr_parts.append(str(num))
                expr_parts.append(op)

            elif op in ["+", "-"]:
                if is_mult:
                    num = random.choice(mult_num_range)
                else:
                    num = random.choice(norm_num_range)
                is_mult = False
                expr_parts.append(str(num))
                expr_parts.append(op)

        if is_mult:
            num = random.choice(mult_num_range)
            expr_parts.append(str(num))
        elif is_division:
            expr_parts.append(str(divisor))
        else:
            num = random.choice(norm_num_range)
            expr_parts.append(str(num))

        expr = "".join(expr_parts)
        answer = eval(expr)

        if answer < 0:
            continue

        return expr, answer
    

# for i in range(3):
#     print("Easy Question: ")
#     equation, answer = generate_arithmetic(difficulty="easy")
#     print(f"Equation: {equation}, Answer: {answer}")

# for i in range(3):
#     print("Medium Question: ")
#     equation, answer = generate_arithmetic(difficulty="medium")
#     print(f"Equation: {equation}, Answer: {answer}")
    
# for i in range(3):
#     print("Hard Question: ")
#     equation, answer = generate_arithmetic(difficulty="hard")
#     print(f"Equation: {equation}, Answer: {answer}")