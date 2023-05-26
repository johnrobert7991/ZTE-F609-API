from router import Router
from flask import Flask, request, abort, Response
import threading
import time

## Init Flask App
app = Flask(__name__)

@app.before_request
def loginRouter() :
    global MyRouter
    MyRouter = Router("192.168.1.1", "admin", "Telkomdso123")

@app.route('/ban_list', methods=['GET'])
def ban_list() :
    data = request.values.to_dict()

    if data :
        name = data.get("name")
        if name :
            return MyRouter.getBanList(name)
        abort(400)
        abort(Response("Query Parameter Not Allowed!"))

    return MyRouter.getBanList()

@app.route('/ban', methods=['GET'])
def ban() :
    data = request.values.to_dict()

    if data :
        name = data.get("name")
        macId = data.get("mac")
        if all([name, macId]) :
            return MyRouter.ban(name, macId)

    abort(400)
    abort(Response("Query Parameter Not Allowed!"))

@app.route('/unban', methods=['GET'])
def unban() :
    data = request.values.to_dict()

    if data :
        name = data.get("name")
        macId = data.get("mac")
        if name :
            return MyRouter.unban("name", name)
        elif macId :
            return MyRouter.unban("mac", macId)

    abort(400)
    abort(Response("Query Parameter Not Allowed!"))


if __name__ == "__main__" :
    app.run(debug=True, host="0.0.0.0")
