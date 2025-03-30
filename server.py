from flask import Flask, render_template, request, redirect, url_for
import checkcertificates
from waitress import serve
import os
import configparser
import sqlite3
from datetime import datetime


app = Flask(__name__)
config = configparser.ConfigParser()
default_endpoints = ["latenightlinux.com", "jupiterbroadcasting.com:443", "colonyevents.com"]

# make a backup of config.ini
def backup_config():
    if os.path.exists('config/config.ini'):
        config.read('config/config.ini')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        os.rename('config/config.ini', f'config/config_{timestamp}.ini.bak')
        with open('config/config.ini', 'w') as configfile:
            config.write(configfile)


# Read the application version from the version file
def get_app_version():
    version_file_path = 'config/version'
    if os.path.exists(version_file_path):
        with open(version_file_path, 'r') as version_file:
            return version_file.read().strip()
    return "Unknown Version"

# read the endpoints from the database
def get_endpoints():
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('SELECT host, port, id FROM endpoints')
    endpoints = cursor.fetchall()
    conn.close()
    return endpoints

@app.route('/add_endpoint', methods=['POST'])
def add_endpoint():
    host = request.form['host']
    port = request.form['port']
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO endpoints (host, port) VALUES (?, ?)', (host, port))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_endpoints'))

@app.route('/update_endpoint/<int:id>', methods=['POST'])
def update_endpoint(id):
    host = request.form['host']
    port = request.form['port']
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE endpoints SET host = ?, port = ? WHERE id = ?', (host, port, id))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_endpoints'))

@app.route('/delete_endpoint/<int:id>', methods=['GET'])
def delete_endpoint(id):
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM endpoints WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_endpoints'))

@app.route('/edit_endpoints')
def edit_endpoints():
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, host, port FROM endpoints')
    endpoints = [{'id': row[0], 'host': row[1], 'port': row[2]} for row in cursor.fetchall()]
    conn.close()
    app_version = get_app_version()
    return render_template('edit_endpoints.html', endpoints=endpoints, app_version=app_version)


@app.route('/')
@app.route('/index')
def index():
    endpoints = get_endpoints()
    endpoints = [f"{host}:{port}:{id}" for host, port, id in endpoints]  # Include all three values
    data = checkcertificates.get_certificates_data(endpoints)
    app_version = get_app_version()  # Get the application version
    return render_template('index.html', data=data, app_version=app_version, warn_days=int(warn_days), critical_days=int(critical_days))

# create sqlite3 database and table
def init_db(option):
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT,
            port TEXT
        )
    ''')

    # if option == "default" add the default endpoints to the database and copy the config.ini.default to config.ini
    if option == "default":
        for endpoint in default_endpoints:
            host, port = (endpoint.split(":") + ["443"])[:2]  # Default to port 443 if not specified
            add_endpoint(host, port)
        # copy config.ini.default to config.ini
        with open('config.ini.default', 'r') as default_file:
            with open('config/config.ini', 'w') as config_file:
                config_file.write(default_file.read())
        # comment out the endpoints in the config.ini file
        config.read('config/config.ini')
        config['default']['endpoints'] = ""
        with open('config/config.ini', 'w') as configfile:
            config.write(configfile)

    # if option == "custom" read the config.ini file and add the endpoints to the database
    if option == "custom":
        config.read('config/config.ini')
        for endpoint in config['default']['endpoints'].split(','):
            host, port = (str(endpoint).split(":") + ["443"])[:2]  # Default to port 443 if not specified
            host, port = host.strip(), port.strip()  # Strip whitespace from host and port
            add_endpoint(host, port)
        # comment out the endpoints in the config.ini file
        config['default']['endpoints'] = ""
        with open('config/config.ini', 'w') as configfile:
            config.write(configfile)

def remove_endpoint(id):
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM endpoints WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def add_endpoint(host, port):
    conn = sqlite3.connect('config/endpoints.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO endpoints (host, port) VALUES (?, ?)', (host, port))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    if not os.path.exists('config'):
        os.makedirs('config')
    # if config/config.ini exists and contains endpoints and the endpoints.db file does not exist initialize the database with the endpoints from config.ini
    if os.path.exists('config/config.ini') and not os.path.exists('config/endpoints.db'):
        init_db("custom")
    # if config/config.ini does not exist and the endpoints.db file does not exist initialize the database with the default endpoints
    if not os.path.exists('config/config.ini') and not os.path.exists('config/endpoints.db'):
        init_db("default")
    config.read('config/config.ini')
    warn_days = config['default']['warn_days']
    critical_days = config['default']['critical_days']
    port = config['server']['port']
    serve(app, host="0.0.0.0", port=port)
