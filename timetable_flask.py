#Here, assets that will be used are mentioned and imported

from flask import Flask, render_template, url_for, redirect, request
from cs50 import SQL
import random
import math

#This is how the site and database are set up.
app = Flask(__name__)
db = SQL("sqlite:///database.db")

#global arrays
school_days = []
periods = 0
period_list = []
grades = 0
iterations = 1000
subjects = [0] #provides the list of subjects. '0' symbolises a 'free' period
ranked_subject_arrays = [] #this array will store our rankings
block_content = [] #this array stores which subjects are in which block

#functions, subroutines

#change to test git
def mult(x,y):
    return x*y
# reset the school table in the database
def table_reset(group_count):
    db.execute("drop table if exists school;")
    db.execute("create table school('subject_name' varchar(225), 'id' int, 'block' int);")
    db.execute("insert into school(id, subject_name, block) values(0, 'buffer', ?);", group_count)

    for i in range(0, group_count):
        block_column_name = "block_" + str(i + 1)
        db.execute("alter table school add ? int", block_column_name)

# for an array of strings, it separates words into an array
def string_array_converter(word_list, reset_check):
    #temporary array and storage for letters
    array = []
    temp_word = ""
    for i in range(0, len(word_list)):
        temp_letter = str(word_list[i])
        if temp_letter == ",":
            #capitalises the first letter of each subject name
            temp_word = temp_word.capitalize()
            #where there is a new word, it appends the array
            array.append(temp_word)
            temp_letter = ""
            temp_word = ""
        elif temp_letter != " ":
            #ignores spaces
            temp_word = temp_word + temp_letter

    #adds the last word, if the user doesn't want a reset.
    if reset_check != "reset":
        temp_word = temp_word.capitalize()
        array.append(temp_word)
    return array

# returns which subject groups clash
def clash_setup(array):

    array_2 = []

    for i in range(0, len(array)):
        new_arr = True
        checker = []
        for j in range(0, len(array[i])):
            
            exists = -1
            for k in range(0, len(array_2)):
                for l in range(0, len(array_2[k])):
                    if array_2[k][l] == array[i][j]:
                        new_arr = False
                        checker.append(array_2[k][l])
                        exists = k

        if new_arr == True:
            array_2.append([])

        value = []
        for j in range(0, len(array[i])):
            approved = True
            for x in range(0, len(checker)):
                if array[i][j] == checker[x]:
                    approved = False
            if approved == True:
                value.append(array[i][j])
        
        for j in range(0, len(value)):
            array_2[exists].append(value[j])

    return(array_2)

# sets up separate entities for each day, and it's error-logging counterpart
def day_setup(day, grades, periods):
    temp_error = day + "_error"
    db.execute("drop table if exists ?;", day)
    db.execute("drop table if exists ?;", temp_error)
    db.execute("create table ?('period' int);", day)
    db.execute("create table ?('period' int);", temp_error)
    for i in range(0, grades):
        temp_name = "grade_" + str(i)
        db.execute("alter table ? add ? int", day, temp_name)
    db.execute("alter table ? add 'clash' int", temp_error)
    db.execute("alter table ? add 'overlap' int", temp_error)

# checking the amount of subjects that should be included
def subject_fitness(array_content):
    #In this fitness function: 
    # x should be the master array
    # It will check the relationship between the average desired number of subjects and the actual number of subjects per week.
    total = 0
    for grade in range(0, grades):
        x = []
        for i in range(0, len(subjects)):
            x.append(0)
            for day in range(0, len(school_days)):
                x[i] += array_content[grade][day][i]
        
        for i in range(0, len(subjects)):
            total = total + abs(x[i] - subject_set[i])
                
    
    return total

# setting up the condition for one of the fitness functions        
def condition_construct(grades):
    #clash condition construction creation carnival
    if grades >= 2:
        condition = "where (grade_0 = grade_1 and not (grade_0 = -1 or grade_1 = -1))"

        #here, the condition is altered to increase in length according to the number of grades present
        for i in range(0, (grades - 2)):
            for j in range(i, (grades - 1)):
                temp_grade1 = str("grade_" + str(j))
                temp_grade2 = str("grade_" + str((grades - (i + 1))))
                condition = str(condition + " or (" + temp_grade1 + " = " + temp_grade2 + " and not (" + temp_grade1 + " = -1 or " + temp_grade2 + " = -1))")

    else:
        condition = "where (0 = 1)"
    return condition

# creates an error database for locating the location of errors
def construct_errors(array_content, d, grades, condition):

    error_db = str(d + "_error")

    db.execute("update ? set 'clash' = 0;", error_db)
    db.execute("update ? set 'overlap' = 0;", error_db)
    
    xcondition = str("select period from " + d + " " + condition + ";")
    
    # Locating clashes between subjects
    x = db.execute(xcondition)
    for i in range(0, len(x)):
        db.execute("update ? set 'clash' = 1 where period = ?;", error_db, str(x[i]["period"]))

    # Locating overlaps over recesses
    for i in range(0, grades):
        for j in range(0, (len(array_content[i]) - 1)):
            for k in range(0, len(period_list) - 1):
                if ((array_content[i][j] != 0) and (j == (period_list[k] - 1))):
                    if array_content[i][j] == array_content[i][j+1]:
                        db.execute("update ? set 'overlap' = 1 where period = ?;", error_db, str((j + 1)))
                        db.execute("update ? set 'overlap' = 1 where period = ?;", error_db, str((j + 2)))

# fitness function, validates the actual timetable
def construct_fitness(array_content, array_length, d, grades, condition):

    error_db = str(d + "_error")
    
    #In this fitness function:
    # x refers to the clashes between grades
    # y refers to the overlaps across break times
    # z refers to the amount of extra or missing periods

    x = len(db.execute("select period from ? where 'clash' = 1;", error_db))
    y = len(db.execute("select period from ? where 'overlap' = 1;", error_db))
    z = 0

    for i in range(0, grades):
        z += abs(len(array_content[i]) - array_length)

    fit = 5*x + 1*y + 1*z


    return [fit]
            
    #The fitness function should check the following:
    
    #- Clashes. Grade 2 cannot have subject A if Grade 1 is also having subject A at the same time.
    #- Overlaps. A double session should not extend through 'breaks' or 'lunch' times.
    #- Missing/extra. Sometimes, the program might lead to some days having more or less subjects than expected.

# helps to log error locations into temporary arrays later in the program
def error_log(main_array, error_array, limit):
    for i in range(0, len(error_array)):
        temp = error_array[i]["period"] - 1
        if (temp < limit):
            main_array[temp] = 1

    return main_array



#==============================================================================================================
# Here, the actual website is constructed. Python will be the backend.
#==============================================================================================================

@app.route("/")
def index():
    return redirect(url_for("home"))

@app.route("/home")
def home():
    #initialisation, resetting the table when the program is run
    table_reset(0)
    return render_template("index.html")

#Users use this HTML page to change how many subject groups there are
@app.route("/subjects/groups", methods = ["GET", "POST"])
def add_groups():
    return render_template("add_groups.html", message = "")

#Users determine which subjects exist
@app.route("/subjects/select", methods = ["GET", "POST"])
def add_subjects():
    #Checks if a response has been provided
    if request.method == "POST":
        #Variable used to determine whether more subjects should be added, or to proceed to the next step.
        check = str(request.form.get("submission"))

        #algorithm to add subjects to database.
        if check != "next":
            #gets the number of subject groups from the previous html. Sets it in a database
            html_groups = request.form.get("groups")

            #checks if the user actually entered a number
            if str(html_groups) == "":
                return render_template("add_groups.html", message = "Please enter the number of subject groups.")
            elif str(html_groups) != "None":
                groups = int(html_groups)
                table_reset(groups)

            groups = int(db.execute("select block from school where id = 0;")[0]["block"])
            #obtains the subject list from the html
            subject_list = str(request.form.get("subject_list"))
            counter = int(db.execute("select max(id) as maximum from school")[0]["maximum"])

            if check == "reset":
                table_reset(groups)
                counter = 0

            if subject_list != "None":
                array = string_array_converter(subject_list, check)

                #counter
                for i in range(0, len(array)):
                    existing = db.execute("select subject_name from school where id > 0")

                    if array[i] != "":
                        #Here, it checks if the subject name already exists in the database. If it does, it doesnt add it.
                        new = True
                        for j in range(0, len(existing)):
                            if array[i] == existing[j]["subject_name"]:
                                new = False

                        if new == True:
                            counter = counter + 1  
                            db.execute("insert into school(id, subject_name) values(?, ?)", counter, array[i])

            #selects all distinct subjects
            subject_list = db.execute("select distinct subject_name from school where id >= 1")

            unique_ids = []
            for i in range(0, len(subject_list)):
                temp_id = db.execute("select id from school where subject_name = ?", subject_list[i]["subject_name"])
                unique_ids.append(temp_id[0]["id"])
                for j in range(0, groups):
                                db.execute("update school set ? = 0 where id = ?", "block_" + str(j + 1), i + 1)

            return render_template("add_subjects.html", x = subject_list, groups = groups)

        #Runs the next step, which is to select which groups each subject belongs to
        elif check == "next":
            groups = int(db.execute("select block from school where id = 0;")[0]["block"])
            subject_list = db.execute("select distinct subject_name from school where id >= 1")
            return render_template("group_selection.html", groups = groups, subjects = subject_list, subject_groups = "None")

    else:
        return ("error")

@app.route("/subjects/select/groups", methods = ["GET", "POST"])
def select_subject_groups():

    global block_content
    #Checks if a previous form has been submitted
    if request.method == "POST":
        #Variable to check for which function to execute.
        check = str(request.form.get("submission"))

        groups = int(db.execute("select block from school where id = 0;")[0]["block"])
        subject_list = db.execute("select distinct subject_name from school where id >= 1")
        subject_groups = subject_list

        #Assigning subjects to their blocks
        if check == "confirm":
            db.execute("drop table if exists clash;")
            db.execute("create table clash('clash_id' int, 'block' int);")
            db.execute("insert into clash('clash_id', 'block') values(-1, -1)")
            
            clash_array = []

            for i in range(0, len(subject_list)):
                clash_array.append([])
                for j in range(0, groups):
                    temp_id = str(j + 1) + "." + str(i + 1)

                    #This is the id of the field for each subject group
                    temp_database_id = "block_" + str(j + 1)

                    #This locates which subjects have been checked off by the user
                    html_subject_id = str(request.form.get(temp_id))

                    if html_subject_id != "None":
                        db.execute("update school set ? = 1 where id = ?", temp_database_id, i + 1)
                        clash_array[i].append(j)
                    
                    temp = db.execute("select * from school where id = ?", i + 1)
                    if temp[0][temp_database_id] == 1:
                        subject_groups[i][j] = 1

            clash_array = clash_setup(clash_array)

            for i in range(0, len(clash_array)):
                for j in range(0, len(clash_array[i])):
                    db.execute("insert into clash('clash_id', 'block') values(?, ?)", i, clash_array[i][j])

            block_content = []
            temp_limit = int(db.execute("select block from school where id = 0")[0]["block"])
            for i in range(0, temp_limit):
                block = ("block_" + str(i + 1))
                temp_block_content = db.execute("select subject_name from school where " + block + " = 1;")
                block_content.append([])
                for j in range(0, len(temp_block_content)):
                    block_content[i].append(temp_block_content[j]["subject_name"])

            

            return render_template("group_selection.html", groups = groups, subjects = subject_list, subject_groups = subject_groups)
        
        #removing subjects from their groups
        elif check == "delete":
            for i in range(0, len(subject_list)):
                for j in range(0, groups):
                    temp_id = str(j + 1) + "." + str(i + 1)

                    #This is the id of the field for each subject group
                    temp_database_id = "block_" + str(j + 1)

                    #Resetting the entire table
                    db.execute("update school set ? = 0 where id = ?", temp_database_id, i + 1)
                    subject_groups[i][j] = 0
            block_content = []

            return render_template("group_selection.html", groups = groups, subjects = subject_list, subject_groups = subject_groups)

        elif check == "next":
            
            return render_template("general_information.html", missing = False)

    else:
        return url_for("index")

@app.route("/subjects/general", methods = ["GET", "POST"])
def general_information():
    if request.method == "POST":
        global school_days, periods, grades
        school_days = []
        week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for i in range(0, 7):
            temp = str(request.form.get(week[i]))
            if temp != "None":
                school_days.append(week[i])
        
        if len(school_days) > 0:

            periods = int(request.form.get("html_periods"))
            grades = int(request.form.get("html_grades"))
            return render_template("recess.html", periods = periods)
        else:
            return render_template("general_information.html", missing = True)
    else:
        return redirect(url_for("index"))

@app.route("/subjects/recess", methods = ["GET", "POST"])
def recess_selection():
    if request.method == "POST":

        #from the 'recess.html' file, we extract the data about recess periods and append them to a global array.
        # all variables that will be used in the mutation subroutine later is globalised.
        global clash_condition, ranked_subject_arrays, period_list, subjects, subject_set

        groups = int(db.execute("select block from school where id = 0;")[0]["block"])
        period_list = []

        for i in range(1, periods):
            if str(request.form.get(str(i))) != "None":
                period_list.append(i)
        period_list.append(periods)

        #adding the groups onto the array...
        for i in range(0, groups):
            subjects.append((i + 1))


        # Number of subjects for each year group should be even. subject A should have the same quantity as subject B per week.
        # minimise free periods. Free periods may stay as single subjects. Can be placed anywhere.

        #this variable defines that there should be this many of each subject per week for a given grade.
        subject_count = math.floor((len(school_days) * periods) / (len(subjects) - 1))

        # the condition for the clashes between subjects is declared here
        
        clash_condition = condition_construct(grades)

        #this function here assigns how many repetitions of each subject will be present.
        #the number of 'free' periods is determined by the subject_count variable.
        subject_set = [(len(school_days) * periods) - (subject_count * (len(subjects) - 1))]
        for _ in range(0, len(subjects) - 1):
            subject_set.append(subject_count)

        #it'll some iterations here
        for iteration in range(iterations):
        #determine how many of each subject will be present for each school day.
        #initialise 3d array to store how many of each subject will be there per day, per grade.
        #also apply free subjects to this array on initialisation.
            master_subject_array = []

            for i in range(0, grades):
                temp_subject_array = []
                for _ in range(0, len(school_days)):
                    temp_subject_array.append([0, 0, 0, 0, 0, 0, 0])
                #This randomly chooses which days get the free periods.
                for _ in range(0, subject_set[0]):
                    temp_subject_array[random.randint(0, len(school_days) - 1)][0] += 1
                master_subject_array.append(temp_subject_array)


            #adding subjects (double or single) to the end of each day, fitting parameters
            subject_sample = random.sample(range(1, len(subjects)), len(subjects) - 1)
            temp_set = subject_set

            for grade in range(0, grades):
                for day in range(0, len(school_days)):
                    temp_periods = 7 - master_subject_array[grade][day][0]
                    index = 0
                        #This condition-controlled iteration determines which subjects get double blocks per day.
                    for index in range(0, len(subjects) - 1):
                        if temp_periods > 0:
                            if temp_periods > 1:
                                d_or_s = random.randint(1, 2)
                                if d_or_s == 2:
                                    temp_periods = temp_periods - 1
                            master_subject_array[grade][day][subject_sample[index]] = d_or_s
                            temp_periods = temp_periods - 1
            
            ranked_subject_arrays.append((subject_fitness(master_subject_array), master_subject_array))
            ranked_subject_arrays.sort()
        
        return redirect(url_for("timetable_construct"))
    else:
        return redirect(url_for("index"))

@app.route("/construct/process", methods = ["GET", "POST"])
def timetable_construct():
    if request.method == "POST":

        global ranked_subject_arrays, block_content

        healthiest = ranked_subject_arrays[0][0]
        best_set = ranked_subject_arrays[0][1]
        collection = ranked_subject_arrays[:100]
        timetable = [9999999, [], [], [], []]
    
        # Once we have our first healthy batch, we want to mutate it many times
        # We can actually let the user decide how many times to mutate the array

        ranked_subject_arrays = []
        ranked_subject_arrays.append((healthiest, best_set))
        #here, the program randomises a selection of possible subject combinations, and is compared using a fitness subroutine
        for iteration in range(iterations):
            master_subject_array = []

            current_set = random.choice(collection)
            current_set = current_set[1]

            for grade in range(0, len(current_set)):
                master_subject_array.append([])
                for days in range(0, len(current_set[grade])):
                    master_subject_array[grade].append([])
                    master_subject_array[grade][days].append(current_set[grade][days][0])
                    for i in range(1, len(current_set[grade][days])):
                        if current_set[grade][days][i] > 0:
                            choice = random.randint(1, 2)
                            master_subject_array[grade][days].append(choice)
                        else:
                            master_subject_array[grade][days].append(0)
            
            ranked_subject_arrays.append((subject_fitness(master_subject_array), master_subject_array))
            ranked_subject_arrays.sort()

        if ranked_subject_arrays[0][0] < healthiest:
            healthiest = ranked_subject_arrays[0][0]
            best_set = ranked_subject_arrays[0][1]
            collection = ranked_subject_arrays[:100]

        for index in range(iterations // 100):
            
            total_issues = 0
            healthiest_set = []
            temp_array = ranked_subject_arrays[index][1]
            clashes = []
            overlaps = []
            #logs clashes and overlaps
            for i in range(0, len(school_days)):
                clashes.append([])
                overlaps.append([])
                for _ in range(0, periods):
                    clashes[i].append(0)
                    overlaps[i].append(0)
                
            for day in range(0, len(school_days)):
                healthiest_set.append([])
                lowest_issues = [99999, []]
                temp_db = str(school_days[day])
                
                for iteration in range(iterations // 100):
                    
                    day_setup(school_days[day], grades, periods)
                    g = []
                    for grade in range(0, grades):
                        g.append([])
                        subject_set = random.sample(subjects, len(subjects))
                        x = 1 #too many period variable names, using this as a substitute.
                        
                        for j in range(0, len(subjects)):
                            
                            current_subject = temp_array[grade][day][subject_set[j]]
                            
                            while current_subject > 0:
                                g[grade].append(subject_set[j])
                                
                                temp = int(db.execute("select clash_id from clash where block = ?;", (g[grade][-1] - 1))[0]["clash_id"])

                                if len(db.execute("select * from ? where exists(select period from ? where period = ?);", temp_db, temp_db, str(x))) == 0:
                                    db.execute("insert into ?('period') values(?);", temp_db, str(x))
                                    db.execute("insert into ?('period') values(?);", temp_db + "_error", str(x))
                                db.execute("update ? set ? = ? where period = ?;", temp_db, str("grade_" + str(grade)), str(temp), str(x))
                                x += 1
                                current_subject -= 1

                    construct_errors(g, school_days[day], grades, clash_condition)
                    temp_issues = construct_fitness(g, periods, school_days[day], grades, clash_condition)
                    if temp_issues[0] < lowest_issues[0]:
                        #assigning new values for clashes and overlaps
                        temp_clash = db.execute("select period from ? where clash = 1;", str(school_days[day] + "_error"))
                        temp_overlap = db.execute("select period from ? where overlap = 1;", str(school_days[day] + "_error"))
                        clashes[day] = (error_log(clashes[day], temp_clash, periods))
                        overlaps[day] = (error_log(overlaps[day], temp_overlap, periods))
                        healthiest_set[day] = (g)
                        lowest_issues = temp_issues


                total_issues += lowest_issues[0]
            total_issues += ranked_subject_arrays[index][0]
            if total_issues < timetable[0]:
                timetable[0] = total_issues
                timetable[1] = healthiest_set
                timetable[2] = ranked_subject_arrays[index]
                timetable[3] = clashes
                timetable[4] = overlaps
        
        return render_template("timetable_builder.html", periods = period_list, grades = timetable[1], days = school_days, errors = [timetable[3], timetable[4]], block_content = block_content)

    else:
        timetable = [9999999, [], [], [], []]
        return render_template("timetable_builder.html", periods = period_list, grades = timetable[1], days = school_days, errors = [], block_content = [])
