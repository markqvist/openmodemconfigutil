import requests
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import webview
import random
import os
import sys


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests threaded via mixin"""

class appRequestHandler(BaseHTTPRequestHandler):
	def json_headers(request):
		request.send_response(200)
		request.send_header("Content-Type", "text/json")
		request.end_headers()

	def do_GET(request):
		if (request.path == "/"):
			request.send_response(302)
			request.send_header("Location", "/app/")
			request.end_headers()

		if (request.path == "/favicon.ico"):
			request.path = "/app/favicon.ico"

		if (request.path.startswith("/app/")):
			path = request.path.replace("/app/", "")
			file = None
			print(path)

			if (path == ""):
				file = "index.html"
			else:
				file = path

			base, extension = os.path.splitext(file)
			request.send_response(200)
			
			if (extension == ".css"):
				request.send_header("Content-Type", "text/css")
			if (extension == ".js"):
				request.send_header("Content-Type", "text/javascript")
			if (extension == ".html"):
				request.send_header("Content-Type", "text/html")

			request.end_headers()

			requestpath = "./public/"+file
			print(requestpath)

			fh = open(requestpath, "rb")
			request.wfile.write(fh.read())
			fh.close()

def get_port():
	return random.randrange(40000,49999,1)

def start_server():
	cwd = os.getcwd()
	print("CWD is: "+str(cwd))
	retries = 0
	server_started = False

	while not server_started and retries < 100:
		try:	
			port = get_port()
			server_address = ("127.0.0.1", port)
			httpd = ThreadedHTTPServer(server_address, appRequestHandler)
			threading.Thread(target=httpd.serve_forever).start()
			print("Server running on port "+str(port))
			retval = webview.create_window('App Name', 'http://localhost:'+str(port)+'/', width=575, height=600)
			if retval == None:
				os._exit(0)

		except Exception as e:
			retries += 1

	print("Could not start server, exiting")
	exit()


def main():
	start_server()

if __name__ == "__main__":
	main()