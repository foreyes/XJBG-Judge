import flask, os, uuid, time, threading, pickle
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = flask.Flask(__name__)
auth = HTTPBasicAuth()
mutex = threading.Lock()
task_queue = []
result_set = {}
user_task_list = {}
best_score = {}

@auth.verify_password
def verify_password(username, password):
    return check_password_hash('pbkdf2:sha256:150000$90mwOZkt$34005826ad9fc2261188c69ad96b997601192d78c0fd6e2201086bde326abda3', username) and check_password_hash('pbkdf2:sha256:150000$BCUnBAOF$296875e81e0f40addb9acb96b89066b820d109042540800306ceeb90212efb29', password)

def save_data():
	pickle.dump(best_score, open("best_score.txt", "wb"))
	pickle.dump(user_task_list, open("user_task_list.txt", "wb"))
	pickle.dump(result_set, open("result_set.txt", "wb"))


def load_data():
	global best_score, user_task_list, result_set
	if os.path.exists("best_score.txt"):
		best_score = pickle.load(open("best_score.txt", "rb"))

	if os.path.exists("user_task_list.txt"):
		user_task_list = pickle.load(open("user_task_list.txt", "rb"))

	if os.path.exists("result_set.txt"):
		result_set = pickle.load(open("result_set.txt", "rb"))


@app.route("/add_task", methods= ["POST"])
@auth.login_required
def add_task():
	# check file exist
	file = flask.request.files["file"]
	if not file:
		return flask.redirect("/?no_file=1")
	# check username
	username = flask.request.form["username"]
	if not username:
		return flask.redirect("/?no_username=1")

	# get uuid and save file
	task_id = str(uuid.uuid1())
	file.save("pending_files/" + task_id)
	dataset = flask.request.form["dataset"]
	result_set[task_id] = {"dataset": dataset, "status": "Pending", "submit_time":time.ctime(), "cmptime":time.time(), "time": None, "detail":"", "task_id":task_id, "username" : username}

	# attach task to user
	if username not in user_task_list:
		user_task_list[username] = []
		best_score[username] = 1e9
	user_task_list[username].append(task_id)

	# add to queue
	with mutex:
		task_queue.append(task_id)

	return flask.redirect("/user/" + username)


@app.route("/", methods = ["GET"])
@auth.login_required
def submit():
	no_file = flask.request.args.get("no_file") == '1' or False
	no_username = flask.request.args.get("no_username") == '1' or False
	current_bst = []
	for i in best_score:
		current_bst.append((best_score[i],i))
	current_bst = sorted(current_bst)
	while len(current_bst)!=0 and current_bst[0][0] == None and current_bst[-1][0] != None:
		current_bst.append(current_bst[0])
		del current_bst[0]
	submissions = sorted([result_set[i] for i in result_set], key = lambda x: x["cmptime"])
	submissions.reverse()
	return flask.render_template("submit.html", no_file=no_file, no_username=no_username, ranklist = current_bst, submissions = submissions)


@app.route("/user/<username>", methods = ["GET"])
@auth.login_required
def user_history(username):
	if username not in user_task_list:
		tasks = []
	else:
		tasks = user_task_list[username]
		tasks = [result_set[task_id] for task_id in tasks]
		tasks.reverse()
	return flask.render_template("user_history.html", username=username, tasks=tasks)


def init():
	import os
	load_data()
	os.system("mkdir -p pending_files")


def judge(task_id):
	print("judging " + task_id)

	# generate judge script and run it.
	dataset = result_set[task_id]["dataset"]
	os.system("mv pending_files/{} /main.cpp".format(task_id))
	os.system("./judge.sh {}".format(dataset))

	with open("/compile_result.txt", "r") as f:
		result = f.read(1)
		if result:
			return (1e9,"Compile Error", open("/compile_result.txt", "r").read())

	with open("/time_result.txt", "r") as f:
		result = f.read()
		if not result:
			return (1e9,"Time Limit Exceeded", "")
		if "Segmentation fault" in result:
			return (1e9,"Run Time Error", "")

		detail = result
		time_used = float(result.split(" seconds time elapsed")[0].split(" ")[-1])

	with open("/output_check.txt", "rb") as f:
		result = f.read(1)
		if result:
			return (1e9,"No Output", detail)

	with open("/answer_result.txt", "rb") as f:
		result = f.read(1)
		if result:
			return (1e9,"Wrong Answer", detail)

	return (time_used, "Accepted", detail)


def judger():
	print("juder start")
	global task_queue
	while True:
		if len(task_queue) == 0:
			time.sleep(0.1)
			continue
		# get task info
		with mutex:
			task_id = task_queue[0]
			task_queue = task_queue[1:]

		# run task
		result_set[task_id]["status"] = "Running"
		result = judge(task_id)
		cu = result_set[task_id]["username"]
		best_score[cu] = min(result[0],best_score[cu])
		result_set[task_id]["time"] = result[0]
		result_set[task_id]["status"] = result[1]
		result_set[task_id]["detail"] = result[2]
		# TODO: avoid losing running task
		save_data()


if __name__ == "__main__":
	init()
	judger_thread = threading.Thread(target=judger)
	judger_thread.start()
	app.run(host='0.0.0.0', port=5001,debug = True)
