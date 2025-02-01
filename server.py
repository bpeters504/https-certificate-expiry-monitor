from flask import Flask, render_template, request
import checkcertificates
from waitress import serve
import os
import configparser

app = Flask(__name__)
config = configparser.ConfigParser()
endpoints = []

@app.route('/')
@app.route('/index')
def index():
    endpoints = [endpoint.strip() for endpoint in config["default"]['endpoints'].split(',')]
    data = checkcertificates.get_certificates_data(endpoints)
    return render_template('index.html', data=data)



if __name__ == '__main__':
    config.read('config.ini')
    port = config['server']['port']
    serve(app, host="0.0.0.0", port=port)
