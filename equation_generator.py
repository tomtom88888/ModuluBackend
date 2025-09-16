import random

def generate_arithmetic(difficulty="easy"):
    if difficulty == "easy":
        num_count = random.randint(2, 3)
        num_range = list(range(1, 11))
        ops_allowed = ["+", "-"]
    elif difficulty == "medium":
        num_count = random.randint(3, 5)
        num_range = list(range(1, 51))
        ops_allowed = ["+", "-", "*", "/"]
    else:  # hard
        num_count = random.randint(4, 6)
        num_range = list(range(1, 101))
        ops_allowed = ["+", "-", "*", "/"]

    ops = [random.choice(ops_allowed) for _ in range(num_count - 1)]
    expr_parts = [str(random.choice(num_range))]

    for op in ops:
        if op == "*":
            next_num = random.choice(num_range[:max(1, len(num_range)//5)])
            expr_parts.append("*")
            expr_parts.append(str(next_num))

        elif op == "/":
            if difficulty in ["easy", "medium"]:
                divisor = random.randint(2, 10)
                k = random.randint(1, 10)
                numerator = divisor * k
                expr_parts[-1] = str(numerator)
                expr_parts.append("/")
                expr_parts.append(str(divisor))

            else:  # hard
                divisor = random.choice([2, 3])
                k = random.randint(1, 10)
                # choose whole, half, or third
                if divisor == 2:
                    numerator = 2 * k + random.choice([0, 1])  # whole or half
                else:
                    numerator = 3 * k + random.choice([0, 1, 2])  # whole, 1/3, or 2/3
                expr_parts[-1] = str(numerator)
                expr_parts.append("/")
                expr_parts.append(str(divisor))

        elif op == "+":
            expr_parts.append("+")
            expr_parts.append(str(random.choice(num_range)))

        elif op == "-":
            expr_parts.append("-")
            expr_parts.append(str(random.choice(num_range)))

    expr = "".join(expr_parts)
    try:
        answer = eval(expr)
    except ZeroDivisionError:
        return generate_arithmetic(difficulty)

    return expr, answer


# Demo
for level in ["easy", "medium", "hard"]:
    print("\n", level.upper())
    for _ in range(5):
        print(generate_arithmetic(level))
