import csv
import random
import copy
from tabulate import tabulate
import re  # Importing the 're' module
import math  # Importing the 'math' module

# Data Structures
class Auditorium:
    def __init__(self, auditorium_id, capacity):
        self.id = auditorium_id
        self.capacity = int(capacity)

class Group:
    def __init__(self, group_number, student_amount, subgroups):
        self.number = group_number
        self.size = int(student_amount)
        self.subgroups = subgroups.strip('"').split(';') if subgroups else []

class Lecturer:
    def __init__(self, lecturer_id, name, subjects_can_teach, types_can_teach, max_hours_per_week):
        self.id = lecturer_id
        self.name = name
        # Updated parsing to handle commas and semicolons
        self.subjects_can_teach = [s.strip() for s in re.split(';|,', subjects_can_teach)] if subjects_can_teach else []
        self.types_can_teach = [t.strip() for t in re.split(';|,', types_can_teach)] if types_can_teach else []
        self.max_hours_per_week = int(max_hours_per_week)

class Subject:
    def __init__(self, subject_id, name, group_id, num_lectures, num_practicals, requires_subgroups, week_type):
        self.id = subject_id
        self.name = name
        self.group_id = group_id
        self.num_lectures = int(num_lectures)
        self.num_practicals = int(num_practicals)
        self.requires_subgroups = True if requires_subgroups.lower() == 'yes' else False
        self.week_type = week_type.lower()  # 'both', 'even', 'odd'

# Functions to read CSV files
def read_auditoriums(filename):
    auditoriums = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            auditoriums.append(Auditorium(row['auditoriumID'], row['capacity']))
    return auditoriums

def read_groups(filename):
    groups = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            groups.append(Group(row['groupNumber'], row['studentAmount'], row['subgroups']))
    return groups

def read_lecturers(filename):
    lecturers = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            lecturers.append(Lecturer(
                row['lecturerID'],
                row['lecturerName'],
                row['subjectsCanTeach'],
                row['typesCanTeach'],
                row['maxHoursPerWeek']
            ))
    return lecturers

def read_subjects(filename):
    subjects = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            subjects.append(Subject(
                row['id'],
                row['name'],
                row['groupID'],
                row['numLectures'],
                row['numPracticals'],
                row['requiresSubgroups'],
                row['weekType']
            ))
    return subjects

# Loading data
auditoriums = read_auditoriums('../IS_lab_4_basedOn3/auditoriums.csv')
groups = read_groups('groups.csv')
lecturers = read_lecturers('lecturers.csv')
subjects = read_subjects('subjects.csv')

# Checking that each subject has at least one lecturer
subject_ids = set(subject.id for subject in subjects)
lecturer_subjects = set()
for lecturer in lecturers:
    lecturer_subjects.update(lecturer.subjects_can_teach)

missing_subjects = subject_ids - lecturer_subjects
if missing_subjects:
    print(f"Warning: No lecturers available for the following subjects: {', '.join(missing_subjects)}")

# Defining time slots: 5 days, 4 periods per day
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = ['1', '2', '3', '4']  # Periods per day
TIME_SLOTS = [(day, period) for day in DAYS for period in PERIODS]

class Lesson:
    def __init__(self, subject, lesson_type, group, subgroup=None):
        self.subject = subject
        self.type = lesson_type  # 'Lecture' or 'Practice'
        self.group = group
        self.subgroup = subgroup  # For practicals if subgroups are required
        self.time_slot = None
        self.auditorium = None
        self.lecturer = None

class Schedule:
    def __init__(self):
        # Key: time_slot (day, period), Value: list of lessons at that time
        self.even_timetable = {time_slot: [] for time_slot in TIME_SLOTS}
        self.odd_timetable = {time_slot: [] for time_slot in TIME_SLOTS}
        self.fitness = None  # To be calculated

    def calculate_fitness(self):
        penalty = 0
        # Fitness for even week
        penalty += self._calculate_fitness_for_week(self.even_timetable)
        # Fitness for odd week
        penalty += self._calculate_fitness_for_week(self.odd_timetable)
        # Soft constraints for subjects
        penalty += self._calculate_soft_constraints()
        if penalty < 0:
            penalty = 0
        self.fitness = 1 / (1 + penalty)

    def _calculate_fitness_for_week(self, timetable):
        penalty = 0
        # Minimize gaps in the schedule for groups (soft constraint)
        for group in groups:
            subgroups = group.subgroups if group.subgroups else [None]
            for subgroup in subgroups:
                schedule_list = []
                for time_slot, lessons in timetable.items():
                    for lesson in lessons:
                        if lesson.group.number == group.number and lesson.subgroup == subgroup:
                            schedule_list.append(time_slot)
                schedule_sorted = sorted(schedule_list, key=lambda x: (DAYS.index(x[0]), int(x[1])))
                for i in range(len(schedule_sorted) - 1):
                    day1, period1 = schedule_sorted[i]
                    day2, period2 = schedule_sorted[i + 1]
                    if day1 == day2:
                        gaps = int(period2) - int(period1) - 1
                        if gaps > 0:
                            penalty += gaps
        # Minimize gaps in the schedule for lecturers (soft constraint)
        for lecturer in lecturers:
            schedule_list = []
            for time_slot, lessons in timetable.items():
                for lesson in lessons:
                    if lesson.lecturer and lesson.lecturer.id == lecturer.id:
                        schedule_list.append(time_slot)
            schedule_sorted = sorted(schedule_list, key=lambda x: (DAYS.index(x[0]), int(x[1])))
            for i in range(len(schedule_sorted) - 1):
                day1, period1 = schedule_sorted[i]
                day2, period2 = schedule_sorted[i + 1]
                if day1 == day2:
                    gaps = int(period2) - int(period1) - 1
                    if gaps > 0:
                        penalty += gaps
            # Balancing lecturer workload (soft constraint)
            hours_assigned = len(schedule_list)
            max_hours = lecturer.max_hours_per_week
            if hours_assigned > max_hours:
                penalty += (hours_assigned - max_hours) * 2  # Penalty for exceeding
        return penalty

    def _calculate_soft_constraints(self):
        penalty = 0
        # Adding penalties for not meeting or exceeding the required number of hours per subject (soft constraint)
        for subject in subjects:
            group = next((g for g in groups if g.number == subject.group_id), None)
            if not group:
                continue
            subgroups = group.subgroups if subject.requires_subgroups else [None]
            scheduled_lectures = 0
            scheduled_practicals = {s: 0 for s in subgroups}
            required_lectures = subject.num_lectures
            required_practicals = subject.num_practicals
            for subgroup in subgroups:
                for timetable in [self.even_timetable, self.odd_timetable]:
                    for time_slot, lessons in timetable.items():
                        for lesson in lessons:
                            if lesson.type == 'Лекція' and lesson.subject.id == subject.id \
                                    and lesson.group.number == group.number:
                                scheduled_lectures += 1
                            elif lesson.type == 'Практика' and lesson.subject.id == subject.id \
                                    and lesson.group.number == group.number and lesson.subgroup == subgroup:
                                scheduled_practicals[subgroup] += 1

            # Calculating the difference between scheduled and required hours
            diff_lectures = scheduled_lectures - required_lectures
            diff_practicals = [abs(practical - required_practicals) for _, practical in scheduled_practicals.items()]
            penalty += abs(diff_lectures) * 2
            penalty += sum(diff_practicals) * 2
        return penalty


def get_possible_lecturers(lesson):
    # Matching lecturers by subject.id and lesson type (hard constraint)
    possible = [lecturer for lecturer in lecturers if
                lesson.subject.id in lecturer.subjects_can_teach and
                lesson.type in lecturer.types_can_teach]
    if not possible:
        print(f"No lecturer available for {lesson.subject.name} ({lesson.type}) with subject ID {lesson.subject.id}.")
    return possible

def is_conflict(lesson, time_slot, timetable):
    for existing_lesson in timetable[time_slot]:
        # Check for lecturer conflict (hard constraint)
        if lesson.lecturer and existing_lesson.lecturer and existing_lesson.lecturer.id == lesson.lecturer.id:
            return True
        # Check for auditorium conflict (hard constraint)
        if lesson.auditorium and existing_lesson.auditorium and existing_lesson.auditorium.id == lesson.auditorium.id:
            return True
        # Check for group and subgroup conflict (hard constraint)
        if lesson.group.number == existing_lesson.group.number:
            if lesson.subgroup == existing_lesson.subgroup:
                return True
            # If one of the lessons is without subgroups, it conflicts with all subgroups
            if not lesson.subgroup or not existing_lesson.subgroup:
                return True
    return False

# Genetic algorithm settings
POPULATION_SIZE = 50
GENERATIONS = 100

def create_initial_population():
    population = []
    for _ in range(POPULATION_SIZE):
        schedule = Schedule()
        lessons_to_schedule = []
        for subject in subjects:
            group = next((g for g in groups if g.number == subject.group_id), None)
            if not group:
                continue
            # Lectures
            for _ in range(subject.num_lectures):
                lessons_to_schedule.append(Lesson(subject, 'Лекція', group))
            # Practicals
            if subject.requires_subgroups and group.subgroups:
                num_practicals_per_subgroup = math.ceil(subject.num_practicals / len(group.subgroups))
                for subgroup in group.subgroups:
                    for _ in range(num_practicals_per_subgroup):
                        lessons_to_schedule.append(Lesson(subject, 'Практика', group, subgroup))
            else:
                for _ in range(subject.num_practicals):
                    lessons_to_schedule.append(Lesson(subject, 'Практика', group))
        # Randomize the order of lessons
        random.shuffle(lessons_to_schedule)
        # Assign lessons
        for lesson in lessons_to_schedule:
            possible_lecturers = get_possible_lecturers(lesson)
            if not possible_lecturers:
                continue
            lesson.lecturer = random.choice(possible_lecturers)
            if lesson.subgroup:
                students = lesson.group.size // len(lesson.group.subgroups)
            else:
                students = lesson.group.size
            suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= students]
            if not suitable_auditoriums:
                continue
            lesson.auditorium = random.choice(suitable_auditoriums)
            assigned = assign_randomly(lesson, schedule)
            if not assigned:
                # If assignment failed, add penalty
                schedule.fitness = 0
        schedule.calculate_fitness()
        population.append(schedule)
    return population

def assign_randomly(lesson, schedule):
    timetables = [schedule.even_timetable, schedule.odd_timetable]
    assigned = False
    for timetable in timetables:
        available_time_slots = TIME_SLOTS.copy()
        random.shuffle(available_time_slots)
        for time_slot in available_time_slots:
            if not is_conflict(lesson, time_slot, timetable):
                lesson.time_slot = time_slot
                timetable[time_slot].append(copy.deepcopy(lesson))
                assigned = True
                break
        if assigned:
            break
    return assigned

def selection(population):
    # Select the best schedules based on fitness (elitism)
    population.sort(key=lambda x: x.fitness, reverse=True)
    selected = population[:int(0.2 * len(population))]  # Select top 20%
    return selected

def crossover(parent1, parent2):
    child = Schedule()
    for time_slot in TIME_SLOTS:
        # Decide whether to copy lessons from parent1 or parent2
        if random.random() < 0.5:
            source_lessons_even = parent1.even_timetable[time_slot]
            source_lessons_odd = parent1.odd_timetable[time_slot]
        else:
            source_lessons_even = parent2.even_timetable[time_slot]
            source_lessons_odd = parent2.odd_timetable[time_slot]
        # Copy lessons for even week
        for lesson in source_lessons_even:
            if not is_conflict(lesson, time_slot, child.even_timetable):
                child.even_timetable[time_slot].append(copy.deepcopy(lesson))
        # Copy lessons for odd week
        for lesson in source_lessons_odd:
            if not is_conflict(lesson, time_slot, child.odd_timetable):
                child.odd_timetable[time_slot].append(copy.deepcopy(lesson))
    # Calculate fitness after crossover
    child.calculate_fitness()
    return child

def mutate(schedule):
    # Randomly change some lessons in the schedule
    mutation_rate = 0.1  # 10% chance of mutation
    for week in ['even', 'odd']:
        timetable = schedule.even_timetable if week == 'even' else schedule.odd_timetable
        opposite_timetable = schedule.odd_timetable if week == 'even' else schedule.even_timetable
        # Chance to transfer lessons between weeks
        if random.random() < mutation_rate:
            transfer_lesson_between_weeks(timetable, opposite_timetable)
        # Chance to add a new lesson
        if random.random() < mutation_rate:
            add_random_lesson(timetable)
        # Chance to remove an existing lesson
        if random.random() < mutation_rate:
            remove_random_lesson(timetable)
        for time_slot in TIME_SLOTS:
            if timetable[time_slot]:
                for lesson in timetable[time_slot][:]:
                    if random.random() < mutation_rate:
                        original_time_slot = lesson.time_slot
                        new_time_slot = random.choice(TIME_SLOTS)
                        if new_time_slot == original_time_slot:
                            continue
                        if not is_conflict(lesson, new_time_slot, timetable):
                            timetable[original_time_slot].remove(lesson)
                            lesson.time_slot = new_time_slot
                            timetable[new_time_slot].append(lesson)
    # Calculate fitness after mutation
    schedule.calculate_fitness()

def transfer_lesson_between_weeks(from_timetable, to_timetable):
    # Choose a random time slot and lesson
    time_slots_with_lessons = [ts for ts in from_timetable if from_timetable[ts]]
    if not time_slots_with_lessons:
        return
    time_slot = random.choice(time_slots_with_lessons)
    lessons_to_transfer = from_timetable[time_slot][:]
    # Check if lessons can be transferred without conflicts
    can_transfer = True
    for lesson in lessons_to_transfer:
        if is_conflict(lesson, time_slot, to_timetable):
            can_transfer = False
            break
    if can_transfer:
        # Transfer lessons
        from_timetable[time_slot] = []
        to_timetable[time_slot].extend(lessons_to_transfer)

def add_random_lesson(timetable):
    # Choose a random subject
    subject = random.choice(subjects)
    group = next((g for g in groups if g.number == subject.group_id), None)
    if not group:
        return
    # Choose a random lesson type
    lesson_type = random.choice(['Лекція', 'Практика'])
    lessons_to_add = []
    if lesson_type == 'Практика' and subject.requires_subgroups and group.subgroups:
        for subgroup in group.subgroups:
            lesson = Lesson(subject, lesson_type, group, subgroup)
            lessons_to_add.append(lesson)
    else:
        lesson = Lesson(subject, lesson_type, group)
        lessons_to_add.append(lesson)
    # Assign lecturer and auditorium
    for lesson in lessons_to_add:
        possible_lecturers = get_possible_lecturers(lesson)
        if not possible_lecturers:
            return
        lecturer = random.choice(possible_lecturers)
        lesson.lecturer = lecturer
        if lesson.subgroup:
            students = group.size // len(group.subgroups)
            suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= students]
        else:
            students = group.size
            suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= students]
        if not suitable_auditoriums:
            return
        auditorium = random.choice(suitable_auditoriums)
        lesson.auditorium = auditorium
    # Assign time slot
    available_time_slots = TIME_SLOTS.copy()
    random.shuffle(available_time_slots)
    for time_slot in available_time_slots:
        conflict = False
        for lesson in lessons_to_add:
            if is_conflict(lesson, time_slot, timetable):
                conflict = True
                break
        if not conflict:
            for lesson in lessons_to_add:
                lesson.time_slot = time_slot
                timetable[time_slot].append(copy.deepcopy(lesson))
            break

def remove_random_lesson(timetable):
    # Choose a random lesson to remove
    all_lessons = [lesson for lessons in timetable.values() for lesson in lessons]
    if not all_lessons:
        return
    lesson_to_remove = random.choice(all_lessons)
    # If it's a lesson with subgroups, remove all related lessons
    lessons_to_remove = []
    if lesson_to_remove.subgroup:
        for lessons in timetable.values():
            for lesson in lessons:
                if (lesson.subject.id == lesson_to_remove.subject.id and
                    lesson.group.number == lesson_to_remove.group.number and
                    lesson.type == lesson_to_remove.type and
                    lesson.subgroup == lesson_to_remove.subgroup):
                    lessons_to_remove.append(lesson)
    else:
        lessons_to_remove.append(lesson_to_remove)
    for lesson in lessons_to_remove:
        timetable[lesson.time_slot].remove(lesson)

def genetic_algorithm():
    population = create_initial_population()
    for generation in range(GENERATIONS):
        selected = selection(population)
        new_population = []
        # Elitism: retain top 10% individuals without changes
        elite_size = max(1, int(0.1 * POPULATION_SIZE))
        elites = selected[:elite_size]
        new_population.extend(copy.deepcopy(elites))
        # Random crossover and mutation for the rest
        while len(new_population) < POPULATION_SIZE:
            parent1, parent2 = random.sample(selected, 2)
            child = crossover(parent1, parent2)
            mutate(child)
            new_population.append(child)
        population = new_population
        best_fitness = max(schedule.fitness for schedule in population)
        if (generation + 1) % 10 == 0 or best_fitness == 1.0:
            print(f'Generation {generation + 1}: Best Fitness = {best_fitness}\n')
        if best_fitness == 1.0:
            print(f'Optimal schedule found at generation {generation + 1}.')
            break
    best_schedule = max(population, key=lambda x: x.fitness)
    return best_schedule

def print_schedule(schedule):
    even_week_table = []
    odd_week_table = []
    headers = [
        'Timeslot',
        'Group(s)',
        'Subject',
        'Type',
        'Lecturer',
        'Auditorium',
        'Students',
        'Capacity'
    ]

    def create_row(time_slot, lesson):
        timeslot_str = f"{time_slot[0]}, period {time_slot[1]}"
        group_str = lesson.group.number
        if lesson.subgroup:
            group_str += f" (Subgroup {lesson.subgroup})"
        subject_str = lesson.subject.name
        type_str = lesson.type
        lecturer_str = lesson.lecturer.name if lesson.lecturer else "N/A"
        auditorium_str = lesson.auditorium.id if lesson.auditorium else "N/A"
        if lesson.subgroup and lesson.group.subgroups:
            students = lesson.group.size // len(lesson.group.subgroups)
        else:
            students = lesson.group.size
        students_str = str(students)
        capacity_str = str(lesson.auditorium.capacity) if lesson.auditorium else "N/A"
        row = [
            timeslot_str,
            group_str,
            subject_str,
            type_str,
            lecturer_str,
            auditorium_str,
            students_str,
            capacity_str
        ]
        return row

    for time_slot in TIME_SLOTS:
        lessons_even = schedule.even_timetable[time_slot]
        for lesson in lessons_even:
            row = create_row(time_slot, lesson)
            even_week_table.append(row)
        lessons_odd = schedule.odd_timetable[time_slot]
        for lesson in lessons_odd:
            row = create_row(time_slot, lesson)
            odd_week_table.append(row)

    print("\nBest schedule - EVEN week:\n")
    if even_week_table:
        print(tabulate(even_week_table, headers=headers, tablefmt="grid", stralign="center"))
    else:
        print("No lessons scheduled for EVEN week.\n")

    print("\nBest schedule - ODD week:\n")
    if odd_week_table:
        print(tabulate(odd_week_table, headers=headers, tablefmt="grid", stralign="center"))
    else:
        print("No lessons scheduled for ODD week.\n")

if __name__ == "__main__":
    # Run the genetic algorithm and get the best schedule
    best_schedule = genetic_algorithm()
    # Print the final schedule to the console
    print_schedule(best_schedule)
