import flask, os, uuid, time, threading

TIME_LIMIT = 120

app = flask.Flask(__name__)
mutex = threading.Lock()
task_queue = []
result_set = {}
user_task_list = {}


@app.route("/add_task", methods= ["POST"])
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
	result_set[task_id] = {"status": "pending", "time": None,"detail":"","task_id":task_id}

	# attach task to user
	if username not in user_task_list:
		user_task_list[username] = []
	user_task_list[username].append(task_id)

	# add to queue
	with mutex:
		task_queue.append(task_id)

	return flask.redirect("/user/" + username)


@app.route("/", methods = ["GET"])
def submit():
	no_file = flask.request.args.get("no_file") == '1' or False
	no_username = flask.request.args.get("no_username") == '1' or False
	return flask.render_template("submit.html", no_file=no_file, no_username=no_username)

@app.route("/user/<username>", methods = ["GET"])
def user_history(username):
	tasks = user_task_list[username]
	tasks = [result_set[task_id] for task_id in tasks]
	tasks.reverse()
	return flask.render_template("user_history.html", username=username, tasks=tasks)


# TODO
def init():
	import os
	os.system("mkdir -p pending_files")


def judge(task_id):
	print("judging " + task_id)
	os.system("mv pending_files/{} /main.cpp".format(task_id))
	os.system("./judge.sh")

	with open("/compile_result.txt", "rb") as f:
		result = f.read(1)
		if result:
			return (None,"Compile Error", open("/compile_result.txt", "r").read())

	with open("/time_result.txt", "r") as f:
		result = f.read()
		if not result:
			return (None,"Time Limit Exceeded", "")
		if "Segmentation fault" in result:
			return (None,"Run Time Error", "")

		detail = result
		time_used = float(result.split(" seconds time elapsed")[0].split(" ")[-1])

	with open("/output_check.txt", "rb") as f:
		result = f.read(1)
		if result:
			return (None,"No Output", detail)

	with open("/answer_result.txt", "rb") as f:
		result = f.read(1)
		if result:
			return (None,"Wrong Answer", detail)

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
		result_set[task_id]["time"] = result[0]
		result_set[task_id]["status"] = result[1]
		result_set[task_id]["detail"] = result[2]

if __name__ == "__main__":
	init()
	judger_thread = threading.Thread(target=judger)
	judger_thread.start()
	app.debug = True
	app.run(host='0.0.0.0', port=5001)
