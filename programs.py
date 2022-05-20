from yaml import load, FullLoader


# Contains all of the programs.
# Example: program_text[1][3][4] is the text for program 1, week 3, task 4.
program_text = {}

with open("program_text.yml") as f:
    data = load(f, Loader=FullLoader)["programs"]
    for program in data:
        program_text[int(program[1:])] = {}
        for week in data[program]:
            program_text[int(program[1:])][int(week[1:])] = {}
            for i in range(len(data[program][week])):
                program_text[int(program[1:])][int(week[1:])][i + 1] = data[program][week][i]
    f.close()
