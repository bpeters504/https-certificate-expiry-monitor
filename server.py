from flask import Flask, render_template, request
import checkcertificates
from waitress import serve
import os
import configparser

app = Flask(__name__)
config = configparser.ConfigParser()
endpoints = []

# Read the application version from the version file
def get_app_version():
    version_file_path = 'config/version'
    if os.path.exists(version_file_path):
        with open(version_file_path, 'r') as version_file:
            return version_file.read().strip()
    return "Unknown Version"


@app.route('/')
@app.route('/index')
def index():
    endpoints = [endpoint.strip() for endpoint in config["default"]['endpoints'].split(',')]
    data = checkcertificates.get_certificates_data(endpoints)
    app_version = get_app_version()  # Get the application version
    return render_template('index.html', data=data, app_version=app_version)



if __name__ == '__main__':
    if not os.path.exists('config'):
        os.makedirs('config')
    if not os.path.exists('config/config.ini'):
        with open('config.ini.default', 'r') as default_file:
            with open('config/config.ini', 'w') as config_file:
                config_file.write(default_file.read())
    config.read('config/config.ini')
    port = config['server']['port']
    serve(app, host="0.0.0.0", port=port)
